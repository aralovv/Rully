"""
Security & Telegram initData verification for RULLY Mini App.
Implements official Telegram WebApp HMAC-SHA256 cryptographic verification.
Supports multi-token fallback for zero-downtime token rotation.
"""

import os
import hmac
import hashlib
import json
import urllib.parse
from typing import Dict, Any, Optional, Tuple, List
from src.bot.config import BOT_TOKEN

def get_allowed_bot_tokens() -> List[str]:
    """
    Returns prioritized list of bot tokens to validate Telegram HMAC signatures.
    Includes current environment token and previous tokens for zero-downtime rotation.
    """
    tokens = []
    env_token = os.getenv("BOT_TOKEN", "").strip()
    if env_token:
        tokens.append(env_token)

    if BOT_TOKEN and BOT_TOKEN not in tokens:
        tokens.append(BOT_TOKEN)

    # Known valid tokens in this system for seamless transition
    known_tokens = [
        "8657532177:AAGsyMFpzuwPus9jOdFRNP8f65qa8E-4q8g",
        "5875526565:AAEwGdyseiyejQQkf67_WEkvKX0cz0EX94s"
    ]
    for kt in known_tokens:
        if kt not in tokens:
            tokens.append(kt)

    return tokens

def verify_telegram_init_data(init_data: str, bot_token: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Verifies Telegram Mini App initData cryptographic signature.
    Returns (is_valid, user_dict).
    """
    if not init_data:
        return False, None

    init_data = str(init_data).strip()

    # Strip URL hash symbol if passed
    if init_data.startswith("#"):
        init_data = init_data[1:]

    # Handle tgWebAppData= wrapping if URL query or hash was passed
    if "tgWebAppData=" in init_data:
        try:
            parsed_qs = urllib.parse.parse_qs(init_data)
            if "tgWebAppData" in parsed_qs:
                extracted = parsed_qs["tgWebAppData"][0]
                if "hash=" in extracted or "hash%3D" in extracted:
                    init_data = extracted
            if init_data.startswith("tgWebAppData="):
                init_data = init_data[len("tgWebAppData="):]
        except Exception:
            pass

    # Handle double-URL-encoded strings
    if "hash=" not in init_data and "hash%3D" in init_data:
        init_data = urllib.parse.unquote(init_data)

    # Allow dev / testing bypass if prefixed with dev_ or mock mode
    if init_data.startswith("dev_user_") or init_data.startswith("test_user_"):
        user_id_str = init_data.split("_")[-1]
        user_id = int(user_id_str) if user_id_str.isdigit() else 8809526955
        return True, {
            "id": user_id,
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser",
            "language_code": "uz"
        }

    try:
        parsed_params = urllib.parse.parse_qsl(init_data, keep_blank_values=True)
        params_dict = dict(parsed_params)

        if "hash" not in params_dict:
            return False, None

        received_hash = params_dict.pop("hash")

        # Sort alphabetically and format as key=value separated by \n
        sorted_pairs = sorted(params_dict.items(), key=lambda x: x[0])
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_pairs)

        tokens_to_try = [bot_token] if bot_token else get_allowed_bot_tokens()

        for token in tokens_to_try:
            if not token:
                continue

            # 1. secret_key = HMAC_SHA256("WebAppData", bot_token)
            secret_key = hmac.new(
                key=b"WebAppData",
                msg=token.encode("utf-8"),
                digestmod=hashlib.sha256
            ).digest()

            # 2. calculated_hash = HMAC_SHA256(secret_key, data_check_string)
            calculated_hash = hmac.new(
                key=secret_key,
                msg=data_check_string.encode("utf-8"),
                digestmod=hashlib.sha256
            ).hexdigest()

            if hmac.compare_digest(calculated_hash, received_hash):
                # Parse user object if available
                user_info = None
                if "user" in params_dict:
                    try:
                        user_info = json.loads(params_dict["user"])
                    except Exception:
                        user_info = None

                return True, user_info

        return False, None

    except Exception:
        return False, None


def generate_dev_init_data(user_id: int = 8809526955, bot_token: Optional[str] = None) -> str:
    """
    Generates a cryptographically valid initData query string for automated tests.
    """
    token = bot_token or BOT_TOKEN
    user_json = json.dumps({
        "id": user_id,
        "first_name": "Tester",
        "last_name": "Rully",
        "username": "kurs_savdo",
        "language_code": "uz"
    }, separators=(',', ':'))

    params = {
        "auth_date": "1731760000",
        "query_id": "AAHd6g0bAAAAAN3qDRvVq2x1",
        "user": user_json
    }

    sorted_pairs = sorted(params.items(), key=lambda x: x[0])
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted_pairs)

    secret_key = hmac.new(
        key=b"WebAppData",
        msg=token.encode("utf-8"),
        digestmod=hashlib.sha256
    ).digest()

    sig = hmac.new(
        key=secret_key,
        msg=data_check_string.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()

    encoded_params = urllib.parse.urlencode(params)
    return f"{encoded_params}&hash={sig}"
