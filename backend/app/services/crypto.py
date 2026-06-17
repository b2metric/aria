import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def get_fernet() -> Fernet:
    """Get Fernet instance based on SECRET_KEY."""
    # Use ARIA_SECRET_KEY, fallback to a default for local dev
    secret_key = os.getenv("ARIA_SECRET_KEY", "fallback_secret_key_for_dev_only_change_in_prod")
    
    # We need exactly 32 url-safe base64-encoded bytes.
    # So we derive it using PBKDF2.
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"aria_salt",
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    return Fernet(key)

def encrypt_password(password: str) -> str:
    """Encrypt a plaintext password."""
    if not password:
        return ""
    f = get_fernet()
    return f.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    """Decrypt an encrypted password."""
    if not encrypted_password:
        return ""
    try:
        f = get_fernet()
        return f.decrypt(encrypted_password.encode()).decode()
    except Exception:
        # If decryption fails (e.g., old plaintext passwords), return as is
        # This provides a fallback migration path.
        return encrypted_password
