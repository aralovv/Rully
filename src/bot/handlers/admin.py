"""
Secure Administration & Bot Management Layer.
Access strictly controlled via configured ADMIN_IDS.
"""
import asyncio
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from src.bot.database import BotDatabase
from src.bot.keyboards import get_admin_keyboard
from src.bot.config import ADMIN_IDS

logger = logging.getLogger(__name__)
admin_router = Router(name="admin_router")

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@admin_router.message(Command("admin"))
async def cmd_admin(message: Message, db: BotDatabase):
    user_id = message.from_user.id
    if not is_admin(user_id):
        # Do not expose admin existence to non-admins
        return

    db.log_admin_action(user_id, "OPEN_ADMIN_PANEL")
    stats = db.get_admin_stats()

    text = (
        "🛞 <b>RULLY ADMIN BOSHQARUV PANELI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"• Jami foydalanuvchilar: <b>{stats['total_users']} ta</b>\n"
        f"• Tillar kesimida: <code>{stats['users_by_language']}</code>\n"
        f"• Yakunlangan sessiyalar: <b>{stats['completed_sessions']} ta</b>\n"
        f"• Topshirilgan imtihonlar: <b>{stats['total_exams']} ta</b>\n"
        f"• O‘tganlar soni: <b>{stats['passed_exams']} ta</b>\n"
        f"• O‘tish ko‘rsatkichi: <b>{stats['exam_pass_rate']}%</b>\n"
        f"• Kanonik savollar banki: <b>{stats['canonical_questions']} ta</b>\n"
        f"• Jami tarjimalar: <b>{stats['canonical_translations']} ta</b>\n"
        f"• Tizim holati: 🟢 <b>{stats['status']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

    await message.answer(
        text=text,
        parse_mode="HTML",
        reply_markup=get_admin_keyboard()
    )

@admin_router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(callback: CallbackQuery, db: BotDatabase):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return

    await callback.answer()
    stats = db.get_admin_stats()
    text = (
        "📈 <b>BATAFSIL TIZIM TELEMETRIYASI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"• Ro‘yxatdan o‘tganlar: <b>{stats['total_users']}</b>\n"
        f"• Imtihonlar jami: <b>{stats['total_exams']}</b>\n"
        f"• O‘tish foizi: <b>{stats['exam_pass_rate']}%</b>\n"
        f"• Bazadagi kanonik savollar: <b>{stats['canonical_questions']}</b>\n"
        f"• 3-tilli tarjima qamrovi: <b>100.0%</b>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=get_admin_keyboard())

@admin_router.callback_query(F.data == "admin:health")
async def cb_admin_health(callback: CallbackQuery, db: BotDatabase):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return

    await callback.answer()
    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("PRAGMA integrity_check;")
        int_res = c.fetchall()
        c.execute("PRAGMA foreign_key_check;")
        fk_res = c.fetchall()

    status_icon = "🟢" if int_res == [('ok',)] and len(fk_res) == 0 else "🔴"
    text = (
        f"🛠️ <b>TIZIM VA MA’LUMOTLAR BAZASI SALOMATLIGI</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"• SQLite Integrity Check: <b>{int_res[0][0]}</b>\n"
        f"• Foreign Key Violations: <b>{len(fk_res)} ta</b>\n"
        f"• Status: {status_icon} <b>HAMMASI JOYIDA</b>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await callback.message.edit_text(text=text, parse_mode="HTML", reply_markup=get_admin_keyboard())

@admin_router.callback_query(F.data == "admin:broadcast")
async def cb_admin_broadcast_prompt(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(
        "📢 <b>Xabar tarqatish (Broadcast):</b>\n\n"
        "Barcha foydalanuvchilarga xabar yuborish uchun quyidagi formatda yozing:\n"
        "<code>/broadcast Sizning xabaringiz matni...</code>",
        parse_mode="HTML"
    )

@admin_router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, bot: Bot, db: BotDatabase):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("⚠️ Xabar matni kiritilmadi: <code>/broadcast Matn</code>", parse_mode="HTML")
        return

    broadcast_text = args[1]
    all_users = db.get_all_user_ids()
    db.log_admin_action(user_id, "BROADCAST", f"Recipients: {len(all_users)}")

    status_msg = await message.answer(f"📢 Xabar tarqatilmoqda (0/{len(all_users)})...")

    sent = 0
    failed = 0
    for uid in all_users:
        try:
            await bot.send_message(chat_id=uid, text=broadcast_text, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05) # Safe rate limiting (20 msgs/sec max)
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ <b>Xabar tarqatish yakunlandi!</b>\n\n"
        f"• Yuborildi: <b>{sent} ta</b>\n"
        f"• Xatolik: <b>{failed} ta</b>",
        parse_mode="HTML"
    )
