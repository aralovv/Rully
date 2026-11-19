"""
Mistakes Practice ("Xatolar banki") Launcher for RULLY.
Directs users to the Mistakes Bank section in RULLY.
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
from src.bot.database import BotDatabase
from src.bot.config import WEB_APP_URL

mistakes_router = Router(name="mistakes_router")

@mistakes_router.message(Command("mistakes"))
@mistakes_router.message(F.text.in_([
    "🛠️ Xatolar ustida ishlash",
    "🛠️ Хатолар устида ишлаш",
    "🛠️ Работа над ошибками",
    "📚 Xatolar banki",
    "📚 Хатолар банки",
    "📚 Банк ошибок",
    "📚 Xatolarim ustida ishlash",
    "📚 Хатоларим устида ишлаш"
]))
@mistakes_router.callback_query(F.data == "menu:mistakes")
async def show_mistakes_flow(event: Message | CallbackQuery, db: BotDatabase):
    user_id = event.from_user.id
    lang = db.get_user_language(user_id)

    if isinstance(event, CallbackQuery):
        await event.answer()

    mistakes_count = len(db.get_user_mistakes(user_id))

    title = (
        "🛠️ <b>Xatolar ustida ishlash</b>" if lang == "uz_latn" else (
            "🛠️ <b>Хатолар устида ишлаш</b>" if lang == "uz_cyrl" else
            "🛠️ <b>Работа над ошибками</b>"
        )
    )

    if mistakes_count == 0:
        desc = (
            "🟢 <b>Ajoyib natija!</b> Hozircha sizda yechilmagan xatolar mavjud emas.\n\n"
            "Xatolar bankiga faqat siz belgilagan va xato deb topilgan savollar qo‘shiladi (tashlab ketilgan yoki belgilanmagan savollar qo‘shilmaydi).\n\n"
            "Bilimingizni sinash uchun <b>RULLY</b> platformasida Davlat imtihoni yoki Moslashuvchan test topshiring!" if lang == "uz_latn" else (
                "🟢 <b>Ажойиб натижа!</b> Ҳозирча сизда ечилмаган хатолар мавжуд эмас.\n\n"
                "Хатолар банкига фақат сиз белгилаган ва хато деб топилган саволлар қўшилади (ташлаб кетилган саволлар қўшилмайди).\n\n"
                "Билимингизни синаш учун <b>RULLY</b> платформасида Давлат имтиҳони ёки Мослашувчан тест топширинг!" if lang == "uz_cyrl" else
                "🟢 <b>Отличный результат!</b> У вас нет нерешенных ошибок.\n\n"
                "В банк ошибок попадают исключительно те вопросы, на которые вы дали неверный ответ (пропущенные вопросы не сохраняются).\n\n"
                "Для проверки знаний сдайте Государственный экзамен или пройдите настраиваемый тест в <b>RULLY</b>!"
            )
        )
    else:
        desc = (
            f"Sizda hozirda <b>{mistakes_count} ta</b> yechilmagan xato savol mavjud.\n\n"
            "Har bir xato ustida to‘g‘ri ishlaganingizdan so‘ng, u avtomatik tarzda xatolar ro‘yxatidan chiqariladi.\n\n"
            "Diagnostikani boshlash uchun quyidagi tugmani bosing:" if lang == "uz_latn" else (
                f"Сизда ҳозирда <b>{mistakes_count} та</b> ечилмаган хато савол мавжуд.\n\n"
                "Ҳар бир хато устида тўғри ишлаганингиздан сўнг, у автоматик тарзда хатолар рўйхатидан чиқарилади.\n\n"
                "Диагностикани бошлаш учун қуйидаги тугмани босинг:" if lang == "uz_cyrl" else
                f"У вас <b>{mistakes_count}</b> неисправленных ошибок.\n\n"
                "После верного повторного решения вопрос автоматически удаляется из базы ошибок.\n\n"
                "Для работы над ошибками нажмите кнопку ниже:"
            )
        )

    btn_text = (
        "🛠️ Diagnostikani ochish" if lang == "uz_latn" else (
            "🛠️ Диагностикани очиш" if lang == "uz_cyrl" else
            "🛠️ Открыть работу над ошибками"
        )
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, web_app=WebAppInfo(url=f"{WEB_APP_URL}#profile"))],
        [InlineKeyboardButton(text="🎛️ Bosh menyu" if lang == "uz_latn" else ("🎛️ Бош меню" if lang == "uz_cyrl" else "🎛️ Главное меню"), callback_data="menu:main")]
    ])

    if isinstance(event, CallbackQuery):
        await event.message.answer(f"{title}\n\n{desc}", parse_mode="HTML", reply_markup=kb)
    else:
        await event.answer(f"{title}\n\n{desc}", parse_mode="HTML", reply_markup=kb)
