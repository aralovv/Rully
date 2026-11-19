"""
Official Exam Simulation Launcher for RULLY.
Directs users to the full-screen official exam view in RULLY.
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from src.bot.database import BotDatabase
from src.bot.config import WEB_APP_URL

exam_router = Router(name="exam_router")

@exam_router.message(Command("exam"))
@exam_router.message(F.text.in_([
    "🏛️ Davlat nazariy imtihoni (20)",
    "🏛️ Давлат назарий имтиҳони (20)",
    "🏛️ Теоретический госэкзамен (20)",
    "🏆 Davlat imtihoni (20 ta savol)",
    "🏆 Давлат имтиҳони (20 та савол)",
    "🏆 Государственный экзамен (20 вопросов)",
    "🏆 Haqiqiy imtihon (20 savol / 25 daq)",
    "🏆 Ҳақиқий имтиҳон (20 савол / 25 дақ)",
    "🏆 Официальный экзамен (20 вопросов / 25 мин)"
]))
@exam_router.callback_query(F.data == "menu:exam")
async def start_exam_flow(event: Message | CallbackQuery, bot: Bot, db: BotDatabase):
    user_id = event.from_user.id
    lang = db.get_user_language(user_id)

    if isinstance(event, CallbackQuery):
        await event.answer()

    title = (
        "🏛️ <b>Davlat nazariy imtihoni (VMQ 408)</b>" if lang == "uz_latn" else (
            "🏛️ <b>Давлат назарий имтиҳони (ВМҚ 408)</b>" if lang == "uz_cyrl" else
            "🏛️ <b>Государственный теоретический экзамен (ПКМ 408)</b>"
        )
    )
    desc = (
        "Davlat nazariy imtihoni SBDD kompyuterlashtirilgan zal andozasida <b>RULLY</b> platformasida o‘tkaziladi:\n\n"
        "• Jami savollar: <b>20 ta</b>\n"
        "• Vaqt chegarasi: <b>25 daqiqa</b>\n"
        "• O‘tish talabi: <b>kamida 18 ta to‘g‘ri javob</b> (90%)\n"
        "• Kompyuter tizimi andozasi (F1-F4 tugmalar, izohsiz, tezkor savol katakchalari).\n\n"
        "Imtihonni boshlash uchun quyidagi tugmani bosing:" if lang == "uz_latn" else (
            "Давлат назарий имтиҳони СБДД компьютерлаштирилган зал андозасида <b>RULLY</b> платформасида ўтказилади:\n\n"
            "• Жами саволлар: <b>20 та</b>\n"
            "• Вақт чегараси: <b>25 дақиқа</b>\n"
            "• Ўтиш талаби: <b>камида 18 та тўғри жавоб</b> (90%)\n"
            "• Компьютер тизими андозаси (F1-F4 тугмалар, изоҳсиз, тезкор савол катакчалари).\n\n"
            "Имтиҳонни бошлаш учун қуйидаги тугмани босинг:" if lang == "uz_cyrl" else
            "Государственный экзамен проводится по стандарту компьютерных залов СБДД в <b>RULLY</b>:\n\n"
            "• Количество вопросов: <b>20</b>\n"
            "• Лимит времени: <b>25 минут</b>\n"
            "• Проходной балл: <b>не менее 18 правильных ответов</b> (90%)\n"
            "• Интерфейс компьютерного класса (клавиши F1-F4, без подсказок, быстрый переход).\n\n"
            "Для запуска экзамена нажмите кнопку ниже:"
        )
    )
    btn_text = (
        "🚦 Imtihonni boshlash (20 ta savol)" if lang == "uz_latn" else (
            "🚦 Имтиҳонни бошлаш (20 та савол)" if lang == "uz_cyrl" else
            "🚦 Начать экзамен (20 вопросов)"
        )
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, web_app=WebAppInfo(url=f"{WEB_APP_URL}#exam"))],
        [InlineKeyboardButton(text="🎛️ Bosh menyu" if lang == "uz_latn" else ("🎛️ Бош меню" if lang == "uz_cyrl" else "🎛️ Главное меню"), callback_data="menu:main")]
    ])

    if isinstance(event, CallbackQuery):
        await event.message.answer(f"{title}\n\n{desc}", parse_mode="HTML", reply_markup=kb)
    else:
        await event.answer(f"{title}\n\n{desc}", parse_mode="HTML", reply_markup=kb)
