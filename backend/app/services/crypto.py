import base64
import logging
import uuid

from cachetools import TTLCache
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import DEV_FALLBACK_SECRET, get_settings

log = logging.getLogger(__name__)

# DEK cache: customer_id -> (Fernet instance)
# TTL = 300 seconds (5 mins)
_dek_cache = TTLCache(maxsize=1000, ttl=300)


def evict_dek_cache(customer_id: uuid.UUID | str) -> None:
    """Drop a customer's cached DEK so the next access re-reads the config.

    Call after a provider switch / key rotation re-wraps the stored DEK.
    """
    _dek_cache.pop(str(customer_id), None)


class KmsError(Exception):
    """Raised when a KEK provider is unknown or an external KMS call fails."""


class KEKProvider:
    """Base Key-Encryption-Key provider.

    A KEK wraps (encrypts) and unwraps (decrypts) each customer's Data
    Encryption Key (DEK). ``app`` uses a local Fernet KEK; the cloud providers
    delegate the wrap/unwrap to an external KMS. ``encrypted_dek`` is always a
    ``str`` (base64 for the cloud providers); ``raw_dek`` is the Fernet key.
    """

    @classmethod
    def wrap_dek(cls, raw_dek: bytes, key_uri: str | None = None) -> str:
        raise NotImplementedError

    @classmethod
    def unwrap_dek(cls, encrypted_dek: str, key_uri: str | None = None) -> bytes:
        raise NotImplementedError

    @classmethod
    def validate_key(cls, key_uri: str | None = None) -> bool:
        """Fail-fast reachability check: a wrap→unwrap round-trip must match.

        Returns False (never raises) so callers can surface a clean error.
        """
        try:
            probe = Fernet.generate_key()
            return cls.unwrap_dek(cls.wrap_dek(probe, key_uri), key_uri) == probe
        except Exception as e:  # noqa: BLE001 — reachability probe, any failure = invalid
            log.warning("KEK validate failed (provider=%s, key=%s): %s", cls.__name__, key_uri, e)
            return False


class AppKEKProvider(KEKProvider):
    """App-level KEK (Key Encryption Key) using the system ARIA_SECRET_KEY."""

    @classmethod
    def get_kek_fernet(cls) -> Fernet:
        settings = get_settings()
        secret_key = settings.aria_secret_key or DEV_FALLBACK_SECRET
        # Fail loud rather than silently wrap every customer DB password with a key
        # derived from the public dev fallback. validate_runtime catches this at boot;
        # this is defense-in-depth for any path that skips the startup gate.
        if secret_key == DEV_FALLBACK_SECRET and not settings.is_development:
            raise RuntimeError(
                "ARIA_SECRET_KEY is unset (or the dev default) in a non-development "
                "environment; refusing to derive the master KEK from the well-known "
                "fallback. Set a strong ARIA_SECRET_KEY."
            )
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"aria_salt",  # static by design — changing it would orphan existing DEKs
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
        return Fernet(key)

    @classmethod
    def unwrap_dek(cls, encrypted_dek: str, key_uri: str | None = None) -> bytes:
        return cls.get_kek_fernet().decrypt(encrypted_dek.encode())

    @classmethod
    def wrap_dek(cls, raw_dek: bytes, key_uri: str | None = None) -> str:
        return cls.get_kek_fernet().encrypt(raw_dek).decode()

    @classmethod
    def validate_key(cls, key_uri: str | None = None) -> bool:
        # The app KEK is always available (derived from ARIA_SECRET_KEY).
        return True


class AwsKmsProvider(KEKProvider):
    """Wrap/unwrap the DEK via AWS KMS (``key_uri`` = key ARN or key-id)."""

    @staticmethod
    def _client():  # pragma: no cover - thin SDK seam, patched in tests
        try:
            import boto3
        except ImportError as e:  # noqa: TRY003
            raise KmsError("boto3 is required for the AWS KMS provider") from e
        return boto3.client("kms")

    @classmethod
    def wrap_dek(cls, raw_dek: bytes, key_uri: str | None = None) -> str:
        if not key_uri:
            raise KmsError("AWS KMS requires a key ARN/URI")
        resp = cls._client().encrypt(KeyId=key_uri, Plaintext=raw_dek)
        return base64.b64encode(resp["CiphertextBlob"]).decode()

    @classmethod
    def unwrap_dek(cls, encrypted_dek: str, key_uri: str | None = None) -> bytes:
        resp = cls._client().decrypt(CiphertextBlob=base64.b64decode(encrypted_dek), KeyId=key_uri)
        return resp["Plaintext"]


class GcpKmsProvider(KEKProvider):
    """Wrap/unwrap the DEK via Google Cloud KMS (``key_uri`` = cryptoKey path)."""

    @staticmethod
    def _client():  # pragma: no cover - thin SDK seam, patched in tests
        try:
            from google.cloud import kms
        except ImportError as e:  # noqa: TRY003
            raise KmsError("google-cloud-kms is required for the GCP KMS provider") from e
        return kms.KeyManagementServiceClient()

    @classmethod
    def wrap_dek(cls, raw_dek: bytes, key_uri: str | None = None) -> str:
        if not key_uri:
            raise KmsError("GCP KMS requires a cryptoKey resource URI")
        resp = cls._client().encrypt(request={"name": key_uri, "plaintext": raw_dek})
        return base64.b64encode(resp.ciphertext).decode()

    @classmethod
    def unwrap_dek(cls, encrypted_dek: str, key_uri: str | None = None) -> bytes:
        resp = cls._client().decrypt(
            request={"name": key_uri, "ciphertext": base64.b64decode(encrypted_dek)}
        )
        return resp.plaintext


class AzureKmsProvider(KEKProvider):
    """Wrap/unwrap the DEK via Azure Key Vault (``key_uri`` = key identifier URL)."""

    _ALGORITHM = "RSA-OAEP-256"

    @staticmethod
    def _client(key_uri: str):  # pragma: no cover - thin SDK seam, patched in tests
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.keys.crypto import CryptographyClient
        except ImportError as e:  # noqa: TRY003
            raise KmsError("azure-keyvault-keys is required for the Azure KMS provider") from e
        return CryptographyClient(key_uri, credential=DefaultAzureCredential())

    @classmethod
    def wrap_dek(cls, raw_dek: bytes, key_uri: str | None = None) -> str:
        if not key_uri:
            raise KmsError("Azure Key Vault requires a key identifier URL")
        result = cls._client(key_uri).wrap_key(cls._ALGORITHM, raw_dek)
        return base64.b64encode(result.encrypted_key).decode()

    @classmethod
    def unwrap_dek(cls, encrypted_dek: str, key_uri: str | None = None) -> bytes:
        result = cls._client(key_uri).unwrap_key(cls._ALGORITHM, base64.b64decode(encrypted_dek))
        return result.key


_PROVIDERS: dict[str, type[KEKProvider]] = {
    "app": AppKEKProvider,
    "aws": AwsKmsProvider,
    "gcp": GcpKmsProvider,
    "azure": AzureKmsProvider,
}


def get_kek_provider(provider: str | None) -> type[KEKProvider]:
    """Resolve a KEK provider class by name (defaults to ``app``)."""
    cls = _PROVIDERS.get((provider or "app").lower())
    if cls is None:
        raise KmsError(f"Unsupported KEK provider: {provider}")
    return cls


def rewrap_dek(
    encrypted_dek: str,
    *,
    old_provider: str | None,
    old_key_uri: str | None,
    new_provider: str | None,
    new_key_uri: str | None,
) -> str:
    """Re-wrap a DEK under a new provider/key (used for provider switch + rotation).

    Unwraps with the current KEK and re-wraps with the target KEK, so existing
    ciphertext stays decryptable after the configuration change.
    """
    raw_dek = get_kek_provider(old_provider).unwrap_dek(encrypted_dek, old_key_uri)
    return get_kek_provider(new_provider).wrap_dek(raw_dek, new_key_uri)


def get_fernet_for_customer(customer_id: uuid.UUID | str = None, connection=None) -> Fernet:
    """Get the Fernet instance using the customer's DEK, or fallback to global KEK."""
    if not customer_id:
        return AppKEKProvider.get_kek_fernet()

    cust_id_str = str(customer_id)
    if cust_id_str in _dek_cache:
        return _dek_cache[cust_id_str]

    if not connection:
        # If no DB connection provided, fallback to global KEK
        log.warning(
            "No connection provided to fetch DEK for %s, falling back to global KEK", cust_id_str
        )
        return AppKEKProvider.get_kek_fernet()

    try:
        # Fetch DEK from DB synchronously using the provided connection
        result = connection.execute(
            text(
                "SELECT provider, key_uri, encrypted_dek FROM customer_key_configs WHERE customer_id = :cid AND is_active = true"
            ),
            {"cid": cust_id_str},
        ).fetchone()

        if result:
            provider, key_uri, encrypted_dek = result
            raw_dek = get_kek_provider(provider).unwrap_dek(encrypted_dek, key_uri)
            f = Fernet(raw_dek)
            _dek_cache[cust_id_str] = f
            return f
    except Exception as e:
        log.error("Failed to fetch DEK for %s: %s", cust_id_str, e)

    # Fallback if no config or error
    return AppKEKProvider.get_kek_fernet()


def encrypt_password(password: str, customer_id=None, connection=None) -> str:
    """Encrypt a plaintext password."""
    if not password:
        return ""
    f = get_fernet_for_customer(customer_id, connection)
    return f.encrypt(password.encode()).decode()


def decrypt_password(encrypted_password: str, customer_id=None, connection=None) -> str:
    """Decrypt an encrypted password."""
    if not encrypted_password:
        return ""
    try:
        f = get_fernet_for_customer(customer_id, connection)
        return f.decrypt(encrypted_password.encode()).decode()
    except Exception:
        # Fallback migration path for old passwords
        return encrypted_password


async def async_get_fernet_for_customer(
    customer_id: uuid.UUID | str = None, session: AsyncSession = None
) -> Fernet:
    if not customer_id:
        return AppKEKProvider.get_kek_fernet()

    cust_id_str = str(customer_id)
    if cust_id_str in _dek_cache:
        return _dek_cache[cust_id_str]

    if not session:
        log.warning(
            "No session provided to fetch DEK for %s, falling back to global KEK", cust_id_str
        )
        return AppKEKProvider.get_kek_fernet()

    try:
        result = await session.execute(
            text(
                "SELECT provider, key_uri, encrypted_dek FROM customer_key_configs WHERE customer_id = :cid AND is_active = true"
            ),
            {"cid": cust_id_str},
        )
        row = result.fetchone()

        if row:
            provider, key_uri, encrypted_dek = row
            raw_dek = get_kek_provider(provider).unwrap_dek(encrypted_dek, key_uri)
            f = Fernet(raw_dek)
            _dek_cache[cust_id_str] = f
            return f
    except Exception as e:
        log.error("Failed to fetch DEK async for %s: %s", cust_id_str, e)

    return AppKEKProvider.get_kek_fernet()


async def async_encrypt_password(
    password: str, customer_id=None, session: AsyncSession = None
) -> str:
    if not password:
        return ""
    f = await async_get_fernet_for_customer(customer_id, session)
    return f.encrypt(password.encode()).decode()


async def async_decrypt_password(
    encrypted_password: str, customer_id=None, session: AsyncSession = None
) -> str:
    if not encrypted_password:
        return ""
    try:
        f = await async_get_fernet_for_customer(customer_id, session)
        return f.decrypt(encrypted_password.encode()).decode()
    except Exception:
        return encrypted_password
