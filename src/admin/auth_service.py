"""
Admin Authentication, OTP Verification, and Session Security Service.
Implements:
- Argon2id password verification
- Multi-factor Telegram OTP challenge lifecycle
- Brute-force protection and rate limiting
- Secure session tokens and rotation
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from dotenv import load_dotenv

from src.security.crypto import (
    hash_password, verify_password, generate_secure_otp,
    hash_otp, verify_otp_hash, generate_session_token
)
from src.security.telegram_notifier import send_admin_otp

load_dotenv()
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")
DEFAULT_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "Anvarjon")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Anvarjon2007!@")
DEFAULT_ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "1956239701"))
SESSION_DURATION_HOURS = 12
OTP_EXPIRY_MINUTES = 5
MAX_OTP_ATTEMPTS = 5

# In-memory rate limiter for failed login attempts by IP
_login_failures: Dict[str, list] = {}


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def ensure_admin_user_exists() -> Dict[str, Any]:
    """Ensures the primary admin user exists in admin_users table."""
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM admin_users WHERE username = ?", (DEFAULT_ADMIN_USERNAME,))
        row = c.fetchone()
        if not row:
            hashed_pw = hash_password(DEFAULT_ADMIN_PASSWORD)
            now_str = datetime.utcnow().isoformat()
            c.execute("""
                INSERT INTO admin_users (username, password_hash, telegram_id, role, is_active, created_at)
                VALUES (?, ?, ?, 'SUPERADMIN', 1, ?)
            """, (DEFAULT_ADMIN_USERNAME, hashed_pw, DEFAULT_ADMIN_TELEGRAM_ID, now_str))
            conn.commit()
            c.execute("SELECT * FROM admin_users WHERE username = ?", (DEFAULT_ADMIN_USERNAME,))
            row = c.fetchone()
        return dict(row)


def is_rate_limited(ip_address: str, max_attempts: int = 8, window_minutes: int = 15) -> bool:
    """Checks if IP is temporarily blocked due to repeated failed login attempts."""
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=window_minutes)
    attempts = _login_failures.get(ip_address, [])
    # Keep only attempts in recent window
    valid_attempts = [t for t in attempts if t > window_start]
    _login_failures[ip_address] = valid_attempts
    return len(valid_attempts) >= max_attempts


def record_failed_attempt(ip_address: str):
    """Records a failed authentication attempt."""
    now = datetime.utcnow()
    if ip_address not in _login_failures:
        _login_failures[ip_address] = []
    _login_failures[ip_address].append(now)


def clear_failed_attempts(ip_address: str):
    """Clears failed attempts for an IP upon successful authentication."""
    if ip_address in _login_failures:
        _login_failures.pop(ip_address, None)


async def initiate_admin_login(username: str, password: str, ip_address: str = "", user_agent: str = "") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Step 1 of Admin Authentication:
    Verifies username and password, then generates and sends Telegram OTP.
    Returns (success, message, result_data).
    """
    if is_rate_limited(ip_address):
        return False, "Juda ko‘p urinishlar qilindi. Iltimos, 15 daqiqadan so‘ng qayta urinib ko‘ring.", None

    admin = ensure_admin_user_exists()

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM admin_users WHERE username = ? AND is_active = 1", (username,))
        user_row = c.fetchone()

        if not user_row or not verify_password(user_row["password_hash"], password):
            record_failed_attempt(ip_address)
            # Log failed login attempt
            now_str = datetime.utcnow().isoformat()
            c.execute("""
                INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
                VALUES (0, 'LOGIN_FAILED', ?, ?)
            """, (f"Username: {username}, IP: {ip_address}", now_str))
            conn.commit()
            return False, "Foydalanuvchi nomi yoki parol noto‘g‘ri.", None

        # Password verified! Clear rate limit for this IP
        clear_failed_attempts(ip_address)

        admin_id = user_row["id"]
        telegram_id = user_row["telegram_id"]

        # Invalidate previous unexpired OTP challenges for this admin
        c.execute("UPDATE admin_otp_challenges SET is_used = 1 WHERE admin_id = ? AND is_used = 0", (admin_id,))

        # Generate new random OTP
        otp_code = generate_secure_otp(6)
        challenge_id = generate_session_token()
        otp_hashed = hash_otp(otp_code)

        now_dt = datetime.utcnow()
        expires_dt = now_dt + timedelta(minutes=OTP_EXPIRY_MINUTES)
        now_str = now_dt.isoformat()
        expires_str = expires_dt.isoformat()

        c.execute("""
            INSERT INTO admin_otp_challenges (
                challenge_id, admin_id, otp_hash, telegram_id, attempts_count, max_attempts, is_used, created_at, expires_at
            ) VALUES (?, ?, ?, ?, 0, ?, 0, ?, ?)
        """, (challenge_id, admin_id, otp_hashed, telegram_id, MAX_OTP_ATTEMPTS, now_str, expires_str))

        # Log OTP challenge created (NEVER logging the OTP itself)
        c.execute("""
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (?, 'OTP_CHALLENGE_CREATED', ?, ?)
        """, (admin_id, f"Challenge: {challenge_id[:8]}..., SentToTelegram: {telegram_id}", now_str))

        conn.commit()

    # Deliver OTP via Telegram Bot
    sent = await send_admin_otp(otp_code, telegram_id, ip_address)
    if not sent:
        logger.warning(f"Failed to send Telegram OTP to {telegram_id}. Check bot token / user interaction.")

    return True, "Parol tasdiqlandi. Telegram bot orqali yuborilgan bir martalik kodni (OTP) kiriting.", {
        "challenge_id": challenge_id,
        "telegram_id_masked": f"***{str(telegram_id)[-4:]}",
        "expires_in_seconds": OTP_EXPIRY_MINUTES * 60
    }


async def verify_admin_otp(challenge_id: str, otp_code: str, ip_address: str = "", user_agent: str = "") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Step 2 of Admin Authentication:
    Verifies single-use OTP code and generates authorized session token.
    """
    now_dt = datetime.utcnow()
    now_str = now_dt.isoformat()

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM admin_otp_challenges WHERE challenge_id = ?", (challenge_id,))
        challenge = c.fetchone()

        if not challenge:
            return False, "Yaroqsiz yoki mavjud bo‘lmagan tekshiruv sessiyasi.", None

        if challenge["is_used"]:
            return False, "Ushbu bir martalik kod allaqachon ishlatilgan. Qaytadan kiring.", None

        # Check expiration
        expires_dt = datetime.fromisoformat(challenge["expires_at"].replace("Z", ""))
        if now_dt > expires_dt:
            c.execute("UPDATE admin_otp_challenges SET is_used = 1 WHERE challenge_id = ?", (challenge_id,))
            conn.commit()
            return False, "Bir martalik kodning amal qilish muddati tugagan (5 daqiqa).", None

        # Check attempt count
        attempts = challenge["attempts_count"] + 1
        if attempts > challenge["max_attempts"]:
            c.execute("UPDATE admin_otp_challenges SET is_used = 1 WHERE challenge_id = ?", (challenge_id,))
            conn.commit()
            return False, "Noto‘g‘ri kod kiritish urinishlari soni oshib ketdi. Yangi kod so‘rang.", None

        # Increment attempts count
        c.execute("UPDATE admin_otp_challenges SET attempts_count = ? WHERE challenge_id = ?", (attempts, challenge_id))
        conn.commit()

        # Constant-time OTP comparison
        if not verify_otp_hash(otp_code.strip(), challenge["otp_hash"]):
            remaining = challenge["max_attempts"] - attempts
            return False, f"Noto‘g‘ri kod kiritildi. Qolgan urinishlar: {max(0, remaining)} ta.", None

        # Valid OTP! Mark challenge as used
        c.execute("UPDATE admin_otp_challenges SET is_used = 1 WHERE challenge_id = ?", (challenge_id,))

        admin_id = challenge["admin_id"]

        # Generate new 64-character session token
        session_token = generate_session_token()
        session_expires_dt = now_dt + timedelta(hours=SESSION_DURATION_HOURS)
        session_expires_str = session_expires_dt.isoformat()

        c.execute("""
            INSERT INTO admin_sessions (
                session_id, admin_id, ip_address, user_agent, created_at, expires_at, is_revoked, last_activity_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?)
        """, (session_token, admin_id, ip_address, user_agent, now_str, session_expires_str, now_str))

        # Update last login on admin user
        c.execute("UPDATE admin_users SET last_login_at = ? WHERE id = ?", (now_str, admin_id))

        # Audit log
        c.execute("""
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (?, 'ADMIN_LOGIN_SUCCESS', ?, ?)
        """, (admin_id, f"IP: {ip_address}, UserAgent: {user_agent[:100]}", now_str))

        # Fetch admin details
        c.execute("SELECT id, username, telegram_id, role FROM admin_users WHERE id = ?", (admin_id,))
        admin_data = dict(c.fetchone())

        conn.commit()

    return True, "Muvaffaqiyatli avtorizatsiyadan o‘tildi.", {
        "session_token": session_token,
        "expires_at": session_expires_str,
        "admin": admin_data
    }


def validate_admin_session(session_token: str) -> Optional[Dict[str, Any]]:
    """Validates an active admin session token, updating last activity timestamp."""
    if not session_token:
        return None

    now_dt = datetime.utcnow()
    now_str = now_dt.isoformat()

    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT s.*, u.username, u.telegram_id, u.role, u.is_active
            FROM admin_sessions s
            JOIN admin_users u ON s.admin_id = u.id
            WHERE s.session_id = ? AND s.is_revoked = 0 AND u.is_active = 1
        """, (session_token,))
        row = c.fetchone()

        if not row:
            return None

        # Check expiration
        expires_dt = datetime.fromisoformat(row["expires_at"].replace("Z", ""))
        if now_dt > expires_dt:
            c.execute("UPDATE admin_sessions SET is_revoked = 1 WHERE session_id = ?", (session_token,))
            conn.commit()
            return None

        # Update last activity
        c.execute("UPDATE admin_sessions SET last_activity_at = ? WHERE session_id = ?", (now_str, session_token))
        conn.commit()

        return {
            "id": row["admin_id"],
            "username": row["username"],
            "telegram_id": row["telegram_id"],
            "role": row["role"],
            "session_id": row["session_id"]
        }


def revoke_admin_session(session_token: str) -> bool:
    """Logs out and invalidates an active admin session."""
    if not session_token:
        return False
    with _get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE admin_sessions SET is_revoked = 1 WHERE session_id = ?", (session_token,))
        c.execute("""
            INSERT INTO admin_audit_logs (admin_id, action, details, performed_at)
            VALUES (0, 'ADMIN_LOGOUT', ?, ?)
        """, (f"Session: {session_token[:8]}...", datetime.utcnow().isoformat()))
        conn.commit()
        return True
