"""
Comprehensive 3-Language Localization Dictionary for Avtotest Telegram Bot.
Supports:
- uz_latn (O'zbekcha Lotin)
- uz_cyrl (Ўзбекча Кирилл)
- ru (Русский)
Guarantees 100% language purity in Cyrillic and Russian.
"""

from typing import Dict, Any

STRINGS: Dict[str, Dict[str, str]] = {
    "uz_latn": {
        # Brand & Welcome
        "welcome_title": "🚗 <b>RULLY</b>",
        "welcome_text": (
            "Assalomu alaykum! O‘zbekiston haydovchilik guvohnomasi imtihonlariga "
            "tayyorgarlik ko‘rish <b>RULLY</b> platformasiga xush kelibsiz."
        ),
        "language_selected": "✅ Interfeys tili: <b>O‘zbekcha (Lotin)</b> o‘rnatildi.",
        "menu_title": "🚗 <b>RULLY</b>",

        # Main Menu Buttons (The Core Modes)
        "btn_rully_app": "🚗 RULLY ilovasi",
        "btn_exam": "🏆 Nazariy imtihon (20 ta savol)",
        "btn_custom_test": "⚙️ Aralash test va mavzular",
        "btn_amaliy": "🏁 Avtodrom va Amaliyot",
        "btn_categories": "🎯 Kategoriyalar",
        "btn_quick_test": "⚡ Tezkor test (10 ta)",
        "btn_mistakes": "📚 Xatolar banki",
        "btn_results": "📊 Tayyorgarlik darajasi",
        "btn_settings": "🌐 Tilni o‘zgartirish",
        "btn_help": "ℹ️ Yordam",

        # Card Widget Headers
        "card_header_exam": "🚗 <b>AVTOTEST • HAQIQIY IMTIHON</b>",
        "card_header_custom": "🚗 <b>AVTOTEST • MOSLASHUVCHAN TEST</b>",
        "card_header_mistakes": "🚗 <b>AVTOTEST • XATOLAR USTIDA ISHLASH</b>",
        "card_header_category": "🚗 <b>AVTOTEST • MAVZU BO‘YICHA TEST</b>",
        "card_header_quick": "🚗 <b>AVTOTEST • TEZKOR TEST</b>",

        "question_progress": "Savol: <b>{current}/{total}</b>",
        "card_badge_question": "📌 <b>Savol:</b> [ <b>{current:02d} / {total:02d}</b> ]",
        "card_badge_time": "⏳ <b>Vaqt:</b> [ <b>{mins:02d}:{secs:02d}</b> ]",
        "card_badge_category": "📁 <b>Mavzu:</b> [ <i>{category}</i> ]",

        # Card Feedback Headers
        "feedback_correct_header": "✅ <b>TO‘G‘RI JAVOB!</b>",
        "feedback_incorrect_header": "❌ <b>NOTO‘G‘RI JAVOB!</b>",
        "feedback_correct_tag": "<i>(To‘g‘ri javob)</i>",
        "feedback_selected_wrong_tag": "<i>(Sizning javobingiz)</i>",

        # Common Navigation
        "btn_back": "⬅️ Orqaga",
        "btn_main_menu": "🏠 Bosh menyu",
        "btn_next_question": "Keyingi savol ➡️",
        "btn_finish_early": "⏹️ Testni yakunlash",
        "btn_retry_mistakes": "🔄 Xatolarni qayta ishlash",
        "btn_start_new_exam": "🏆 Yangi imtihon topshirish",

        # Pre-test Settings Widget
        "settings_widget_title": "⚙️ <b>MOSLASHUVCHAN TEST SOZLAMALARI</b>",
        "settings_widget_desc": "Testni boshlashdan oldin parametrlarni o‘zingizga moslang:",
        "settings_label_count": "📊 <b>Savollar soni:</b> [ <b>{count} ta</b> ]",
        "settings_label_time": "⏳ <b>Vaqt chegarasi:</b> [ <b>{time_str}</b> ]",
        "settings_label_answer": "🎯 <b>To‘g‘ri javobni ko‘rsatish:</b> [ <b>{ans_str}</b> ]",
        "settings_label_expl": "💡 <b>Qonuniy izohni ko‘rsatish:</b> [ <b>{expl_str}</b> ]",
        "settings_btn_start": "🚀 Testni boshlash ({count} ta savol)",
        "settings_unlimited": "♾️ Cheksiz",
        "settings_minutes": "{mins} daqiqa",
        "settings_yes": "✅ Ha (Darhol)",
        "settings_no": "❌ Faqat oxirida",
        "settings_expl_yes": "✅ Ha",
        "settings_expl_no": "❌ Yo‘q",

        # Legal References & Feedback
        "correct_answer_feedback": "✅ <b>TO‘G‘RI JAVOB!</b>",
        "incorrect_answer_feedback": "❌ <b>NOTO‘G‘RI!</b>\nTo‘g‘ri javob: <b>[{correct_key}]</b>",
        "legal_reference_header": "📖 <b>Qonuniy asos:</b>",
        "explanation_header": "💡 <b>Izoh:</b>",

        # Exam Results
        "result_passed_title": "🏆 <b>TABRIKLAYMIZ! IMTIHONDAN O‘TDINGIZ!</b>",
        "result_failed_title": "😢 <b>IMTIHON NATIJASI: O‘TA OLMADINGIZ</b>",
        "result_summary": (
            "📊 <b>Yakuniy ko‘rsatkichlar:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "• Jami savollar: <b>{total} ta</b>\n"
            "• To‘g‘ri javoblar: <b>{correct} ta</b> ({percentage}%)\n"
            "• Xatolar: <b>{incorrect} ta</b>\n"
            "• Sarflangan vaqt: <b>{time_str}</b>\n"
            "• O‘tish talabi: <b>kamida 18 ta (90%)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>Status:</b> {status_text}\n"
        ),
        "status_passed": "🟢 <b>O‘TDI</b>",
        "status_failed": "🔴 <b>YIQILDI</b>",

        # Mistakes Mode
        "no_mistakes": (
            "🎉 <b>Ajoyib natija!</b>\n\n"
            "Sizda hozircha xato qilingan savollar yo‘q.\n"
            "Bilimingizni sinash uchun imtihon topshiring yoki moslashuvchan test ishlang!"
        ),
        "mistakes_intro": (
            "📚 <b>XATOLAR USTIDA ISHLASH</b>\n\n"
            "Siz ilgari xato qilgan <b>{count} ta</b> savol bo‘yicha mashg‘ulot testi tayyorlandi.\n"
            "Har bir to‘g‘ri javob berilgan savol xatolar ro‘yxatidan chiqariladi."
        ),
        "btn_start_mistakes": "🚀 Mashg‘ulotni boshlash ({count} ta savol)",

        # Stats
        "stats_title": "📊 <b>SIZNING KO‘RSATKICHLARINGIZ</b>",
        "stats_text": (
            "• Topshirilgan imtihonlar: <b>{total_exams} ta</b>\n"
            "• Muvaffaqiyatli: <b>{passed_exams} ta</b>\n"
            "• O‘tish ko‘rsatkichi: <b>{pass_rate}%</b>\n"
            "• Jami ishlangan savollar: <b>{total_questions} ta</b>\n"
            "• To‘g‘rilik darajasi: <b>{accuracy}%</b>\n"
            "• Yechilmagan xatolar: <b>{unresolved_mistakes} ta</b>\n"
        ),

        # Help
        "help_text": (
            "ℹ️ <b>YORDAM VA PLATFORMA QOIDALARI</b>\n\n"
            "<b>Nazariy imtihon (VMQ 408):</b>\n"
            "• Imtihon 20 ta tasodifiy savoldan iborat.\n"
            "• Ajratilgan vaqt: 25 daqiqa.\n"
            "• O‘tish talabi: kamida 18 ta to‘g‘ri javob (ko‘pi bilan 2 ta xatoga yo‘l qo‘yiladi).\n"
            "• F1-F4 tezkor boshqaruv tugmalari va to‘g‘ridan-to‘g‘ri savol katakchalari.\n\n"
            "<b>RULLY platformasi bo‘limlari:</b>\n"
            "1. 🏆 <b>Nazariy imtihon:</b> Imtihon zali kompyuter tizimi andozasida.\n"
            "2. ⚙️ <b>Aralash test:</b> Savollar soni, qulay vaqt slayderi va izohlarni o‘zingiz sozlaysiz.\n"
            "3. 🏁 <b>Avtodrom va Amaliyot:</b> 10 ta amaliy mashq, bosqichma-bosqich cheklist va imtihon vaziyatlari.\n"
            "4. 📚 <b>Xatolar banki:</b> Faqat siz mustaqil ishlab adashgan savollaringiz saqlanadi.\n"
            "5. 📊 <b>Tayyorgarlik indeksi:</b> 4 ta ko‘rsatkich asosida real bilim darajangizni hisoblaydi."
        ),

        # Errors & Notifications
        "active_session_exists": "⚠️ Sizda allaqachon faol test mavjud. Iltimos, avval uni yakunlang yoki bekor qiling.",
        "session_expired": "⏰ <b>Vaqt tugadi!</b> Belgilangan vaqt chegarasi yakunlandi.",
        "session_cancelled": "🛑 Faol test bekor qilindi.",
        "already_answered": "⚠️ Siz bu savolga allaqachon javob bergansiz.",
        "error_generic": "⚠️ Xatolik yuz berdi. Iltimos, /menu orqali qayta urinib ko‘ring."
    },

    "uz_cyrl": {
        # Brand & Welcome
        "welcome_title": "🚗 <b>RULLY</b>",
        "welcome_text": (
            "Ассалому алайкум! Ўзбекистон ҳайдовчилик гувоҳномаси имтиҳонларига "
            "тайёргарлик кўриш <b>RULLY</b> платформасига хуш келибсиз."
        ),
        "language_selected": "✅ Интерфейс тили: <b>Ўзбекча (Кирилл)</b> ўрнатилди.",
        "menu_title": "🚗 <b>RULLY</b>",

        # Main Menu Buttons
        "btn_rully_app": "🚗 RULLY иловаси",
        "btn_exam": "🏆 Назарий имтиҳон (20 та савол)",
        "btn_custom_test": "⚙️ Аралаш тест ва мавзулар",
        "btn_amaliy": "🏁 Автодром ва Амалиўт",
        "btn_categories": "🎯 Категориялар",
        "btn_quick_test": "⚡ Тезкор тест (10 та)",
        "btn_mistakes": "📚 Хатолар банки",
        "btn_results": "📊 Тайёргарлик даражаси",
        "btn_settings": "🌐 Тилни ўзгартириш",
        "btn_help": "ℹ️ Ёрдам",

        # Card Widget Headers
        "card_header_exam": "🚗 <b>АВТОТЕСТ • ҲАҚИҚИЙ ИМТИҲОН</b>",
        "card_header_custom": "🚗 <b>АВТОТЕСТ • МОСЛАШУВЧАН ТЕСТ</b>",
        "card_header_mistakes": "🚗 <b>АВТОТЕСТ • ХАТОЛАР УСТИДА ИШЛАШ</b>",
        "card_header_category": "🚗 <b>АВТОТЕСТ • МАВЗУ БЎЙИЧА ТЕСТ</b>",
        "card_header_quick": "🚗 <b>АВТОТЕСТ • ТЕЗКОР ТЕСТ</b>",

        "question_progress": "Савол: <b>{current}/{total}</b>",
        "card_badge_question": "📌 <b>Савол:</b> [ <b>{current:02d} / {total:02d}</b> ]",
        "card_badge_time": "⏳ <b>Вақт:</b> [ <b>{mins:02d}:{secs:02d}</b> ]",
        "card_badge_category": "📁 <b>Бўлим:</b> [ <i>{category}</i> ]",

        # Card Feedback Headers
        "feedback_correct_header": "✅ <b>ТЎҒРИ ЖАВОБ!</b>",
        "feedback_incorrect_header": "❌ <b>НОТЎҒРИ ЖАВОБ!</b>",
        "feedback_correct_tag": "<i>(Тўғри жавоб)</i>",
        "feedback_selected_wrong_tag": "<i>(Сизнинг жавобингиз)</i>",

        # Common Navigation
        "btn_back": "⬅️ Орқага",
        "btn_main_menu": "🏠 Бош меню",
        "btn_next_question": "Кейинги савол ➡️",
        "btn_finish_early": "⏹️ Тестни якунлаш",
        "btn_retry_mistakes": "🔄 Хатоларни қайта ишлаш",
        "btn_start_new_exam": "🏆 Янги имтиҳон топшириш",

        # Pre-test Settings Widget
        "settings_widget_title": "⚙️ <b>МОСЛАШУВЧАН ТЕСТ СОЗЛАМАЛАРИ</b>",
        "settings_widget_desc": "Тестни бошлашдан олдин параметрларни ўзингизга мосланг:",
        "settings_label_count": "📊 <b>Саволлар сони:</b> [ <b>{count} та</b> ]",
        "settings_label_time": "⏳ <b>Вақт чегараси:</b> [ <b>{time_str}</b> ]",
        "settings_label_answer": "🎯 <b>Тўғри жавобни кўрсатиш:</b> [ <b>{ans_str}</b> ]",
        "settings_label_expl": "💡 <b>Қонуний изоҳни кўрсатиш:</b> [ <b>{expl_str}</b> ]",
        "settings_btn_start": "🚀 Тестни бошлаш ({count} та савол)",
        "settings_unlimited": "♾️ Чексиз",
        "settings_minutes": "{mins} дақиқа",
        "settings_yes": "✅ Ҳа (Дарҳол)",
        "settings_no": "❌ Фақат якунда",
        "settings_expl_yes": "✅ Ҳа",
        "settings_expl_no": "❌ Йўқ",

        # Legal References & Feedback
        "correct_answer_feedback": "✅ <b>ТЎҒРИ ЖАВОБ!</b>",
        "incorrect_answer_feedback": "❌ <b>НОТЎҒРИ!</b>\nТўғри жавоб: <b>[{correct_key}]</b>",
        "legal_reference_header": "📖 <b>Қонуний асос:</b>",
        "explanation_header": "💡 <b>Изоҳ:</b>",

        # Exam Results
        "result_passed_title": "🏆 <b>ТАБРИКЛАЙМИЗ! ИМТИҲОНДАН ЎТДИНГИЗ!</b>",
        "result_failed_title": "😢 <b>ИМТИҲОН НАТИЖАСИ: ЎТА ОЛМАДИНГИЗ</b>",
        "result_summary": (
            "📊 <b>Якуний кўрсаткичлар:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "• Жами саволлар: <b>{total} та</b>\n"
            "• Тўғри жавоблар: <b>{correct} та</b> ({percentage}%)\n"
            "• Хатолар: <b>{incorrect} та</b>\n"
            "• Сарфланган вақт: <b>{time_str}</b>\n"
            "• Ўтиш талаби: <b>камида 18 та (90%)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>Статус:</b> {status_text}\n"
        ),
        "status_passed": "🟢 <b>ЎТДИ</b>",
        "status_failed": "🔴 <b>ЙИҚИЛДИ</b>",

        # Mistakes Mode
        "no_mistakes": (
            "🎉 <b>Ажойиб натижа!</b>\n\n"
            "Сизда ҳозирча хато қилинган саволлар йўқ.\n"
            "Билимингизни синаш учун имтиҳон топширинг ёки мослашувчан тест ишланг!"
        ),
        "mistakes_intro": (
            "📚 <b>ХАТОЛАР УСТИДА ИШЛАШ</b>\n\n"
            "Сиз илгари хато қилган <b>{count} та</b> савол бўйича машғулот тести тайёрланди.\n"
            "Ҳар бир тўғри жавоб берилган савол хатолар рўйхатидан чиқарилади."
        ),
        "btn_start_mistakes": "🚀 Машғулотни бошлаш ({count} та савол)",

        # Stats
        "stats_title": "📊 <b>СИЗНИНГ КЎРСАТКИЧЛАРИНГИЗ</b>",
        "stats_text": (
            "• Топширилган имтиҳонлар: <b>{total_exams} та</b>\n"
            "• Муваффақиятли: <b>{passed_exams} та</b>\n"
            "• Ўтиш кўрсаткичи: <b>{pass_rate}%</b>\n"
            "• Жами ишланган саволлар: <b>{total_questions} та</b>\n"
            "• Тўғрилик даражаси: <b>{accuracy}%</b>\n"
            "• Ечилмаган хатолар: <b>{unresolved_mistakes} та</b>\n"
        ),

        # Help
        "help_text": (
            "ℹ️ <b>ЁРДАМ ВА ПЛАТФОРМА ҚОИДАЛАРИ</b>\n\n"
            "<b>Назарий имтиҳон (ВМҚ 408):</b>\n"
            "• Имтиҳон 20 та тасодифий саволдан иборат.\n"
            "• Ажратилган вақт: 25 дақиқа.\n"
            "• Ўтиш талаби: камида 18 та тўғри жавоб (кўпи билан 2 та хатога йўл қўйилади).\n"
            "• F1-F4 тезкор бошқарув тугмалари ва тўғридан-тўғри савол катакчалари.\n\n"
            "<b>RULLY платформаси бўлимлари:</b>\n"
            "1. 🏆 <b>Назарий имтиҳон:</b> Имтиҳон зали компьютер тизими андозасида.\n"
            "2. ⚙️ <b>Аралаш тест:</b> Саволлар сони, қулай вақт слайдери ва изоҳларни ўзингиз созлайсиз.\n"
            "3. 🏁 <b>Автодром ва Амалиўт:</b> 10 та амалий машқ, босқичма-босқич чек-лист ва имтиҳон вазиятлари.\n"
            "4. 📚 <b>Хатолар банки:</b> Фақат сиз мустақил ишлаб адашган саволларингиз сақланади.\n"
            "5. 📊 <b>Тайёргарлик индекси:</b> 4 та кўрсаткич асосида реал билим даражангизни ҳисоблайди."
        ),

        # Errors
        "active_session_exists": "⚠️ Сизда аллақачон фаол тест мавжуд. Илтимос, аввал уни якунланг ёки бекор қилинг.",
        "session_expired": "⏰ <b>Вақт тугади!</b> Белгиланган вақт чегараси якунланди.",
        "session_cancelled": "🛑 Фаол тест бекор қилинди.",
        "already_answered": "⚠️ Сиз бу саволга аллақачон жавоб бергансиз.",
        "error_generic": "⚠️ Хатолик юз берди. Илтимос, /menu орқали қайта уриниб кўринг."
    },

    "ru": {
        # Brand & Welcome
        "welcome_title": "🚗 <b>RULLY</b>",
        "welcome_text": (
            "Здравствуйте! Добро пожаловать на платформу <b>RULLY</b> "
            "для подготовки к экзаменам на водительские права в Узбекистане."
        ),
        "language_selected": "✅ Язык интерфейса установлен: <b>Русский</b>.",
        "menu_title": "🚗 <b>RULLY</b>",

        # Main Menu Buttons
        "btn_rully_app": "🚗 Приложение RULLY",
        "btn_exam": "🏆 Теоретический экзамен (20 вопросов)",
        "btn_custom_test": "⚙️ Настраиваемый тест",
        "btn_amaliy": "🏁 Автодром и Практика",
        "btn_categories": "🎯 Темы и категории",
        "btn_quick_test": "⚡ Быстрый тест (10)",
        "btn_mistakes": "📚 Банк ошибок",
        "btn_results": "📊 Индекс готовности",
        "btn_settings": "🌐 Сменить язык",
        "btn_help": "ℹ️ Помощь",

        # Card Widget Headers
        "card_header_exam": "🚗 <b>АВТОТЕСТ • ГОСУДАРСТВЕННЫЙ ЭКЗАМЕН</b>",
        "card_header_custom": "🚗 <b>АВТОТЕСТ • НАСТРАИВАЕМЫЙ ТЕСТ</b>",
        "card_header_mistakes": "🚗 <b>АВТОТЕСТ • РАБОТА НАД ОШИБКАМИ</b>",
        "card_header_category": "🚗 <b>АВТОТЕСТ • ТЕСТ ПО ТЕМЕ</b>",
        "card_header_quick": "🚗 <b>АВТОТЕСТ • БЫСТРЫЙ ТЕСТ</b>",

        "question_progress": "Вопрос: <b>{current}/{total}</b>",
        "card_badge_question": "📌 <b>Вопрос:</b> [ <b>{current:02d} / {total:02d}</b> ]",
        "card_badge_time": "⏳ <b>Время:</b> [ <b>{mins:02d}:{secs:02d}</b> ]",
        "card_badge_category": "📁 <b>Раздел:</b> [ <i>{category}</i> ]",

        # Card Feedback Headers
        "feedback_correct_header": "✅ <b>ВЕРНЫЙ ОТВЕТ!</b>",
        "feedback_incorrect_header": "❌ <b>НЕВЕРНЫЙ ОТВЕТ!</b>",
        "feedback_correct_tag": "<i>(Правильный ответ)</i>",
        "feedback_selected_wrong_tag": "<i>(Ваш ответ)</i>",

        # Common Navigation
        "btn_back": "⬅️ Назад",
        "btn_main_menu": "🏠 Главное меню",
        "btn_next_question": "Следующий вопрос ➡️",
        "btn_finish_early": "⏹️ Завершить досрочно",
        "btn_retry_mistakes": "🔄 Повторить ошибки",
        "btn_start_new_exam": "🏆 Начать новый экзамен",

        # Pre-test Settings Widget
        "settings_widget_title": "⚙️ <b>ПАРАМЕТРЫ ТЕСТИРОВАНИЯ</b>",
        "settings_widget_desc": "Настройте параметры теста перед началом:",
        "settings_label_count": "📊 <b>Число вопросов:</b> [ <b>{count}</b> ]",
        "settings_label_time": "⏳ <b>Лимит времени:</b> [ <b>{time_str}</b> ]",
        "settings_label_answer": "🎯 <b>Показ ответа:</b> [ <b>{ans_str}</b> ]",
        "settings_label_expl": "💡 <b>Пояснение ПДД:</b> [ <b>{expl_str}</b> ]",
        "settings_btn_start": "🚀 Начать тест ({count} вопросов)",
        "settings_unlimited": "♾️ Без лимита",
        "settings_minutes": "{mins} минут",
        "settings_yes": "✅ Да (Сразу)",
        "settings_no": "❌ Только в конце",
        "settings_expl_yes": "✅ Да",
        "settings_expl_no": "❌ Нет",

        # Legal References & Feedback
        "correct_answer_feedback": "✅ <b>ВЕРНО!</b>",
        "incorrect_answer_feedback": "❌ <b>НЕВЕРНО!</b>\nПравильный ответ: <b>[{correct_key}]</b>",
        "legal_reference_header": "📖 <b>Пункт ПДД:</b>",
        "explanation_header": "💡 <b>Пояснение:</b>",

        # Exam Results
        "result_passed_title": "🏆 <b>ПОЗДРАВЛЯЕМ! ЭКЗАМЕН СДАН!</b>",
        "result_failed_title": "😢 <b>РЕЗУЛЬТАТ ЭКЗАМЕНА: НЕ СДАНО</b>",
        "result_summary": (
            "📊 <b>Итоговые показатели:</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "• Всего вопросов: <b>{total}</b>\n"
            "• Правильных ответов: <b>{correct}</b> ({percentage}%)\n"
            "• Ошибок: <b>{incorrect}</b>\n"
            "• Затраченное время: <b>{time_str}</b>\n"
            "• Проходной балл: <b>минимум 18 (90%)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<b>Статус:</b> {status_text}\n"
        ),
        "status_passed": "🟢 <b>СДАНО</b>",
        "status_failed": "🔴 <b>НЕ СДАНО</b>",

        # Mistakes Mode
        "no_mistakes": (
            "🎉 <b>Отличный результат!</b>\n\n"
            "У вас нет нерешенных ошибок.\n"
            "Чтобы проверить знания, сдайте официальный экзамен или начните настраиваемый тест!"
        ),
        "mistakes_intro": (
            "📚 <b>РАБОТА НАД ОШИБКАМИ</b>\n\n"
            "Сформирован тренировочный тест из <b>{count}</b> вопросов, в которых вы ранее ошиблись.\n"
            "Каждый правильно решенный вопрос исключается из списка ошибок."
        ),
        "btn_start_mistakes": "🚀 Начать тренировку ({count} вопросов)",

        # Stats
        "stats_title": "📊 <b>ВАША СТАТИСТИКА</b>",
        "stats_text": (
            "• Сдано экзаменов: <b>{total_exams}</b>\n"
            "• Успешно сданных: <b>{passed_exams}</b>\n"
            "• Процент сдачи: <b>{pass_rate}%</b>\n"
            "• Всего решено вопросов: <b>{total_questions}</b>\n"
            "• Точность ответов: <b>{accuracy}%</b>\n"
            "• Нерешенных ошибок: <b>{unresolved_mistakes}</b>\n"
        ),

        # Help
        "help_text": (
            "ℹ️ <b>ПОМОЩЬ И ПРАВИЛА ПЛАТФОРМЫ</b>\n\n"
            "<b>Теоретический экзамен (ПКМ 408):</b>\n"
            "• Экзаменационный билет состоит из 20 случайных вопросов.\n"
            "• Время на выполнение: 25 минут.\n"
            "• Для сдачи необходимо ответить верно минимум на 18 вопросов (допускается не более 2 ошибок).\n"
            "• Управление клавишами F1-F4 и быстрый переход по номерам вопросов.\n\n"
            "<b>Разделы платформы RULLY:</b>\n"
            "1. 🏆 <b>Теоретический экзамен:</b> Повторяет реальный интерфейс экзаменационного зала.\n"
            "2. ⚙️ <b>Настраиваемый тест:</b> Регулировка количества вопросов, слайдер таймера и пояснения ПДД.\n"
            "3. 🏁 <b>Автодром и Практика:</b> 10 практических модулей, чек-лист готовности и дорожные ситуации.\n"
            "4. 📚 <b>Банк ошибок:</b> Сохраняет только те вопросы, в которых вы допустили реальную ошибку.\n"
            "5. 📊 <b>Индекс готовности:</b> Комплексная оценка вероятности успешной сдачи по 4 факторам."
        ),

        # Errors
        "active_session_exists": "⚠️ У вас уже запущен активный тест. Пожалуйста, завершите его или отмените через /cancel.",
        "session_expired": "⏰ <b>Время вышло!</b> Лимит времени исчерпан.",
        "session_cancelled": "🛑 Текущий тест отменен.",
        "already_answered": "⚠️ Вы уже ответили на этот вопрос.",
        "error_generic": "⚠️ Произошла ошибка. Пожалуйста, повторите через /menu."
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
