import base64
import logging
import os
import uuid

from cachetools import TTLCache
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# DEK cache: customer_id -> (Fernet instance)
# TTL = 300 seconds (5 mins)
_dek_cache = TTLCache(maxsize=1000, ttl=300)


class AppKEKProvider:
    """App-level KEK (Key Encryption Key) using the system ARIA_SECRET_KEY."""

    @classmethod
    def get_kek_fernet(cls) -> Fernet:
        secret_key = os.getenv("ARIA_SECRET_KEY", "fallback_secret_key_for_dev_only_change_in_prod")
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"aria_salt",
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
        return Fernet(key)

    @classmethod
    def unwrap_dek(cls, encrypted_dek: str, key_uri: str = None) -> bytes:
        return cls.get_kek_fernet().decrypt(encrypted_dek.encode())

    @classmethod
    def wrap_dek(cls, raw_dek: bytes, key_uri: str = None) -> str:
        return cls.get_kek_fernet().encrypt(raw_dek).decode()


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
            if provider == "app":
                raw_dek = AppKEKProvider.unwrap_dek(encrypted_dek, key_uri)
                f = Fernet(raw_dek)
                _dek_cache[cust_id_str] = f
                return f
            else:
                log.error("Unsupported KEK provider: %s", provider)
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
            if provider == "app":
                raw_dek = AppKEKProvider.unwrap_dek(encrypted_dek, key_uri)
                f = Fernet(raw_dek)
                _dek_cache[cust_id_str] = f
                return f
            else:
                log.error("Unsupported KEK provider: %s", provider)
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
