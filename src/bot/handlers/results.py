"""
User Results & Performance Analytics Handlers.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from src.bot.database import BotDatabase
from src.bot.config import WEB_APP_URL
from src.bot.strings import get_str

results_router = Router(name="results_router")

@results_router.message(Command("results"))
@results_router.callback_query(F.data == "menu:results")
async def show_user_results(event: Message | CallbackQuery, db: BotDatabase):
    user_id = event.from_user.id
    lang = db.get_user_language(user_id)

    if isinstance(event, CallbackQuery):
        await event.answer()

    stats = db.get_user_stats(user_id)
    history = db.get_user_exam_history(user_id, limit=5)
    readiness = stats.get("readiness_score", 0)

    title = get_str("stats_title", lang)
    readiness_line = (
        f"🎯 <b>Haqiqiy tayyorgarlik darajasi:</b> <b>{readiness}%</b>\n<i>(4 ta asosiy omil: Davlat imtihoni, aniqlik, qamrov va xatolar banki)</i>\n" if lang == "uz_latn" else (
            f"🎯 <b>Ҳақиқий тайёргарлик даражаси:</b> <b>{readiness}%</b>\n<i>(4 та асосий омил: Давлат имтиҳони, аниқлик, қамров ва хатолар банки)</i>\n" if lang == "uz_cyrl" else
            f"🎯 <b>Реальный индекс готовности:</b> <b>{readiness}%</b>\n<i>(4 фактора: гос. экзамен, точность, охват базы и банк ошибок)</i>\n"
        )
    )

    stats_body = get_str("stats_text", lang,
                         total_exams=stats["total_exams"],
                         passed_exams=stats["passed_exams"],
                         pass_rate=stats["pass_rate"],
                         total_questions=stats["total_questions_answered"],
                         accuracy=stats["accuracy"],
                         unresolved_mistakes=stats["unresolved_mistakes"])

    lines = [
        title,
        "",
        readiness_line,
        stats_body
    ]

    if history:
        history_header = (
            "🕒 <b>So‘nggi imtihonlar:</b>" if lang == "uz_latn" else (
                "🕒 <b>Сўнгги имтиҳонлар:</b>" if lang == "uz_cyrl" else
                "🕒 <b>Последние экзамены:</b>"
            )
        )
        sec_unit = "son" if lang == "uz_latn" else ("сон" if lang == "uz_cyrl" else "сек")
        lines.append(history_header)
        lines.append("<pre>")
        for h in history:
            res_icon = "🟢" if h["passed"] else "🔴"
            lines.append(f"{res_icon} {h['correct_count']}/{h['total_questions']} ({h['percentage']}%) | {int(h['time_taken_seconds'])}{sec_unit}")
        lines.append("</pre>")

    msg_text = "\n".join(lines)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚗 RULLY'da batafsil tahlil" if lang == "uz_latn" else ("🚗 RULLY'да батафсил таҳлил" if lang == "uz_cyrl" else "🚗 Подробный анализ в RULLY"), web_app=WebAppInfo(url=f"{WEB_APP_URL}#profile"))],
        [InlineKeyboardButton(text="🏠 Bosh menyu" if lang == "uz_latn" else ("🏠 Бош меню" if lang == "uz_cyrl" else "🏠 Главное меню"), callback_data="menu:main")]
    ])

    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text=msg_text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await event.message.answer(text=msg_text, parse_mode="HTML", reply_markup=kb)
    else:
        await event.answer(text=msg_text, parse_mode="HTML", reply_markup=kb)
