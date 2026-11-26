"""
Canonical Statutory Reference Catalog for RULLY 2.0 (Phase 4).

Provides structured, trilingual (uz_latn, uz_cyrl, ru) reference catalogs grounded in:
- Cabinet of Ministers Resolution No. 172 (April 12, 2022) "Rules of Road Traffic" (29 Chapters + Annex 1 Road Signs)
- Cabinet of Ministers Resolution No. 408 (Exam & Practical Testing Standards)

Read-only statutory metadata; zero runtime database mutations.
"""

from typing import Any, Dict, List


SUPPORTED_LANGS = ("uz_latn", "uz_cyrl", "ru")


def _pick(mapping: Dict[str, str], lang: str) -> str:
    if lang in mapping:
        return mapping[lang]
    return mapping.get("uz_latn", "")


# ---------------------------------------------------------------------------
# Road Sign Groups Mapped to Native RULLY Canonical Category IDs
# ---------------------------------------------------------------------------
SIGN_GROUPS: List[Dict[str, Any]] = [
    {
        "id": "warning",
        "code_prefix": "1",
        "category_id": 21,
        "shape_badge": "triangle",
        "name": {
            "uz_latn": "Ogohlantiruvchi belgilar",
            "uz_cyrl": "Огоҳлантирувчи белгилар",
            "ru": "Предупреждающие знаки",
        },
        "distance_rule": {
            "uz_latn": "Aholi punktida 50–100 m, tashqarisida 150–300 m oldin o‘rnatiladi.",
            "uz_cyrl": "Аҳоли пунктида 50–100 м, ташқарисида 150–300 м олдин ўрнатилади.",
            "ru": "Устанавливаются в населённых пунктах за 50–100 м, вне — за 150–300 м.",
        },
    },
    {
        "id": "priority",
        "code_prefix": "2",
        "category_id": 17,
        "shape_badge": "diamond",
        "name": {
            "uz_latn": "Imtiyoz belgilari",
            "uz_cyrl": "Имтиёз белгилари",
            "ru": "Знаки приоритета",
        },
        "distance_rule": {
            "uz_latn": "Chorrahalar va tor yo‘l qismlaridan o‘tish navbatini belgilaydi.",
            "uz_cyrl": "Чорраҳалар ва тор йўл қисмларидан ўтиш навбатини белгилайди.",
            "ru": "Устанавливают очерёдность проезда перекрёстков и узких участков.",
        },
    },
    {
        "id": "prohibitory",
        "code_prefix": "3",
        "category_id": 23,
        "shape_badge": "circle_red",
        "name": {
            "uz_latn": "Taqiqlovchi belgilar",
            "uz_cyrl": "Тақиқловчи белгилар",
            "ru": "Запрещающие знаки",
        },
        "distance_rule": {
            "uz_latn": "Taqiq o‘rnatilgan joydan eng yaqin chorrahagacha (yoki bekor qiluvchi belgiga qadar) amal qiladi.",
            "uz_cyrl": "Тақиқ ўрнатилган жойдан энг яқин чорраҳагача (ёки бекор қилувчи белгига қадар) амал қилади.",
            "ru": "Действуют от места установки до ближайшего перекрёстка либо отменяющего знака.",
        },
    },
    {
        "id": "mandatory",
        "code_prefix": "4",
        "category_id": 2,
        "shape_badge": "circle_blue",
        "name": {
            "uz_latn": "Buyuruvchi belgilar",
            "uz_cyrl": "Буюрувчи белгилар",
            "ru": "Предписывающие знаки",
        },
        "distance_rule": {
            "uz_latn": "Faqat ko‘rsatilgan yo‘nalishlarda yoki belgilangan minimal tezlikdan kam bo‘lmagan holda harakatga ruxsat beradi.",
            "uz_cyrl": "Фақат кўрсатилган йўналишларда ёки белгиланган минимал тезликдан кам бўлмаган ҳолда ҳаракатга рухсат беради.",
            "ru": "Разрешают движение только в указанных направлениях или не ниже заданной скорости.",
        },
    },
    {
        "id": "info",
        "code_prefix": "5",
        "category_id": 18,
        "shape_badge": "square_blue",
        "name": {
            "uz_latn": "Axborot-ko‘rsatkich belgilari",
            "uz_cyrl": "Ахборот-кўрсаткич белгилари",
            "ru": "Информационно-указательные знаки",
        },
        "distance_rule": {
            "uz_latn": "Harakat tartiblari, bir tomonlama yo‘llar, piyodalar o‘tish joyi va aholi punktlarini bildiradi.",
            "uz_cyrl": "Ҳаракат тартиблари, бир томонлама йўллар, пиёдалар ўтиш жойи ва аҳоли пунктларини билдиради.",
            "ru": "Информируют об особых режимах движения, переходах и границах населённых пунктов.",
        },
    },
    {
        "id": "service",
        "code_prefix": "6",
        "category_id": 18,
        "shape_badge": "service_blue",
        "name": {
            "uz_latn": "Servis belgilari",
            "uz_cyrl": "Сервис белгилари",
            "ru": "Знаки сервиса",
        },
        "distance_rule": {
            "uz_latn": "Tibbiy yordam, AYOQSH, texnik xizmat va dam olish joylari haqida xabar beradi.",
            "uz_cyrl": "Тиббий ёрдам, АЁҚШ, техник хизмат ва дам олиш жойлари ҳақида хабар беради.",
            "ru": "Информируют о расположении медпунктов, АЗС, СТО и мест отдыха.",
        },
    },
    {
        "id": "plate",
        "code_prefix": "7",
        "category_id": 1,
        "shape_badge": "plate_white",
        "name": {
            "uz_latn": "Qo‘shimcha axborot belgilari",
            "uz_cyrl": "Қўшимча ахборот белгилари",
            "ru": "Знаки дополнительной информации (таблички)",
        },
        "distance_rule": {
            "uz_latn": "Mustaqil qo‘llanilmaydi; faqat birga o‘rnatilgan asosiy belgining taʼsirini aniqlashtiradi.",
            "uz_cyrl": "Мустақил қўлланилмайди; фақат бирга ўрнатилган асосий белгининг таъсирини аниқлаштиради.",
            "ru": "Самостоятельно не применяются; уточняют или ограничивают действие основного знака.",
        },
    },
]


# Curated Core Uzbekistan Annex 1 Road Signs Catalog (for Visual Road Signs Explorer)
SIGNS_CATALOG: List[Dict[str, Any]] = [
    # 1. Warning (Ogohlantiruvchi)
    {
        "code": "1.1",
        "group": "warning",
        "shape": "triangle",
        "glyph": "rail_barrier",
        "label": "",
        "name": {"uz_latn": "Shlagbaumli temir yo‘l kesishmasi", "uz_cyrl": "Шлагбаумли темир йўл кесишмаси", "ru": "Ж/д переезд со шлагбаумом"},
        "rule": {"uz_latn": "Oldinda shlagbaumli temir yo‘l kesishmasi bor; temir yo‘lga 100 m qolganda quvib o‘tish taqiqlanadi.", "uz_cyrl": "Олдинда шлагбаумли темир йўл кесишмаси бор; темир йўлга 100 м қолганда қувиб ўтиш тақиқланади.", "ru": "Впереди переезд со шлагбаумом; обгон запрещён за 100 м до переезда."},
    },
    {
        "code": "1.2",
        "group": "warning",
        "shape": "triangle",
        "glyph": "train",
        "label": "",
        "name": {"uz_latn": "Shlagbaumsiz temir yo‘l kesishmasi", "uz_cyrl": "Шлагбаумсиз темир йўл кесишмаси", "ru": "Ж/д переезд без шлагбаума"},
        "rule": {"uz_latn": "Shlagbaum yo‘q; poyezd yaqinlashmayotganiga shaxsan ishonch hosil qilish shart.", "uz_cyrl": "Шлагбаум йўқ; поезд яқинлашмаётганига шахсан ишонч ҳосил қилиш шарт.", "ru": "Переезд не оборудован шлагбаумом; убедитесь в отсутствии поезда."},
    },
    {
        "code": "1.11.1",
        "group": "warning",
        "shape": "triangle",
        "glyph": "turn_right",
        "label": "",
        "name": {"uz_latn": "Xavfli burilish (o‘ngga)", "uz_cyrl": "Хавфли бурилиш (ўнгга)", "ru": "Опасный поворот (направо)"},
        "rule": {"uz_latn": "Kichik radiusli yoki ko‘rinishi cheklangan o‘ng burilish. Qayrilish va quvib o‘tish xavfli.", "uz_cyrl": "Кичик радиусли ёки кўриниши чекланган ўнг бурилиш. Қайрилиш ва қувиб ўтиш хавфли.", "ru": "Закругление дороги малого радиуса направо с ограниченной видимостью."},
    },
    {
        "code": "1.13",
        "group": "warning",
        "shape": "triangle",
        "glyph": "slope_down",
        "label": "12%",
        "name": {"uz_latn": "Tik nishablik", "uz_cyrl": "Тик нишаблик", "ru": "Крутой спуск"},
        "rule": {"uz_latn": "To‘siqqa duch kelinganda nishablikdan pastga tushayotgan haydovchi ko‘tarilayotgan haydovchiga yo‘l berishi shart!", "uz_cyrl": "Тўсиққа дуч келинганда нишабликдан пастга тушаётган ҳайдовчи кўтарилаётган ҳайдовчига йўл бериши шарт!", "ru": "При наличии препятствия уступает водитель, движущийся на спуск!"},
    },
    {
        "code": "1.14",
        "group": "warning",
        "shape": "triangle",
        "glyph": "slope_up",
        "label": "12%",
        "name": {"uz_latn": "Tik balandlik", "uz_cyrl": "Тик баландлик", "ru": "Крутой подъём"},
        "rule": {"uz_latn": "Ko‘tarilish oxirida ko‘rinish cheklangan joyda quvib o‘tish va qayrilish taqiqlanadi.", "uz_cyrl": "Кўтарилиш охирида кўриниш чекланган жойда қувиб ўтиш ва қайрилиш тақиқланади.", "ru": "В конце подъёма с ограниченной видимостью обгон и разворот запрещены."},
    },
    {
        "code": "1.15",
        "group": "warning",
        "shape": "triangle",
        "glyph": "slippery",
        "label": "",
        "name": {"uz_latn": "Sirpanchiq yo‘l", "uz_cyrl": "Сирпанчиқ йўл", "ru": "Скользкая дорога"},
        "rule": {"uz_latn": "Qoplama sirpanchiq; keskin tormozlash va rulni keskin burishdan saqlaning.", "uz_cyrl": "Қоплама сирпанчиқ; кескин тормозлаш ва рулни кескин буришдан сақланинг.", "ru": "Участок с повышенной скользкостью проезжей части."},
    },
    {
        "code": "1.20",
        "group": "warning",
        "shape": "triangle",
        "glyph": "pedestrian",
        "label": "",
        "name": {"uz_latn": "Piyodalar o‘tish joyi", "uz_cyrl": "Пиёдалар ўтиш жойи", "ru": "Пешеходный переход"},
        "rule": {"uz_latn": "Oldinda 5.16.1/5.16.2 belgisi bilan belgilangan piyodalar o‘tish joyi borligidan ogohlantiradi.", "uz_cyrl": "Олдинда 5.16.1/5.16.2 белгиси билан белгиланган пиёдалар ўтиш жойи борлигидан огоҳлантиради.", "ru": "Предупреждает о приближении к пешеходному переходу."},
    },
    {
        "code": "1.21",
        "group": "warning",
        "shape": "triangle",
        "glyph": "children",
        "label": "",
        "name": {"uz_latn": "Bolalar", "uz_cyrl": "Болалар", "ru": "Дети"},
        "rule": {"uz_latn": "Maktab va bog‘chalar oldida o‘rnatiladi (aholi punktida 2 marta takrorlanadi; tezlik chegarasi ko‘pincha 30 km/soat).", "uz_cyrl": "Мактаб ва боғчалар олдида ўрнатилади (аҳоли пунктида 2 марта такрорланади; тезлик чегараси кўпинча 30 км/соат).", "ru": "Участок у школ и детсадов (повторяется; ограничение скорости обычно 30 км/ч)."},
    },
    {
        "code": "1.23",
        "group": "warning",
        "shape": "triangle_work",
        "glyph": "roadworks",
        "label": "",
        "name": {"uz_latn": "Yo‘l ishlari", "uz_cyrl": "Йўл ишлари", "ru": "Дорожные работы"},
        "rule": {"uz_latn": "Vaqtinchalik sariq asosli belgi doimiy belgilardan ustunlikka ega.", "uz_cyrl": "Вақтинчалик сариқ асосли белги доимий белгилардан устунликка эга.", "ru": "Временный знак на жёлтом фоне имеет приоритет над постоянными знаками."},
    },
    # 2. Priority (Imtiyoz)
    {
        "code": "2.1",
        "group": "priority",
        "shape": "diamond",
        "glyph": "text",
        "label": "",
        "name": {"uz_latn": "Asosiy yo‘l", "uz_cyrl": "Асосий йўл", "ru": "Главная дорога"},
        "rule": {"uz_latn": "Tartibga solinmagan chorrahalarda birinchi bo‘lib o‘tish huquqini beradi.", "uz_cyrl": "Тартибга солинмаган чорраҳаларда биринчи бўлиб ўтиш ҳуқуқини беради.", "ru": "Даёт право преимущественного проезда нерегулируемых перекрёстков."},
    },
    {
        "code": "2.2",
        "group": "priority",
        "shape": "diamond_end",
        "glyph": "text",
        "label": "",
        "name": {"uz_latn": "Asosiy yo‘lning oxiri", "uz_cyrl": "Асосий йўлнинг охири", "ru": "Конец главной дороги"},
        "rule": {"uz_latn": "Ustunlik huquqi tugaydi; keyingi chorrahada belgilarga yoki o‘ng qo‘l qoidasiga amal qiling.", "uz_cyrl": "Устунлик ҳуқуқи тугайди; кейинги чорраҳада белгиларга ёки ўнг қўл қоидасига амал қилинг.", "ru": "Отменяет статус главной дороги."},
    },
    {
        "code": "2.4",
        "group": "priority",
        "shape": "inv_triangle",
        "glyph": "empty",
        "label": "",
        "name": {"uz_latn": "Yo‘l bering", "uz_cyrl": "Йўл беринг", "ru": "Уступите дорогу"},
        "rule": {"uz_latn": "Kesib o‘tilayotgan (yoki 7.13 bilan ko‘rsatilgan asosiy) yo‘ldagi transportlarga yo‘l berish shart; halaqit bo‘lmasa to‘xtash shart emas.", "uz_cyrl": "Кесиб ўтилаётган (ёки 7.13 билан кўрсатилган асосий) йўлдаги транспортларга йўл бериш шарт; ҳалақит бўлмаса тўхташ шарт эмас.", "ru": "Обязаны уступить дорогу ТС по главной дороге; остановка требуется только при помехе."},
    },
    {
        "code": "2.5",
        "group": "priority",
        "shape": "octagon",
        "glyph": "text",
        "label": "STOP",
        "name": {"uz_latn": "To‘xtamasdan harakatlanish taqiqlangan", "uz_cyrl": "Тўхтамасдан ҳаракатланиш тақиқланган", "ru": "Движение без остановки запрещено"},
        "rule": {"uz_latn": "Stop-chiziq oldida (yo‘q bo‘lsa qatnov qismi kesishgan chegarada) TO‘LIQ to‘xtash majburiy!", "uz_cyrl": "Стоп-чизиқ олдида (йўқ бўлса қатнов қисми кесишган чегарада) ТЎЛИҚ тўхташ мажбурий!", "ru": "Обязательная полная остановка перед стоп-линией или краем проезжей части!"},
    },
    {
        "code": "2.6",
        "group": "priority",
        "shape": "circle_red",
        "glyph": "priority_yield_opp",
        "label": "",
        "name": {"uz_latn": "Ro‘paradan harakatlanishning ustunligi", "uz_cyrl": "Рўпарадан ҳаракатланишнинг устунлиги", "ru": "Преимущество встречного движения"},
        "rule": {"uz_latn": "Tor joyga kirish taqiqlanadi, agar ro‘paradan kelayotgan transportga xalaqit tug‘ilsa (qizil strelka biz tomonga).", "uz_cyrl": "Тор жойга кириш тақиқланади, агар рўпарадан келаётган транспортга халақит туғилса (қизил стрелка биз томонга).", "ru": "Запрещает въезд на узкий участок, если это затруднит встречное движение."},
    },
    {
        "code": "2.7",
        "group": "priority",
        "shape": "square_blue",
        "glyph": "priority_me",
        "label": "",
        "name": {"uz_latn": "Ro‘parada harakatlanayotganlarga nisbatan ustunlik", "uz_cyrl": "Рўпарада ҳаракатланаётганларга нисбатан устунлик", "ru": "Преимущество перед встречным движением"},
        "rule": {"uz_latn": "Tor yo‘l qismida ro‘paradan kelayotgan transport sizga yo‘l berishi shart (oq strelka bizda).", "uz_cyrl": "Тор йўл қисмида рўпарадан келаётган транспорт сизга йўл бериши шарт (оқ стрелка бизда).", "ru": "Узкий участок дороги, на котором встречный поток обязан уступить вам."},
    },
    # 3. Prohibitory (Taqiqlovchi)
    {
        "code": "3.1",
        "group": "prohibitory",
        "shape": "circle_no_entry",
        "glyph": "brick",
        "label": "",
        "name": {"uz_latn": "Kirish taqiqlangan (Kirpich)", "uz_cyrl": "Кириш тақиқланган (Кирпич)", "ru": "Въезд запрещён"},
        "rule": {"uz_latn": "Barcha transport vositalarining kirishi taqiqlanadi (faqat belgilangan yo‘nalishli transport bundan mustasno).", "uz_cyrl": "Барча транспорт воситаларининг кириши тақиқланади (фақат белгиланган йўналишли транспорт бундан мустасно).", "ru": "Запрещается въезд всех ТС (исключение: маршрутные ТС)."},
    },
    {
        "code": "3.2",
        "group": "prohibitory",
        "shape": "circle_red",
        "glyph": "empty",
        "label": "",
        "name": {"uz_latn": "Harakatlanish taqiqlangan", "uz_cyrl": "Ҳаракатланиш тақиқланган", "ru": "Движение запрещено"},
        "rule": {"uz_latn": "Taʼsir hududida yashovchi/ishlovchilarga, nogironligi bo‘lgan haydovchilarga va pochta/marshrutli transportga ruxsat.", "uz_cyrl": "Таъсир ҳудудида яшовчи/ишловчиларга, ногиронлиги бўлган ҳайдовчиларга ва почта/маршрутли транспортга рухсат.", "ru": "Исключения: маршрутные ТС, жители/работники зоны и водители с инвалидностью."},
    },
    {
        "code": "3.3",
        "group": "prohibitory",
        "shape": "circle_red",
        "glyph": "car",
        "label": "",
        "name": {"uz_latn": "Mexanik transport vositalarining harakatlanishi taqiqlangan", "uz_cyrl": "Механик транспорт воситаларининг ҳаракатланиши тақиқланган", "ru": "Движение механических ТС запрещено"},
        "rule": {"uz_latn": "Velosiped va ot-aravalarga ruxsat etiladi; barcha dvigatelli transportga taqiq (yashovchi/ishlovchilar bundan mustasno).", "uz_cyrl": "Велосипед ва от-араваларга рухсат этилади; барча двигателли транспортга тақиқ (яшовчи/ишловчилар бундан мустасно).", "ru": "Запрещает движение любых механических ТС."},
    },
    {
        "code": "3.4",
        "group": "prohibitory",
        "shape": "circle_red",
        "glyph": "truck",
        "label": "3.5t",
        "name": {"uz_latn": "Yuk avtomobillarining harakatlanishi taqiqlangan", "uz_cyrl": "Юк автомобилларининг ҳаракатланиши тақиқланган", "ru": "Движение грузовых автомобилей запрещено"},
        "rule": {"uz_latn": "Agar belgi ustida massa yozilmagan bo‘lsa, ruxsat etilgan to‘la vazni 3,5 tonnadan ortiq yuk avtomobillariga taalluqli!", "uz_cyrl": "Агар белги устида масса ёзилмаган бўлса, рухсат этилган тўла вазни 3,5 тоннадан ортиқ юк автомобилларига тааллуқли!", "ru": "Если масса не указана, распространяется на грузовые ТС свыше 3,5 тонн."},
    },
    {
        "code": "3.18.1",
        "group": "prohibitory",
        "shape": "circle_slash",
        "glyph": "no_right",
        "label": "",
        "name": {"uz_latn": "O‘ngga burilish taqiqlangan", "uz_cyrl": "Ўнгга бурилиш тақиқланган", "ru": "Поворот направо запрещён"},
        "rule": {"uz_latn": "Faqat qatnov qismlarining shu kesishuviga amal qiladi; to‘g‘riga, chapga va qayrilishga ruxsat etiladi.", "uz_cyrl": "Фақат қатнов қисмларининг шу кесишувига амал қилади; тўғрига, чапга ва қайрилишга рухсат этилади.", "ru": "Действует только на пересечение перед которым установлен; остальные направления разрешены."},
    },
    {
        "code": "3.18.2",
        "group": "prohibitory",
        "shape": "circle_slash",
        "glyph": "no_left",
        "label": "",
        "name": {"uz_latn": "Chapga burilish taqiqlangan", "uz_cyrl": "Чапга бурилиш тақиқланган", "ru": "Поворот налево запрещён"},
        "rule": {"uz_latn": "Diqqat (tuzoq!): Chapga burilish taqiqlanganda QAYRILISH (razvorot) RUXSAT ETILADI!", "uz_cyrl": "Диққат (тузоқ!): Чапга бурилиш тақиқланганда ҚАЙРИЛИШ (разворот) РУХСАТ ЭТИЛАДИ!", "ru": "Важно (ловушка!): поворот налево запрещён, но РАЗВОРОТ РАЗРЕШЁН!"},
    },
    {
        "code": "3.19",
        "group": "prohibitory",
        "shape": "circle_slash",
        "glyph": "no_uturn",
        "label": "",
        "name": {"uz_latn": "Qayrilish taqiqlangan", "uz_cyrl": "Қайрилиш тақиқланган", "ru": "Разворот запрещён"},
        "rule": {"uz_latn": "Qayrilish taqiqlanadi, lekin CHAPGA BURILISH RUXSAT ETILADI!", "uz_cyrl": "Қайрилиш тақиқланади, лекин ЧАПГА БУРИЛИШ РУХСАТ ЭТИЛАДИ!", "ru": "Разворот запрещён, но ПОВОРОТ НАЛЕВО РАЗРЕШЁН!"},
    },
    {
        "code": "3.20",
        "group": "prohibitory",
        "shape": "circle_red",
        "glyph": "no_overtake",
        "label": "",
        "name": {"uz_latn": "Quvib o‘tish taqiqlangan", "uz_cyrl": "Қувиб ўтиш тақиқланган", "ru": "Обгон запрещён"},
        "rule": {"uz_latn": "30 km/soat dan sekin harakatlanuvchi transport, ot-arava, moped va kajavasiz mototsikllarni quvib o‘tish mumkin.", "uz_cyrl": "30 км/соат дан секин ҳаракатланувчи транспорт, от-арава, мопед ва кажавасиз мотоциклларни қувиб ўтиш мумкин.", "ru": "Исключения: тихоходные ТС (<30 км/ч), гужевые повозки, мопеды и мотоциклы без коляски."},
    },
    {
        "code": "3.24",
        "group": "prohibitory",
        "shape": "circle_red",
        "glyph": "text",
        "label": "50",
        "name": {"uz_latn": "Yuqori tezlik cheklangan", "uz_cyrl": "Юқори тезлик чекланган", "ru": "Ограничение максимальной скорости"},
        "rule": {"uz_latn": "Ko‘rsatilgan (masalan, 50 km/soat) tezlikdan oshish taqiqlanadi; keyingi chorraha yoki 3.25/3.31 gacha amal qiladi.", "uz_cyrl": "Кўрсатилган (масалан, 50 км/соат) тезликдан ошиш тақиқланади; кейинги чорраҳа ёки 3.25/3.31 гача амал қилади.", "ru": "Запрещает движение со скоростью выше указанной на знаке до перекрёстка или отменяющего знака."},
    },
    {
        "code": "3.27",
        "group": "prohibitory",
        "shape": "circle_red_blue_x",
        "glyph": "cross_x",
        "label": "",
        "name": {"uz_latn": "To‘xtash taqiqlangan", "uz_cyrl": "Тўхташ тақиқланган", "ru": "Остановка запрещена"},
        "rule": {"uz_latn": "Ham to‘xtash, ham to‘xtab turish taqiqlanadi! O‘rnatilgan yo‘l tomonida amal qiladi; yo‘nalishli transportga istisno.", "uz_cyrl": "Ҳам тўхташ, ҳам тўхтаб туриш тақиқланади! Ўрнатилган йўл томонида амал қилади; йўналишли транспортга истисно.", "ru": "Запрещены и остановка, и стоянка на той стороне дороги, где установлен знак."},
    },
    {
        "code": "3.28",
        "group": "prohibitory",
        "shape": "circle_red_blue_slash",
        "glyph": "single_slash",
        "label": "",
        "name": {"uz_latn": "To‘xtab turish taqiqlangan", "uz_cyrl": "Тўхтаб туриш тақиқланган", "ru": "Стоянка запрещена"},
        "rule": {"uz_latn": "To‘xtab turish (>5 daq) taqiqlanadi, lekin 5 daqiqagacha to‘xtash (yoki odam/yuk tushirish) RUXSAT ETILADI.", "uz_cyrl": "Тўхтаб туриш (>5 дақ) тақиқланади, лекин 5 дақиқагача тўхташ (ёки одам/юк тушириш) РУХСАТ ЭТИЛАДИ.", "ru": "Стоянка запрещена, но кратковременная остановка (посадка/высадка) разрешена."},
    },
    # 4. Mandatory (Buyuruvchi)
    {
        "code": "4.1.1",
        "group": "mandatory",
        "shape": "circle_blue",
        "glyph": "arrow_up",
        "label": "",
        "name": {"uz_latn": "Harakatlanish to‘g‘riga", "uz_cyrl": "Ҳаракатланиш тўғрига", "ru": "Движение прямо"},
        "rule": {"uz_latn": "Chorrahada o‘rnatilsa faqat 1-kesishuvda to‘g‘riga; chorraha boshidan keyin o‘rnatilsa keyingi chorrahagacha o‘ng hovlilarga kirishga ruxsat.", "uz_cyrl": "Чорраҳада ўрнатилса фақат 1-кесишувда тўғрига; чорраҳа бошидан кейин ўрнатилса кейинги чорраҳагача ўнг ҳовлиларга киришга рухсат.", "ru": "Перед перекрёстком — только прямо; за перекрёстком — не запрещает поворот направо во дворы."},
    },
    {
        "code": "4.1.2",
        "group": "mandatory",
        "shape": "circle_blue",
        "glyph": "arrow_right",
        "label": "",
        "name": {"uz_latn": "Harakatlanish o‘ngga", "uz_cyrl": "Ҳаракатланиш ўнгга", "ru": "Движение направо"},
        "rule": {"uz_latn": "Faqat strelka ko‘rsatgan yo‘nalishda (o‘ngga) harakatlanish buyuriladi.", "uz_cyrl": "Фақат стрелка кўрсатган йўналишда (ўнгга) ҳаракатланиш буюрилади.", "ru": "Разрешается движение только направо (исключение: маршрутные ТС)."},
    },
    {
        "code": "4.1.3",
        "group": "mandatory",
        "shape": "circle_blue",
        "glyph": "arrow_left",
        "label": "",
        "name": {"uz_latn": "Harakatlanish chapga", "uz_cyrl": "Ҳаракатланиш чапга", "ru": "Движение налево"},
        "rule": {"uz_latn": "Chapga burilishga buyuruvchi belgi QAYRILISH (razvorot) ga ham ruxsat beradi!", "uz_cyrl": "Чапга бурилишга буюрувчи белги ҚАЙРИЛИШ (разворот) га ҳам рухсат беради!", "ru": "Знаки, разрешающие поворот налево, также РАЗРЕШАЮТ РАЗВОРОТ!"},
    },
    {
        "code": "4.3",
        "group": "mandatory",
        "shape": "circle_blue",
        "glyph": "roundabout",
        "label": "",
        "name": {"uz_latn": "Aylanma harakat", "uz_cyrl": "Айланма ҳаракат", "ru": "Круговое движение"},
        "rule": {"uz_latn": "O‘zbekiston YHQga ko‘ra aylanmada harakatlanayotgan transport kirib kelayotganlarga nisbatan ustunlikka ega.", "uz_cyrl": "Ўзбекистон ЙҲҚга кўра айланмада ҳаракатланаётган транспорт кириб келаётганларга нисбатан устунликка эга.", "ru": "В Узбекистане ТС на круге имеют преимущество перед въезжающими на перекрёсток."},
    },
    {
        "code": "4.6",
        "group": "mandatory",
        "shape": "circle_blue",
        "glyph": "text",
        "label": "40",
        "name": {"uz_latn": "Minimal tezlik cheklangan", "uz_cyrl": "Минимал тезлик чекланган", "ru": "Ограничение минимальной скорости"},
        "rule": {"uz_latn": "Ko‘rsatilgan (40 km/soat) va undan yuqori tezlikda harakatlanish majburiy; sekinroq yurish taqiqlanadi.", "uz_cyrl": "Кўрсатилган (40 км/соат) ва ундан юқори тезликда ҳаракатланиш мажбурий; секинроқ юриш тақиқланади.", "ru": "Движение разрешено только с указанной или большей скоростью."},
    },
    # 5. Information (Axborot-ko'rsatkich)
    {
        "code": "5.1",
        "group": "info",
        "shape": "square_green",
        "glyph": "highway",
        "label": "",
        "name": {"uz_latn": "Avtomagistral", "uz_cyrl": "Автомагистраль", "ru": "Автомагистраль"},
        "rule": {"uz_latn": "Yengil avtomobil 110 km/soatgacha; tezlik <40 km/soat bo‘lgan transportlar, orqaga yurish va to‘xtash taqiqlanadi.", "uz_cyrl": "Енгил автомобиль 110 км/соатгача; тезлик <40 км/соат бўлган транспортлар, орқага юриш ва тўхташ тақиқланади.", "ru": "До 110 км/ч легковым; запрещены ТС <40 км/ч, движение задним ходом и остановка вне площадок."},
    },
    {
        "code": "5.5",
        "group": "info",
        "shape": "square_blue",
        "glyph": "one_way",
        "label": "",
        "name": {"uz_latn": "Bir tomonlama harakatlangan yo‘l", "uz_cyrl": "Бир томонлама ҳаракатланган йўл", "ru": "Дорога с односторонним движением"},
        "rule": {"uz_latn": "Yo‘lning butun kengligi bo‘ylab bir yo‘nalishda harakatlaniladi; xavf tug‘dirmasa orqaga yurish mumkin.", "uz_cyrl": "Йўлнинг бутун кенглиги бўйлаб бир йўналишда ҳаракатланилади; хавф туғдирмаса орқага юриш мумкин.", "ru": "Движение по всей ширине дороги в одном направлении; движение задним ходом допускается при безопасности."},
    },
    {
        "code": "5.15",
        "group": "info",
        "shape": "square_blue",
        "glyph": "text",
        "label": "P",
        "name": {"uz_latn": "To‘xtab turish joyi", "uz_cyrl": "Тўхтаб туриш жойи", "ru": "Место стоянки"},
        "rule": {"uz_latn": "Parkovka maydonchasini bildiradi; qo‘yilgan 7.6.x jadvallar mashinani trotuarga qanday qo‘yishni ko‘rsatadi.", "uz_cyrl": "Парковка майдончасини билдиради; қўйилган 7.6.x жадваллар машинани тротуарга қандай қўйишни кўрсатади.", "ru": "Обозначает парковку; таблички 7.6.x уточняют способ постановки ТС."},
    },
    {
        "code": "5.16.1",
        "group": "info",
        "shape": "square_blue",
        "glyph": "ped_square",
        "label": "",
        "name": {"uz_latn": "Piyodalar o‘tish joyi", "uz_cyrl": "Пиёдалар ўтиш жойи", "ru": "Пешеходный переход"},
        "rule": {"uz_latn": "O‘tish joyining o‘zini belgilaydi; oldindan 5 m masofada to‘xtash taqiqlanadi!", "uz_cyrl": "Ўтиш жойининг ўзини белгилайди; олдиндан 5 м масофада тўхташ тақиқланади!", "ru": "Границы перехода; ближе 5 м перед переходом остановка запрещена!"},
    },
    {
        "code": "5.38",
        "group": "info",
        "shape": "square_blue",
        "glyph": "res_zone",
        "label": "20",
        "name": {"uz_latn": "Turar joy dahasi", "uz_cyrl": "Турар жой даҳаси", "ru": "Жилая зона"},
        "rule": {"uz_latn": "Maksimal tezlik 20 km/soat! Piyodalar butun qatnov qismida ustunlikka ega; o‘tib ketish va dvigatelni yoqib turish taqiqlanadi.", "uz_cyrl": "Максимал тезлик 20 км/соат! Пиёдалар бутун қатнов қисмида устунликка эга; ўтиб кетиш ва двигателни ёқиб туриш тақиқланади.", "ru": "Скорость до 20 км/ч; приоритет у пешеходов, сквозной проезд запрещён."},
    },
    # 6. Service (Servis)
    {
        "code": "6.1",
        "group": "service",
        "shape": "service_blue",
        "glyph": "cross_med",
        "label": "",
        "name": {"uz_latn": "Birinchi tibbiy yordam punkti", "uz_cyrl": "Биринчи тиббий ёрдам пункти", "ru": "Пункт первой медицинской помощи"},
        "rule": {"uz_latn": "Yo‘l bo‘yida tibbiy yordam punktining joylashuvini bildiradi.", "uz_cyrl": "Йўл бўйида тиббий ёрдам пунктининг жойлашувини билдиради.", "ru": "Информирует о пункте оказания первой медицинской помощи."},
    },
    {
        "code": "6.3",
        "group": "service",
        "shape": "service_blue",
        "glyph": "fuel",
        "label": "",
        "name": {"uz_latn": "Yoqilg‘i quyish shoxobchasi", "uz_cyrl": "Ёқилғи қуйиш шохобчаси", "ru": "Автозаправочная станция"},
        "rule": {"uz_latn": "Eng yaqin AYOQSH masofasi va yo‘nalishini ko‘rsatadi.", "uz_cyrl": "Энг яқин АЁҚШ масофаси ва йўналишини кўрсатади.", "ru": "Указывает расположение АЗС."},
    },
    # 7. Auxiliary Plates (Qo'shimcha axborot)
    {
        "code": "7.1.1",
        "group": "plate",
        "shape": "plate_white",
        "glyph": "text",
        "label": "300 m",
        "name": {"uz_latn": "Obyektgacha bo‘lgan masofa", "uz_cyrl": "Объектгача бўлган масофа", "ru": "Расстояние до объекта"},
        "rule": {"uz_latn": "Strelkasiz bo‘lsa — xavfli joy yoki cheklov boshlanishigacha masofani bildiradi (taʼsir uzunligini emas!).", "uz_cyrl": "Стрелкасиз бўлса — хавфли жой ёки чеклов бошланишигача масофани билдиради (таъсир узунлигини эмас!).", "ru": "Без стрелок указывает расстояние ОТ знака до начала опасного участка."},
    },
    {
        "code": "7.2.1",
        "group": "plate",
        "shape": "plate_white",
        "glyph": "plate_range",
        "label": "↑ 100 m ↑",
        "name": {"uz_latn": "Taʼsir oralig‘i (uzunligi)", "uz_cyrl": "Таъсир оралиғи (узунлиги)", "ru": "Зона действия"},
        "rule": {"uz_latn": "Ikki chetidagi yuqori strelkalar belgining necha metr masofa DAVOMIDA amal qilishini bildiradi.", "uz_cyrl": "Икки четидаги юқори стрелкалар белгининг неча метр масофа ДАВОМИДА амал қилишини билдиради.", "ru": "Указывает протяжённость зоны действия знака."},
    },
    {
        "code": "7.2.2",
        "group": "plate",
        "shape": "plate_white",
        "glyph": "plate_down",
        "label": "10 m ↑",
        "name": {"uz_latn": "To‘xtash/to‘xtab turish taʼsir zonasi", "uz_cyrl": "Тўхташ/тўхтаб туриш таъсир зонаси", "ru": "Зона действия запрета стоянки"},
        "rule": {"uz_latn": "3.27–3.30 belgilarining amal qilish uzunligini bildiradi (strelka tepaga — oldinda, pastga — belgidan keyin tugaydi!).", "uz_cyrl": "3.27–3.30 белгиларининг амал қилиш узунлигини билдиради (стрелка тепага — олдинда, пастга — белгидан кейин тугайди!).", "ru": "Стрелка вниз означает окончание зоны действия знака 3.27–3.30."},
    },
    {
        "code": "7.13",
        "group": "plate",
        "shape": "plate_white",
        "glyph": "priority_turn",
        "label": "",
        "name": {"uz_latn": "Asosiy yo‘lning yo‘nalishi", "uz_cyrl": "Асосий йўлнинг йўналиши", "ru": "Направление главной дороги"},
        "rule": {"uz_latn": "Chorraha konfiguratsiyasida qaysi tomondagi yo‘l asosiy (qalin chiziq) va qaysi biri ikkinchi darajali (ingichka) ekanini ko‘rsatadi.", "uz_cyrl": "Чорраҳа конфигурациясида қайси томондаги йўл асосий (қалин чизиқ) ва қайси бири иккинчи даражали (ингичка) эканини кўрсатади.", "ru": "Показывает направление главной дороги (толстая линия) на перекрёстке."},
    },
]


# ---------------------------------------------------------------------------
# Complete 29 Chapters of Cabinet of Ministers Resolution No. 172 (12.04.2022)
# ---------------------------------------------------------------------------
VMQ172_CHAPTERS: List[Dict[str, Any]] = [
    {
        "chapter": 1,
        "category_ids": [0, 39, 41],
        "title": {"uz_latn": "Umumiy qoidalar", "uz_cyrl": "Умумий қоидалар", "ru": "Общие положения"},
        "summary": {
            "uz_latn": "Asosiy atamalar: to‘xtash (<5 daq), to‘xtab turish, asosiy yo‘l, ustunlik, yo‘l berish, mexanik transport va tirkamalar taʼriflari.",
            "uz_cyrl": "Асосий атамалар: тўхташ (<5 дақ), тўхтаб туриш, асосий йўл, устунлик, йўл бериш, механик транспорт ва тиркамалар таърифлари.",
            "ru": "Базовые термины: остановка (<5 мин), стоянка, главная дорога, преимущество, механические ТС.",
        },
    },
    {
        "chapter": 2,
        "category_ids": [16],
        "title": {"uz_latn": "Haydovchilarning umumiy majburiyatlari", "uz_cyrl": "Ҳайдовчиларнинг умумий мажбуриятлари", "ru": "Общие обязанности водителей"},
        "summary": {
            "uz_latn": "Hujjatlar (guvohnoma, texpassport, sug‘urta), xavfsizlik kamari majburiyati, mast holat (0.0‰) taqiqi va YTH sodir bo‘lganda harakatlar.",
            "uz_cyrl": "Ҳужжатлар (гувоҳнома, техпаспорт, суғурта), хавфсизлик камари мажбурияти, маст ҳолат (0.0‰) тақиқи ва ЙТҲ содир бўлганда ҳаракатлар.",
            "ru": "Обязательные документы, ремень безопасности, полный запрет алкоголя и действия при ДТП.",
        },
    },
    {
        "chapter": 3,
        "category_ids": [28],
        "title": {"uz_latn": "Piyodalarning majburiyatlari", "uz_cyrl": "Пиёдаларнинг мажбуриятлари", "ru": "Обязанности пешеходов"},
        "summary": {
            "uz_latn": "Trotuarlar bo‘ylab harakatlanish, aholi punktidan tashqarida qatnov qismi chetidan transport oqimiga qarama-qarshi yurish.",
            "uz_cyrl": "Тротуарлар бўйлаб ҳаракатланиш, аҳоли пунктидан ташқарида қатнов қисми четидан транспорт оқимига қарама-қарши юриш.",
            "ru": "Движение по тротуарам и навстречу потоку ТС за городом, правила перехода проезжей части.",
        },
    },
    {
        "chapter": 4,
        "category_ids": [40],
        "title": {"uz_latn": "Yo‘lovchilarning majburiyatlari", "uz_cyrl": "Йўловчиларнинг мажбуриятлари", "ru": "Обязанности пассажиров"},
        "summary": {
            "uz_latn": "To‘liq to‘xtagandan so‘ng trotuar tomondan chiqish/tushish, xavfsizlik kamarini taqish va haydovchini chalg‘itmaslik.",
            "uz_cyrl": "Тўлиқ тўхтагандан сўнг тротуар томондан чиқиш/тушиш, хавфсизлик камарини тақиш ва ҳайдовчини чалғитмаслик.",
            "ru": "Посадка и высадка со стороны тротуара после полной остановки, обязательность ремня.",
        },
    },
    {
        "chapter": 5,
        "category_ids": [11],
        "title": {"uz_latn": "Maxsus signallarning qo‘llanilishi", "uz_cyrl": "Махсус сигналларнинг қўлланилиши", "ru": "Применение специальных сигналов"},
        "summary": {
            "uz_latn": "Ko‘k/qizil miltillovchi chiroq va tovush signali yoqilgan tezkor xizmatlarga to‘siqsiz yo‘l berish shartlari; to‘q sariq chiroqning cheklovlari.",
            "uz_cyrl": "Кўк/қизил милтилловчи чироқ ва товуш сигнали ёқилган тезкор хизматларга тўсиқсиз йўл бериш шартлари; тўқ сариқ чироқнинг чекловлари.",
            "ru": "Приоритет спецтранспорта с синим/красным маячком и сиреной; правила жёлтого проблескового маячка.",
        },
    },
    {
        "chapter": 6,
        "category_ids": [29],
        "title": {"uz_latn": "Ogohlantiruvchi va avariya ishoralari", "uz_cyrl": "Огоҳлантирувчи ва авария ишоралари", "ru": "Предупреждающие и аварийные сигналы"},
        "summary": {
            "uz_latn": "Burilish chiroqlarini oldindan yoqish, qo‘l bilan signal berish usullari va avariya uchburchagini o‘rnatish (15 m / 30 m).",
            "uz_cyrl": "Бурилиш чироқларини олдиндан ёқиш, қўл билан сигнал бериш усуллари ва авария учбурчагини ўрнатиш (15 м / 30 м).",
            "ru": "Сигналы поворота рукой и указателями, установка знака аварийной остановки (15 м / 30 м).",
        },
    },
    {
        "chapter": 7,
        "category_ids": [5, 34],
        "title": {"uz_latn": "Yo‘l harakatini tartibga solish", "uz_cyrl": "Йўл ҳаракатини тартибга солиш", "ru": "Регулирование дорожного движения"},
        "summary": {
            "uz_latn": "Svetofor signallari, qo‘shimcha yashil strelka qoidalari va Tartibga soluvchining (regulyirovshik) 3 asosiy holati hamda ustunligi.",
            "uz_cyrl": "Светофор сигналлари, қўшимча яшил стрелка қоидалари ва Тартибга солувчининг (регулировщик) 3 асосий ҳолати ҳамда устунлиги.",
            "ru": "Сигналы светофора, доп. секции и 3 ключевых положения регулировщика (приоритет над знаками).",
        },
    },
    {
        "chapter": 8,
        "category_ids": [8],
        "title": {"uz_latn": "Harakatlanishni boshlash, yo‘nalishni o‘zgartirish", "uz_cyrl": "Ҳаракатланишни бошлаш, йўналишни ўзгартириш", "ru": "Начало движения и маневрирование"},
        "summary": {
            "uz_latn": "Bir vaqtda qayta tizilishda o‘ng qo‘l qoidasi, chekka bo‘lakni egallash, tramvay izlaridan burilish va qayrilish taqiqlangan joylar.",
            "uz_cyrl": "Бир вақтда қайта тизилишда ўнг қўл қоидаси, чекка бўлакни эгаллаш, трамвай изларидан бурилиш ва қайрилиш тақиқланган жойлар.",
            "ru": "Перестроение («помеха справа»), крайнее положение перед поворотом, запрещённые места для разворота.",
        },
    },
    {
        "chapter": 9,
        "category_ids": [14],
        "title": {"uz_latn": "Qatnov qismida transport vositalarining joylashuvi", "uz_cyrl": "Қатнов қисмида транспорт воситаларининг жойлашуви", "ru": "Расположение ТС на проезжей части"},
        "summary": {
            "uz_latn": "3+ bo‘lakli yo‘llarda chekka chap bo‘lakdan foydalanish, 3.5 t yuk mashinalari cheklovi va tramvay izlariga chiqish tartibi.",
            "uz_cyrl": "3+ бўлакли йўлларда чекка чап бўлакдан фойдаланиш, 3.5 т юк машиналари чеклови ва трамвай изларига чиқиш тартиби.",
            "ru": "Запрет левой полосы при свободных правых, трамвайные пути попутного направления.",
        },
    },
    {
        "chapter": 10,
        "category_ids": [26],
        "title": {"uz_latn": "Harakatlanish tezligi", "uz_cyrl": "Ҳаракатланиш тезлиги", "ru": "Скорость движения"},
        "summary": {
            "uz_latn": "Turar joy dahasi 20, maktab 30, aholi punkti 60, shatakka olish 50, tashqarida 70/100, avtomagistralda 110 km/soat meʼyorlari.",
            "uz_cyrl": "Турар жой даҳаси 20, мактаб 30, аҳоли пункти 60, шатакка олиш 50, ташқарида 70/100, автомагистралда 110 км/соат меъёрлари.",
            "ru": "Лимиты: 20 жилая зона, 30 у школ, 60 город, 50 буксировка, 100 трасса, 110 автомагистраль.",
        },
    },
    {
        "chapter": 11,
        "category_ids": [33],
        "title": {"uz_latn": "Quvib o‘tish", "uz_cyrl": "Қувиб ўтиш", "ru": "Обгон"},
        "summary": {
            "uz_latn": "Quvib o‘tish taqiqlangan barcha 7 holat (chorraha, temir yo‘ldan 100m, ko‘prik/tunnel, piyoda o‘tish joyi, ko‘rinish cheklangan joylar).",
            "uz_cyrl": "Қувиб ўтиш тақиқланган барча 7 ҳолат (чорраҳа, темир йўлдан 100м, кўприк/туннель, пиёда ўтиш жойи, кўриниш чекланган жойлар).",
            "ru": "Запрещённые зоны обгона (перекрёстки, 100 м до переезда, мосты, тоннели, переходы).",
        },
    },
    {
        "chapter": 12,
        "category_ids": [7],
        "title": {"uz_latn": "To‘xtash va to‘xtab turish", "uz_cyrl": "Тўхташ ва тўхтаб туриш", "ru": "Остановка и стоянка"},
        "summary": {
            "uz_latn": "Masofa cheklovlari: 3 m uzluksiz chiziqdan, 5 m piyodalar o‘tish joyi va chorrahadan, 15 m bekatdan, 50 m temir yo‘l kesishmasidan.",
            "uz_cyrl": "Масофа чекловлари: 3 м узлуксиз чизиқдан, 5 м пиёдалар ўтиш жойи ва чорраҳадан, 15 м бекатдан, 50 м темир йўл кесишмасидан.",
            "ru": "Нормы дистанции: 3 м от сплошной, 5 м от перехода/перекрёстка, 15 м от остановки, 50 м до переезда.",
        },
    },
    {
        "chapter": 13,
        "category_ids": [4, 6, 25, 31, 38],
        "title": {"uz_latn": "Chorrahalarda harakatlanish", "uz_cyrl": "Чорраҳаларда ҳаракатланиш", "ru": "Проезд перекрёстков"},
        "summary": {
            "uz_latn": "Tartibga solingan va solinmagan chorrahalar, tramvayning doimiy ustunligi, o‘ng qo‘l qoidasi va yashil strelka bilan burilish.",
            "uz_cyrl": "Тартибга солинган ва солинмаган чорраҳалар, трамвайнинг доимий устунлиги, ўнг қўл қоидаси ва яшил стрелка билан бурилиш.",
            "ru": "Регулируемые и нерегулируемые перекрёстки, приоритет трамвая и правило «помехи справа».",
        },
    },
    {
        "chapter": 14,
        "category_ids": [30],
        "title": {"uz_latn": "Piyodalar o‘tish joylari va bekatlar", "uz_cyrl": "Пиёдалар ўтиш жойлари ва бекатлар", "ru": "Пешеходные переходы и остановки"},
        "summary": {
            "uz_latn": "Piyodalar o‘tish joyida to‘liq yo‘l berish, qatnov qismi o‘rtasida to‘xtab qolgan tramvay eshiklari tomonidagi yo‘lovchilarga yo‘l berish.",
            "uz_cyrl": "Пиёдалар ўтиш жойида тўлиқ йўл бериш, қатнов қисми ўртасида тўхтаб қолган трамвай эшиклари томонидаги йўловчиларга йўл бериш.",
            "ru": "Пропуск пешеходов на переходах и при посадке/высадке из трамвая.",
        },
    },
    {
        "chapter": 15,
        "category_ids": [36],
        "title": {"uz_latn": "Temir yo‘l kesishmalari orqali harakatlanish", "uz_cyrl": "Темир йўл кесишмалари орқали ҳаракатланиш", "ru": "Движение через железнодорожные пути"},
        "summary": {
            "uz_latn": "Shlagbaumga kamida 5 m (bo‘lmasa relsga 10 m) masofada to‘xtash; majburiy to‘xtaganda yo‘lovchilarni tushirib xabar berish tartibi.",
            "uz_cyrl": "Шлагбаумга камида 5 м (бўлмаса рельсга 10 м) масофада тўхташ; мажбурий тўхтаганда йўловчиларни тушириб хабар бериш тартиби.",
            "ru": "Остановка за 5 м до шлагбаума (10 м до рельсов); действия при вынужденной остановке на переезде.",
        },
    },
    {
        "chapter": 16,
        "category_ids": [13],
        "title": {"uz_latn": "Avtomagistrallarda harakatlanish", "uz_cyrl": "Автомагистралларда ҳаракатланиш", "ru": "Движение по автомагистралям"},
        "summary": {
            "uz_latn": "Piyoda, velosiped, moped, traktor va <40 km/soat transport taqiqi; orqaga yurish va texnologik uzilishlarda qayrilish qatʼiyan man etiladi.",
            "uz_cyrl": "Пиёда, велосипед, мопед, трактор ва <40 км/соат транспорт тақиқи; орқага юриш ва технологик узилишларда қайрилиш қатъиян ман этилади.",
            "ru": "Запрет движения ТС <40 км/ч, разворотов в технологических разрывах и движения задним ходом.",
        },
    },
    {
        "chapter": 17,
        "category_ids": [35],
        "title": {"uz_latn": "Turar joy dahalarida harakatlanish", "uz_cyrl": "Турар жой даҳаларида ҳаракатланиш", "ru": "Движение в жилых зонах"},
        "summary": {
            "uz_latn": "Tezlik 20 km/soat, piyodalar ustunligi, dvigatelni o‘chirmay to‘xtab turish va yuk >3.5t avtomobillar kirishi taqiqi.",
            "uz_cyrl": "Тезлик 20 км/соат, пиёдалар устунлиги, двигателни ўчирмай тўхтаб туриш ва юк >3.5т автомобиллар кириши тақиқи.",
            "ru": "Скорость до 20 км/ч, запрет сквозного проезда, учебной езды и стоянки с работающим двигателем.",
        },
    },
    {
        "chapter": 18,
        "category_ids": [19],
        "title": {"uz_latn": "Yo‘nalishli transport vositalarining imtiyozlari", "uz_cyrl": "Йўналишли транспорт воситаларининг имтиёзлари", "ru": "Приоритет маршрутных ТС"},
        "summary": {
            "uz_latn": "5.14 ajratilgan bo‘lakka chiqish taqiqi hamda aholi punktida bekatdan chiqayotgan avtobus/trolleybusga yo‘l berish majburiyati.",
            "uz_cyrl": "5.14 ажратилган бўлакка чиқиш тақиқи ҳамда аҳоли пунктида бекатдан чиқаётган автобус/троллейбусга йўл бериш мажбурияти.",
            "ru": "Выезд на выделенную полосу и обязанность уступать автобусу, отъезжающему от остановки в городе.",
        },
    },
    {
        "chapter": 19,
        "category_ids": [22],
        "title": {"uz_latn": "Tashqi yoritish asboblaridan foydalanish", "uz_cyrl": "Ташқи ёритиш асбобларидан фойдаланиш", "ru": "Пользование внешними световыми приборами"},
        "summary": {
            "uz_latn": "Yaqin va uzoq yorituvchi faralar (ro‘para kelayotganga kamida 150 m qolganda almashtirish) va kunduzgi chiroqlar tartibi.",
            "uz_cyrl": "Яқин ва узоқ ёритувчи фаралар (рўпара келаётганга камида 150 м қолганда алмаштириш) ва кундузги чироқлар тартиби.",
            "ru": "Переключение дальнего света на ближний минимум за 150 м до встречного ТС.",
        },
    },
    {
        "chapter": 20,
        "category_ids": [32],
        "title": {"uz_latn": "Mexanik transport vositalarini shatakka olish", "uz_cyrl": "Механик транспорт воситаларини шатакка олиш", "ru": "Буксировка механических ТС"},
        "summary": {
            "uz_latn": "Qattiq ulagich <=4 m, egiluvchan tros 4–6 m; tormozi nosoz bo‘lsa faqat qattiq ulagich/qisman yuklash; yaxmalakda tros taqiqlanadi!",
            "uz_cyrl": "Қаттиқ улагич <=4 м, эгилувчан трос 4–6 м; тормози носоз бўлса фақат қаттиқ улагич/қисман юклаш; яхмалакда трос тақиқланади!",
            "ru": "Жёсткая сцепка <=4 м, гибкая 4–6 м; в гололедицу гибкая сцепка запрещена.",
        },
    },
    {
        "chapter": 21,
        "category_ids": [37],
        "title": {"uz_latn": "Boshqarishni o‘rgatish", "uz_cyrl": "Бошқаришни ўргатиш", "ru": "Учебная езда"},
        "summary": {
            "uz_latn": "Yosh talablari (16+ mototsikl, 18+ B/C toifa, 21+ D toifa), qo‘shimcha pedal/oyna bilan jihozlangan o‘quv avtomobillari.",
            "uz_cyrl": "Ёш талаблари (16+ мотоцикл, 18+ B/C тоифа, 21+ D тоифа), қўшимча педаль/ойна билан жиҳозланган ўқув автомобиллари.",
            "ru": "Требования к обучаемому, инструктору и оборудованию учебного автомобиля (доп. педали, зеркало).",
        },
    },
    {
        "chapter": 22,
        "category_ids": [40],
        "title": {"uz_latn": "Odam tashish", "uz_cyrl": "Одам ташиш", "ru": "Перевозка людей"},
        "summary": {
            "uz_latn": "12 yoshgacha bolalar uchun maxsus o‘rindiq (avtokreslo), yuk kuzovida va tirkamada odam tashish taqiqlari.",
            "uz_cyrl": "12 ёшгача болалар учун махсус ўриндиқ (автокресло), юк кузовида ва тиркамада одам ташиш тақиқлари.",
            "ru": "Удерживающие устройства для детей до 12 лет, ограничения на перевозку в кузове грузовика.",
        },
    },
    {
        "chapter": 23,
        "category_ids": [20],
        "title": {"uz_latn": "Yuk tashish", "uz_cyrl": "Юк ташиш", "ru": "Перевозка грузов"},
        "summary": {
            "uz_latn": "Yukning chetdan chiqish meʼyorlari: old/orqadan >1 m yoki yondan >0.4 m chiqsa «Katta o‘lchamli yuk» belgisi/chirog‘i shart.",
            "uz_cyrl": "Юкнинг четдан чиқиш меъёрлари: олд/орқадан >1 м ёки ёндан >0.4 м чиқса «Катта ўлчамли юк» белгиси/чироғи шарт.",
            "ru": "Обязательное обозначение груза, выступающего спереди/сзади >1 м или сбоку >0,4 м.",
        },
    },
    {
        "chapter": 24,
        "category_ids": [27],
        "title": {"uz_latn": "Velosiped, moped va aravalar harakati", "uz_cyrl": "Велосипед, мопед ва аравалар ҳаракати", "ru": "Движение велосипедов, мопедов и гужевых повозок"},
        "summary": {
            "uz_latn": "14 yoshdan yo‘lda yurish (moped 16+), chekka o‘ng qatordan 1 qatorda harakatlanish va yo‘lovchi/yuk tashish cheklovlari.",
            "uz_cyrl": "14 ёшдан йўлда юриш (мопед 16+), чекка ўнг қатордан 1 қаторда ҳаракатланиш ва йўловчи/юк ташиш чекловлари.",
            "ru": "Возрастные пороги (14 лет велосипед, 16 мопед), движение по крайней правой полосе в один ряд.",
        },
    },
    {
        "chapter": 25,
        "category_ids": [3, 15],
        "title": {"uz_latn": "Foydalanishni taqiqlovchi texnik shartlar", "uz_cyrl": "Фойдаланишни тақиқловчи техник шартлар", "ru": "Неисправности, запрещающие эксплуатацию ТС"},
        "summary": {
            "uz_latn": "Rul lyufti (M1 <=10°), shina protektori (L 0.8mm, M1 1.6mm, M2/M3 2.0mm) va tormoz/oyna tozalagich nosozligi qoidalari.",
            "uz_cyrl": "Руль люфти (M1 <=10°), шина протектори (L 0.8мм, M1 1.6мм, M2/M3 2.0мм) ва тормоз/ойна тозалагич носозлиги қоидалари.",
            "ru": "Люфт руля (M1 <=10°), глубина протектора (L 0,8мм, M1 1,6мм) и 5 критических поломок (запрет движения).",
        },
    },
    {
        "chapter": 26,
        "category_ids": [10],
        "title": {"uz_latn": "Mansabdor shaxslarning majburiyatlari", "uz_cyrl": "Мансабдор шахсларнинг мажбуриятлари", "ru": "Обязанности должностных лиц"},
        "summary": {
            "uz_latn": "Texnik nosoz yoki mast haydovchini yo‘nalishga chiqarmaslik va yo‘l tashkilotlari javobgarligi.",
            "uz_cyrl": "Техник носоз ёки маст ҳайдовчини йўналишга чиқармаслик ва йўл ташкилотлари жавобгарлиги.",
            "ru": "Ответственность должностных лиц за выпуск неисправного ТС или водителя без медосмотра.",
        },
    },
    {
        "chapter": 27,
        "category_ids": [9, 15],
        "title": {"uz_latn": "Harakat xavfsizligi va tibbiy yordam asoslari", "uz_cyrl": "Ҳаракат хавфсизлиги ва тиббий ёрдам асослари", "ru": "Обеспечение безопасности и первая помощь"},
        "summary": {
            "uz_latn": "Reanimatsiya 30:2 nisbati, arterial qon ketishda jgut (10–15 sm yuqoriga; yozda 1s, qishda 30d), to‘xtash yo‘li va shinalar.",
            "uz_cyrl": "Реанимация 30:2 нисбати, артериал қон кетишда жгут (10–15 см юқорига; ёзда 1с, қишда 30д), тўхташ йўли ва шиналар.",
            "ru": "СЛР 30:2, жгут при артериальном кровотечении (лето 1 ч, зима 30 мин), остановочный путь.",
        },
    },
    {
        "chapter": 28,
        "category_ids": [21, 17, 23, 2, 18, 1],
        "title": {"uz_latn": "Yo‘l belgilari (1-ilova)", "uz_cyrl": "Йўл белгилари (1-илова)", "ru": "Дорожные знаки (Приложение 1)"},
        "summary": {
            "uz_latn": "Barcha 7 guruh yo‘l belgilari, amal qilish zonalari va sariq fonli vaqtinchalik belgilar ustunligi.",
            "uz_cyrl": "Барча 7 гуруҳ йўл белгилари, амал қилиш зоналари ва сариқ фонли вақтинчалик белгилар устунлиги.",
            "ru": "7 групп дорожных знаков, их зоны действия и приоритет временных знаков.",
        },
    },
    {
        "chapter": 29,
        "category_ids": [12, 42],
        "title": {"uz_latn": "Yo‘l chiziqlari (2-ilova)", "uz_cyrl": "Йўл чизиқлари (2-илова)", "ru": "Дорожная разметка (Приложение 2)"},
        "summary": {
            "uz_latn": "Yotiq (1.1 uzluksiz, 1.5 uzuq, 1.4 sariq to‘xtash taqiqi) va tik chiziqlar hamda vaqtinchalik to‘q sariq chiziq ustunligi.",
            "uz_cyrl": "Ётиқ (1.1 узлуксиз, 1.5 узуқ, 1.4 сариқ тўхташ тақиқи) ва тик чизиқлар ҳамда вақтинчалик тўқ сариқ чизиқ устунлиги.",
            "ru": "Горизонтальная (1.1, 1.4 жёлтая, 1.5) и вертикальная разметка, приоритет временной оранжевой.",
        },
    },
]


# VMQ 408 & Key Exam Benchmark Cards
KEY_NORMS: List[Dict[str, Any]] = [
    {
        "badge": "18 / 20",
        "tone": "emerald",
        "title": {"uz_latn": "Nazariy imtihon standarti (VMQ 408)", "uz_cyrl": "Назарий имтиҳон стандарти (ВМҚ 408)", "ru": "Стандарт теории (ПКМ №408)"},
        "detail": {"uz_latn": "20 ta savol uchun 25 daqiqa ajratiladi. Ko‘pi bilan 2 ta xato ruxsat etiladi; 3-xato imtihonni darhol to‘xtatadi.", "uz_cyrl": "20 та савол учун 25 дақиқа ажратилади. Кўпи билан 2 та хато рухсат этилади; 3-хато имтиҳонни дарҳол тўхтатади.", "ru": "20 вопросов за 25 минут. Допустимо максимум 2 ошибки; 3-я ошибка мгновенно завершает экзамен."},
    },
    {
        "badge": "20 / 30 / 60",
        "tone": "primary",
        "title": {"uz_latn": "Shahar ichidagi tezlik chegaralari", "uz_cyrl": "Шаҳар ичидаги тезлик чегаралари", "ru": "Скорость в населённых пунктах"},
        "detail": {"uz_latn": "Turar joy dahasida 20 km/soat, maktablar oldida 30 km/soat, aholi punktlarida umumiy meʼyor 60 km/soat.", "uz_cyrl": "Турар жой даҳасида 20 км/соат, мактаблар олдида 30 км/соат, аҳоли пунктларида умумий меъёр 60 км/соат.", "ru": "20 км/ч во дворах/жилой зоне, 30 км/ч у школ, общий городской лимит 60 км/ч."},
    },
    {
        "badge": "100 / 110",
        "tone": "primary",
        "title": {"uz_latn": "Shahar tashqarisidagi tezlik", "uz_cyrl": "Шаҳар ташқарисидаги тезлик", "ru": "Скорость вне города"},
        "detail": {"uz_latn": "Yengil avtomobillar shahar tashqarisida 100 km/soat, avtomagistralda 110 km/soat; shatakka olish doim 50 km/soat.", "uz_cyrl": "Енгил автомобиллар шаҳар ташқарисида 100 км/соат, автомагистралда 110 км/соат; шатакка олиш доим 50 км/соат.", "ru": "Легковые: 100 км/ч на трассе, 110 км/ч на автомагистрали; буксировка всегда до 50 км/ч."},
    },
    {
        "badge": "< 100 ball",
        "tone": "amber",
        "title": {"uz_latn": "Amaliy imtihon (Avtodrom) meʼyori", "uz_cyrl": "Амалий имтиҳон (Автодром) меъёри", "ru": "Практический экзамен (Автодром)"},
        "detail": {"uz_latn": "Jarima ballari yig‘indisi 100 ballga yetmasligi shart. Kamar taqmaslik, chiziqni bosish yoki avariya holati darhol imtihondan chetlatadi.", "uz_cyrl": "Жарима баллари йиғиндиси 100 баллга етмаслиги шарт. Камар тақмаслик, чизиқни босиш ёки авария ҳолати дарҳол имтиҳондан четлатади.", "ru": "Сумма штрафных баллов < 100. Непристёгнутый ремень, наезд на линию или аварийная ситуация — дисквалификация."},
    },
]


def get_road_signs_reference(lang: str = "uz_latn") -> Dict[str, Any]:
    selected_lang = lang if lang in SUPPORTED_LANGS else "uz_latn"
    groups_out = [
        {
            "id": g["id"],
            "code_prefix": g["code_prefix"],
            "category_id": g["category_id"],
            "shape_badge": g["shape_badge"],
            "name": _pick(g["name"], selected_lang),
            "distance_rule": _pick(g["distance_rule"], selected_lang),
        }
        for g in SIGN_GROUPS
    ]
    cat_by_group = {g["id"]: g["category_id"] for g in SIGN_GROUPS}
    signs_out = [
        {
            "code": s["code"],
            "group": s["group"],
            "category_id": cat_by_group.get(s["group"], 18),
            "shape": s["shape"],
            "glyph": s["glyph"],
            "label": s.get("label", ""),
            "name": _pick(s["name"], selected_lang),
            "rule": _pick(s["rule"], selected_lang),
        }
        for s in SIGNS_CATALOG
    ]
    return {
        "ok": True,
        "language": selected_lang,
        "source_act": "VMQ №172 (12.04.2022) — 1-ilova",
        "source_url": "https://lex.uz/docs/5963102" if selected_lang != "ru" else "https://lex.uz/ru/docs/5963102",
        "groups": groups_out,
        "signs": signs_out,
        "total_signs": len(signs_out),
    }


def get_law_reference(lang: str = "uz_latn") -> Dict[str, Any]:
    selected_lang = lang if lang in SUPPORTED_LANGS else "uz_latn"
    chapters_out = [
        {
            "chapter": ch["chapter"],
            "title": _pick(ch["title"], selected_lang),
            "summary": _pick(ch["summary"], selected_lang),
            "category_ids": ch["category_ids"],
        }
        for ch in VMQ172_CHAPTERS
    ]
    norms_out = [
        {
            "badge": n["badge"],
            "tone": n["tone"],
            "title": _pick(n["title"], selected_lang),
            "detail": _pick(n["detail"], selected_lang),
        }
        for n in KEY_NORMS
    ]
    return {
        "ok": True,
        "language": selected_lang,
        "resolution": "Vazirlar Mahkamasining 2022-yil 12-apreldagi 172-son qarori"
        if selected_lang != "ru"
        else "Постановление Кабинета Министров №172 от 12.04.2022",
        "source_url": "https://lex.uz/docs/5963102" if selected_lang != "ru" else "https://lex.uz/ru/docs/5963102",
        "chapters": chapters_out,
        "total_chapters": len(chapters_out),
        "norms": norms_out,
    }
