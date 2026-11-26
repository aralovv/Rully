"""
Telegram Delivery & Notification Service for Admin OTP, Order/Payment Alerts, and User Payment Confirmations.
"""

import os
import logging
import httpx
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from src.db_adapter import get_db_connection

load_dotenv()

logger = logging.getLogger(__name__)

# Dedicated OTP Bot Token (or fallback to main BOT_TOKEN)
OTP_BOT_TOKEN = os.getenv("ADMIN_OTP_BOT_TOKEN") or os.getenv("BOT_TOKEN", "")
MAIN_BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_TELEGRAM_ID = int(os.getenv("ADMIN_TELEGRAM_ID", "1956239701"))
ORDERS_GROUP_CHAT_ID = int(os.getenv("ORDERS_GROUP_CHAT_ID", "-5464313435"))
DB_PATH = os.getenv("DB_PATH", "master_database.sqlite")


def get_user_mention(user_id: int) -> str:
    """Helper to fetch username or first name from active DB (Turso or SQLite) for rich Telegram mentions."""
    try:
        with get_db_connection(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("SELECT username, first_name FROM telegram_users WHERE user_id = ?", (user_id,))
            row = c.fetchone()
            if row:
                uname = row[0] if not hasattr(row, "get") else row.get("username")
                fname = row[1] if not hasattr(row, "get") else row.get("first_name")
                if uname:
                    return f"@{uname} (ID: <code>{user_id}</code>)"
                elif fname:
                    return f"<b>{fname}</b> (ID: <code>{user_id}</code>)"
    except Exception:
        pass
    return f"<code>{user_id}</code>"


async def send_telegram_message(bot_token: str, chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Sends an asynchronous message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                return True
            else:
                logger.error(f"Telegram sendMessage failed [{res.status_code}]: {res.text}")
                return False
    except Exception as e:
        logger.error(f"Telegram delivery exception: {e}")
        return False


async def broadcast_order_alert(text: str) -> bool:
    """
    Broadcasts an order-related alert exclusively to the official 'Buyurtmalar Rully' group.
    Admin personal account is excluded to keep it clean and reserved only for login OTP codes.
    """
    if ORDERS_GROUP_CHAT_ID:
        return await send_telegram_message(MAIN_BOT_TOKEN, ORDERS_GROUP_CHAT_ID, text)
    return False


async def send_admin_otp(otp_code: str, admin_telegram_id: int = ADMIN_TELEGRAM_ID, ip_address: Optional[str] = None) -> bool:
    """
    Delivers a single-use OTP code to the administrator's Telegram account.
    Never logs the OTP code itself.
    """
    ip_info = f"\nIP: <code>{ip_address}</code>" if ip_address else ""
    text = (
        "🔐 <b>RULLY Admin Panel</b>\n\n"
        f"Tasdiqlash kodi: <code>{otp_code}</code>\n"
        "Muddati: 5 daqiqa. Kodni hech kimga bermang."
        f"{ip_info}"
    )
    return await send_telegram_message(OTP_BOT_TOKEN, admin_telegram_id, text)


async def send_order_created_alert(order: Dict[str, Any]) -> bool:
    """
    Notifies the 'Buyurtmalar Rully' group when a user generates a new payment order / invoice.
    """
    amount = order.get("final_amount_uzs", 0)
    amount_str = f"{amount:,}".replace(",", " ")
    user_id = order.get("user_id", 0)
    user_label = get_user_mention(user_id)
    plan_name = order.get("plan_name", "PRO Obuna")
    card_suffix = order.get("card_suffix", "...")
    order_id = order.get("order_id", "ORD-...")

    text = (
        "📋 <b>Yangi buyurtma yaratildi</b>\n\n"
        f"Buyurtma: <code>{order_id}</code>\n"
        f"Foydalanuvchi: {user_label}\n"
        f"Tarif: <b>{plan_name}</b>\n"
        f"Summa: <b>{amount_str} UZS</b>\n"
        f"Karta: <b>*{card_suffix}</b>\n"
        "Holati: ⏳ To‘lov kutilmoqda (15 daqiqa)"
    )
    return await broadcast_order_alert(text)


async def send_payment_alert_to_admin(order_id: str, amount_uzs: int, user_id: int, plan_name: str, card_suffix: str) -> bool:
    """Alerts the 'Buyurtmalar Rully' group and admin when an automated payment is matched and activated."""
    amount_str = f"{amount_uzs:,}".replace(",", " ")
    user_label = get_user_mention(user_id)
    text = (
        "💰 <b>Yangi muvaffaqiyatli to‘lov</b>\n\n"
        f"Buyurtma: <code>{order_id}</code>\n"
        f"Foydalanuvchi: {user_label}\n"
        f"Summa: <b>{amount_str} UZS</b>\n"
        f"Tarif: <b>{plan_name}</b>\n"
        f"Karta: <b>*{card_suffix}</b>\n"
        "Holati: 🟢 Avtomatik faollashtirildi"
    )
    return await broadcast_order_alert(text)


async def send_stars_payment_alert_to_admin(order_id: str, stars_amount: int, user_id: int, plan_name: str) -> bool:
    """Alerts the 'Buyurtmalar Rully' group when a Telegram Stars (XTR) payment completes."""
    user_label = get_user_mention(user_id)
    text = (
        "⭐ <b>Yangi Telegram Stars (XTR) to‘lov</b>\n\n"
        f"Buyurtma: <code>{order_id}</code>\n"
        f"Foydalanuvchi: {user_label}\n"
        f"Summa: <b>{stars_amount} ⭐ (XTR)</b>\n"
        f"Tarif: <b>{plan_name}</b>\n"
        "Holati: 🟢 Bir zumda avtomatik faollashtirildi"
    )
    return await broadcast_order_alert(text)


async def send_late_payment_alert_to_admin(order_id: str, amount_uzs: int, user_id: int, card_suffix: str) -> bool:
    """Alerts the 'Buyurtmalar Rully' group and admin when a payment arrives for an expired order."""
    amount_str = f"{amount_uzs:,}".replace(",", " ")
    user_label = get_user_mention(user_id)
    text = (
        "⚠️ <b>Kechiktirilgan to‘lov aniqlandi</b>\n\n"
        f"Buyurtma: <code>{order_id}</code> (Muddati o‘tgan)\n"
        f"Foydalanuvchi: {user_label}\n"
        f"Summa: <b>{amount_str} UZS</b>\n"
        f"Karta: <b>*{card_suffix}</b>\n"
        "Holati: 🟡 Admin tekshiruvi talab qilinadi\n\n"
        "Boshqaruv panelida 'To‘lovlar' bo‘limidan tasdiqlashingiz mumkin."
    )
    return await broadcast_order_alert(text)


async def send_late_payment_approved_alert(order_id: str, amount_uzs: int, user_id: int, plan_name: str, admin_name: str) -> bool:
    """Alerts the 'Buyurtmalar Rully' group and admin when an administrator manually approves a late payment."""
    amount_str = f"{amount_uzs:,}".replace(",", " ")
    user_label = get_user_mention(user_id)
    text = (
        "✅ <b>Kechiktirilgan to‘lov tasdiqlandi</b>\n\n"
        f"Buyurtma: <code>{order_id}</code>\n"
        f"Foydalanuvchi: {user_label}\n"
        f"Summa: <b>{amount_str} UZS</b>\n"
        f"Tarif: <b>{plan_name}</b>\n"
        f"Admin: <b>{admin_name}</b>\n"
        "Holati: 🟢 Obuna berildi"
    )
    return await broadcast_order_alert(text)


async def send_unmatched_payment_alert(
    amount_uzs: int,
    card_suffix: str,
    payment_source: str,
    diagnostic_hint: Optional[str] = None,
    candidate_order_id: Optional[str] = None,
) -> bool:
    """Alerts the 'Buyurtmalar Rully' group and admin when an incoming payment does not match any order."""
    amount_str = f"{amount_uzs:,}".replace(",", " ")
    hint_block = ""
    if candidate_order_id or diagnostic_hint:
        hint_block = "\n"
        if candidate_order_id:
            hint_block += f"Ehtimoliy buyurtma: <code>{candidate_order_id}</code>\n"
        if diagnostic_hint:
            hint_block += f"Diagnostika: <i>{diagnostic_hint}</i>\n"
    text = (
        "❓ <b>Noma’lum to‘lov kelib tushdi</b>\n\n"
        f"Summa: <b>{amount_str} UZS</b>\n"
        f"Karta: <b>*{card_suffix}</b>\n"
        f"Manba: <b>{payment_source}</b>\n"
        f"{hint_block}"
        "Holati: ⚪ Mos buyurtma topilmadi (Admin panel orqali tekshiring)"
    )
    return await broadcast_order_alert(text)


async def send_user_payment_success_notification(user_id: int, plan_name: str, expires_at: str, duration_days: Optional[int] = None) -> bool:
    """Notifies the user in Telegram that their payment was verified and PRO is active."""
    exp_date = expires_at[:10] if expires_at else ""
    dur_text = f"+{duration_days} kunlik " if duration_days else ""
    text = (
        f"🎉 Tabriklaymiz! Hisobingizda <b>{dur_text}PRO obuna</b> muvaffaqiyatli faollashtirildi.\n\n"
        f"Tarif: <b>{plan_name}</b>\n"
        f"Amal qilish muddati: <b>{exp_date} gacha</b>\n\n"
        "Barcha imtihon testlari va amaliy tahlillar siz uchun to‘liq ochiq."
    )
    return await send_telegram_message(MAIN_BOT_TOKEN, user_id, text)


async def send_user_subscription_granted_notification(user_id: int, duration_days: int, expires_at: str) -> bool:
    """Notifies the user in Telegram that a subscription was granted or extended by administrator."""
    exp_date = expires_at[:10] if expires_at else ""
    text = (
        f"🎉 Tabriklaymiz! Hisobingizda <b>+{duration_days} kunlik PRO obuna</b> muvaffaqiyatli faollashtirildi.\n\n"
        f"Amal qilish muddati: <b>{exp_date} gacha</b>\n\n"
        "Barcha imtihon testlari va amaliy tahlillar siz uchun to‘liq ochiq."
    )
    return await send_telegram_message(MAIN_BOT_TOKEN, user_id, text)


async def send_payment_invoice_to_user(
    user_id: int,
    plan_name: str,
    cardholder_name: str,
    card_number_full: str,
    final_amount_uzs: int,
    order_id: str
) -> bool:
    """Sends an automated payment invoice directly to the user in Telegram chat."""
    raw_card = card_number_full.replace(" ", "")
    formatted_card = " ".join([raw_card[i:i+4] for i in range(0, len(raw_card), 4)]) if len(raw_card) == 16 else raw_card
    amount_str = f"{final_amount_uzs:,}".replace(",", " ")

    text = (
        "<b>To‘lov uchun ma’lumotlar:</b>\n\n"
        f"Karta: <code>{formatted_card}</code>\n"
        f"Qabul qiluvchi: <b>{cardholder_name}</b>\n"
        f"Summa: <code>{final_amount_uzs}</code> so‘m ({amount_str} so‘m)\n"
        f"Tarif: <b>{plan_name}</b>\n\n"
        "To‘lov avtomatik faollashishi uchun aynan ko‘rsatilgan summani o‘tkazing. "
        "Invoys 15 daqiqa davomida amal qiladi.\n\n"
        f"Buyurtma kodi: <code>{order_id}</code>"
    )
    return await send_telegram_message(MAIN_BOT_TOKEN, user_id, text)


_last_mtproto_alerted_status = None
_last_mtproto_alert_time = 0.0

async def send_mtproto_status_alert(status: str, detail: str = "", force: bool = False) -> bool:
    """
    Sends an immediate critical alert to the administrator's personal Telegram account
    if MTProto loses connection, encounters an auth error, or disconnects.
    Deduplicated to avoid flooding.
    """
    global _last_mtproto_alerted_status, _last_mtproto_alert_time
    import time
    now = time.time()

    # Avoid duplicate spam within 30 minutes unless status changed or forced
    if not force and status == _last_mtproto_alerted_status and (now - _last_mtproto_alert_time) < 1800:
        return False

    _last_mtproto_alerted_status = status
    _last_mtproto_alert_time = now

    admin_id = ADMIN_TELEGRAM_ID
    if not admin_id or not MAIN_BOT_TOKEN:
        return False

    if status == "CONNECTED":
        icon = "🟢"
        title = "MTProto Ulandi va Faol"
        instruction = "Humocardbot xabarnomalari 24/7 rejimda tinglanmoqda."
    elif status == "AUTH_REQUIRED":
        icon = "🔴"
        title = "MTProto: Qayta Avtorizatsiya Talab Qilinadi"
        instruction = "Telegram sessiyasi bekor qilingan. Iltimos, <code>python connect_mtproto.py</code> orqali qayta ulang."
    elif status == "NOT_INSTALLED":
        icon = "🚨"
        title = "MTProto: Telethon O'rnatilmagan"
        instruction = "Serverda <code>telethon</code> kutubxonasi topilmadi. Build Command <code>pip install -r requirements-render.txt</code> ekanini tekshiring."
    elif status == "DISCONNECTED":
        icon = "🟡"
        title = "MTProto: Aloqa Uzildi"
        instruction = "MTProto mijozi aloqani yo'qotdi yoki sessiya topilmadi. Avtomatik qayta ulanish kutilmoqda."
    else:
        icon = "⚠️"
        title = f"MTProto: Xatolik ({status})"
        instruction = "MTProto ishlashida muammo aniqlandi."

    text = (
        f"{icon} <b>DIQQAT: {title}</b>\n\n"
        f"Holat: <b>{status}</b>\n"
        f"Tafsilot: <i>{detail}</i>\n\n"
        f"ℹ️ {instruction}"
    )
    return await send_telegram_message(MAIN_BOT_TOKEN, admin_id, text)

