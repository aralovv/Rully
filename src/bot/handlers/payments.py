"""
Native Telegram Stars (XTR) Bot Payment Handlers.

Handles:
- Inline chat Stars checkout callback (`buy_stars:<plan_id>`) using `bot.send_invoice(..., currency="XTR")`
- Mandatory <10s `pre_checkout_query` validation
- Idempotent `F.successful_payment` fulfillment + admin group telemetry
"""

from __future__ import annotations

import asyncio
import logging
from aiogram import Bot, F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    WebAppInfo,
)

from src.bot.config import WEB_APP_URL
from src.bot.database import BotDatabase
from src.payments.stars_service import (
    create_stars_invoice_order,
    fulfill_stars_payment,
    validate_stars_pre_checkout,
)
from src.security.telegram_notifier import send_stars_payment_alert_to_admin

logger = logging.getLogger(__name__)
payments_router = Router(name="payments_router")


@payments_router.callback_query(F.data.startswith("buy_stars:"))
async def cb_buy_with_telegram_stars(
    callback: CallbackQuery,
    bot: Bot,
    db: BotDatabase,
):
    """Sends a native Telegram Stars (`XTR`) invoice card directly into the user's chat."""
    plan_id = callback.data.split(":", 1)[1].strip()
    user_id = callback.from_user.id
    lang = db.get_user_language(user_id)
    db.get_or_create_user(
        user_id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )

    try:
        order = await create_stars_invoice_order(user_id=user_id, plan_id=plan_id, create_link=False)
    except ValueError:
        err_txt = (
            "Tanlangan tarif hozircha faol emas."
            if lang == "uz_latn"
            else ("Танланган тариф ҳозирча фаол эмас." if lang == "uz_cyrl" else "Выбранный тариф сейчас недоступен.")
        )
        await callback.answer(err_txt, show_alert=True)
        return

    await callback.answer()
    title = f"RULLY PRO — {order['plan_name']}"[:32]
    if lang == "ru":
        desc = f"{order['duration_days']} дн. полного PRO доступа: безлимитный экзамен, AI Наставник 2.0 и Автодром 2D."
    elif lang == "uz_cyrl":
        desc = f"{order['duration_days']} кунлик тўлиқ PRO кириш: чексиз имтиҳон, AI Устоз 2.0 ва Автодром 2D."
    else:
        desc = f"{order['duration_days']} kunlik to‘liq PRO kirish: cheksiz imtihon, AI Ustoz 2.0 va Avtodrom 2D."

    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title=title,
        description=desc[:255],
        payload=order["payload"],
        currency="XTR",
        provider_token="",
        prices=[LabeledPrice(label=order["plan_name"][:32], amount=int(order["stars_amount"]))],
    )


@payments_router.pre_checkout_query()
async def handle_stars_pre_checkout(query: PreCheckoutQuery):
    """Strictly validates XTR order ownership, amount, and pending state before payment capture."""
    ok, err_msg = await asyncio.to_thread(
        validate_stars_pre_checkout,
        query.invoice_payload,
        query.total_amount,
        query.currency,
        query.from_user.id,
    )
    if ok:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message=err_msg or "To‘lovni tasdiqlab bo‘lmadi.")


@payments_router.message(F.successful_payment)
async def handle_stars_successful_payment(message: Message, db: BotDatabase):
    """Idempotently unlocks PRO subscription immediately after Telegram confirms `XTR` capture."""
    sp = message.successful_payment
    user_id = message.from_user.id
    lang = db.get_user_language(user_id)

    res = await asyncio.to_thread(
        fulfill_stars_payment,
        user_id=user_id,
        payload=sp.invoice_payload,
        currency=sp.currency,
        total_amount=sp.total_amount,
        telegram_payment_charge_id=sp.telegram_payment_charge_id,
        provider_payment_charge_id=sp.provider_payment_charge_id,
    )

    if not res.get("ok"):
        logger.error("Failed to fulfill Stars payment for user=%s: %s", user_id, res)
        await message.answer(
            "⚠️ To‘lov qabul qilindi, lekin obuna faollashtirishda kechikish yuz berdi. Qo‘llab-quvvatlash xizmatiga yozing."
        )
        return

    exp_date = str(res.get("expires_at") or "")[:10]
    plan_name = res.get("plan_name", "PRO")
    stars_amt = res.get("stars_amount", sp.total_amount)

    if lang == "ru":
        msg_text = (
            f"🎉 <b>Спасибо за оплату через Telegram Stars!</b>\n\n"
            f"Тариф: <b>{plan_name}</b> ({stars_amt} ⭐)\n"
            f"Действует до: <b>{exp_date}</b>\n\n"
            "Все возможности RULLY PRO разблокированы!"
        )
        btn_open = "🚀 Открыть RULLY PRO"
    elif lang == "uz_cyrl":
        msg_text = (
            f"🎉 <b>Telegram Stars орқали тўлов учун раҳмат!</b>\n\n"
            f"Тариф: <b>{plan_name}</b> ({stars_amt} ⭐)\n"
            f"Амал қилиш муддати: <b>{exp_date} гача</b>\n\n"
            "Барча RULLY PRO имкониятлари фаоллаштирилди!"
        )
        btn_open = "🚀 RULLY PRO’ни очиш"
    else:
        msg_text = (
            f"🎉 <b>Telegram Stars orqali to‘lov muvaffaqiyatli qabul qilindi!</b>\n\n"
            f"Tarif: <b>{plan_name}</b> ({stars_amt} ⭐)\n"
            f"Amal qilish muddati: <b>{exp_date} gacha</b>\n\n"
            "Barcha RULLY PRO imkoniyatlari bir zumda ochildi!"
        )
        btn_open = "🚀 RULLY PRO’ni ochish"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=btn_open, web_app=WebAppInfo(url=f"{WEB_APP_URL}#profile"))]]
    )
    await message.answer(text=msg_text, parse_mode="HTML", reply_markup=kb)

    if not res.get("already_processed"):
        try:
            asyncio.create_task(
                send_stars_payment_alert_to_admin(
                    order_id=res.get("order_id", ""),
                    stars_amount=int(stars_amt),
                    user_id=user_id,
                    plan_name=plan_name,
                )
            )
        except Exception:
            pass
