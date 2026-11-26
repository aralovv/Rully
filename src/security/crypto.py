"""
Cryptographic Utilities for Admin Control Panel and MTProto Payment System.
Provides:
- Argon2id password hashing and verification
- Fernet/AES symmetric encryption for payment card numbers and MTProto sessions
- Cryptographically secure OTP and session token generation
"""

import os
import re
import hmac
import base64
import secrets
import hashlib
from typing import Tuple
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# Initialize Argon2id password hasher (RFC 9106 recommended parameters)
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16
)

_DEV_FALLBACK_SECRET = "rully_dev_only_non_prod_secret_key_change_in_prod_2026"
_LEGACY_PLAIN_DIGITS_RE = re.compile(r"^\d{8,24}$")


def _is_prod_runtime() -> bool:
    return (
        os.getenv("ENVIRONMENT", "").strip().lower() in ("production", "prod", "standalone-cloud")
        or bool(os.getenv("VERCEL"))
        or bool(os.getenv("RENDER"))
    )


def _get_secret_key() -> str:
    raw = os.getenv("SECRET_KEY", "").strip()
    if raw:
        return raw
    if _is_prod_runtime() and "PYTEST_CURRENT_TEST" not in os.environ:
        raise RuntimeError("SECURITY CRITICAL: SECRET_KEY environment variable is required in production.")
    return _DEV_FALLBACK_SECRET


def _get_cipher() -> Fernet:
    fernet_key = base64.urlsafe_b64encode(hashlib.sha256(_get_secret_key().encode("utf-8")).digest())
    return Fernet(fernet_key)


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id."""
    if not password:
        raise ValueError("Password cannot be empty.")
    return _hasher.hash(password)


def verify_password(hash_str: str, password: str) -> bool:
    """Verifies a plaintext password against an Argon2id hash."""
    if not hash_str or not password:
        return False
    try:
        return _hasher.verify(hash_str, password)
    except (VerifyMismatchError, Exception):
        return False


def encrypt_data(data: str) -> str:
    """Encrypts sensitive plaintext string using AES-CBC/Fernet."""
    if not data:
        return ""
    encrypted_bytes = _get_cipher().encrypt(data.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')


def decrypt_data(encrypted_str: str) -> str:
    """Decrypts ciphertext string back to plaintext, failing closed on invalid ciphertext."""
    if not encrypted_str:
        return ""
    text = str(encrypted_str).strip()
    try:
        decrypted_bytes = _get_cipher().decrypt(text.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except Exception as exc:
        # Allow legacy unencrypted numeric PAN only if purely digits (never fake-decrypt 'ENC:' or corrupted Fernet tokens)
        if _LEGACY_PLAIN_DIGITS_RE.fullmatch(text):
            return text
        raise ValueError("Decryption failed: invalid ciphertext or SECRET_KEY mismatch") from exc


def generate_secure_otp(length: int = 6) -> str:
    """Generates a cryptographically random numeric OTP (default 6 digits)."""
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_otp(otp: str, salt: str = "rully_otp_salt_2026") -> str:
    """Creates an HMAC-SHA256 digest of the OTP keyed by SECRET_KEY. Plaintext OTPs are NEVER stored."""
    key = _get_secret_key().encode("utf-8")
    msg = f"{salt}:{otp}".encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_otp_hash(otp: str, stored_hash: str, salt: str = "rully_otp_salt_2026") -> bool:
    """Compares an OTP against the stored hash using constant-time comparison."""
    computed = hash_otp(otp, salt)
    return secrets.compare_digest(computed, stored_hash)


def generate_session_token() -> str:
    """Generates a 64-character cryptographically secure hex session token."""
    return secrets.token_hex(32)


def mask_card_number(card_number: str) -> Tuple[str, str]:
    """
    Given a full card number (e.g. '9860123456785370'),
    returns (masked_number, suffix):
    e.g. ('9860 **** **** 5370', '5370')
    """
    clean = "".join(c for c in card_number if c.isdigit())
    if len(clean) >= 16:
        first4 = clean[:4]
        suffix = clean[-4:]
        masked = f"{first4} **** **** {suffix}"
        return masked, suffix
    elif len(clean) >= 4:
        suffix = clean[-4:]
        masked = f"**** **** **** {suffix}"
        return masked, suffix
    else:
        return "****", clean
