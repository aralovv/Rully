"""
RULLY - 1-Click Interactive MTProto Telegram Connector.
Run this script once from terminal to authorize your Telegram account that receives @Humocardbot SMS.
The session will be securely encrypted and saved directly to Turso Cloud Database.
Once saved, Render 24/7 worker will automatically listen to Humocardbot payments!
"""

import sys
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from src.mtproto.service import DEFAULT_API_ID, DEFAULT_API_HASH, get_mtproto_manager
from src.security.telegram_notifier import send_mtproto_status_alert

async def interactive_connect():
    print("=" * 60)
    print("🚗 RULLY MTProto (@Humocardbot) Ulanish Yordamchisi")
    print("=" * 60)
    print("Ushbu vosita @Humocardbot xabarnomalari keladigan Telegram")
    print("akkauntingizni xavfsiz shifrlab Turso bazasiga ulaydi.\n")

    manager = get_mtproto_manager()

    phone = input("📱 Telefon raqamingizni xalqaro formatda kiriting (masalan, +998901234567): ").strip()
    if not phone:
        print("❌ Telefon raqami kiritilmadi!")
        return

    client = TelegramClient(StringSession(), DEFAULT_API_ID, DEFAULT_API_HASH)
    await client.connect()

    print(f"\n📨 {phone} raqamiga Telegram tasdiqlash kodi yuborilmoqda...")
    try:
        sent_code = await client.send_code_request(phone)
    except Exception as e:
        print(f"❌ Xatolik yuz berdi: {e}")
        await client.disconnect()
        return

    code = input("🔑 Telegram ilovangizga kelgan 5 xonali kodni kiriting: ").strip()

    try:
        await client.sign_in(phone, code, phone_code_hash=sent_code.phone_code_hash)
    except SessionPasswordNeededError:
        print("🔐 Ushbu akkauntda 2FA (Ikki bosqichli parol) o'rnatilgan.")
        pw = input("2FA parolingizni kiriting: ").strip()
        try:
            await client.sign_in(password=pw)
        except Exception as e:
            print(f"❌ 2FA paroli noto'g'ri: {e}")
            await client.disconnect()
            return
    except Exception as e:
        print(f"❌ Kod noto'g'ri yoki xatolik: {e}")
        await client.disconnect()
        return

    me = await client.get_me()
    session_str = client.session.save()
    manager.phone_number = phone
    manager.save_session(session_str, me)

    try:
        await send_mtproto_status_alert(
            "CONNECTED",
            f"Akkaunt (@{me.username or me.first_name}, {phone}) muvaffaqiyatli ulandi! Humocardbot xabarnomalari 24/7 rejimda tinglanmoqda.",
            force=True
        )
    except Exception:
        pass

    print("\n" + "=" * 60)
    print(f"✅ TABRIKLAYMIZ! MTProto muvaffaqiyatli ulandi!")
    print(f"👤 Akkaunt: {me.first_name} (@{me.username or 'username_yoq'})")
    print(f"📱 Telefon: {phone}")
    print(f"☁️ Sessiya shifrlangan holda Turso Cloud bazasiga saqlandi!")
    print(f"🚀 Render'dagi 24/7 worker endi Humocardbot xabarlarini avtomatik ushlaydi!")
    print("=" * 60)

    await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(interactive_connect())
    except KeyboardInterrupt:
        print("\nOperatsiya to'xtatildi.")
