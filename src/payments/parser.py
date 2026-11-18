"""
Humocardbot Payment Notification Parser.
Extracts transaction details from SMS/Telegram notifications sent by Humocardbot.
"""

import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def parse_humocard_notification(text: str) -> Optional[Dict[str, Any]]:
    """
    Parses Humocardbot notification message.
    Expected format:
      🎉 To’ldirish
      ➕ 10.000,00 UZS
      📍 HAMKORBANK PAYME AJ
      💳 HUMOCARD *5370
      🕓 00:05 15.11.2026
      💰 10.010,00 UZS

    Crucial:
    The incoming transaction amount (➕ 10.000,00 UZS) must be strictly distinguished
    from the resulting account balance (💰 10.010,00 UZS).
    """
    if not text or not isinstance(text, str):
        return None

    # Check for incoming transaction keywords (Latin / Cyrillic)
    is_incoming = bool(re.search(r"(To[’'`]ldirish|Тўлдириш|Toldirish|Kirim|Кирим|➕)", text, re.IGNORECASE))
    if not is_incoming:
        # Check if it's an outgoing payment (To'lov, Chiqim, O'tkazma, ➖)
        if re.search(r"(To[’'`]lov|Chiqim|O[’'`]tkazma|Тўлов|Чиқим|➖)", text, re.IGNORECASE):
            return {
                "is_incoming": False,
                "transaction_type": "OUTGOING",
                "raw_message": text
            }
        return None

    # 1. Incoming Amount (immediately after ➕)
    # Examples: '➕ 10.000,00 UZS', '➕ 50.347,00 UZS', '➕ 14 000 UZS'
    amount_match = re.search(r"➕\s*([\d\s\.]+)(?:,(\d{2}))?\s*UZS", text, re.IGNORECASE)
    if not amount_match:
        # Alternative pattern without plus if 'To’ldirish' is present
        amount_match = re.search(r"(?:To[’'`]ldirish|Тўлдириш)\s*\n\s*([\d\s\.]+)(?:,(\d{2}))?\s*UZS", text, re.IGNORECASE)
        if not amount_match:
            return None

    raw_amount = amount_match.group(1).replace(".", "").replace(" ", "").replace("\xa0", "").strip()
    try:
        amount_uzs = int(raw_amount)
    except ValueError:
        return None

    # 2. Card Identifier / Suffix (e.g. '*5370' or '5370')
    card_match = re.search(r"💳[^\n]*\*?(\d{4})", text)
    if not card_match:
        card_match = re.search(r"(?:HUMO|UZCARD|KARTA)[^\n]*\*?(\d{4})", text, re.IGNORECASE)
    card_suffix = card_match.group(1) if card_match else ""

    # 3. Source / Payment System (📍 ...)
    source_match = re.search(r"📍\s*([^\n]+)", text)
    payment_source = source_match.group(1).strip() if source_match else "UNKNOWN"

    # 4. Timestamp (🕓 00:05 15.11.2026 or similar)
    time_match = re.search(r"🕓\s*(\d{2}:\d{2})\s+(\d{2}\.\d{2}\.\d{4})", text)
    if time_match:
        timestamp_str = f"{time_match.group(2)} {time_match.group(1)}"
    else:
        # Try DD.MM.YYYY HH:MM
        time_match2 = re.search(r"(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})", text)
        timestamp_str = f"{time_match2.group(1)} {time_match2.group(2)}" if time_match2 else ""

    # 5. Resulting Balance (💰 ...)
    balance_match = re.search(r"💰\s*([\d\s\.]+)(?:,(\d{2}))?\s*UZS", text, re.IGNORECASE)
    balance_uzs = None
    if balance_match:
        raw_balance = balance_match.group(1).replace(".", "").replace(" ", "").replace("\xa0", "").strip()
        try:
            balance_uzs = int(raw_balance)
        except ValueError:
            pass

    return {
        "is_incoming": True,
        "transaction_type": "INCOMING",
        "amount_uzs": amount_uzs,
        "card_suffix": card_suffix,
        "payment_source": payment_source,
        "timestamp_str": timestamp_str,
        "balance_uzs": balance_uzs,
        "raw_message": text
    }
