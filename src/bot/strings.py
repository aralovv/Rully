"""
Comprehensive 3-Language Localization Dictionary for Avtotest Telegram Bot.
Supports:
- uz_latn (O'zbekcha Lotin)
- uz_cyrl (Ўзбекча Кирилл)
- ru (Русский)
Guarantees 100% language purity in Cyrillic and Russian.
Bespoke automotive & state driving examination iconography.
"""

from typing import Dict, Any

STRINGS: Dict[str, Dict[str, str]] = {
    "uz_latn": {
        # Brand & Welcome
        "welcome_title": "🛞 <b>RULLY</b>",
        "welcome_text": (
            "Assalomu alaykum! O‘zbekiston davlat haydovchilik guvohnomasi imtihonlariga "
            "tayyorgarlik ko‘rish <b>RULLY</b> platformasiga xush kelibsiz."
        ),
        "language_selected": "✅ Interfeys tili: <b>O‘zbekcha (Lotin)</b> o‘rnatildi.",
        "menu_title": "🛞 <b>RULLY BOSHQARUV PANELI</b>",

        # Main Menu Buttons (The Core Modes)
        "btn_rully_app": "🛞 RULLY ilovasi",
        "btn_exam": "🏛️ Davlat nazariy imtihoni (20)",
        "btn_custom_test": "🔀 Moslashuvchan test (Aralash)",
        "btn_amaliy": "🚧 Avtodrom va amaliy mashqlar",
        "btn_categories": "🚦 YHQ mavzulari bo‘yicha",
        "btn_quick_test": "⏱️ Tezkor ekspress-test (10)",
        "btn_mistakes": "🛠️ Xatolar ustida ishlash",
        "btn_results": "🪪 Haydovchilik darajasi (Indeks)",
        "btn_settings": "🗺️ Tizim tili",
        "btn_help": "🔰 Nizom va qoidalar",

        # Card Widget Headers
        "card_header_exam": "🏛️ <b>DAVLAT NAZARIY IMTIHONI (VMQ 408)</b>",
        "card_header_custom": "🔀 <b>MOSLASHUVCHAN MASHG‘ULOT</b>",
        "card_header_mistakes": "🛠️ <b>XATOLARNI DIAGNOSTIKA QILISH</b>",
        "card_header_category": "🚦 <b>YHQ MAVZUSI BO‘YICHA SINOV</b>",
        "card_header_quick": "⏱️ <b>TEZKOR EKSPRESS-SINOV</b>",

        "question_progress": "Savol: <b>{current}/{total}</b>",
        "card_badge_question": "📋 <b>Savol:</b> [ <b>{current:02d} / {total:02d}</b> ]",
        "card_badge_time": "⏱️ <b>Vaqt:</b> [ <b>{mins:02d}:{secs:02d}</b> ]",
        "card_badge_category": "🏷️ <b>Bo‘lim:</b> [ <i>{category}</i> ]",

        # Card Feedback Headers
        "feedback_correct_header": "🟢 <b>TO‘G‘RI JAVOB!</b>",
        "feedback_incorrect_header": "🔴 <b>XATO JAVOB!</b>",
        "feedback_correct_tag": "<i>(To‘g‘ri javob)</i>",
        "feedback_selected_wrong_tag": "<i>(Sizning javobingiz)</i>",

        # Common Navigation
        "btn_back": "↩️ Orqaga",
        "btn_main_menu": "🎛️ Bosh menyu",
        "btn_next_question": "Keyingi savol ⏩",
        "btn_finish_early": "🏁 Testni yakunlash",
        "btn_retry_mistakes": "🔄 Xatolarni qayta yechish",
        "btn_start_new_exam": "🏛️ Yangi davlat imtihoni",

        # Pre-test Settings Widget
        "settings_widget_title": "🎛️ <b>MOSLASHUVCHAN TEST SOZLAMALARI</b>",
        "settings_widget_desc": "Mashg‘ulotni boshlashdan oldin parametrlarni o‘zingizga moslang:",
        "settings_label_count": "📊 <b>Savollar miqdori:</b> [ <b>{count} ta</b> ]",
        "settings_label_time": "⏱️ <b>Vaqt chegarasi:</b> [ <b>{time_str}</b> ]",
        "settings_label_answer": "🎯 <b>Natijani ko‘rsatish:</b> [ <b>{ans_str}</b> ]",
        "settings_label_expl": "⚖️ <b>Qonuniy asos:</b> [ <b>{expl_str}</b> ]",
        "settings_btn_start": "🚦 Testni boshlash ({count} ta savol)",
        "settings_unlimited": "♾️ Cheksiz",
        "settings_minutes": "{mins} daqiqa",
        "settings_yes": "🟢 Ha (Darhol)",
        "settings_no": "⚪ Faqat yakunda",
        "settings_expl_yes": "🟢 Ha",
        "settings_expl_no": "⚪ Yo‘q",

        # Legal References & Feedback
        "correct_answer_feedback": "🟢 <b>TO‘G‘RI JAVOB!</b>",
        "incorrect_answer_feedback": "🔴 <b>XATO JAVOB!</b>\nTo‘g‘ri javob: <b>[{correct_key}]</b>",
        "legal_reference_header": "⚖️ <b>Huquqiy asos (YHQ moddasi):</b>",
        "explanation_header": "🔍 <b>Ekspert tahlili:</b>",

        # Exam Results
        "result_passed_title": "🎉 <b>TABRIKLAYMIZ! DAVLAT IMTIHONI TOPSHIRILDI!</b>",
        "result_failed_title": "🛑 <b>DAVLAT IMTIHONI TOPSHIRILMADI</b>",
        "result_summary": (
            "📊 <b>Yakuniy bayonnoma ko‘rsatkichlari:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "• Jami savollar: <b>{total} ta</b>\n"
            "• To‘g‘ri javoblar: <b>{correct} ta</b> ({percentage}%)\n"
            "• Xatolar soni: <b>{incorrect} ta</b>\n"
            "• Sarflangan vaqt: <b>{time_str}</b>\n"
            "• Davlat standarti: <b>kamida 18 ta (90%)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>Yakuniy xulosa:</b> {status_text}\n"
        ),
        "status_passed": "🟢 <b>MUVAFFAQIYATLI (O‘TDI)</b>",
        "status_failed": "🔴 <b>YIQILDI (VMQ 408 talabi)</b>",

        # Mistakes Mode
        "no_mistakes": (
            "🟢 <b>Ajoyib ko‘rsatkich!</b>\n\n"
            "Sizda hozircha diagnostika qilinadigan xatolar mavjud emas.\n"
            "Bilimingizni sinash uchun davlat imtihonini topshiring yoki moslashuvchan test ishlang!"
        ),
        "mistakes_intro": (
            "🛠️ <b>XATOLARNI DIAGNOSTIKA QILISH VA TUZATISH</b>\n\n"
            "Siz ilgari noaniq javob bergan <b>{count} ta</b> savol bo‘yicha tahliliy test tayyorlandi.\n"
            "Har bir to‘g‘ri yechilgan savol xatolar ro‘yxatidan chiqariladi."
        ),
        "btn_start_mistakes": "🚦 Mashg‘ulotni boshlash ({count} ta savol)",

        # Stats
        "stats_title": "🪪 <b>HAYDOVCHILIK TAYYORGARLIK KO‘RSATKICHLARI</b>",
        "stats_text": (
            "• Topshirilgan davlat imtihonlari: <b>{total_exams} ta</b>\n"
            "• Muvaffaqiyatli topshirilgan: <b>{passed_exams} ta</b>\n"
            "• O‘tish ko‘rsatkichi: <b>{pass_rate}%</b>\n"
            "• Jami yechilgan savollar: <b>{total_questions} ta</b>\n"
            "• Aniqlik indeksi: <b>{accuracy}%</b>\n"
            "• Qolgan xatolar: <b>{unresolved_mistakes} ta</b>\n"
        ),

        # Help
        "help_text": (
            "🔰 <b>DAVLAT IMTIHONI VA PLATFORMA NIZOMI</b>\n\n"
            "<b>Davlat nazariy imtihoni (VMQ 408):</b>\n"
            "• Imtihon biletida 20 ta tasodifiy savol beriladi.\n"
            "• Ajratilgan vaqt: 25 daqiqa.\n"
            "• O‘tish meʼyori: kamida 18 ta to‘g‘ri javob (ko‘pi bilan 2 ta xatoga ruxsat beriladi).\n\n"
            "<b>RULLY platformasi bo‘limlari:</b>\n"
            "1. 🏛️ <b>Davlat imtihoni:</b> SBDD kompyuterlashtirilgan zal terminali andozasida.\n"
            "2. 🔀 <b>Moslashuvchan test:</b> Savollar soni, vaqt nazorati va qonuniy izohlarni mustaqil sozlash.\n"
            "3. 🚧 <b>Avtodrom va amaliyot:</b> 10 ta amaliy mashq, bosqichma-bosqich cheklist va imtihon vaziyatlari.\n"
            "4. 🛠️ <b>Xatolar ustida ishlash:</b> Faqat siz mustaqil ishlab adashgan savollaringiz diagnostikasi.\n"
            "5. 🪪 <b>Haydovchilik indeksi:</b> Real bilim va tayyorgarlik darajangizni hisoblaydi."
        ),

        # Errors & Notifications
        "active_session_exists": "⚠️ Sizda faol test seansi mavjud. Davom eting yoki uni yakunlang.",
        "session_expired": "⏱️ <b>Vaqt tugadi!</b> Belgilangan imtihon vaqti yakunlandi.",
        "session_cancelled": "🛑 Test seansi bekor qilindi.",
        "already_answered": "⚠️ Siz bu savolga allaqachon javob bergansiz.",
        "error_generic": "⚠️ Tizimda xatolik yuz berdi. Iltimos, /menu orqali qayta urinib ko‘ring."
    },

    "uz_cyrl": {
        # Brand & Welcome
        "welcome_title": "🛞 <b>RULLY</b>",
        "welcome_text": (
            "Ассалому алайкум! Ўзбекистон давлат ҳайдовчилик гувоҳномаси имтиҳонларига "
            "тайёргарлик кўриш <b>RULLY</b> платформасига хуш келибсиз."
        ),
        "language_selected": "✅ Интерфейс тили: <b>Ўзбекча (Кирилл)</b> ўрнатилди.",
        "menu_title": "🛞 <b>RULLY БОШҚАРУВ ПАНЕЛИ</b>",

        # Main Menu Buttons
        "btn_rully_app": "🛞 RULLY иловаси",
        "btn_exam": "🏛️ Давлат назарий имтиҳони (20)",
        "btn_custom_test": "🔀 Мослашувчан тест (Аралаш)",
        "btn_amaliy": "🚧 Автодром ва амалий машқлар",
        "btn_categories": "🚦 ЙҲҚ мавзулари бўйича",
        "btn_quick_test": "⏱️ Тезкор экспресс-тест (10)",
        "btn_mistakes": "🛠️ Хатолар устида ишлаш",
        "btn_results": "🪪 Ҳайдовчилик даражаси (Индекс)",
        "btn_settings": "🗺️ Тизим тили",
        "btn_help": "🔰 Низом ва қоидалар",

        # Card Widget Headers
        "card_header_exam": "🏛️ <b>ДАВЛАТ НАЗАРИЙ ИМТИҲОНИ (ВМҚ 408)</b>",
        "card_header_custom": "🔀 <b>МОСЛАШУВЧАН МАШҒУЛОТ</b>",
        "card_header_mistakes": "🛠️ <b>ХАТОЛАРНИ ДИАГНОСТИКА ҚИЛИШ</b>",
        "card_header_category": "🚦 <b>ЙҲҚ МАВЗУСИ БЎЙИЧА СИНОВ</b>",
        "card_header_quick": "⏱️ <b>ТЕЗКОР ЭКСПРЕСС-СИНОВ</b>",

        "question_progress": "Савол: <b>{current}/{total}</b>",
        "card_badge_question": "📋 <b>Савол:</b> [ <b>{current:02d} / {total:02d}</b> ]",
        "card_badge_time": "⏱️ <b>Вақт:</b> [ <b>{mins:02d}:{secs:02d}</b> ]",
        "card_badge_category": "🏷️ <b>Бўлим:</b> [ <i>{category}</i> ]",

        # Card Feedback Headers
        "feedback_correct_header": "🟢 <b>ТЎҒРИ ЖАВОБ!</b>",
        "feedback_incorrect_header": "🔴 <b>ХАТО ЖАВОБ!</b>",
        "feedback_correct_tag": "<i>(Тўғри жавоб)</i>",
        "feedback_selected_wrong_tag": "<i>(Сизнинг жавобингиз)</i>",

        # Common Navigation
        "btn_back": "↩️ Орқага",
        "btn_main_menu": "🎛️ Бош меню",
        "btn_next_question": "Кейинги савол ⏩",
        "btn_finish_early": "🏁 Тестни якунлаш",
        "btn_retry_mistakes": "🔄 Хатоларни қайта ечиш",
        "btn_start_new_exam": "🏛️ Янги давлат имтиҳони",

        # Pre-test Settings Widget
        "settings_widget_title": "🎛️ <b>МОСЛАШУВЧАН ТЕСТ СОЗЛАМАЛАРИ</b>",
        "settings_widget_desc": "Машғулотни бошлашдан олдин параметрларни ўзингизга мосланг:",
        "settings_label_count": "📊 <b>Саволлар миқдори:</b> [ <b>{count} та</b> ]",
        "settings_label_time": "⏱️ <b>Вақт чегараси:</b> [ <b>{time_str}</b> ]",
        "settings_label_answer": "🎯 <b>Натижани кўрсатиш:</b> [ <b>{ans_str}</b> ]",
        "settings_label_expl": "⚖️ <b>Қонуний асос:</b> [ <b>{expl_str}</b> ]",
        "settings_btn_start": "🚦 Тестни бошлаш ({count} та савол)",
        "settings_unlimited": "♾️ Чексиз",
        "settings_minutes": "{mins} дақиқа",
        "settings_yes": "🟢 Ҳа (Дарҳол)",
        "settings_no": "⚪ Фақат якунда",
        "settings_expl_yes": "🟢 Ҳа",
        "settings_expl_no": "⚪ Йўқ",

        # Legal References & Feedback
        "correct_answer_feedback": "🟢 <b>ТЎҒРИ ЖАВОБ!</b>",
        "incorrect_answer_feedback": "🔴 <b>ХАТО ЖАВОБ!</b>\nТўғри жавоб: <b>[{correct_key}]</b>",
        "legal_reference_header": "⚖️ <b>Ҳуқуқий асос (ЙҲҚ моддаси):</b>",
        "explanation_header": "🔍 <b>Эксперт таҳлили:</b>",

        # Exam Results
        "result_passed_title": "🎉 <b>ТАБРИКЛАЙМИЗ! ДАВЛАТ ИМТИҲОНИ ТОПШИРИЛДИ!</b>",
        "result_failed_title": "🛑 <b>ДАВЛАТ ИМТИҲОНИ ТОПШИРИЛМАДИ</b>",
        "result_summary": (
            "📊 <b>Якуний баённома кўрсаткичлари:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "• Жами саволлар: <b>{total} та</b>\n"
            "• Тўғри жавоблар: <b>{correct} та</b> ({percentage}%)\n"
            "• Хатолар сони: <b>{incorrect} та</b>\n"
            "• Сарфланган вақт: <b>{time_str}</b>\n"
            "• Давлат стандарти: <b>камида 18 та (90%)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>Якуний хулоса:</b> {status_text}\n"
        ),
        "status_passed": "🟢 <b>МУВАФФАҚИЯТЛИ (ЎТДИ)</b>",
        "status_failed": "🔴 <b>ЙИҚИЛДИ (ВМҚ 408 талаби)</b>",

        # Mistakes Mode
        "no_mistakes": (
            "🟢 <b>Ажойиб кўрсаткич!</b>\n\n"
            "Сизда ҳозирча диагностика қилинадиган хатолар мавжуд эмас.\n"
            "Билимингизни синаш учун давлат имтиҳонини топширинг ёки мослашувчан тест ишланг!"
        ),
        "mistakes_intro": (
            "🛠️ <b>ХАТОЛАРНИ ДИАГНОСТИКА ҚИЛИШ ВА ТУЗАТИШ</b>\n\n"
            "Сиз илгари ноаниқ жавоб берган <b>{count} та</b> савол бўйича таҳлилий тест тайёрланди.\n"
            "Ҳар бир тўғри ечилган савол хатолар рўйхатидан чиқарилади."
        ),
        "btn_start_mistakes": "🚦 Машғулотни бошлаш ({count} та савол)",

        # Stats
        "stats_title": "🪪 <b>ҲАЙДОВЧИЛИК ТАЙЁРГАРЛИК КЎРСАТКИЧЛАРИ</b>",
        "stats_text": (
            "• Топширилган давлат имтиҳонлари: <b>{total_exams} та</b>\n"
            "• Муваффақиятли топширилган: <b>{passed_exams} та</b>\n"
            "• Ўтиш кўрсаткичи: <b>{pass_rate}%</b>\n"
            "• Жами ечилган саволлар: <b>{total_questions} та</b>\n"
            "• Аниқлик индекси: <b>{accuracy}%</b>\n"
            "• Қолган хатолар: <b>{unresolved_mistakes} та</b>\n"
        ),

        # Help
        "help_text": (
            "🔰 <b>ДАВЛАТ ИМТИҲОНИ ВА ПЛАТФОРМА НИЗОМИ</b>\n\n"
            "<b>Давлат назарий имтиҳони (ВМҚ 408):</b>\n"
            "• Имтиҳон билетида 20 та тасодифий савол берилади.\n"
            "• Ажратилган вақт: 25 дақиқа.\n"
            "• Ўтиш меъёри: камида 18 та тўғри жавоб (кўпи билан 2 та хатога рухсат берилади).\n\n"
            "<b>RULLY платформаси бўлимлари:</b>\n"
            "1. 🏛️ <b>Давлат имтиҳони:</b> СБДД компьютерлаштирилган зал терминали андозасида.\n"
            "2. 🔀 <b>Мослашувчан тест:</b> Саволлар сони, вақт назорати ва қонуний изоҳларни мустақил созлаш.\n"
            "3. 🚧 <b>Автодром ва амалиёт:</b> 10 та амалий машқ, босқичма-босқич чек-лист ва имтиҳон вазиятлари.\n"
            "4. 🛠️ <b>Хатолар устида ишлаш:</b> Фақат сиз мустақил ишлаб адашган саволларингиз диагностикаси.\n"
            "5. 🪪 <b>Ҳайдовчилик индекси:</b> Реал билим ва тайёргарлик даражангизни ҳисоблайди."
        ),

        # Errors
        "active_session_exists": "⚠️ Сизда фаол тест сеанси мавжуд. Давом этинг ёки уни якунланг.",
        "session_expired": "⏱️ <b>Вақт тугади!</b> Белгиланган имтиҳон вақти якунланди.",
        "session_cancelled": "🛑 Тест сеанси бекор қилинди.",
        "already_answered": "⚠️ Сиз бу саволга аллақачон жавоб бергансиз.",
        "error_generic": "⚠️ Тизимда хатолик юз берди. Илтимос, /menu орқали қайта уриниб кўринг."
    },

    "ru": {
        # Brand & Welcome
        "welcome_title": "🛞 <b>RULLY</b>",
        "welcome_text": (
            "Здравствуйте! Добро пожаловать на платформу <b>RULLY</b> "
            "для подготовки к государственным экзаменам на получение водительского удостоверения."
        ),
        "language_selected": "✅ Язык интерфейса установлен: <b>Русский</b>.",
        "menu_title": "🛞 <b>ПАНЕЛЬ УПРАВЛЕНИЯ RULLY</b>",

        # Main Menu Buttons
        "btn_rully_app": "🛞 Приложение RULLY",
        "btn_exam": "🏛️ Теоретический госэкзамен (20)",
        "btn_custom_test": "🔀 Настраиваемый тест (Микс)",
        "btn_amaliy": "🚧 Автодром и практические упражнения",
        "btn_categories": "🚦 Темы и категории ПДД",
        "btn_quick_test": "⏱️ Экспресс-тест (10 вопросов)",
        "btn_mistakes": "🛠️ Работа над ошибками",
        "btn_results": "🪪 Индекс готовности водителя",
        "btn_settings": "🗺️ Язык интерфейса",
        "btn_help": "🔰 Регламент и правила",

        # Card Widget Headers
        "card_header_exam": "🏛️ <b>ГОСУДАРСТВЕННЫЙ ЭКЗАМЕН (ПКМ 408)</b>",
        "card_header_custom": "🔀 <b>НАСТРАИВАЕМЫЙ ТРЕНИНГ</b>",
        "card_header_mistakes": "🛠️ <b>ДИАГНОСТИКА И РАЗБОР ОШИБОК</b>",
        "card_header_category": "🚦 <b>ТЕСТИРОВАНИЕ ПО ТЕМЕ ПДД</b>",
        "card_header_quick": "⏱️ <b>ЭКСПРЕСС-ТЕСТИРОВАНИЕ</b>",

        "question_progress": "Вопрос: <b>{current}/{total}</b>",
        "card_badge_question": "📋 <b>Вопрос:</b> [ <b>{current:02d} / {total:02d}</b> ]",
        "card_badge_time": "⏱️ <b>Время:</b> [ <b>{mins:02d}:{secs:02d}</b> ]",
        "card_badge_category": "🏷️ <b>Раздел:</b> [ <i>{category}</i> ]",

        # Card Feedback Headers
        "feedback_correct_header": "🟢 <b>ВЕРНЫЙ ОТВЕТ!</b>",
        "feedback_incorrect_header": "🔴 <b>НЕВЕРНЫЙ ОТВЕТ!</b>",
        "feedback_correct_tag": "<i>(Правильный ответ)</i>",
        "feedback_selected_wrong_tag": "<i>(Ваш ответ)</i>",

        # Common Navigation
        "btn_back": "↩️ Назад",
        "btn_main_menu": "🎛️ Главное меню",
        "btn_next_question": "Следующий вопрос ⏩",
        "btn_finish_early": "🏁 Завершить тест",
        "btn_retry_mistakes": "🔄 Повторить ошибки",
        "btn_start_new_exam": "🏛️ Новый госэкзамен",

        # Pre-test Settings Widget
        "settings_widget_title": "🎛️ <b>ПАРАМЕТРЫ И НАСТРОЙКИ ТЕСТИРОВАНИЯ</b>",
        "settings_widget_desc": "Настройте параметры тестирования перед началом:",
        "settings_label_count": "📊 <b>Количество вопросов:</b> [ <b>{count}</b> ]",
        "settings_label_time": "⏱️ <b>Лимит времени:</b> [ <b>{time_str}</b> ]",
        "settings_label_answer": "🎯 <b>Показ ответа:</b> [ <b>{ans_str}</b> ]",
        "settings_label_expl": "⚖️ <b>Нормативный пункт:</b> [ <b>{expl_str}</b> ]",
        "settings_btn_start": "🚦 Начать тест ({count} вопросов)",
        "settings_unlimited": "♾️ Без лимита",
        "settings_minutes": "{mins} минут",
        "settings_yes": "🟢 Да (Сразу)",
        "settings_no": "⚪ Только в конце",
        "settings_expl_yes": "🟢 Да",
        "settings_expl_no": "⚪ Нет",

        # Legal References & Feedback
        "correct_answer_feedback": "🟢 <b>ВЕРНО!</b>",
        "incorrect_answer_feedback": "🔴 <b>НЕВЕРНО!</b>\nПравильный ответ: <b>[{correct_key}]</b>",
        "legal_reference_header": "⚖️ <b>Нормативный пункт ПДД:</b>",
        "explanation_header": "🔍 <b>Экспертный анализ:</b>",

        # Exam Results
        "result_passed_title": "🎉 <b>ПОЗДРАВЛЯЕМ! ГОСУДАРСТВЕННЫЙ ЭКЗАМЕН СДАН!</b>",
        "result_failed_title": "🛑 <b>ГОСУДАРСТВЕННЫЙ ЭКЗАМЕН НЕ СДАН</b>",
        "result_summary": (
            "📊 <b>Итоговый протокол тестирования:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "• Всего вопросов: <b>{total}</b>\n"
            "• Правильных ответов: <b>{correct}</b> ({percentage}%)\n"
            "• Ошибок: <b>{incorrect}</b>\n"
            "• Затраченное время: <b>{time_str}</b>\n"
            "• Государственный норматив: <b>минимум 18 (90%)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>Заключение комиссии:</b> {status_text}\n"
        ),
        "status_passed": "🟢 <b>СДАНО УСПЕШНО</b>",
        "status_failed": "🔴 <b>НЕ СДАНО (требование ПКМ 408)</b>",

        # Mistakes Mode
        "no_mistakes": (
            "🟢 <b>Отличный результат!</b>\n\n"
            "У вас нет зафиксированных ошибок для разбора.\n"
            "Чтобы проверить знания, сдайте официальный госэкзамен или начните настраиваемый тест!"
        ),
        "mistakes_intro": (
            "🛠️ <b>ДИАГНОСТИКА И РАБОТА НАД ОШИБКАМИ</b>\n\n"
            "Сформирован тренировочный тест из <b>{count}</b> вопросов, в которых вы ранее допустили неточность.\n"
            "Каждый правильно решенный вопрос исключается из базы ошибок."
        ),
        "btn_start_mistakes": "🚦 Начать тренировку ({count} вопросов)",

        # Stats
        "stats_title": "🪪 <b>ПОКАЗАТЕЛИ ГОТОВНОСТИ ВОДИТЕЛЯ</b>",
        "stats_text": (
            "• Сдано госэкзаменов: <b>{total_exams}</b>\n"
            "• Успешно сданных: <b>{passed_exams}</b>\n"
            "• Процент сдачи: <b>{pass_rate}%</b>\n"
            "• Всего решено вопросов: <b>{total_questions}</b>\n"
            "• Индекс точности: <b>{accuracy}%</b>\n"
            "• Нерешенных ошибок: <b>{unresolved_mistakes}</b>\n"
        ),

        # Help
        "help_text": (
            "🔰 <b>РЕГЛАМЕНТ ГОСЭКЗАМЕНА И ПРАВИЛА ПЛАТФОРМЫ</b>\n\n"
            "<b>Теоретический экзамен (ПКМ 408):</b>\n"
            "• Экзаменационный билет состоит из 20 случайных вопросов.\n"
            "• Время на выполнение: 25 минут.\n"
            "• Стандарт сдачи: минимум 18 правильных ответов (допускается не более 2 ошибок).\n\n"
            "<b>Разделы платформы RULLY:</b>\n"
            "1. 🏛️ <b>Теоретический госэкзамен:</b> Точный аналог автоматизированного терминала СБДД.\n"
            "2. 🔀 <b>Настраиваемый тест:</b> Выбор числа вопросов, управление таймером и нормативные комментарии.\n"
            "3. 🚧 <b>Автодром и практика:</b> 10 практических модулей, чек-лист готовности и разбор ситуаций.\n"
            "4. 🛠️ <b>Работа над ошибками:</b> Диагностика только тех вопросов, где вы допустили ошибку.\n"
            "5. 🪪 <b>Индекс готовности:</b> Оценка вероятности сдачи по методологии реального вождения."
        ),

        # Errors
        "active_session_exists": "⚠️ У вас уже запущен активный сеанс тестирования. Завершите его или отмените через /cancel.",
        "session_expired": "⏱️ <b>Время вышло!</b> Лимит времени экзамена исчерпан.",
        "session_cancelled": "🛑 Сеанс тестирования отменен.",
        "already_answered": "⚠️ Вы уже ответили на этот вопрос.",
        "error_generic": "⚠️ В системе произошла ошибка. Пожалуйста, повторите через /menu."
    }
}

def get_str(key: str, language: str = "uz_latn", **kwargs: Any) -> str:
    """Safely retrieves localized template and formats it."""
    lang_dict = STRINGS.get(language, STRINGS["uz_latn"])
    template = lang_dict.get(key, STRINGS["uz_latn"].get(key, f"[{key}]"))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template
