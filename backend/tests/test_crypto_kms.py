"""CMEK external KMS providers — wrap/unwrap round-trips (Sprint 15 Task 6).

The cloud SDKs (boto3 / google-cloud-kms / azure-keyvault-keys) are NOT a hard
dependency — providers import them lazily inside ``_client``. These tests mock
that seam so they exercise the wrap/unwrap contract without any SDK installed,
and confirm the ``app`` KEK fallback still works.
"""

from __future__ import annotations

import base64
from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet

from backend.app.services.crypto import (
    AppKEKProvider,
    AwsKmsProvider,
    AzureKmsProvider,
    GcpKmsProvider,
    KmsError,
    get_kek_provider,
    rewrap_dek,
)


def test_get_kek_provider_selection() -> None:
    assert get_kek_provider("app") is AppKEKProvider
    assert get_kek_provider("aws") is AwsKmsProvider
    assert get_kek_provider("gcp") is GcpKmsProvider
    assert get_kek_provider("azure") is AzureKmsProvider
    assert get_kek_provider("APP") is AppKEKProvider  # case-insensitive
    assert get_kek_provider(None) is AppKEKProvider  # default


def test_get_kek_provider_unknown_raises() -> None:
    with pytest.raises(KmsError):
        get_kek_provider("hashicorp-vault")


def test_app_provider_roundtrip() -> None:
    dek = Fernet.generate_key()
    wrapped = AppKEKProvider.wrap_dek(dek)
    assert isinstance(wrapped, str)
    assert AppKEKProvider.unwrap_dek(wrapped) == dek


def test_app_validate_key_always_true() -> None:
    assert AppKEKProvider.validate_key(None) is True


def test_aws_provider_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    dek = Fernet.generate_key()
    fake = MagicMock()
    fake.encrypt.return_value = {"CiphertextBlob": b"AWS_CIPHER"}
    fake.decrypt.return_value = {"Plaintext": dek}
    monkeypatch.setattr(AwsKmsProvider, "_client", staticmethod(lambda: fake))

    arn = "arn:aws:kms:eu-west-1:123:key/abc"
    wrapped = AwsKmsProvider.wrap_dek(dek, arn)
    assert wrapped == base64.b64encode(b"AWS_CIPHER").decode()
    assert AwsKmsProvider.unwrap_dek(wrapped, arn) == dek
    assert fake.encrypt.call_args.kwargs["KeyId"] == arn
    assert fake.encrypt.call_args.kwargs["Plaintext"] == dek


def test_gcp_provider_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    dek = Fernet.generate_key()
    fake = MagicMock()
    fake.encrypt.return_value = MagicMock(ciphertext=b"GCP_CIPHER")
    fake.decrypt.return_value = MagicMock(plaintext=dek)
    monkeypatch.setattr(GcpKmsProvider, "_client", staticmethod(lambda: fake))

    key = "projects/p/locations/eu/keyRings/r/cryptoKeys/k"
    wrapped = GcpKmsProvider.wrap_dek(dek, key)
    assert wrapped == base64.b64encode(b"GCP_CIPHER").decode()
    assert GcpKmsProvider.unwrap_dek(wrapped, key) == dek


def test_azure_provider_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    dek = Fernet.generate_key()
    fake = MagicMock()
    fake.wrap_key.return_value = MagicMock(encrypted_key=b"AZ_CIPHER")
    fake.unwrap_key.return_value = MagicMock(key=dek)
    monkeypatch.setattr(AzureKmsProvider, "_client", staticmethod(lambda key_uri: fake))

    key = "https://v.vault.azure.net/keys/k/ver"
    wrapped = AzureKmsProvider.wrap_dek(dek, key)
    assert wrapped == base64.b64encode(b"AZ_CIPHER").decode()
    assert AzureKmsProvider.unwrap_dek(wrapped, key) == dek


def test_validate_key_detects_bad_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    # decrypt returns the wrong plaintext → validation must fail (not raise).
    fake = MagicMock()
    fake.encrypt.return_value = {"CiphertextBlob": b"X"}
    fake.decrypt.return_value = {"Plaintext": b"not-the-dek"}
    monkeypatch.setattr(AwsKmsProvider, "_client", staticmethod(lambda: fake))
    assert AwsKmsProvider.validate_key("arn:aws:kms:eu-west-1:123:key/abc") is False


def test_rewrap_dek_app_to_aws(monkeypatch: pytest.MonkeyPatch) -> None:
    dek = Fernet.generate_key()
    app_wrapped = AppKEKProvider.wrap_dek(dek)

    fake = MagicMock()
    fake.encrypt.return_value = {"CiphertextBlob": b"REWRAP_BLOB"}
    fake.decrypt.return_value = {"Plaintext": dek}
    monkeypatch.setattr(AwsKmsProvider, "_client", staticmethod(lambda: fake))

    new_wrapped = rewrap_dek(
        app_wrapped,
        old_provider="app",
        old_key_uri=None,
        new_provider="aws",
        new_key_uri="arn:aws:kms:eu-west-1:123:key/abc",
    )
    # The DEK survives the re-wrap: unwrapping the new blob yields the original.
    assert AwsKmsProvider.unwrap_dek(new_wrapped, "arn:aws:kms:eu-west-1:123:key/abc") == dek
