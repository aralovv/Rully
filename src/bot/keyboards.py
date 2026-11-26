"""
Native Telegram Keyboards for Avtotest Bot.
Pure native Inline and Reply keyboards with full 3-language localization.
No Mini App or Web App buttons.
"""

from typing import List, Dict, Any, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from src.bot.strings import get_str
from src.bot.config import WEB_APP_URL

# 1. Language Selection Keyboard
def get_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O‘zbekcha (Lotin)", callback_data="lang:uz_latn")],
        [InlineKeyboardButton(text="🇺🇿 Ўзбекча (Кирилл)", callback_data="lang:uz_cyrl")],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru")]
    ])

# 2. Main Menu Keyboard (RULLY App Direct Launcher + Help)
def get_main_menu_keyboard(language: str = "uz_latn") -> InlineKeyboardMarkup:
    rully_btn = (
        "🚗 RULLY ilovasi" if language == "uz_latn" else (
            "🚗 RULLY иловаси" if language == "uz_cyrl" else
            "🚗 Приложение RULLY"
        )
    )
    help_btn = (
        "ℹ️ Yordam" if language == "uz_latn" else (
            "ℹ️ Ёрдам" if language == "uz_cyrl" else
            "ℹ️ Помощь"
        )
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=rully_btn, web_app=WebAppInfo(url=WEB_APP_URL))
        ],
        [
            InlineKeyboardButton(text=help_btn, callback_data="menu:help")
        ]
    ])

# 3. Persistent Reply Keyboard
def get_main_reply_keyboard(language: str = "uz_latn") -> ReplyKeyboardMarkup:
    rully_btn = (
        "🚗 RULLY ilovasi" if language == "uz_latn" else (
            "🚗 RULLY иловаси" if language == "uz_cyrl" else
            "🚗 Приложение RULLY"
        )
    )
    help_btn = (
        "ℹ️ Yordam" if language == "uz_latn" else (
            "ℹ️ Ёрдам" if language == "uz_cyrl" else
            "ℹ️ Помощь"
        )
    )
    return ReplyKeyboardMarkup(keyboard=[
        [
            KeyboardButton(text=rully_btn, web_app=WebAppInfo(url=WEB_APP_URL)),
            KeyboardButton(text=help_btn)
        ]
    ], resize_keyboard=True)

# 4. Interactive Pre-Test Settings Widget Keyboard
def get_custom_settings_keyboard(settings: Dict[str, Any], language: str = "uz_latn") -> InlineKeyboardMarkup:
    """
    Renders interactive toggles for:
    - Question Count (10, 20, 30, 50, 100, 122)
    - Time Limit (0, 10, 20, 30, 60 min)
    - Instant Answer Check (True / False)
    - Legal Explanation (True / False)
    """
    curr_cnt = settings.get("count", 20)
    curr_time = settings.get("time_min", 20)
    show_ans = settings.get("show_answer", True)
    show_expl = settings.get("show_expl", True)

    # Row 1: Question Count Options
    count_options = [10, 20, 30, 50, 100, 122]
    cnt_buttons = []
    for c in count_options:
        label = f"🔘 {c}" if c == curr_cnt else f"{c}"
        cnt_buttons.append(InlineKeyboardButton(text=label, callback_data=f"cfg:cnt:{c}"))

    # Row 2: Time Limit Options
    time_options = [
        (0, "♾️" if language != "ru" else "♾️"),
        (10, "10m" if language == "uz_latn" else ("10д" if language == "uz_cyrl" else "10м")),
        (20, "20m" if language == "uz_latn" else ("20д" if language == "uz_cyrl" else "20м")),
        (30, "30m" if language == "uz_latn" else ("30д" if language == "uz_cyrl" else "30м")),
        (60, "60m" if language == "uz_latn" else ("60д" if language == "uz_cyrl" else "60м"))
    ]
    time_buttons = []
    for t_val, t_label in time_options:
        label = f"🔘 {t_label}" if t_val == curr_time else t_label
        time_buttons.append(InlineKeyboardButton(text=label, callback_data=f"cfg:time:{t_val}"))

    # Row 3: Answer feedback toggle
    if language == "uz_latn":
        ans_label = f"🎯 Javob: {'✅ Darhol' if show_ans else '❌ Faqat oxirida'}"
    elif language == "uz_cyrl":
        ans_label = f"🎯 Жавоб: {'✅ Дарҳол' if show_ans else '❌ Фақат якунда'}"
    else:
        ans_label = f"🎯 Показ ответа: {'✅ Сразу' if show_ans else '❌ Только в конце'}"

    # Row 4: Explanation toggle
    if language == "uz_latn":
        expl_label = f"💡 Qonuniy izoh: {'✅ Ha' if show_expl else '❌ Yo‘q'}"
    elif language == "uz_cyrl":
        expl_label = f"💡 Қонуний изоҳ: {'✅ Ҳа' if show_expl else '❌ Йўқ'}"
    else:
        expl_label = f"💡 Пояснение ПДД: {'✅ Да' if show_expl else '❌ Нет'}"

    # Row 5: Start Button
    start_label = get_str("settings_btn_start", language, count=curr_cnt)

    return InlineKeyboardMarkup(inline_keyboard=[
        cnt_buttons,
        time_buttons,
        [InlineKeyboardButton(text=ans_label, callback_data="cfg:toggle:ans")],
        [InlineKeyboardButton(text=expl_label, callback_data="cfg:toggle:expl")],
        [InlineKeyboardButton(text=start_label, callback_data="cfg:action:start")],
        [InlineKeyboardButton(text=get_str("btn_back", language), callback_data="menu:main")]
    ])

# 5. Quiz Option Selection Keyboard
def get_quiz_options_keyboard(options: List[Dict[str, Any]], session_id: str,
                              selected_key: Optional[str] = None,
                              correct_key: Optional[str] = None,
                              language: str = "uz_latn") -> InlineKeyboardMarkup:
    """
    Renders styled option buttons: [ 🅰️ A ], [ 🅱️ B ], [ 🅲 C ], [ 🅳 D ]
    """
    emoji_map = {"A": "🅰️", "B": "🅱️", "C": "🅲", "D": "🅳", "E": "🅴"}
    buttons = []
    for opt in options:
        key = opt["key"]
        icon = emoji_map.get(key, key)
        if selected_key:
            if key == correct_key:
                label = f"✅ {key}"
            elif key == selected_key:
                label = f"❌ {key}"
            else:
                label = f"{key}"
            cb_data = "quiz:noop"
        else:
            label = f"{icon} {key}"
            cb_data = f"ans:{session_id}:{key}"

        buttons.append(InlineKeyboardButton(text=label, callback_data=cb_data))

    rows = [buttons]
    if not selected_key:
        rows.append([
            InlineKeyboardButton(text=get_str("btn_finish_early", language), callback_data=f"quiz:finish:{session_id}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# 6. Quiz Feedback Navigation Keyboard
def get_quiz_feedback_keyboard(session_id: str, is_last_question: bool = False,
                               language: str = "uz_latn") -> InlineKeyboardMarkup:
    if is_last_question:
        if language == "ru":
            next_label = "🏁 Посмотреть результаты"
        elif language == "uz_cyrl":
            next_label = "🏁 Натижани кўриш"
        else:
            next_label = "🏁 Natijani ko‘rish"
    else:
        next_label = get_str("btn_next_question", language)

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=next_label, callback_data=f"quiz:next:{session_id}")
        ],
        [
            InlineKeyboardButton(text=get_str("btn_main_menu", language), callback_data="menu:main")
        ]
    ])

# 7. Mistakes Navigation Keyboard
def get_mistakes_intro_keyboard(count: int, language: str = "uz_latn") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_str("btn_start_mistakes", language, count=count), callback_data="mistakes:start")
        ],
        [
            InlineKeyboardButton(text=get_str("btn_main_menu", language), callback_data="menu:main")
        ]
    ])

def get_no_mistakes_keyboard(language: str = "uz_latn") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_str("btn_exam", language), callback_data="menu:exam")
        ],
        [
            InlineKeyboardButton(text=get_str("btn_custom_test", language), callback_data="menu:custom_test")
        ],
        [
            InlineKeyboardButton(text=get_str("btn_main_menu", language), callback_data="menu:main")
        ]
    ])

# 8. Results Keyboard
def get_results_keyboard(session_id: str, language: str = "uz_latn",
                         has_mistakes: bool = True) -> InlineKeyboardMarkup:
    rows = []
    if has_mistakes:
        rows.append([
            InlineKeyboardButton(text=get_str("btn_retry_mistakes", language), callback_data="menu:mistakes")
        ])
    rows.append([
        InlineKeyboardButton(text=get_str("btn_start_new_exam", language), callback_data="menu:exam")
    ])
    rows.append([
        InlineKeyboardButton(text=get_str("btn_main_menu", language), callback_data="menu:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# 9. Categories Selection Keyboard (Paginated)
def get_categories_keyboard(categories: List[Dict[str, Any]], page: int = 0,
                            page_size: int = 5, language: str = "uz_latn") -> InlineKeyboardMarkup:
    total_cats = len(categories)
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, total_cats)
    current_page_cats = categories[start_idx:end_idx]

    rows = []
    for cat in current_page_cats:
        cat_id = cat["category_id"]
        cat_name = cat["name"]
        q_count = cat["question_count"]
        label = f"{cat_name} ({q_count})"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"cat:select:{cat_id}")])

    # Pagination navigation row
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"cat:page:{page - 1}"))
    
    total_pages = ((total_cats - 1) // page_size) + 1 if total_cats > 0 else 1
    nav_row.append(InlineKeyboardButton(text=f"{page + 1} / {total_pages}", callback_data="cat:noop"))

    if end_idx < total_cats:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"cat:page:{page + 1}"))

    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text=get_str("btn_back", language), callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_webapp_route_url(route: str = "") -> str:
    """Builds resilient Mini App deep-link URL preserving both query param and fragment."""
    base = WEB_APP_URL.split("?")[0].split("#")[0].rstrip("/")
    clean_route = (route or "").strip().lstrip("#").lstrip("/")
    if not clean_route:
        return base
    return f"{base}?route={clean_route}#{clean_route}"


# 11. Deep-Link Section Card Keyboard
def get_deep_link_card_keyboard(
    route_target: str,
    app_btn_text: str,
    language: str = "uz_latn",
    inline_callback: Optional[str] = None,
    inline_btn_text: Optional[str] = None,
) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=app_btn_text, web_app=WebAppInfo(url=build_webapp_route_url(route_target)))]
    ]
    if inline_callback and inline_btn_text:
        rows.append([InlineKeyboardButton(text=inline_btn_text, callback_data=inline_callback)])
    rows.append([InlineKeyboardButton(text=get_str("btn_main_menu", language), callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# 12. Help / Quick Mini App Section Shortcuts Hub
def get_help_sections_keyboard(language: str = "uz_latn") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=get_str("btn_exam", language), web_app=WebAppInfo(url=build_webapp_route_url("exam"))),
        ],
        [
            InlineKeyboardButton(text=get_str("btn_srs_review", language), callback_data="menu:srs"),
            InlineKeyboardButton(text=get_str("btn_bilets", language), callback_data="menu:bilets"),
        ],
        [
            InlineKeyboardButton(text=get_str("btn_signs", language), web_app=WebAppInfo(url=build_webapp_route_url("signs"))),
            InlineKeyboardButton(text=get_str("btn_rules", language), web_app=WebAppInfo(url=build_webapp_route_url("rules"))),
        ],
        [
            InlineKeyboardButton(text=get_str("btn_amaliy", language), web_app=WebAppInfo(url=build_webapp_route_url("amaliy"))),
            InlineKeyboardButton(text=get_str("btn_ai_ustoz", language), web_app=WebAppInfo(url=build_webapp_route_url("ai"))),
        ],
        [
            InlineKeyboardButton(text=get_str("btn_back", language), callback_data="menu:main")
        ],
    ])


# 13. Official Ticket (Bilet 1..67) Selector Keyboard
def get_bilet_selection_keyboard(
    total_tickets: int = 67,
    page: int = 0,
    page_size: int = 10,
    language: str = "uz_latn",
) -> InlineKeyboardMarkup:
    safe_total = max(1, int(total_tickets))
    total_pages = ((safe_total - 1) // page_size) + 1
    page = max(0, min(page, total_pages - 1))
    start_num = page * page_size + 1
    end_num = min(start_num + page_size - 1, safe_total)

    rows = []
    current_row = []
    for ticket_no in range(start_num, end_num + 1):
        current_row.append(InlineKeyboardButton(text=f"#{ticket_no}", callback_data=f"bilet:start:{ticket_no}"))
        if len(current_row) == 5:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"bilet:page:{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"{page + 1} / {total_pages}", callback_data="bilet:noop"))
    if page + 1 < total_pages:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"bilet:page:{page + 1}"))
    rows.append(nav_row)

    rows.append([
        InlineKeyboardButton(text=get_str("btn_rully_app", language), web_app=WebAppInfo(url=build_webapp_route_url("tickets")))
    ])
    rows.append([InlineKeyboardButton(text=get_str("btn_main_menu", language), callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# 10. Admin Keyboard
def get_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Tizim holati", callback_data="admin:health"),
            InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin:users")
        ],
        [
            InlineKeyboardButton(text="📢 Xabar yuborish (Broadcast)", callback_data="admin:broadcast")
        ],
        [
            InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="menu:main")
        ]
    ])
