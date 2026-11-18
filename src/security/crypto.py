"""
Cryptographic Utilities for Admin Control Panel and MTProto Payment System.
Provides:
- Argon2id password hashing and verification
- Fernet/AES symmetric encryption for payment card numbers and MTProto sessions
- Cryptographically secure OTP and session token generation
"""

import os
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

# Encryption key for sensitive data (cards, sessions)
_SECRET_KEY = os.getenv("SECRET_KEY", "rully_secure_secret_key_32_bytes_minimum_for_crypto_production_2026")
# Generate a deterministic 32-byte url-safe base64 key from _SECRET_KEY
_fernet_key = base64.urlsafe_b64encode(hashlib.sha256(_SECRET_KEY.encode()).digest())
_cipher = Fernet(_fernet_key)


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(hash_str: str, password: str) -> bool:
    """Verifies a plaintext password against an Argon2id hash."""
    try:
        return _hasher.verify(hash_str, password)
    except (VerifyMismatchError, Exception):
        return False


def encrypt_data(data: str) -> str:
    """Encrypts sensitive plaintext string using AES-CBC/Fernet."""
    if not data:
        return ""
    encrypted_bytes = _cipher.encrypt(data.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')


def decrypt_data(encrypted_str: str) -> str:
    """Decrypts ciphertext string back to plaintext."""
    if not encrypted_str:
        return ""
    try:
        decrypted_bytes = _cipher.decrypt(encrypted_str.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except Exception:
        # Fallback if unencrypted / legacy format
        return encrypted_str


def generate_secure_otp(length: int = 6) -> str:
    """Generates a cryptographically random numeric OTP (default 6 digits)."""
    # Range 100000 to 999999
    return "".join(secrets.choice("0123456789") for _ in range(length))


def hash_otp(otp: str, salt: str = "rully_otp_salt_2026") -> str:
    """Creates a SHA-256 hash of the OTP with salt. OTP values are NEVER stored in plaintext."""
    return hashlib.sha256(f"{salt}:{otp}".encode('utf-8')).hexdigest()


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
