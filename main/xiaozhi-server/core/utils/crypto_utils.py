import os
import base64
import hashlib
from cryptography.fernet import Fernet


def _get_fernet(key: str) -> Fernet:
    key_bytes = hashlib.sha256(key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def encrypt(data: bytes, key: str) -> bytes:
    """Encrypt bytes using the provided key."""
    f = _get_fernet(key)
    return f.encrypt(data)


def decrypt(data: bytes, key: str) -> bytes:
    """Decrypt bytes using the provided key."""
    f = _get_fernet(key)
    return f.decrypt(data)
