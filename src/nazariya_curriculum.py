"""
RULLY Mini App - Comprehensive Theory Curriculum & Lessons Engine (Nazariy O'quv Dasturi).
Provides sequential 41-module curriculum mapped to official Uzbekistan Traffic Rules (YHQ 2022).
Each module contains:
- Official sequential ordering (1..41)
- Category ID mapping for database question tests
- Concise lesson summary (Dars)
- Key regulatory rules and requirements (Asosiy qoidalar)
- High-yield exam traps & tricks (Imtihon tuzoqlari)
- Instant AI Ustoz contextual prompt
Full trilingual purity: uz_latn, uz_cyrl, ru.
"""

from typing import Dict, Any, List, Optional

THEORY_MODULES: List[Dict[str, Any]] = [
    {
        "order": 1,
        "category_id": 0,
        "category_ids": [0, 39, 41],
        "badge": {"uz_latn": "Asosiy qoida", "uz_cyrl": "Асосий қоида", "ru": "Базовые правила"},
        "duration_min": 7,
        "title": {
            "uz_latn": "Umumiy qoidalar va asosiy atamalar",
            "uz_cyrl": "Умумий қоидалар ва асосий атамалар",
            "ru": "Общие положения и основные термины"
        },
        "summary": {
            "uz_latn": "Yo‘l harakati qoidalarining poydevori: yo‘l, qatnov qismi, chorraha, asosiy yo‘l, ruxsat etilgan to‘la vazn va boshqa asosiy tushunchalar.",
            "uz_cyrl": "Йўл ҳаракати қоидаларининг пойдевори: йўл, қатнов қисми, чорраҳа, асосий йўл, рухсат этилган тўла вазн ва бошқа асосий тушунчалар.",
            "ru": "Фундамент ПДД: дорога, проезжая часть, перекресток, главная дорога, разрешенная максимальная масса и базовые понятия."
        },
        "key_rules": {
            "uz_latn": [
                "O‘zbekiston Respublikasi hududida transport vositalarining o‘ng tomonlama harakati belgilangan.",
                "Asosiy yo‘l — qoplamali (asfalt, beton, tosh) yo‘lning qoplamasiz (tuproq) yo‘lga nisbatan ustunligi, yoki tegishli belgilar (2.1, 2.3.1-2.3.3, 5.1) bilan belgilangan yo‘ldir.",
                "Chorraha — bir sathda kesishadigan, tutashadigan yoki ayriledigan yo‘llar hududi. Yo‘lga tutash hududlardan (hovli, AYoQSh) chiqish joylari chorraha hisoblanmaydi.",
                "Ruxsat etilgan to‘la vazn — ishlab chiqaruvchi tomonidan belgilangan yuk, haydovchi va yo‘lovchilar bilan birgalikdagi eng yuqori og‘irlik chegarasi."
            ],
            "uz_cyrl": [
                "Ўзбекистон Республикаси ҳудудида транспорт воситаларининг ўнг томонлама ҳаракати белгиланган.",
                "Асосий йўл — қопламали (асфальт, бетон, тош) йўлнинг қопламасиз (тупроқ) йўлга нисбатан устунлиги, ёки тегишли белгилар (2.1, 2.3.1-2.3.3, 5.1) билан белгиланган йўлдир.",
                "Чорраҳа — бир сатҳда кесишадиган, туташадиган ёки айриладиган йўллар ҳудуди. Туташ ҳудудлардан (ҳовли, АЁҚШ) чиқиш жойлари чорраҳа ҳисобланмайди.",
                "Рухсат этилган тўла вазн — ишлаб чиқарувчи корхона томонидан белгиланган юк, ҳайдовчи ва йўловчилар билан биргаликдаги энг юқори оғирлик чегараси."
            ],
            "ru": [
                "В Республике Узбекистан установлено правостороннее движение транспортных средств.",
                "Главная дорога — дорога с твердым покрытием по отношению к грунтовой, либо обозначенная знаками 2.1, 2.3.1–2.3.3 или 5.1.",
                "Перекресток — место пересечения, примыкания или разветвления дорог на одном уровне. Выезды с прилегающих территорий перекрестками не являются.",
                "Разрешенная максимальная масса — масса снаряженного ТС с грузом, водителем и пассажирами, установленная предприятием-изготовителем."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Qoplamasiz (tuproq) yo‘lning bevosita chorrahaga tutash qismiga asfalt to‘shalgan bo‘lsa ham, u baribir ikkinchi darajali yo‘l bo‘lib qoladi!",
                "⚠️ Hovlilar va yoqilg‘i quyish shoxobchalaridan chiqish chorraha EMAS. Ulardan chiquvchi har qanday haydovchi yo‘ldagilarga yo‘l berishi shart."
            ],
            "uz_cyrl": [
                "⚠️ Қопламасиз (тупроқ) йўлнинг бевосита чорраҳага туташ қисмига асфальт ётқизилган бўлса ҳам, у барибир иккинчи даражали йўл ҳисобланади!",
                "⚠️ Ҳовлилар ва ёқилғи қуйиш шахобчаларидан чиқиш жойлари чорраҳа ЭМАС. Улардан чиқаётган ҳайдовчи йўлдаги барчага йўл бериши шарт."
            ],
            "ru": [
                "⚠️ Наличие на второстепенной (грунтовой) дороге непосредственно перед перекрестком участка с покрытием НЕ делает её равной по значению с пересекаемой!",
                "⚠️ Выезды со дворов и АЗС перекрестками НЕ являются. Выезжающий обязан уступить дорогу всем участникам движения."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Asosiy yo‘l va qoplamali yo‘lning farqlarini hamda chorraha hisoblanmaydigan holatlarni tushuntirib ber",
            "uz_cyrl": "Асосий йўл ва қопламали йўлнинг фарқларини ҳамда чорраҳа ҳисобланмайдиган ҳолатларни тушунтириб бер",
            "ru": "Объясни отличия главной дороги и ситуации, которые не считаются перекрестком"
        }
    },
    {
        "order": 2,
        "category_id": 16,
        "category_ids": [16],
        "badge": {"uz_latn": "Majburiyat", "uz_cyrl": "Мажбурият", "ru": "Обязанности"},
        "duration_min": 6,
        "title": {
            "uz_latn": "Haydovchilarning umumiy vazifalari",
            "uz_cyrl": "Ҳайдовчиларнинг умумий вазифалари",
            "ru": "Общие обязанности водителей"
        },
        "summary": {
            "uz_latn": "Haydovchining harakatlanishdan oldingi tekshiruvlari, hujjatlar to‘plami, xavfsizlik kamari va yo‘lda taqiqlangan harakatlar.",
            "uz_cyrl": "Ҳайдовчининг ҳаракатланишдан олдинги текширувлари, ҳужжатлар тўплами, хавфсизлик камари ва йўлда тақиқланган ҳаракатлар.",
            "ru": "Проверка ТС перед выездом, перечень обязательных документов, ремни безопасности и запрещенные действия."
        },
        "key_rules": {
            "uz_latn": [
                "Yo‘lga chiqishdan oldin transport vositasining texnik sozligini tekshirish shart.",
                "Harakat vaqtida xavfsizlik kamarini taqish shart (orqa o‘rindiqdagi yo‘lovchilar ham agar konstruksiyada ko‘zda tutilgan bo‘lsa).",
                "Harakatlanayotganda telefondan (qo‘lda ushlab) foydalanish qat'iyan taqiqlanadi.",
                "Spirtli ichimlik, giyohvandlik yoki charchoq holatida avtomobil boshqarish qat'iyan man etiladi."
            ],
            "uz_cyrl": [
                "Йўлга чиқишдан олдин транспорт воситасининг техник созлигини текшириш шарт.",
                "Ҳаракат вақтида хавфсизлик камарини тақиш шарт (орқа ўриндиқдаги йўловчилар ҳам конструкциясида бўлса).",
                "Ҳаракатланаётганда телефондан (қўлда ушлаб) фойдаланиш қатъиян тақиқланади.",
                "Спиртли ичимлик, гиёҳвандлик ёки чарчоқ ҳолатида автомобиль бошқариш қатъиян ман этилади."
            ],
            "ru": [
                "Перед выездом водитель обязан проверить и обеспечить исправное техническое состояние ТС.",
                "При движении водитель и все пассажиры обязаны быть пристегнуты ремнями безопасности.",
                "Во время движения запрещается пользоваться телефоном без устройств 'hands-free'.",
                "Управление в состоянии алкогольного, наркотического опьянения или переутомления категорически запрещено."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Avariya to‘xtashi sodir bo‘lganda zudlik bilan avariya chiroqlari yoqiladi va ogohlantiruvchi qizil uchburchak belgi qo‘yiladi (aholi punktida 15m, tashqarida 30m).",
                "⚠️ Mototsikl boshqarganda qulflangan motoshlem kiyish majburiydir."
            ],
            "uz_cyrl": [
                "⚠️ Авариявий тўхташ содир бўлганда дарҳол авария чироқлари ёқилади ва қизил учбурчак белги ўрнатилади (аҳоли пунктида 15м, ташқарида 30м).",
                "⚠️ Мотоцикл бошқарганда қулфланган мотошлем кийиш мажбурийдир."
            ],
            "ru": [
                "⚠️ При вынужденной остановке сначала включается аварийная сигнализация, затем выставляется знак (не менее 15 м в населенном пункте, 30 м вне).",
                "⚠️ При управлении мотоциклом мотошлем должен быть не просто надет, а обязательно застегнут."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Haydovchining harakatlanish vaqtida taqiqlangan harakatlari va tekshiruv majburiyatlarini tushuntirib ber",
            "uz_cyrl": "Ҳайдовчининг ҳаракатланиш вақтида тақиқланган ҳаракатлари ва текширув мажбуриятларини тушунтириб бер",
            "ru": "Расскажи основные обязанности водителя и правила использования ремней безопасности"
        }
    },
    {
        "order": 3,
        "category_id": 28,
        "category_ids": [28],
        "badge": {"uz_latn": "Piyodalar", "uz_cyrl": "Пиёдалар", "ru": "Пешеходы"},
        "duration_min": 5,
        "title": {
            "uz_latn": "Piyodalar va yo‘lovchilarning vazifalari",
            "uz_cyrl": "Пиёдалар ва йўловчиларнинг вазифалари",
            "ru": "Обязанности пешеходов и пассажиров"
        },
        "summary": {
            "uz_latn": "Piyodalarning yo‘lni kesib o‘tish tartibi, trotuarlar, yo‘l yoqasi va ko‘rinish cheklangan vaqtdagi qoidalari.",
            "uz_cyrl": "Пиёдаларнинг йўлни кесиб ўтиш тартиби, тротуарлар, йўл ёқаси ва кўриниш чекланган вақтдаги қоидалари.",
            "ru": "Правила перехода проезжей части, движение по обочинам и обязанности пассажиров."
        },
        "key_rules": {
            "uz_latn": [
                "Piyodalar trotuarlar yoki piyodalar yo‘lkasidan, ular bo‘lmaganda yo‘l yoqasidan yurishlari kerak.",
                "Aholi punktlaridan tashqarida yo‘l yoqasida yurayotgan piyodalar transport vositalari harakatiga QARSHI yo‘nalishda yurishi shart.",
                "Yo‘lni faqat piyodalar o‘tish joylaridan, ular bo‘lmaganda esa chorraha chegaralarida trotuar chizig‘i bo‘ylab kesib o‘tish lozim.",
                "Tartibga solinmagan piyodalar o‘tish joyiga chiqishdan oldin harakat xavfsizligiga to‘liq ishonch hosil qilish shart."
            ],
            "uz_cyrl": [
                "Пиёдалар тротуарлар ёки пиёдалар йўлкасидан, улар бўлмаганда йўл ёқасидан юришлари керак.",
                "Аҳоли пунктларидан ташқарида пиёдалар транспорт воситалари ҳаракатига ҚАРШИ йўналишда юриши шарт.",
                "Йўлни фақат пиёдалар ўтиш жойларидан, улар бўлмаганда чорраҳа чегараларида тротуар чизиғи бўйлаб кесиб ўтиш лозим.",
                "Тартибга солинмаган пиёдалар ўтиш жойига чиқишдан олдин хавфсизликка тўлиқ ишонч ҳосил қилиш шарт."
            ],
            "ru": [
                "Пешеходы должны двигаться по тротуарам, пешеходным дорожкам, а при их отсутствии — по обочинам.",
                "Вне населенных пунктов при движении по обочине пешеходы обязаны идти НАВСТРЕЧУ движению транспортных средств.",
                "Переходить дорогу следует по пешеходным переходам, а при их отсутствии — на перекрестках по линии тротуаров.",
                "На нерегулируемых переходах пешеход обязан оценить расстояние и убедиться в безопасности до выхода на дорогу."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Velosiped yoki mototsikl yetaklab borayotgan piyoda aholi punktidan tashqarida harakat yo‘nalishi bo‘ylab (o‘ng tomondan) yuradi!",
                "⚠️ Qorong‘i vaqtda yo‘ldan o‘tayotgan piyodalarga nur qaytaruvchi elementlar taqish qat'iy tavsiya etiladi."
            ],
            "uz_cyrl": [
                "⚠️ Велосипед ёки мотоцикл етаклаб бораётган пиёда аҳоли пунктидан ташқарида ҳаракат йўналиши БЎЙЛАБ (ўнг томондан) юради!",
                "⚠️ Қоронғи вақтда йўлдан ўтаётган пиёдаларга нур қайтарувчи элементлар тақиш тавсия этилади."
            ],
            "ru": [
                "⚠️ Лица, ведущие велосипед или мотоцикл, вне населенных пунктов должны следовать ПО ХОДУ движения транспорта!",
                "⚠️ В темное время суток пешеходам настоятельно рекомендуется иметь при себе световозвращающие элементы."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Piyodalarning harakat yo‘nalishiga qarshi yoki bo‘ylab yurish qoidalaridagi farqlarni tushuntirib ber",
            "uz_cyrl": "Пиёдаларнинг ҳаракат йўналишига қарши ёки бўйлаб юриш қоидаларидаги фарқларни тушунтириб бер",
            "ru": "Когда пешеход идет навстречу движению, а когда по направлению движения транспорта?"
        }
    },
    {
        "order": 4,
        "category_id": 11,
        "category_ids": [11],
        "badge": {"uz_latn": "Maxsus transport", "uz_cyrl": "Махсус транспорт", "ru": "Спецтранспорт"},
        "duration_min": 5,
        "title": {
            "uz_latn": "Maxsus transport vositalarining imtiyozlari",
            "uz_cyrl": "Махсус транспорт воситаларининг имтиёзлари",
            "ru": "Приоритет специальных транспортных средств"
        },
        "summary": {
            "uz_latn": "Ko‘k va qizil mayoqchalar, maxsus tovush signali va ularga yo‘l berish qoidalari.",
            "uz_cyrl": "Кўк ва қизил маёқчалар, махсус товуш сигнали ва уларга йўл бериш қоидалари.",
            "ru": "Синие и красные проблесковые маячки, звуковые сигналы и правила предоставления преимущества."
        },
        "key_rules": {
            "uz_latn": [
                "Ko‘k (yoki ko‘k va qizil) rangli miltillovchi mayoqcha va maxsus tovush signali yoqilgan transport vositasi imtiyozga ega bo‘ladi.",
                "Boshqa haydovchilar ushbu transport vositasiga va u kuzatib borayotgan eskortga to‘siqsiz o‘tib ketish imkoniyatini berishi shart.",
                "Ko‘k mayoqchasi yoniq transport vositasi svetofor, yo‘l belgilari va chiziqlari talablaridan chekinishi mumkin (faqat tartibga soluvchi ishorasidan mustasno).",
                "To‘xtab turgan miltillovchi mayoqchali avtomobilga yaqinlashganda haydovchi tezlikni zarur bo‘lsa to‘xtash darajasigacha kamaytirishi lozim."
            ],
            "uz_cyrl": [
                "Кўк (ёки кўк ва қизил) милтилловчи маёқча ва махсус товуш сигнали ёқилган транспорт воситаси имтиёзга эга бўлади.",
                "Бошқа ҳайдовчилар ушбу транспортга ва у кузатиб бораётган колоннага тўсиқсиз ўтиб кетиш имкониятини бериши шарт.",
                "Маёқчаси ёниқ махсус транспорт светофор, йўл белгилари ва чизиқлари талабларидан чекиниши мумкин (тартибга солувчи бундан мустасно).",
                "Тўхтаб турган маёқчали автомобиль ёнидан ўтаётганда тезликни кескин камайтириш шарт."
            ],
            "ru": [
                "Преимущество возникает только при ОДНОВРЕМЕННО включенном синем (сине-красном) маячке и специальном звуковом сигнале.",
                "Водители обязаны уступить дорогу такому спецтранспорту и сопровождаемым им автомобилям.",
                "Спецтранспорт с включенным маячком может отступать от требований знаков, разметки и сигналов светофора, обеспечив безопасность.",
                "При приближении к стоящему спецтранспорту с включенным синим маячком необходимо снизить скорость и быть готовым остановиться."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ FAQAT ko‘k mayoqchaning o‘zi imtiyoz BERMAYDI — imtiyoz uchun tovush signali (sirena) ham birga yoqilgan bo‘lishi shart!",
                "⚠️ Sariq yoki zarg‘aldoq rangli mayoqcha yo‘lda IMTIYOZ BERMAYDI — u faqat ogohlantirish vazifasini bajaradi."
            ],
            "uz_cyrl": [
                "⚠️ ФАҚАТ кўк маёқчанинг ўзи имтиёз БЕРМАЙДИ — имтиёз учун товуш сигнали (сирена) ҳам бир вақтда ёқилган бўлиши керак!",
                "⚠️ Сариқ ёки зарғалдоқ маёқча ҳаракатда ҲЕЧ ҚАНДАЙ ИМТИЁЗ БЕРМАЙДИ — у фақат огоҳлантириш учун хизмат қилади."
            ],
            "ru": [
                "⚠️ Один только синий маячок БЕЗ сирены приоритета НЕ дает! Для преимущества нужны оба сигнала одновременно.",
                "⚠️ Желтые и оранжевые маячки НЕ ДАЮТ преимущества в движении — они служат только для предупреждения об опасности."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Maxsus transport qachon imtiyozga ega bo‘ladi va sariq mayoqchaning farqi nimada?",
            "uz_cyrl": "Махсус транспорт қачон имтиёзга эга бўлади ва сариқ маёқчанинг фарқи нимада?",
            "ru": "В каких случаях спецтранспорт имеет преимущество и для чего нужен желтый маячок?"
        }
    },
    {
        "order": 5,
        "category_id": 34,
        "category_ids": [34],
        "badge": {"uz_latn": "Svetofor", "uz_cyrl": "Светофор", "ru": "Светофор"},
        "duration_min": 7,
        "title": {
            "uz_latn": "Svetofor ishoralari",
            "uz_cyrl": "Светофор ишоралари",
            "ru": "Сигналы светофора"
        },
        "summary": {
            "uz_latn": "Yashil, sariq, qizil va qo‘shimcha tarmoq (strelka) ishoralari hamda reversiv svetoforlar.",
            "uz_cyrl": "Яшил, сариқ, қизил ва қўшимча тармоқ (стрелка) ишоралари ҳамда реверсив светофорлар.",
            "ru": "Значения сигналов светофора, стрелки дополнительных секций и реверсивные светофоры."
        },
        "key_rules": {
            "uz_latn": [
                "Yashil ishora — harakatga ruxsat beradi. Yashil miltillovchi ishora — uning vaqti tugayotganidan ogohlantiradi.",
                "Sariq ishora — harakatlanishni taqiqlaydi (keskin tormozlanishsiz to‘xtash imkoni bo‘lmagan hollardan tashqari).",
                "Qizil ishora (shu jumladan miltillovchi) — harakatlanishni qat'iyan taqiqlaydi.",
                "Qo‘shimcha tarmoq (strelka) — faqat shu yo‘nalishda harakatlanishga ruxsat beradi. Qizil bilan birga yongan strelka boshqalarga yo‘l berish shartini yuklaydi."
            ],
            "uz_cyrl": [
                "Яшил ишора — ҳаракатга рухсат беради. Яшил милтилловчи — вақти тугаётганини билдиради.",
                "Сариқ ишора — ҳаракатни тақиқлайди (кескин тормозсиз тўхтай олмаслик ҳолати бундан мустасно).",
                "Қизил ишора — ҳаракатни қатъиян тақиқлайди.",
                "Қўшимча стрелка асосий қизил билан бирга ёнганда — бурилиш мумкин, лекин бошқа барча йўналишдаги транспортларга йўл бериш шарти билан."
            ],
            "ru": [
                "Зеленый сигнал разрешает движение. Мигающий зеленый предупреждает о скорой смене сигнала.",
                "Желтый сигнал ЗАПРЕЩАЕТ движение (кроме случаев, когда невозможно остановиться без экстренного торможения).",
                "Красный сигнал категорически запрещает движение.",
                "Стрелка дополнительной секции, включенная одновременно с красным сигналом, разрешает поворот только при условии уступить дорогу ВСЕМ остальным ТС."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Qizil va sariq ishoraning bir vaqtda yonishi harakatlanishni TAQIQLAYDI va tez orada yashil yonishini bildiradi.",
                "⚠️ Qizil chiroq bilan yongan qo‘shimcha yashil strelkada chapga yoki o‘ngga burilayotgan haydovchi o‘ziga yashil chiroqda kelayotgan barcha mashinalarga yo‘l berishi shart!"
            ],
            "uz_cyrl": [
                "⚠️ Қизил ва сариқ чироқ бир вақтда ёнганда ҳаракатланиш ТАҚИҚЛАНАДИ!",
                "⚠️ Қизил чироқ билан ёнган қўшимча стрелкада ҳаракатланаётган ҳайдовчи бошқа йўналишдан асосий яшил чироқда келаётганларга албатта йўл бериши шарт."
            ],
            "ru": [
                "⚠️ Сочетание красного и желтого сигналов движение ЗАПРЕЩАЕТ и информирует о предстоящем включении зеленого.",
                "⚠️ Стрелка с основным красным НЕ дает приоритета! Вы обязаны пропустить автомобили, едущие на свой основной зеленый."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Svetoforning qizil chirog‘i bilan birga yongan qo‘shimcha strelka qoidasini tushuntirib ber",
            "uz_cyrl": "Светофорнинг қизил чироғи билан бирга ёнган қўшимча стрелка қоидасини тушунтириб бер",
            "ru": "Как правильно проезжать перекресток по дополнительной секции светофора с основным красным?"
        }
    },
    {
        "order": 6,
        "category_id": 5,
        "category_ids": [5],
        "badge": {"uz_latn": "Regulyirovshik", "uz_cyrl": "Регулировщик", "ru": "Регулировщик"},
        "duration_min": 8,
        "title": {
            "uz_latn": "Tartibga soluvchining ishoralari",
            "uz_cyrl": "Тартибга солувчининг ишоралари",
            "ru": "Сигналы регулировщика"
        },
        "summary": {
            "uz_latn": "Tartibga soluvchi (inspektor) ishoralari svetofor va yo‘l belgilaridan ustun turadi. 3 ta asosiy qoida va qo‘l harakatlari.",
            "uz_cyrl": "Тартибга солувчи ишоралари светофор ва йўл белгиларидан устун туради. 3 та асосий қоида ва ҳаракатлар.",
            "ru": "Сигналы регулировщика имеют приоритет над светофорами и знаками. 3 ключевых положения рук и корпуса."
        },
        "key_rules": {
            "uz_latn": [
                "Tartibga soluvchining ishoralari svetofor, yo‘l belgilari va chiziqlari talablaridan MUTLAQ USTUN turadi.",
                "Qo‘llari yon tomonga uzatilgan (yoki tushirilgan): Ko‘krak va orqa tomondan harakat taqiqlanadi (qizil). Yon tomonlardan tramvay to‘g‘riga, qolganlar to‘g‘riga va o‘ngga (yashil).",
                "O‘ng qo‘li oldinga uzatilgan: Ko‘krak tomondan faqat o‘ngga; Chap tomondan barcha yo‘nalishlarga; Orqa va o‘ng yon tomondan harakat taqiqlanadi.",
                "Qo‘li yuqoriga ko‘tarilgan: Barcha transport vositalari va piyodalar uchun harakatlanish taqiqlanadi (sariq chiroq tengdoshi)."
            ],
            "uz_cyrl": [
                "Тартибга солувчининг ишоралари светофор ва белгилардан МУТЛАҚ УСТУН туради.",
                "Қўллари ёнга ёзилган (ёки туширилган): Кўкрак ва орқа томондан ҳаракат тақиқланади (қизил). Ён томонлардан тўғрига ва ўнгга ҳаракатланиш мумкин.",
                "Ўнг қўли олдинга узатилган: Чап томондан келаётган транспортларга барча йўналишларга рухсат берилади. Кўкрак томондан фақат ўнгга.",
                "Қўли юқорига кўтарилган: Барча учун ҳаракатланиш тақиқланади."
            ],
            "ru": [
                "Сигналы регулировщика имеют абсолютный приоритет перед сигналами светофора и дорожными знаками.",
                "Руки вытянуты в стороны или опущены: со стороны груди и спины движение ЗАПРЕЩЕНО. С боков: прямо и направо.",
                "Правая рука вытянута вперед: со стороны левого бока — во всех направлениях; с груди — только направо; со спины и правого бока — ЗАПРЕЩЕНО.",
                "Рука поднята вверх: движение всех транспортных средств и пешеходов ЗАПРЕЩЕНО."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Oltin qoida: 'Inspektorning yelkasi yoki yoni bo‘ylab harakatlaning, ko‘krak va orqasiga qarab yurmang!'",
                "⚠️ Tramvay tartibga soluvchining 'yengidan kirib, ikkinchi yengidan chiqadi' (faqat bitta yo‘nalishda yuradi)."
            ],
            "uz_cyrl": [
                "⚠️ Олтин қоида: Кўкрак ва орқа томондан юриш қатъиян тақиқланади ('Кўкрак ва орқа — қизил девор').",
                "⚠️ Трамвай доимо тартибга солувчининг 'енгидан кириб, енгидан чиқади' (оддий автомобиллардан фарқли)."
            ],
            "ru": [
                "⚠️ Золотое правило: 'В грудь и спину ехать нельзя — это стена!'",
                "⚠️ Трамвай всегда движется строго 'из рукава в рукав' регулировщика (без отклонений)."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Regulyirovshik (tartibga soluvchi) ishoralarini imtihonda adashmaslik uchun oson qoidasini tushuntirib ber",
            "uz_cyrl": "Тартибга солувчи ишораларини имтиҳонда адашмаслик учун осон формуласини тушунтириб бер",
            "ru": "Объясни простое мнемоническое правило для сигналов регулировщика"
        }
    },
    {
        "order": 7,
        "category_id": 29,
        "category_ids": [29],
        "badge": {"uz_latn": "Signallar", "uz_cyrl": "Сигналлар", "ru": "Сигналы"},
        "duration_min": 5,
        "title": {
            "uz_latn": "Ogohlantiruvchi va avariya ishoralari",
            "uz_cyrl": "Огоҳлантирувчи ва авария ишоралари",
            "ru": "Предупреждающие и аварийные сигналы"
        },
        "summary": {
            "uz_latn": "Burilish ko‘rsatkichlari, qo‘l ishoralari, avariya to‘xtash chiroqlari va favqulodda to‘xtash belgisi.",
            "uz_cyrl": "Бурилиш кўрсаткичлари, қўл ишоралари, авария чироқлари ва шошилинч тўхташ белгиси.",
            "ru": "Указатели поворота, сигналы руками, аварийная сигнализация и знак аварийной остановки."
        },
        "key_rules": {
            "uz_latn": [
                "Harakatlanishni boshlash, qayta tizilish, burilish va to‘xtashdan oldin tegishli yo‘nalishdagi burilish chirog‘ini yoqish shart.",
                "Burilish signali manyovr boshlanishidan OLDIN beriladi va manyovr tugashi bilanoq o‘chiriladi.",
                "Burilish ko‘rsatkichi ishlamasa, qo‘l bilan ishora qilinadi (chapga uzatilgan qo‘l — chapga; tirsakdan 90 gradus bukilgan qo‘l — o‘ngga).",
                "Tovush signali aholi punktida FAQAT yo‘l-transport hodisasining oldini olish uchungina qo‘llanilishi mumkin."
            ],
            "uz_cyrl": [
                "Ҳаракатни бошлаш, қаторни ўзгартириш, бурилиш ва тўхташдан олдин бурилиш чироғини ёқиш шарт.",
                "Бурилиш сигнали манёврдан ОЛДИН берилади ва манёвр тугаши билан ўчирилади.",
                "Чироқ ишламаса қўл билан ишора берилади.",
                "Аҳоли пунктларида овозли сигнал (клаксон) чалиш ФАҚАТ ЙТҲнинг олдини олиш учунгина мумкин."
            ],
            "ru": [
                "Перед началом движения, перестроением, поворотом и остановкой водитель обязан подавать сигналы поворота.",
                "Подача сигнала производится заблаговременно до начала маневра и прекращается немедленно после его завершения.",
                "При неисправности световых указателей сигналы подаются рукой.",
                "Звуковые сигналы в населенных пунктах разрешается применять ТОЛЬКО для предотвращения ДТП."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Burilish chirog‘ini yoqish haydovchiga HECH QANDAY IMTIYOZ bermaydi va uni xavfsizlik choralarini ko‘rishdan ozod etmaydi!",
                "⚠️ Avariya to‘xtash belgisi aholi punktlarida kamida 15 metr, aholi punktlaridan tashqarida kamida 30 metr masofada o‘rnatiladi."
            ],
            "uz_cyrl": [
                "⚠️ Бурилиш чироғини ёқиш ҳайдовчига ҲЕЧ ҚАНДАЙ ИМТИЁЗ БЕРМАЙДИ!",
                "⚠️ Авария тўхташ белгиси аҳоли пунктида камида 15 м, ташқарида камида 30 м масофада ўрнатилади."
            ],
            "ru": [
                "⚠️ Подача сигнала поворота НЕ дает водителю преимущества и не освобождает от принятия мер предосторожности!",
                "⚠️ Знак аварийной остановки устанавливается на расстоянии не менее 15 м в городе и 30 м вне населенных пунктов."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Qo‘l bilan beriladigan burilish ishoralari va tovush signalini qo‘llash qoidalarini tushuntirib ber",
            "uz_cyrl": "Қўл билан бериладиган бурилиш ишоралари ва овозли сигнал қоидаларини тушунтириб бер",
            "ru": "Правила подачи сигналов поворота рукой и расстояния установки знака аварийной остановки"
        }
    },
    {
        "order": 8,
        "category_id": 8,
        "category_ids": [8],
        "badge": {"uz_latn": "Manyovr", "uz_cyrl": "Манёвр", "ru": "Маневрирование"},
        "duration_min": 7,
        "title": {
            "uz_latn": "Harakatlanishni boshlash, manyovr qilish",
            "uz_cyrl": "Ҳаракатланишни бошлаш, манёвр қилиш",
            "ru": "Начало движения, маневрирование"
        },
        "summary": {
            "uz_latn": "Qayta tizilish, 'o‘ng qo‘l qoidasi' (o‘ngdan xalaqit), chekka qatorni egallash, orqaga harakatlanish va qayrilib olish qoidalari.",
            "uz_cyrl": "Қайта тизилиш, 'ўнг қўл қоидаси', чекка қаторни эгаллаш, орқага ҳаракатланиш ва қайрилиб олиш қоидалари.",
            "ru": "Перестроение, помеха справа, занятие крайнего положения, разворот и движение задним ходом."
        },
        "key_rules": {
            "uz_latn": [
                "Harakatlanishni boshlayotgan haydovchi qatnov qismidagi barcha harakat ishtirokchilariga yo‘l berishi shart.",
                "Bir vaqtda qayta tizilayotgan (kesishuvchi) transport vositalari orasida O‘NG TOMONDAN kelayotgan haydovchi ustunlikka ega.",
                "O‘ngga burilishdan oldin — o‘ng chekka qatorni, chapga burilish yoki qayrilib olishdan oldin — chap chekka qatorni egallash shart.",
                "Orqaga harakatlanish piyodalar o‘tish joylarida, ko‘priklarda, tunnellarda, temir yo‘l kesishmalarida va bekatlarda taqiqlanadi."
            ],
            "uz_cyrl": [
                "Ҳаракатни бошлаётган ҳайдовчи йўлдаги барча ҳаракат иштирокчиларига йўл бериши шарт.",
                "Бир вақтда қатор алмаштираётган (ўзаро кесишаётган) транспортлар орасида ЎНГ ТОМОНДАГИ ҳайдовчи устунликка эга.",
                "Бурилишдан олдин тегишли чекка бўлакни эгаллаш шарт.",
                "Орқага ҳаракатланиш чорраҳаларда, кўприкларда, тоннелларда ва пиёдалар ўтиш жойларида тақиқланади."
            ],
            "ru": [
                "При выезде на дорогу с прилегающей территории водитель обязан уступить дорогу всем транспортным средствам и пешеходам.",
                "При одновременном перестроении преимущество имеет водитель, находящийся СПРАВА ('помеха справа').",
                "Перед поворотом направо, налево или разворотом водитель обязан заблаговременно занять соответствующее крайнее положение.",
                "Движение задним ходом запрещается на перекрестках, пешеходных переходах, мостах, путепроводах, в тоннелях."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Qayta tizilayotgan haydovchi o‘z qatorida to‘g‘ri ketayotgan mashinaga YO‘L BERISHI SHART!",
                "⚠️ Qayrilib olish taqiqlangan joyda orqaga harakatlanish ham deyarli har doim taqiqlanadi (chorrahalar bundan mustasno: chorrahada qayrilib olish mumkin, lekin orqaga harakatlanish man etiladi)."
            ],
            "uz_cyrl": [
                "⚠️ Қаторни ўзгартираётган ҳайдовчи ўз қаторида тўғри кетаётган машинага ЙЎЛ БЕРИШИ ШАРТ!",
                "⚠️ Чорраҳаларда орқага ҳаракатланиш ҚАТЪИЯН ТАҚИҚЛАНАДИ."
            ],
            "ru": [
                "⚠️ При перестроении водитель обязан уступить дорогу ТС, движущимся попутно БЕЗ изменения направления движения!",
                "⚠️ На перекрестках движение задним ходом КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО (разворот разрешен)."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Bir vaqtda qayta tizilishda kim yo‘l berishi kerak va orqaga yurish qayerlarda taqiqlangan?",
            "uz_cyrl": "Бир вақтда қатор алмаштиришда ким йўл бериши керак ва орқага ҳаракатланиш қаерларда тақиқланган?",
            "ru": "Кто кому уступает при одновременном перестроении и где запрещено движение задним ходом?"
        }
    },
    {
        "order": 9,
        "category_id": 14,
        "category_ids": [14],
        "badge": {"uz_latn": "Joylashuv", "uz_cyrl": "Жойлашув", "ru": "Расположение ТС"},
        "duration_min": 6,
        "title": {
            "uz_latn": "Qatnov qismida transport vositalarining joylashuvi",
            "uz_cyrl": "Қатнов қисмида транспорт воситаларининг жойлашуви",
            "ru": "Расположение транспортных средств на проезжей части"
        },
        "summary": {
            "uz_latn": "Harakatlanish bo‘laklari sonini aniqlash, o‘ng tomonga yaqin yurish, quvib o‘tish va tramvay izlaridan foydalanish.",
            "uz_cyrl": "Ҳаракат бўлакларини аниқлаш, ўнг томонга яқин юриш, қувиб ўтиш ва трамвай изларидан фойдаланиш.",
            "ru": "Количество полос движения, движение по правой стороне и использование трамвайных путей."
        },
        "key_rules": {
            "uz_latn": [
                "Aholi punktlaridan tashqarida bo‘sh o‘ng qator turganda chap qatorlardan yurish taqiqlanadi (imkon qadar o‘ngga yaqin yurish kerak).",
                "Uch va undan ortiq bo‘lakli yo‘llarda ruxsat etilgan to‘la vazni 3.5 tonnadan ortiq yuk avtomobillariga chap chekka bo‘lakka faqat burilish yoki qayrilib olish uchungina o‘tishga ruxsat beriladi.",
                "Qarama-qarshi yo‘nalishdagi tramvay izlariga chiqish qat'iyan man etiladi.",
                "Bir yo‘nalishli yo‘llarda sekin harakatlanuvchi transport vositalari o‘ng chekka qatordan harakatlanishi shart."
            ],
            "uz_cyrl": [
                "Аҳоли пунктларидан ташқарида бўш ўнг қатор турганда чап қаторлардан юриш тақиқланади.",
                "3 ва ундан ортиқ бўлакли йўлларда 3.5 тоннадан ортиқ юк машиналари чап чекка бўлакка фақат бурилиш ёки қайрилиш учун чиқиши мумкин.",
                "Қарама-қарши йўналишдаги трамвай изларига чиқиш қатъиян тақиқланади."
            ],
            "ru": [
                "Вне населенных пунктов запрещается занимать левые полосы движения при свободных правых.",
                "На дорогах с тремя и более полосами грузовым автомобилям более 3.5 т выезжать на крайнюю левую полосу разрешается только для поворота налево и разворота.",
                "Выезд на трамвайные пути встречного направления категорически запрещен."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Aholi punktida agar barcha o‘ng qatorlar band bo‘lsa, chap qatordan harakatlanish mumkin.",
                "⚠️ Bir xil sathda joylashgan yo‘nalishdosh tramvay izlaridan burilish va qayrilib olishda (agar belgilar taqiqlamasa) foydalanish shart."
            ],
            "uz_cyrl": [
                "⚠️ Аҳоли пунктида ўнг бўлаклар банд бўлгандагина чап бўлакдан юришга рухсат этилади.",
                "⚠️ Бир сатҳдаги йўналишдош трамвай изларидан бурилиш учун фойдаланиш керак (белгилар бўлмаса)."
            ],
            "ru": [
                "⚠️ В населенных пунктах занимать левые полосы разрешается при интенсивном движении, когда заняты другие полосы.",
                "⚠️ Поворот налево и разворот должны выполняться с попутных трамвайных путей на одном уровне, если знаками 5.15.1/2 не предписан иной порядок."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Yuk avtomobillarining chap chekka bo‘lakka chiqish cheklovlarini tushuntirib ber",
            "uz_cyrl": "Юк автомобилларининг чап чекка бўлакка чиқиш чекловларини тушунтириб бер",
            "ru": "Правила движения по полосам вне города и ограничения для грузовых авто"
        }
    },
    {
        "order": 10,
        "category_id": 26,
        "category_ids": [26],
        "badge": {"uz_latn": "Tezlik", "uz_cyrl": "Тезлик", "ru": "Скорость"},
        "duration_min": 6,
        "title": {
            "uz_latn": "Harakatlanish tezligi",
            "uz_cyrl": "Ҳаракатланиш тезлиги",
            "ru": "Скорость движения"
        },
        "summary": {
            "uz_latn": "Aholi punktlarida (60 km/soat), avtomagistrallarda (110 km/soat), shatakka olishda (50 km/soat) va turar joy dahalarida (20 km/soat) tezlik cheklovlari.",
            "uz_cyrl": "Аҳоли пунктларида (60 км/соат), автомагистралларда (110 км/соат), шатакка олишда (50 км/соат) ва турар жой даҳаларида (20 км/соат) тезлик меъёрлари.",
            "ru": "Скоростные лимиты в городах (60 км/ч), на трассах (110 км/ч), при буксировке (50 км/ч) и в жилых зонах (20 км/ч)."
        },
        "key_rules": {
            "uz_latn": [
                "Aholi punktlarida barcha transport vositalariga — 60 km/soat dan oshmasligi belgilangan.",
                "Turar joy dahalari va hovli hududlarida — 20 km/soat.",
                "Aholi punktlaridan tashqarida: Yengil avtomobillarga avtomagistrallarda — 110 km/soat; Boshqa yo‘llarda — 100 km/soat.",
                "Mexanik transport vositalarini shatakka olib ketayotganda — 50 km/soat dan oshmasligi shart."
            ],
            "uz_cyrl": [
                "Аҳоли пунктларида — 60 км/соат (Тошкент, Нукус ва вилоят марказларида ҳам).",
                "Турар жой даҳалари ва ҳовлиларда — 20 км/соат.",
                "Аҳоли пунктидан ташқарида: Енгил автомобиллар автомагистралда — 110 км/соат, бошқа йўлларда — 100 км/соат.",
                "Шатакка олиб ҳаракатланганда — 50 км/соат."
            ],
            "ru": [
                "В населенных пунктах максимальная скорость — не более 60 км/ч.",
                "В жилых зонах и дворовых территориях — не более 20 км/ч.",
                "Вне населенных пунктов: легковым авто на автомагистралях — 110 км/ч, на остальных дорогах — 100 км/ч.",
                "При буксировке механических транспортных средств — не более 50 км/ч на любых дорогах."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Kuzovida odam tashiyotgan yuk avtomobillari va mototsikllarga aholi punktidan tashqarida ham 60 km/soat dan oshirish taqiqlanadi!",
                "⚠️ Tirkama ulangan yengil avtomobil avtomagistralda 90 km/soat, boshqa yo‘llarda 80 km/soat tezlikda harakatlanishi kerak."
            ],
            "uz_cyrl": [
                "⚠️ Кузовида одам ташиётган юк машиналари ва мотоцикллар учун аҳоли пунктидан ташқарида ҳам тезлик чегараси 60 км/соат!",
                "⚠️ Тиркамали енгил автомобиллар учун тезлик 20 км/соатга пасаяди (магистралда 90, бошқа йўлда 80)."
            ],
            "ru": [
                "⚠️ Грузовикам с людьми в кузове и мотоциклам вне города разрешено не более 60 км/ч!",
                "⚠️ Легковым автомобилям с прицепом на автомагистрали разрешено 90 км/ч, на остальных дорогах — 80 км/ч."
            ]
        },
        "ai_prompt": {
            "uz_latn": "O‘zbekistonda shatakka olish, tirkama bilan yurish va turar joy dahalaridagi tezlik me'yorlarini tushuntirib ber",
            "uz_cyrl": "Ўзбекистонда шатакка олиш, тиркама ва турар жой даҳаларидаги тезлик чегараларини тушунтириб бер",
            "ru": "Скоростные ограничения для легковых авто с прицепом и при буксировке в Узбекистане"
        }
    },
    {
        "order": 11,
        "category_id": 33,
        "category_ids": [33],
        "badge": {"uz_latn": "Quvib o‘tish", "uz_cyrl": "Қувиб ўтиш", "ru": "Обгон"},
        "duration_min": 7,
        "title": {
            "uz_latn": "Quvib o‘tish",
            "uz_cyrl": "Қувиб ўтиш",
            "ru": "Обгон и встречный разъезд"
        },
        "summary": {
            "uz_latn": "Qarama-qarshi harakat bo‘lagiga chiqib quvib o‘tish shartlari, xavfsizlik va quvib o‘tish qat'iyan taqiqlangan xavfli joylar.",
            "uz_cyrl": "Қарама-қарши ҳаракат бўлагига чиқиб қувиб ўтиш шартлари ва қувиб ўтиш қатъиян тақиқланган хавфли жойлар.",
            "ru": "Обгон с выездом на полосу встречного движения, правила безопасности и места, где обгон запрещен."
        },
        "key_rules": {
            "uz_latn": [
                "Quvib o‘tishdan oldin qarama-qarshi bo‘lak yetarli masofada bo‘sh ekanligiga ishonch hosil qilish shart.",
                "Orqadagi yoki oldindagi transport vositasi quvib o‘tishni boshlagan bo‘lsa, quvib o‘tish taqiqlanadi.",
                "Quvib o‘tilayotgan transport vositasi haydovchisiga tezlikni oshirish yoki boshqa yo‘llar bilan to‘sqinlik qilish qat'iyan man etiladi.",
                "Quvib o‘tish taqiqlanadi: chorrahalarda (asosiy bo‘lmagan yo‘llarda), piyodalar o‘tish joylarida, temir yo‘l kesishmalarida va ularga 100 metr yetmasdan, tepalik oxirida va ko‘rish cheklangan joylarda."
            ],
            "uz_cyrl": [
                "Қувиб ўтишдан олдин қарама-қарши бўлакнинг етарли даражада бўшлигига тўлиқ ишонч ҳосил қилиш шарт.",
                "Орқадаги ёки олдиндаги машина қувиб ўтишни бошлаган бўлса, ҳаракат бошлаш тақиқланади.",
                "Қувиб ўтилаётган ҳайдовчи тезликни ошириш орқали халақит бериши тақиқланади.",
                "Тартибга солинмаган чорраҳаларда, пиёдалар ўтиш жойларида, темир йўл кесишмасига 100 м қолганда қувиб ўтиш ТАҚИҚЛАНАДИ."
            ],
            "ru": [
                "Перед началом обгона водитель обязан убедиться в том, что полоса встречного движения свободна на достаточном расстоянии.",
                "Обгон запрещен, если следующее позади или движущееся впереди ТС уже подало сигнал обгона или поворота налево.",
                "Водителю обгоняемого ТС запрещается препятствовать обгону повышением скорости.",
                "Обгон запрещен на регулируемых перекрестках, на нерегулируемых при движении по второстепенной дороге, на пешеходных переходах, ж/д переездах и ближе 100 м перед ними."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Asosiy yo‘lda ketayotgan bo‘lsangiz ham, TARTIBGA SOLINGAN chorrahada quvib o‘tish TAQIQLANADI!",
                "⚠️ Temir yo‘l kesishmasidan O‘TGANDAN KEYIN quvib o‘tish mumkin, lekin kesishmaga 100 metr yetmasdan va kesishmaning o‘zida taqiqlanadi."
            ],
            "uz_cyrl": [
                "⚠️ Светофорли (тартибга солинган) чорраҳаларда ҳар қандай ҳолатда қувиб ўтиш ТАҚИҚЛАНАДИ!",
                "⚠️ Темир йўл кесишмасига 100 метр етмасдан ва кесишма устида қувиб ўтиш ман этилади."
            ],
            "ru": [
                "⚠️ На РЕГУЛИРУЕМЫХ перекрестках обгон запрещен ВСЕГДА, даже если вы едете по главной дороге!",
                "⚠️ На ж/д переездах и ближе 100 метров ПЕРЕД ними обгон запрещен (сразу после переезда — разрешен при отсутствии запрещающих знаков)."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Chorrahalarda va temir yo‘l kesishmalarida quvib o‘tish qachon mumkin va qachon taqiqlanadi?",
            "uz_cyrl": "Чорраҳаларда ва темир йўл кесишмаларида қувиб ўтиш қачон мумкин ва қачон тақиқланади?",
            "ru": "На каких перекрестках разрешен обгон и на каком расстоянии до переезда он запрещен?"
        }
    },
    {
        "order": 12,
        "category_id": 7,
        "category_ids": [7],
        "badge": {"uz_latn": "To‘xtash", "uz_cyrl": "Тўхташ", "ru": "Остановка и стоянка"},
        "duration_min": 7,
        "title": {
            "uz_latn": "To‘xtash va to‘xtab turish",
            "uz_cyrl": "Тўхташ va тўхтаб туриш",
            "ru": "Остановка и стоянка"
        },
        "summary": {
            "uz_latn": "5 daqiqagacha to‘xtash va 5 daqiqadan ortiq to‘xtab turish qoidalari, masofalar (5 metr, 15 metr, 50 metr).",
            "uz_cyrl": "5 дақиқагача тўхташ ва 5 дақиқадан ортиқ тўхтаб туриш қоидалари, масофалар (5 м, 15 м, 50 м).",
            "ru": "Остановка (до 5 мин) и стоянка (более 5 мин), критические расстояния (5 м, 15 м, 50 м)."
        },
        "key_rules": {
            "uz_latn": [
                "To‘xtash — transport vositasi harakatini 5 daqiqagacha (yoki odam chiqish-tushishi, yuk yuklash-tushirish uchun) to‘xtatishdir.",
                "To‘xtab turish — transport harakatini 5 daqiqadan ortiq muddatga qasddan to‘xtatib qo‘yishdir.",
                "To‘xtash taqiqlanadi: tramvay izlarida, ko‘priklarda, tunnellarda, piyodalar o‘tish joyida va unga 5 metr yetmasdan, chorraha qatnov qismlari kesishmasiga 5 metr yetmasdan, bekatlarga 15 metr yetmasdan.",
                "Aholi punktlaridan tashqarida to‘xtab turish faqat maxsus maydonchalarda yoki yo‘l yoqasida amalga oshiriladi."
            ],
            "uz_cyrl": [
                "Тўхташ — 5 дақиқагача (ёки юк ортиш/тушириш, одам чиқариш учун) ҳаракатни тўхтатиш.",
                "Тўхтаб туриш — 5 дақиқадан ортиқ вақтга транспортни тўхтатиб қўйиш.",
                "Пиёдалар ўтиш жойида ва ундан олдин 5 метрдан кам масофада тўхташ тақиқланади (лекин ўтгандан кейин дарҳол мумкин!).",
                "Беккатларга 15 метр етмасдан ва ўтгандан кейин 15 метр масофада тўхташ ман этилади."
            ],
            "ru": [
                "Остановка — преднамеренное прекращение движения на время до 5 минут (или более для посадки/высадки или погрузки).",
                "Стоянка — прекращение движения на время более 5 минут по причинам, не связанным с посадкой/высадкой или погрузкой.",
                "Остановка запрещена: на пешеходных переходах и ближе 5 м перед ними, на перекрестках и ближе 5 м от края пересекаемой проезжей части, ближе 15 м от остановок маршрутных ТС.",
                "Стоянка запрещена ближе 50 м от железнодорожных переездов."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Piyodalar o‘tish joyidan O‘TGANDAN KEYIN DARHOL to‘xtash MUMKIN! Faqat uning ustida va unga 5 metr yetmasdan oldin taqiqlanadi.",
                "⚠️ Temir yo‘l kesishmasiga 50 metrdan yaqin masofada TO‘XTAB TURISH taqiqlanadi (to‘xtash esa faqat kesishmaning o‘zida taqiqlanadi)."
            ],
            "uz_cyrl": [
                "⚠️ Пиёдалар ўтиш жойидан ЎТГАНДАН КЕЙИН ДАРҲОЛ тўхташ МУМКИН!",
                "⚠️ Темир йўл кесишмасига 50 метр етмасдан ТЎХТАБ ТУРИШ тақиқланади."
            ],
            "ru": [
                "⚠️ СРАЗУ ЗА пешеходным переходом остановка РАЗРЕШЕНА! Запрещено только на самом переходе и ближе 5 м ПЕРЕД ним.",
                "⚠️ Ближе 50 м от ж/д переезда запрещена СТОЯНКА. Остановка запрещена только на самом переезде."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Piyodalar o‘tish joyi, bekatlar va temir yo‘lda to‘xtash va to‘xtab turish masofalarini tushuntirib ber",
            "uz_cyrl": "Пиёдалар ўтиш жойи, бекатлар ва темир йўлда тўхташ ва тўхтаб туриш масофаларини тушунтириб бер",
            "ru": "Назови точные расстояния для остановки и стоянки около пешеходного перехода, остановок и ж/д переезда"
        }
    },
    {
        "order": 13,
        "category_id": 25,
        "category_ids": [25],
        "badge": {"uz_latn": "Chorraha", "uz_cyrl": "Чорраҳа", "ru": "Перекрестки"},
        "duration_min": 6,
        "title": {
            "uz_latn": "Chorrahalarda harakatlanish (Umumiy tartib)",
            "uz_cyrl": "Чорраҳаларда ҳаракатланиш (Умумий тартиб)",
            "ru": "Проезд перекрестков (Общие правила)"
        },
        "summary": {
            "uz_latn": "Chorraha turlari, tirbandlik paytida chorrahaga kirish taqiqi, chapga burilishda qarama-qarshi oqimga yo‘l berish.",
            "uz_cyrl": "Чорраҳа турлари, тирбандлик вақтида чорраҳага кириш тақиқи, чапга бурилишда рўпарадагиларга йўл бериш.",
            "ru": "Виды перекрестков, запрет выезда при заторах и правила поворота налево."
        },
        "key_rules": {
            "uz_latn": [
                "O‘ngga yoki chapga burilayotgan haydovchi o‘zi burilayotgan yo‘l qismini kesib o‘tayotgan piyodalar va velosipedchilarga yo‘l berishi shart.",
                "Agar chorrahada yoki undan keyin tirbandlik hosil bo‘lgan bo‘lsa va haydovchini chorrahada to‘xtashga majbur qilsa, chorrahaga kirish qat'iyan taqiqlanadi.",
                "Chorrahalar ikkiga bo‘linadi: Tartibga solingan (svetofor yoki tartibga soluvchi) va Tartibga solinmagan (belgilar bo‘yicha yoki teng ahamiyatli).",
                "Chorrahada chapga burilayotgan yoki qayrilib olayotgan haydovchi qarama-qarshidan to‘g‘riga yoki o‘ngga ketayotgan transportga yo‘l berishi shart."
            ],
            "uz_cyrl": [
                "Ўнгга ёки чапга бурилаётганда пиёдалар ва велосипедчиларга йўл бериш шарт.",
                "Чорраҳадан кейин тирбандлик бўлса ва тўхтаб қолиш хавфи бўлса, чорраҳага кириш ТАҚИҚЛАНАДИ.",
                "Чапга бурилаётган ҳайдовчи рўпарадан тўғрига ва ўнгга кетаётган машиналарга йўл беради."
            ],
            "ru": [
                "При повороте направо или налево водитель обязан уступить дорогу пешеходам и велосипедистам.",
                "Запрещается выезжать на перекресток, если за ним образовался затор, который вынудит водителя остановиться на перекрестке.",
                "Перекрестки делятся на регулируемые (светофор/регулировщик) и нерегулируемые (знаки приоритета или равнозначные).",
                "При повороте налево или развороте водитель обязан уступить дорогу ТС, движущимся со встречного направления прямо или направо."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Svetofor ishlayotgan chorrahada IMTIYOZ BELGILARI (2.1, 2.4 va h.k.) O‘Z KUCHINI YO‘QOTADI va ularga qaralmaydi!",
                "⚠️ Svetofor o‘chgan yoki faqat sariq miltillayotgan bo‘lsa — chorraha TARTIBGA SOLINMAGAN hisoblanadi va imtiyoz belgilariga amal qilinadi."
            ],
            "uz_cyrl": [
                "⚠️ Ишлаб турган светофор устидаги ИМТИЁЗ БЕЛГИЛАРИ (2.1 'Асосий йўл', 2.4 'Йўл беринг') КУЧИНИ ЙЎҚОТАДИ!",
                "⚠️ Светофор ўчганда ёки сариқ милтиллаганда чорраҳа тартибга солинмаган бўлади ва белгиларга қаралади."
            ],
            "ru": [
                "⚠️ При работающем светофоре знаки приоритета НЕ ДЕЙСТВУЮТ и водители руководствуются исключительно сигналами светофора!",
                "⚠️ При выключенном светофоре (или мигающем желтом) перекресток становится нерегулируемым и вступают в силу знаки приоритета."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Svetofor ishlayotganda uning ustidagi ustunlik belgilari amal qiladimi yoki yo‘qmi?",
            "uz_cyrl": "Светофор ишлаётганда унинг устидаги устунлик белгилари амал қиладими ёки йўқми?",
            "ru": "Действуют ли знаки приоритета при работающем светофоре?"
        }
    },
    {
        "order": 14,
        "category_id": 6,
        "category_ids": [6],
        "badge": {"uz_latn": "Svetoforli chorraha", "uz_cyrl": "Светофорли чорраҳа", "ru": "Регулируемые перекрестки"},
        "duration_min": 7,
        "title": {
            "uz_latn": "Tartibga solingan chorrahalar",
            "uz_cyrl": "Тартибга солинган чорраҳалар",
            "ru": "Регулируемые перекрестки"
        },
        "summary": {
            "uz_latn": "Yashil chiroqda burilish tartibi, teng sharoitda tramvay ustunligi, chorrahani tark etish va to‘xtash chizig‘i (STOP-liniya).",
            "uz_cyrl": "Яшил чироқда бурилиш тартиби, трамвай устунлиги, чорраҳани тарк этиш ва тўхташ чизиғи.",
            "ru": "Проезд на зеленый сигнал, приоритет трамвая в равных условиях и завершение проезда перекрестка."
        },
        "key_rules": {
            "uz_latn": [
                "Yashil chiroqda chapga burilayotgan haydovchi qarama-qarshidan to‘g‘riga yoki o‘ngga ketayotgan transportlarga yo‘l berishi shart.",
                "Teng sharoitda (ikkalasiga ham yashil yonganda) tramvay harakat yo‘nalishidan qat'i nazar oddiy avtomobillarga nisbatan MUTLAQ USTUNLIKKA ega.",
                "Yashil chiroqda chorrahaga kirgan haydovchi chiqishdagi svetofor ishorasidan qat'i nazar tanlagan yo‘nalishida harakatni yakunlashi shart (to‘xtash chizig‘i bo‘lmasa).",
                "Agar chorraha ichida to‘xtash chizig‘i (yoki 'STOP' belgisi 5.33) bo‘lsa, har bir oraliq svetofor oldida to‘xtash kerak."
            ],
            "uz_cyrl": [
                "Яшил чироқда чапга бурилаётган ҳайдовчи рўпарадан келаётганларга йўл беради.",
                "Тенг шароитда (ҳар иккисига ҳам яшил бўлганда) ТРАМВАЙ автомобиллардан устун ҳисобланади.",
                "Чорраҳага яшил чироқда кирган ҳайдовчи чиқишдаги чироқдан қатъи назар чиқиб кетиши шарт (стоп-чизиқ бўлмаса).",
                "Чорраҳа ичида стоп-чизиқ бўлса, ҳар бир чироққа бўysuniladi."
            ],
            "ru": [
                "При повороте налево на зеленый сигнал необходимо уступить дорогу встречным ТС, едущим прямо и направо.",
                "В равных условиях (при одновременно разрешающем сигнале) трамвай имеет безоговорочный приоритет перед безрельсовыми ТС.",
                "Водитель, въехавший на перекресток на разрешающий сигнал, обязан выехать в намеченном направлении независимо от сигнала светофора на выходе.",
                "Если на пути движения перед светофорами на перекрестке нанесена стоп-линия (знак 5.33), водитель обязан руководствоваться каждым светофором."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Qo‘shimcha strelka asosiy qizil bilan yonganda tramvay ham imtiyozga EGA EMAS — u asosiy yashilda kelayotganlarga yo‘l berishi shart!",
                "⚠️ Yashil chiroq yonganda ham, chorrahada manevrini yakunlayotgan boshqa mashinalarga va piyodalarga yo‘l berib, keyin harakat boshlanadi."
            ],
            "uz_cyrl": [
                "⚠️ Қўшимча стрелка қизил билан ёнганда ҳатто трамвай ҳам асосий яшил чироқда келаётганларга йўл бериши шарт!",
                "⚠️ Сизга яшил ёнганда ҳам, чорраҳада ҳаракатни тугатаётган машиналарни ўтказиб юбориб кейин юрилади."
            ],
            "ru": [
                "⚠️ Трамвай, двигающийся по сигналу стрелки с основным красным, обязан уступить дорогу ТС, движущимся с других направлений!",
                "⚠️ При включении зеленого сигнала водитель обязан уступить дорогу ТС, завершающим движение через перекресток, и пешеходам."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Tartibga solingan chorrahada tramvay qachon ustun bo‘ladi va qachon yo‘l berishi shart?",
            "uz_cyrl": "Тартибга солинган чорраҳада трамвай қачон устун бўлади ва қачон йўл бериши шарт?",
            "ru": "Когда трамвай имеет преимущество на регулируемом перекрестке, а когда обязан уступить?"
        }
    },
    {
        "order": 15,
        "category_id": 4,
        "category_ids": [4],
        "badge": {"uz_latn": "Teng chorraha", "uz_cyrl": "Тенг чорраҳа", "ru": "Равнозначные дороги"},
        "duration_min": 7,
        "title": {
            "uz_latn": "Tartibga solinmagan teng ahamiyatli chorrahalar",
            "uz_cyrl": "Тартибга солинмаган тенг аҳамиятли чорраҳалар",
            "ru": "Перекрестки равнозначных дорог"
        },
        "summary": {
            "uz_latn": "O‘ngdan xalaqit (o‘ng qo‘l qoidasi), teng sharoitda tramvayning mutlaq ustunligi, to‘rttala tomondan bir vaqtda kelgan holat.",
            "uz_cyrl": "Ўнгдан халақит ('ўнг қўл қоидаси'), тенг шароитда трамвай устунлиги, 4 та машина бир вақтда келгандаги қоида.",
            "ru": "Правило 'помехи справа', приоритет трамвая на равнозначном перекрестке и разъезд четырех ТС."
        },
        "key_rules": {
            "uz_latn": [
                "Teng ahamiyatli chorrahada haydovchi o‘ng tomondan yaqinlashib kelayotgan transport vositasiga yo‘l berishi shart ('o‘ngdan xalaqit').",
                "Teng ahamiyatli yo‘llar chorrahasida tramvay harakat yo‘nalishidan qat'i nazar barcha avtomobillarga nisbatan MUTLAQ USTUNLIKKA ega.",
                "Chapga burilayotgan yoki qayrilib olayotgan haydovchi avval qarama-qarshidan to‘g‘riga yoki o‘ngga ketayotgan transportga yo‘l beradi.",
                "To‘rtta tomondan ham bir vaqtda transport kelsa — qoidalarda bitta qat'iy ustun yo‘q, haydovchilar o‘zaro kelishuv bo‘yicha (bir-biriga yo‘l berib) o‘tadi."
            ],
            "uz_cyrl": [
                "Тенг аҳамиятли чорраҳада ҳайдовчи ЎНГ ТОМОНИДАН келаётган машинага йўл беради ('ўнгдан халақит').",
                "Тенг йўллар чорраҳасида ТРАМВАЙ доимо автомобиллардан устун бўлади.",
                "Чапга бурилаётганда рўпарадан келаётганларга йўл берилади.",
                "4 томондан бир вақтда машина келса — ҳайдовчилар ўзаро келишув асосида ҳаракатланади."
            ],
            "ru": [
                "На перекрестке равнозначных дорог водитель обязан уступить дорогу ТС, приближающимся справа ('помеха справа').",
                "На таких перекрестках трамвай имеет приоритет перед безрельсовыми ТС независимо от направления своего движения.",
                "При повороте налево водитель обязан уступить встречным автомобилям, едущим прямо или поворачивающим направо.",
                "Если к перекрестку с четырех сторон одновременно подъехали 4 ТС, разъезд осуществляется по взаимной договоренности водителей."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Tramvay uchun 'o‘ngdan xalaqit' qoidasi AMAL QILMAYDI! Teng chorrahada mashina tramvayning o‘ngida bo‘lsa ham, mashina tramvayga yo‘l beradi!",
                "⚠️ O‘ng tomonga burilayotgan haydovchining o‘ngida hech kim bo‘lmagani sababli u ko‘pincha chorrahadan birinchi bo‘lib o‘tib ketadi."
            ],
            "uz_cyrl": [
                "⚠️ Трамвай учун 'ўнгдан халақит' қоидаси ИШЛАМАЙДИ! Машина трамвайнинг ўнгида бўлса ҳам, барибир трамвайга йўл беради!",
                "⚠️ Ўнгга бурилаётган машинанинг ўнгида халақит бўлмагани учун у биринчи ўтади."
            ],
            "ru": [
                "⚠️ Для трамвая на равнозначном перекрестке правило 'помехи справа' НЕ ПРИМЕНЯЕТСЯ! Автомобиль всегда уступает трамваю, даже если едет справа от него.",
                "⚠️ Автомобиль, поворачивающий направо, обычно не имеет помехи справа и проезжает перекресток первым."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Teng ahamiyatli chorrahada 'o‘ngdan xalaqit' qoidasi va tramvayning imtiyozi qanday ishlaydi?",
            "uz_cyrl": "Тенг аҳамиятли чорраҳада 'ўнгдан халақит' ва трамвай имтиёзи қандай ишлайди?",
            "ru": "Как работает помеха справа на равнозначном перекрестке и почему трамвай всегда первый?"
        }
    },
    {
        "order": 16,
        "category_id": 38,
        "category_ids": [38],
        "badge": {"uz_latn": "Asosiy yo‘l", "uz_cyrl": "Асосий йўл", "ru": "Главная дорога прямо"},
        "duration_min": 6,
        "title": {
            "uz_latn": "Tartibga solinmagan chorrahalar (asosiy yo‘l to‘g‘ri yo‘nalishda)",
            "uz_cyrl": "Тартибга солинмаган чорраҳалар (асосий йўл тўғри йўналишда)",
            "ru": "Нерегулируемые перекрестки (главная дорога прямо)"
        },
        "summary": {
            "uz_latn": "Asosiy yo‘l (2.1 belgisi) o‘z yo‘nalishini o‘zgartirmagan holatda chorrahani birinchi bo‘lib kesib o‘tish tartibi.",
            "uz_cyrl": "Асосий йўл ўз йўналишини ўзгартирмаган ҳолатда чорраҳадан навбатма-навбат ўтиш тартиби.",
            "ru": "Очередность проезда перекрестка, когда главная дорога проходит в прямом направлении."
        },
        "key_rules": {
            "uz_latn": [
                "Asosiy yo‘lda kelayotgan transport vositalari ikkinchi darajali yo‘ldagilarga nisbatan mutlaq ustunlikka ega.",
                "Ikkala haydovchi ham asosiy yo‘lda bo‘lsa — chapga burilayotgan haydovchi qarama-qarshidan to‘g‘riga yoki o‘ngga ketayotganga yo‘l beradi.",
                "Ikkinchi darajali yo‘lda turgan haydovchilar avval asosiy yo‘ldagilarni to‘liq o‘tkazib yuboradi, so‘ngra o‘zaro 'o‘ngdan xalaqit' qoidasiga ko‘ra o‘tadi.",
                "Ikkinchi darajali yo‘lda kelayotgan tramvay asosiy yo‘ldagi avtomobilga yo‘l berishi shart."
            ],
            "uz_cyrl": [
                "Асосий йўлдаги транспортлар иккинчи даражали йўлдагиларга нисбатан устунликка эга.",
                "Ҳар икки ҳайдовчи асосий йўлда бўлса — чапга бурилаётган рўпарадагисига йўл беради.",
                "Иккинчи даражали йўлдагилар асосий йўлдаги барчани ўтказиб юбориб, сўнгра ўзаро 'ўнгдан халақит' қоидасига кўра ўтади.",
                "Иккинчи даражали йўлдаги трамвай асосий йўлдаги оддий машинага ҳам йўл бериши шарт."
            ],
            "ru": [
                "Транспортные средства на главной дороге имеют приоритет перед ТС на второстепенной дороге независимо от направления движения.",
                "Если оба ТС находятся на главной дороге, поворачивающий налево обязан уступить встречному, едущему прямо или направо.",
                "Водители на второстепенной дороге сначала пропускают всех с главной, затем разъезжаются между собой по 'помехе справа'.",
                "Трамвай на второстепенной дороге ОБЯЗАН уступить автомобилю на главной дороге."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Tramvay FAQAT teng sharoitda ustun bo‘ladi! Agar tramvay 'Yo‘l bering' (2.4) belgisida turgan bo‘lsa, u asosiy yo‘ldagi mashinaga yo‘l beradi!",
                "⚠️ Asosiy yo‘ldagi mashina qayerga burilmasin, u ikkinchi darajali yo‘ldagilardan oldin harakatlanadi."
            ],
            "uz_cyrl": [
                "⚠️ Трамвай ФАҚАТ тенг шароитда устун! Агар трамвай 2.4 'Йўл беринг' белгисида турса, асосий йўлдаги машинага йўл беради!",
                "⚠️ Асосий йўлдаги машина қайси томонга бурилмасин, иккинчи даражали йўлдагилардан олдин ўтади."
            ],
            "ru": [
                "⚠️ Трамвай имеет преимущество ТОЛЬКО в равных условиях! Если трамвай находится на второстепенной дороге со знаком 2.4, он уступает авто на главной!",
                "⚠️ Автомобиль на главной дороге проезжает раньше автомобилей со второстепенной дороги независимо от своего маневра."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Ikkinchi darajali yo‘ldagi tramvay va asosiy yo‘ldagi yengil mashina to‘qnashganda kim birinchi o‘tadi?",
            "uz_cyrl": "Иккинчи даражали йўлдаги трамвай ва асосий йўлдаги машинада ким биринчи ўтади?",
            "ru": "Уступает ли трамвай со второстепенной дороги автомобилю на главной?"
        }
    },
    {
        "order": 17,
        "category_id": 31,
        "category_ids": [31],
        "badge": {"uz_latn": "Yo‘nalish o‘zgarishi", "uz_cyrl": "Йўналиш ўзгариши", "ru": "Главная меняет направление"},
        "duration_min": 7,
        "title": {
            "uz_latn": "Tartibga solinmagan chorrahalar (asosiy yo‘l yo‘nalishi o‘zgarishi)",
            "uz_cyrl": "Тартибга солинмаган чорраҳалар (асосий йўл йўналиши ўзгариши)",
            "ru": "Нерегулируемые перекрестки (главная дорога меняет направление)"
        },
        "summary": {
            "uz_latn": "2.1 va 7.13 'Asosiy yo‘l yo‘nalishi' tablichkasi bo‘lgan chorrahalarda o‘tish tartibi (eng ko‘p adashtiradigan mavzu).",
            "uz_cyrl": "2.1 ва 7.13 'Асосий йўл йўналиши' белгилари бўлган чорраҳаларда ўтиш тартиби (энг кўп хато қилинадиган мавзу).",
            "ru": "Проезд перекрестков со знаками 2.1 и табличкой 7.13 'Направление главной дороги'."
        },
        "key_rules": {
            "uz_latn": [
                "Asosiy yo‘l yo‘nalishi o‘zgarganda, asosiy yo‘lda kelayotgan haydovchilar o‘zaro 'TENG CHORRAHA' (o‘ngdan xalaqit) qoidasiga amal qiladilar.",
                "Ikkinchi darajali yo‘lda kelayotgan haydovchilar ham asosiy yo‘ldagilarni to‘liq o‘tkazib bo‘lgach, o‘zaro 'o‘ngdan xalaqit' qoidasiga amal qiladilar.",
                "1-bosqich: Tablichkadagi qora yo‘g‘on chiziq (asosiy yo‘l) ustidagi mashinalar o‘zaro o‘ng qo‘l qoidasi bilan o‘tadi.",
                "2-bosqich: Qolgan ingichka chiziq (ikkinchi darajali yo‘l) ustidagi mashinalar o‘zaro o‘ng qo‘l qoidasi bilan o‘tadi."
            ],
            "uz_cyrl": [
                "Асосий йўл йўналиши бурилганда, асосий йўлдагилар ўзаро 'ўнгдан халақит' қоидаси билан чиқишади.",
                "Иккинчи даражали йўлдагилар ҳам асосий йўлдагиларни ўтказиб, сўнгра ўзаро 'ўнгдан халақит' қоидаси билан чиқишади.",
                "1-босқич: Йўғон чизиқдагилар ўзаро ўнг қўл қоидаси билан ўтади.",
                "2-босқич: Ингичка чизиқдагилар ўзаро ўнг қўл қоидаси билан ўтади."
            ],
            "ru": [
                "В случае, когда главная дорога меняет направление, водители на главной дороге руководствуются между собой правилами равнозначных дорог ('помеха справа').",
                "Водители на второстепенных дорогах также руководствуются между собой правилами равнозначных дорог после пропуска ТС с главной дороги.",
                "Шаг 1: Разъезжаются ТС на жирной полосе таблички (помеха справа).",
                "Шаг 2: Разъезжаются ТС на тонких полосах таблички (помеха справа)."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Eng keng tarqalgan xato: Ikkinchi darajali yo‘ldagi mashina to‘g‘ri ketayotgan bo‘lsa ham, asosiy yo‘lda burilayotgan mashinaga YO‘L BERISHI SHART!",
                "⚠️ Tablichkaga qarang: yo‘g‘on qora chiziqda turgan har qanday transport ingichka chiziqdagi transportdan mutlaq ustundir."
            ],
            "uz_cyrl": [
                "⚠️ Энг катта хато: Иккинчи даражали йўлда тўғри кетаётган машина асосий йўлда бурилаётган машинага ЙЎЛ БЕРИШИ ШАРТ!",
                "⚠️ Доимо олдин йўғон чизиқдагилар ўтади, фақат улардан кейин ингичка чизиқдагилар ҳаракатланади."
            ],
            "ru": [
                "⚠️ Самая частая ошибка: автомобиль на второстепенной дороге едет прямо и ошибочно думает, что имеет приоритет перед поворачивающим с главной дороги. Это грубая ошибка — главная дорога всегда главнее!",
                "⚠️ ТС на второстепенной дороге обязаны уступить всем ТС на главной независимо от их направления движения."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Asosiy yo‘l yo‘nalishi o‘zgarganda (tablichka 7.13) kim birinchi va kim ikkinchi o‘tishini formulasi bilan tushuntirib ber",
            "uz_cyrl": "Асосий йўл йўналиши ўзгарганда 7.13 табличкаси бўйича ўтишнинг аниқ қоидасини тушунтириб бер",
            "ru": "Формула проезда перекрестка при изменении направления главной дороги (табличка 7.13)"
        }
    },
    {
        "order": 18,
        "category_id": 30,
        "category_ids": [30],
        "badge": {"uz_latn": "Piyodalar yo‘li", "uz_cyrl": "Пиёдалар йўли", "ru": "Пешеходные переходы"},
        "duration_min": 5,
        "title": {
            "uz_latn": "Piyodalar o‘tish joylari va bekatlar",
            "uz_cyrl": "Пиёдалар ўтиш жойлари ва бекатлар",
            "ru": "Пешеходные переходы и остановки"
        },
        "summary": {
            "uz_latn": "Tartibga solinmagan o‘tish joyida piyodaga yo‘l berish, qo‘shni qatordagi to‘xtagan avtomobil va bekatdan chiqayotgan avtobus.",
            "uz_cyrl": "Тартибга солинмаган ўтиш жойида пиёдага йўл бериш, тўхтаган автомобиль ёнидан ўтиш ва бекат қоидаси.",
            "ru": "Пропуск пешеходов на нерегулируемом переходе, опережение остановившегося ТС и остановки маршрутных ТС."
        },
        "key_rules": {
            "uz_latn": [
                "Tartibga solinmagan piyodalar o‘tish joyiga yaqinlashayotgan haydovchi qatnov qismini kesib o‘tayotgan piyodalarga yo‘l berishi shart.",
                "Agar piyodalar o‘tish joyi oldida transport vositasi to‘xtagan yoki tezligini kamaytirgan bo‘lsa, qo‘shni bo‘lakdagi haydovchi ham to‘xtashi yoki tezlikni kamaytirishi shart.",
                "Aholi punktlarida haydovchilar bekatdan yo‘lga chiqayotgan avtobus va trolleybusga yo‘l berishlari shart.",
                "Tramvay bekatida eshiklaridan qatnov qismi orqali chiqayotgan/tushayotgan yo‘lovchilarga yo‘l berish lozim."
            ],
            "uz_cyrl": [
                "Пиёдалар ўтиш жойига яқинлашганда қатнов қисмидаги пиёдаларга йўл бериш шарт.",
                "Агар қўшни бўлакдаги машина тўхтаган бўлса, унинг ёнидан ўтаётган ҳайдовчи ҳам АЛБАТТА тўхташи шарт!",
                "Аҳоли пунктларида бекатдан чиқаётган автобусларга йўл бериш шарт."
            ],
            "ru": [
                "Водитель обязан уступить дорогу пешеходам, переходящим дорогу или вступившим на проезжую часть на нерегулируемом переходе.",
                "Если перед переходом остановилось или снизило скорость ТС, водители соседних полос ОБЯЗАНЫ также остановиться или снизить скорость.",
                "В населенных пунктах водители обязаны уступать дорогу автобусам и троллейбусам, начинающим движение от обозначенной остановки."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ O‘ng qatordagi mashina piyodalar o‘tish joyi oldida to‘xtasa, chap qatordagi haydovchi to‘xtamasdan o‘tib keta OLMAYDI! Bu eng qat'iy tekshiriladigan imtihon qoidasi.",
                "⚠️ Bekatdan chiqayotgan avtobusga yo‘l berish majburiyati FAQAT aholi punktlarida amal qiladi (shahar tashqarisida yo‘l berilmaydi)."
            ],
            "uz_cyrl": [
                "⚠️ Қўшни машина пиёдалар ўтиш жойи олдида тўхтаса — тўхтамасдан ўтиб кетиш қатъиян тақиқланади!",
                "⚠️ Бекатдан чиқаётган автобусга йўл бериш қоидаси фақат шаҳар ичида амал қилади."
            ],
            "ru": [
                "⚠️ Самая опасная ловушка: если справа перед переходом притормозила машина, нельзя продолжать движение без снижения скорости!",
                "⚠️ Приоритет автобуса от остановки действует ТОЛЬКО в населенных пунктах (на трассе автобус уступает дорогу)."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Piyodalar o‘tish joyi oldida to‘xtagan mashinani quvib o‘tish va bekatdagi avtobusga yo‘l berish qoidalarini tushuntirib ber",
            "uz_cyrl": "Пиёдалар ўтиш жойи олдида тўхтаган машина ёнидан ўтиш ва автобусга йўл бериш қоидалари",
            "ru": "Правила проезда пешеходного перехода, если соседняя машина остановилась"
        }
    },
    {
        "order": 19,
        "category_id": 19,
        "category_ids": [19],
        "badge": {"uz_latn": "Yo‘nalishli transport", "uz_cyrl": "Йўналишли транспорт", "ru": "Маршрутные ТС"},
        "duration_min": 5,
        "title": {
            "uz_latn": "Yo‘nalishli transport vositalarining imtiyozlari",
            "uz_cyrl": "Йўналишли транспорт воситаларининг имтиёзлари",
            "ru": "Приоритет маршрутных транспортных средств"
        },
        "summary": {
            "uz_latn": "A ajratilgan bo‘lagi, yo‘nalishli transport vositalari yo‘lkasi va bekatdan qo‘zg‘alayotgan avtobuslar.",
            "uz_cyrl": "А ажратилган бўлаги, йўналишли транспорт йўлаги ва бекатдан чиқаётган автобуслар.",
            "ru": "Полоса для маршрутных ТС (полоса 'А') и приоритет автобусов."
        },
        "key_rules": {
            "uz_latn": [
                "5.11 'Yo‘nalishli transport vositalari uchun ajratilgan bo‘lak' (A harfi) belgilangan bo‘lakda boshqa transport vositalarining harakatlanishi taqiqlanadi.",
                "Ushbu bo‘lak uzuq-uzuq chiziq bilan ajratilgan bo‘lsa, burilish oldidan unga qayta tizilish va odam mindirish/tushirish uchun to‘xtashga ruxsat beriladi.",
                "Aholi punktlarida belgilangan bekatdan harakatni boshlayotgan avtobusga haydovchilar yo‘l berishlari lozim."
            ],
            "uz_cyrl": [
                "'А' ҳарфи билан белгиланган ажратилган йўлакда бошқа транспортларнинг юриши тақиқланади.",
                "Агар йўлак узуқ-узуқ чизиқ билан ажратилган бўлса, бурилиш олдидан ёки йўловчи миндириш учун унга кириш мумкин.",
                "Бекатдан қўзғалаётган автобусларга йўл бериш шарт."
            ],
            "ru": [
                "По полосе с буквой 'А' движение других ТС запрещено.",
                "Если полоса отделена прерывистой линией, на нее разрешается перестраиваться для поворота направо или посадки/высадки пассажиров.",
                "В городах водители обязаны уступать дорогу маршрутным ТС, начинающим движение от остановки."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ 'A' bo‘lagi yaxlit (tutash) chiziq bilan ajratilgan bo‘lsa, unga har qanday holatda kirish qat'iyan taqiqlanadi!",
                "⚠️ Odam mindirish/tushirish yo‘nalishli transportga xalaqit bermaslik sharti bilangina ruxsat etiladi."
            ],
            "uz_cyrl": [
                "⚠️ 'А' бўлаги яхлит чизиқ билан ажратилган бўлса, унга кириш мутлақо мумкин эмас!",
                "⚠️ Йўловчи миндириш фақат автобусларга халақит бермаслик шарти билан мумкин."
            ],
            "ru": [
                "⚠️ Если полоса 'А' отделена сплошной линией разметки, въезд на нее категорически запрещен в любых случаях!",
                "⚠️ Посадка/высадка на прерывистой линии разрешена ТОЛЬКО при условии ненарушения движения маршрутных ТС."
            ]
        },
        "ai_prompt": {
            "uz_latn": "A harfli ajratilgan bo‘lakka oddiy mashinalar qachon kirishi mumkin?",
            "uz_cyrl": "А ҳарфли ажратилган бўлакка оддий машиналар қачон кириши мумкин?",
            "ru": "Когда разрешен заезд на полосу для маршрутных ТС обычным автомобилям?"
        }
    },
    {
        "order": 20,
        "category_id": 36,
        "category_ids": [36],
        "badge": {"uz_latn": "Temir yo‘l", "uz_cyrl": "Темир йўл", "ru": "Ж/Д переезды"},
        "duration_min": 6,
        "title": {
            "uz_latn": "Temir yo‘l kesishmalari orqali harakatlanish",
            "uz_cyrl": "Темир йўл кесишмалари орқали ҳаракатланиш",
            "ru": "Движение через железнодорожные пути"
        },
        "summary": {
            "uz_latn": "Shlagbaum, svetofor, navbatchi ishoralari, poezd yaqinlashganda to‘xtash joyi va favqulodda to‘xtab qolish choralari.",
            "uz_cyrl": "Шлагбаум, светофор, навбатчи ишоралари, поезд яқинлашганда тўхташ жойи ва фавқулодда тўхтаб қолиш.",
            "ru": "Шлагбаум, светофоры, дежурный по переезду, безопасные расстояния остановки и вынужденная остановка."
        },
        "key_rules": {
            "uz_latn": [
                "Haydovchilar temir yo‘lni faqat temir yo‘l kesishmalari orqali, poezdga (lokomotivga) yo‘l bergan holda kesib o‘tishlari kerak.",
                "Kesishmaga kirish taqiqlanadi: shlagbaum yopiq yoki yopilayotgan bo‘lsa, qizil chiroq yongan bo‘lsa, navbatchi taqiqlovchi ishora berayotgan bo‘lsa.",
                "To‘xtash zarur bo‘lganda: Stop-chiziq (yoki 2.5 belgisi) oldida; ular bo‘lmasa shlagbaumga 5 metr qolganda; shlagbaum bo‘lmasa yaqin relsdan 10 metr qolganda to‘xtaladi."
            ],
            "uz_cyrl": [
                "Поездга (локомотивга) доимо мутлақ йўл берилади.",
                "Шлагбаум ёпиқ ёки ёпилаётганда, қизил чироқ ёнганда кесишмага кириш тақиқланади.",
                "Тўхташ жойлари: Стоп-чизиқ олдида; у бўлмаса шлагбаумга 5 метр қолганда; шлагбаум бўлмаса рельсга 10 метр қолганда тўхталади."
            ],
            "ru": [
                "Поезд (локомотив, дрезина) всегда имеет абсолютный приоритет.",
                "Запрещается выезжать на переезд при закрытом или закрывающемся шлагбауме, запрещающем сигнале светофора или дежурного.",
                "Остановка перед переездом: у стоп-линии или знака 2.5; если их нет — не ближе 5 м от шлагбаума; при отсутствии шлагбаума — не ближе 10 м до ближайшего рельса."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Shlagbaum ochilgan bo‘lsa ham, qizil chiroq yonib turgan bo‘lsa harakatlanish QAT'IYAN TAQIQLANADI!",
                "⚠️ Temir yo‘l kesishmasida to‘xtash, quvib o‘tish, orqaga harakatlanish va qayrilib olish butunlay taqiqlangan."
            ],
            "uz_cyrl": [
                "⚠️ Шлагбаум очиқ бўлса-да, қизил чироқ милтиллаб турса ўтиш ТАҚИҚЛАНАДИ!",
                "⚠️ Кесишма устида тўхташ, қувиб ўтиш, қайрилиш ва орқага ҳаракатланиш мутлақо ман этилади."
            ],
            "ru": [
                "⚠️ При открытом шлагбауме, но горящем красном сигнале светофора выезд на переезд КАТЕГОРИЧЕСКИ ЗАПРЕЩЕН!",
                "⚠️ На ж/д переездах запрещены: остановка, стоянка, разворот, задний ход и обгон."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Temir yo‘l kesishmasida to‘xtash masofalari (5 metr va 10 metr qoidalari) qanday farqlanadi?",
            "uz_cyrl": "Темир йўл кесишмасида тўхташ масофалари (5 м ва 10 м қоидаси) қандай фарқланади?",
            "ru": "На каком расстоянии останавливаться перед ж/д переездом со шлагбаумом и без шлагбаума?"
        }
    },
    {
        "order": 21,
        "category_id": 13,
        "category_ids": [13],
        "badge": {"uz_latn": "Magistral", "uz_cyrl": "Магистрал", "ru": "Автомагистраль"},
        "duration_min": 5,
        "title": {
            "uz_latn": "Avtomagistrallarda harakatlanish",
            "uz_cyrl": "Автомагистралларда ҳаракатланиш",
            "ru": "Движение по автомагистралям"
        },
        "summary": {
            "uz_latn": "5.1 belgisi bilan belgilangan yo‘l. Tezlik 110 km/soat. Piyodalar, traktorlar, orqaga yurish va qayrilib olish taqiqlari.",
            "uz_cyrl": "5.1 белгили йўл. Тезлик 110 км/соат. Пиёдалар, тракторлар, орқага юриш ва қайрилиш тақиқлари.",
            "ru": "Дорога со знаком 5.1. Скорость 110 км/ч. Запреты для пешеходов, тракторов, разворота и заднего хода."
        },
        "key_rules": {
            "uz_latn": [
                "Avtomagistralda tezligi 40 km/soat dan kam bo‘lgan transport vositalarining harakatlanishi taqiqlanadi.",
                "Orqaga harakatlanish va ajratuvchi bo‘lakdagi texnologik uzilish joylaridan qayrilib olish qat'iyan taqiqlanadi.",
                "To‘xtab turish faqat 'P' (5.15) yoki 'Dam olish joyi' (7.11) belgilari bilan jihozlangan maxsus maydonchalardagina ruxsat etiladi.",
                "Yuk avtomobillariga (3.5 tonnadan ortiq) 2-bo‘lakdan nariga chapga chiqish taqiqlanadi."
            ],
            "uz_cyrl": [
                "Автомагистралда тезлиги 40 км/соатдан кам транспортларнинг юриши тақиқланади.",
                "Орқага юриш ва технологик узилиш жойларидан қайрилиб олиш қатъиян ман этилади.",
                "Тўхтаб туриш фақат махсус белгиланган 'P' ёки дам олиш майдончаларида мумкин.",
                "3.5 тоннадан ортиқ юк машиналари 2-бўлакдан чапга чиқиши тақиқланади."
            ],
            "ru": [
                "На автомагистралях запрещено движение ТС, скорость которых по техпричинам менее 40 км/ч.",
                "Запрещены разворот и въезд в технологические разрывы разделительной полосы, а также движение задним ходом.",
                "Остановка разрешена только на специальных площадках, обозначенных знаками 5.15 или 7.11.",
                "Грузовым автомобилям свыше 3.5 т запрещено выезжать далее второй полосы."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Avtomagistralda o‘quv mashg‘ulotlarini o‘tkazish TAQIQLANADI!",
                "⚠️ Majburiy to‘xtab qolgan taqdirda mashina qatnov qismidan chetga chiqariladi, avariya chirog‘i yoqiladi va 30 metrdan kam bo‘lmagan masofada belgi qo‘yiladi."
            ],
            "uz_cyrl": [
                "⚠️ Автомагистралда ўқув машинасида бошқаришни ўргатиш ТАҚИҚЛАНАДИ!",
                "⚠️ Мажбурий тўхтаганда белги камида 30 метр масофада ўрнатилади."
            ],
            "ru": [
                "⚠️ На автомагистралях ЗАПРЕЩАЕТСЯ учебная езда!",
                "⚠️ Знак аварийной остановки при вынужденной остановке выставляется не менее чем за 30 метров."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Avtomagistralda nimalar taqiqlangan va majburiy to‘xtaganda nima qilish kerak?",
            "uz_cyrl": "Автомагистралда нималар тақиқланган ва мажбурий тўхтаганда нима қилиш керак?",
            "ru": "Что запрещено на автомагистрали и правила вынужденной остановки?"
        }
    },
    {
        "order": 22,
        "category_id": 35,
        "category_ids": [35],
        "badge": {"uz_latn": "Turar joy dahasi", "uz_cyrl": "Турар жой даҳаси", "ru": "Жилая зона"},
        "duration_min": 5,
        "title": {
            "uz_latn": "Turar joy dahalarida harakatlanish",
            "uz_cyrl": "Турар жой даҳаларида ҳаракатланиш",
            "ru": "Движение в жилых зонах"
        },
        "summary": {
            "uz_latn": "5.38 belgili hududlar va hovlilar. Piyodalarning mutlaq ustunligi, 20 km/soat tezlik va tranzit harakat taqiqi.",
            "uz_cyrl": "5.38 белгили ҳудудлар ва ҳовлилар. Пиёдалар устунлиги, 20 км/соат тезлик ва транзит юриш тақиқи.",
            "ru": "Жилые зоны и дворы. Приоритет пешеходов, ограничение скорости 20 км/ч и запрет сквозного движения."
        },
        "key_rules": {
            "uz_latn": [
                "Turar joy dahalarida piyodalar trotuarda ham, butun qatnov qismida ham harakatlanishi mumkin va ular mutlaq ustunlikka ega.",
                "Ruxsat etilgan eng yuqori tezlik — 20 km/soat.",
                "Turar joy dahalaridan chiqayotgan haydovchi yo‘ldagi barcha transport vositalari va piyodalarga yo‘l berishi shart.",
                "Turar joy dahalarida tranzit (kesib o‘tish) harakatlanish, dvigateli ishlab turgan holda to‘xtab turish va o‘quv haydashi taqiqlanadi."
            ],
            "uz_cyrl": [
                "Турар жой даҳаларида пиёдалар йўлнинг исталган жойидан юриши мумкин ва устунликка эга.",
                "Энг юқори тезлик — 20 км/соат.",
                "Ҳовлилардан ва даҳалардан чиқаётганда йўлдаги барчага йўл берилади.",
                "Транзит (ўтиб кетиш учун) ҳаракатланиш ва двигателни ишлатиб тўхтаб туриш тақиқланади."
            ],
            "ru": [
                "В жилых зонах пешеходы имеют преимущество и могут двигаться как по тротуарам, так и по всей проезжей части.",
                "Максимальная скорость движения — не более 20 км/ч.",
                "При выезде из жилой зоны водители обязаны уступить дорогу другим участникам движения.",
                "Запрещены сквозное движение, учебная езда и стоянка с работающим двигателем."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Ushbu qoidalar rasmiy belgi bo‘lmagan har qanday hovli hududlariga ham to‘liq taalluqlidir!",
                "⚠️ Piyodalar ustunlikka ega bo‘lsa-da, transport vositalari harakatiga asossiz xalaqit bermasliklari lozim."
            ],
            "uz_cyrl": [
                "⚠️ Ушбу қоидалар барча ҳовли ҳудудларига ҳам тўлиқ тегишлидир!",
                "⚠️ Ҳовлидан чиқиш чорраҳа ҳисобланмайди."
            ],
            "ru": [
                "⚠️ Правила жилой зоны распространяются на ВСЕ дворовые территории, даже без знака 5.38!",
                "⚠️ Выезды из дворов не являются перекрестками."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Hovlilarda va turar joy dahalarida nimalar taqiqlangan va tezlik qancha?",
            "uz_cyrl": "Ҳовлиларда нималар тақиқланган ва тезлик қанча бўлиши керак?",
            "ru": "Ограничения и правила движения в жилых зонах и во дворах"
        }
    },
    {
        "order": 23,
        "category_id": 22,
        "category_ids": [22],
        "badge": {"uz_latn": "Chiroqlar", "uz_cyrl": "Чироқлар", "ru": "Свет и фары"},
        "duration_min": 6,
        "title": {
            "uz_latn": "Tashqi yoritish asboblaridan foydalanish",
            "uz_cyrl": "Ташқи ёритиш асбобларидан фойдаланиш",
            "ru": "Пользование внешними световыми приборами"
        },
        "summary": {
            "uz_latn": "Uzoqni (dalniy) va yaqinni (blijniy) yorituvchi chiroqlar, kunduzgi chiroqlar, tuman chiroqlari va ko‘zni qamashtirish holatlari.",
            "uz_cyrl": "Узоқни ва яқинни ёритувчи чироқлар, кундузги чироқлар, туман чироқлари ва кўзни қамаштириш ҳолатлари.",
            "ru": "Ближний и дальний свет, ДХО, противотуманные фары и ослепление."
        },
        "key_rules": {
            "uz_latn": [
                "Qorong‘i vaqtda va yetarli ko‘rinmaslik sharoitida, shuningdek tunnellarda yaqin yoki uzoqni yorituvchi chiroqlar yoqilishi shart.",
                "Uzoqni yorituvchi chiroq qarama-qarshi kelayotgan mashinaga kamida 150 metr qolganda yaqinga o‘tkazilishi shart.",
                "Ko‘cha chiroqlari yoqilgan aholi punktlarida uzoqni yorituvchi chiroqlardan foydalanish taqiqlanadi.",
                "Ko‘z qamashtirilganda: haydovchi zudlik bilan avariya chiroqlarini yoqishi va bo‘lakni o‘zgartirmasdan tezlikni kamaytirib to‘xtashi shart."
            ],
            "uz_cyrl": [
                "Қоронғида ва туннелларда чироқлар ёқилган бўлиши шарт.",
                "Узоқни ёритувчи чироқ қаршидаги машинага камида 150 метр қолганда яқинга ўтказилади.",
                "Ёритилган шаҳар кўчаларида узоқни ёритувчи чироқдан (дальний) фойдаланиш тақиқланади.",
                "Кўз қамаштирилганда: авария чироқлари ёқилади ва қаторни ўзгартирмасдан тўхталади."
            ],
            "ru": [
                "В темное время суток, в условиях недостаточной видимости и в тоннелях должны быть включены фары дальнего или ближнего света.",
                "Дальний свет должен быть переключен на ближний не менее чем за 150 м до встречного ТС.",
                "В населенных пунктах, если дорога освещена, дальний свет запрещен.",
                "При ослеплении водитель обязан включить аварийную сигнализацию и, не меняя полосы движения, снизить скорость и остановиться."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Ko‘z qamashtirilganda ruxsat berilgan yagona to‘g‘ri harakat — o‘z yo‘lida qolib to‘xtashdir! Chetga (obochinaga) burilish qat'iyan taqiqlanadi (xavfli).",
                "⚠️ Orqa tuman chiroqlarini tormoz chiroqlariga ulash taqiqlanadi."
            ],
            "uz_cyrl": [
                "⚠️ Кўз қамаштирилганда бошқа қаторга ўтиш ёки йўл четига бурилиш ТАҚИҚЛАНАДИ — фақат ўз қаторида тўхталади!",
                "⚠️ Орқа туман чироқлари фақат туман вақтида ёқилади."
            ],
            "ru": [
                "⚠️ При ослеплении категорически запрещено перестраиваться или съезжать на обочину! Остановка строго в своей полосе.",
                "⚠️ Задние противотуманные фонари разрешается применять только в условиях недостаточной видимости."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Ko‘z qamashtirilganda haydovchi nima qilishi shart va uzoqni yaqinga o‘tkazish masofasi qancha?",
            "uz_cyrl": "Кўз қамаштирилганда ҳайдовчи нима қилиши шарт ва дальнийни ближнийга ўтказиш масофаси қанча?",
            "ru": "Алгоритм действий водителя при ослеплении и расстояние переключения фар"
        }
    },
    {
        "order": 24,
        "category_id": 32,
        "category_ids": [32],
        "badge": {"uz_latn": "Shatakka olish", "uz_cyrl": "Шатакка олиш", "ru": "Буксировка"},
        "duration_min": 6,
        "title": {
            "uz_latn": "Mexanik transport vositalarini shatakka olish",
            "uz_cyrl": "Механик транспорт воситаларини шатакка олиш",
            "ru": "Буксировка механических транспортных средств"
        },
        "summary": {
            "uz_latn": "Egik va qattiq ulanma, qisman ortish usuli, tormozi va rul boshqaruvi ishlamaydigan mashinalarni shatakka olish cheklovlari.",
            "uz_cyrl": "Эгилувчан ва қаттиқ уланма, қисман ортиш усули, тормози ва рули ишламайдиган машиналарни шатакка олиш.",
            "ru": "Гибкая и жесткая сцепка, частичная погрузка, буксировка с неисправными тормозами и рулем."
        },
        "key_rules": {
            "uz_latn": [
                "Shatakka olishda harakatlanish tezligi — 50 km/soat dan oshmasligi shart.",
                "Egik ulanma (tros) uzunligi — 4 metrdan 6 metrgacha bo‘lishi va har bir metriga qizil bayroqcha yoki belgi qo‘yilishi kerak.",
                "Qattiq ulanma uzunligi — 4 metrdan oshmasligi kerak.",
                "Yaxmalak (muzlama) paytida egik ulanmada (trosda) shatakka olish QAT'IYAN TAQIQLANADI.",
                "Rul boshqaruvi ishlamayotgan bo‘lsa — faqat qisman ortish usulida shatakka olinadi."
            ],
            "uz_cyrl": [
                "Шатакка олишда энг юқори тезлик — 50 км/соат.",
                "Эгилувчан уланма (трос) узунлиги — 4 метрдан 6 метргача бўлиши шарт.",
                "Қаттиқ уланма — 4 метрдан ошмаслиги лозим.",
                "Музлама (яхмалак) вақтида тросда шатакка олиш ТАҚИҚЛАНАДИ.",
                "Рули ишламаса — фақат қисман ортиш усулида олиб кетилади."
            ],
            "ru": [
                "Скорость при буксировке не должна превышать 50 км/ч.",
                "При буксировке на гибкой сцепке расстояние должно быть от 4 до 6 м (со щитками/флажками через каждый метр).",
                "При жесткой сцепке расстояние между ТС — не более 4 м.",
                "Буксировка на гибкой сцепке в гололедицу КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНА.",
                "С неисправным рулевым управлением буксировка разрешена только методом частичной погрузки."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Tormozi ishlamaydigan mashinani qattiq ulanmada shatakka olish mumkin, FAQAT uning vazni shatakka olayotgan mashina vaznining yarmidan ko‘p bo‘lmasa!",
                "⚠️ Mototsikllarni (yon tirkamasiz) shatakka olish ham, ularda shatakka olish ham taqiqlanadi."
            ],
            "uz_cyrl": [
                "⚠️ Тормози ишламаса қаттиқ уланмада олиш мумкин, лекин оғирлиги тортаётган машина оғирлигининг ярмидан ошмаслиги керак!",
                "⚠️ Тросда музлама пайтида шатакка олиш мутлақо мумкин эмас."
            ],
            "ru": [
                "⚠️ При неисправной тормозной системе буксировка на жесткой сцепке разрешена, если фактическая масса буксируемого ТС не превышает половины массы буксирующего!",
                "⚠️ Одиночные мотоциклы без бокового прицепа буксировать запрещено."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Yaxmalakda qaysi usulda shatakka olish taqiqlanadi va tormozi ishlamaydigan mashinani tortish qoidalari qanday?",
            "uz_cyrl": "Музламада қандай шатакка олиш тақиқланади ва тормози ишламайдиган машинани тортиш қоидалари қандай?",
            "ru": "Правила буксировки в гололед и при неисправных тормозах"
        }
    },
    {
        "order": 25,
        "category_id": 40,
        "category_ids": [40],
        "badge": {"uz_latn": "Odam tashish", "uz_cyrl": "Одам ташиш", "ru": "Перевозка людей"},
        "duration_min": 5,
        "title": {
            "uz_latn": "Odam tashish qoidalari",
            "uz_cyrl": "Одам ташиш қоидалари",
            "ru": "Перевозка людей"
        },
        "summary": {
            "uz_latn": "Yo‘lovchilar soni chegarasi, bolalarni tashish qoidalari, yuk avtomobili kuzovida odam tashish shartlari.",
            "uz_cyrl": "Йўловчилар сони, болаларни ташиш қоидалари, юк машинаси кузовида одам ташиш шартлари.",
            "ru": "Нормы посадки, перевозка детей и требования к кузовам грузовых авто."
        },
        "key_rules": {
            "uz_latn": [
                "Odamlar soni transport vositasining texnik tavsifnomasida ko‘rsatilgan o‘rindiqlar sonidan oshmasligi shart.",
                "12 yoshga to‘lmagan bolalarni mototsikl orqa o‘rindig‘ida tashish taqiqlanadi.",
                "12 yoshga to‘lmagan bolalarni yengil avtomobilning old o‘rindig‘ida faqat maxsus bolalar o‘rindig‘i (avtokreslo) bo‘lgandagina tashishga ruxsat beriladi.",
                "Yuk avtomobili kuzovida odam tashish uchun bort balandligi poldan kamida 1 metr bo‘lishi va o‘rindiqlar pol sathidan 30-50 sm pastda o‘rnatilishi lozim."
            ],
            "uz_cyrl": [
                "Одамлар сони техник тавсифномадаги ўриндиқлар сонидан ошмаслиги керак.",
                "12 ёшга тўлмаган болаларни мотоциклда ташиш тақиқланади.",
                "12 ёшгача бўлган болаларни олд ўриндиқда фақат болалар автокреслоси билан ташиш мумкин.",
                "Юк машинаси кузовида одам ташишда борт баландлиги камида 1 метр бўлиши шарт."
            ],
            "ru": [
                "Число перевозимых людей не должно превышать норму, предусмотренную технической характеристикой ТС.",
                "Запрещается перевозить детей до 12 лет на заднем сиденье мотоцикла.",
                "Детей до 12 лет на переднем сиденье легкового авто разрешено перевозить только с использованием детского удерживающего устройства.",
                "Борта грузового авто для перевозки людей должны быть высотой не менее 1 м от пола."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Avtomobil harakatlanayotganda eshiklarni ochish va odamlarni kuzovdan tashqariga chiqarib yurish qat'iyan taqiqlanadi.",
                "⚠️ Yuk avtomobili kuzovida odam tashiyotganda tezlik 60 km/soat dan oshmasligi shart."
            ],
            "uz_cyrl": [
                "⚠️ Ҳаракат вақтида эшикларни очиш ва тана аъзоларини чиқариб юриш тақиқланади.",
                "⚠️ Кузовда одам ташиганда тезлик чегараси — 60 км/соат."
            ],
            "ru": [
                "⚠️ Запрещается открывать двери во время движения и высовываться из окон.",
                "⚠️ Скорость грузовика с людьми в кузове вне города ограничена 60 км/ч."
            ]
        },
        "ai_prompt": {
            "uz_latn": "12 yoshgacha bo‘lgan bolalarni mashinada va mototsiklda tashish qoidalari qanday?",
            "uz_cyrl": "12 ёшгача болаларни машинада ва мотоциклда ташиш қоидалари қандай?",
            "ru": "Правила перевозки детей до 12 лет в автомобиле и на мотоцикле"
        }
    },
    {
        "order": 26,
        "category_id": 20,
        "category_ids": [20],
        "badge": {"uz_latn": "Yuk tashish", "uz_cyrl": "Юк ташиш", "ru": "Перевозка грузов"},
        "duration_min": 5,
        "title": {
            "uz_latn": "Yuk tashish qoidalari",
            "uz_cyrl": "Юк ташиш қоидалари",
            "ru": "Перевозка грузов"
        },
        "summary": {
            "uz_latn": "Yukning gabariti (o‘lchamlari), bo‘yoqlari, ruxsat etilgan to‘la vazn va yirik gabaritli yuk belgisi.",
            "uz_cyrl": "Юкнинг габарити (ўлчамлари), рухсат этилган вазн ва йирик габаритли юк белгиси.",
            "ru": "Габариты груза, допустимая масса и знак 'Крупногабаритный груз'."
        },
        "key_rules": {
            "uz_latn": [
                "Yukning vazni transport vositasining ruxsat etilgan to‘la vaznidan oshmasligi shart.",
                "Yuk haydovchining ko‘rish maydonini to‘smayotgan, boshqaruvni qiyinlashtirmayotgan va chiroqlar hamda raqam belgilarini yopmayotgan bo‘lishi lozim.",
                "Yuk transport vositasi gabaritidan oldi yoki orqaga 1 metrdan, yon tomonga 0.4 metrdan ortiq chiqib tursa — 'Katta o‘lchamli yuk' belgisi bilan belgilanadi.",
                "Yuk orqadan 2 metrdan ortiq chiqib tursa, tashish maxsus qoidalar bo‘yicha amalga oshiriladi."
            ],
            "uz_cyrl": [
                "Юк вазни рухсат этилган тўла вазндан ошмаслиги шарт.",
                "Юк ҳайдовчининг кўришини тўсмаслиги, давлат рақами ва чироқларни ёпиб қўймаслиги лозим.",
                "Юк олди ёки орқадан 1 метрдан, ён томондан 0.4 метрдан ортиқ чиқиб турса — махсус белги қўйилади.",
                "Орқадан 2 метрдан ортиқ чиқиб туриши тақиқланади (махсус рухсатсиз)."
            ],
            "ru": [
                "Масса перевозимого груза не должна превышать величин, установленных предприятием-изготовителем.",
                "Груз не должен ограничивать обзор, затруднять управление, закрывать световые приборы и номерные знаки.",
                "Груз, выступающий за габариты более чем на 1 м спереди/сзади или более чем на 0.4 м сбоку, обозначается знаком 'Крупногабаритный груз'.",
                "Выступ груза сзади более 2 м требует специального разрешения."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Sonlarni eslab qoling: Oldi va orqadan 1 METR, yon tomondan 0.4 METR (40 sm) dan ortsa belgilanishi shart!",
                "⚠️ Qorong‘i vaqtda chiqib turgan yukka qo‘shimcha oq (oldidan) va qizil (orqasidan) chiroq yoki nur qaytargich o‘rnatiladi."
            ],
            "uz_cyrl": [
                "⚠️ Сонларни эслаб қолинг: Олди/орқадан 1 метр, ён томондан 0.4 метр!",
                "⚠️ Қоронғи вақтда чиқиб турган юкка нур қайтаргич ўрнатилади."
            ],
            "ru": [
                "⚠️ Запомните цифры: спереди и сзади более 1 МЕТРА, сбоку более 0.4 МЕТРА (40 см) — знак обязателен!",
                "⚠️ В темное время суток груз дополнительно обозначается спереди белым, сзади красным фонарем/световозвращателем."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Katta o‘lchamli yuk qachon belgilanadi va orqadan necha metr chiqib turishi mumkin?",
            "uz_cyrl": "Катта ўлчамли юк қачон белгиланади ва орқадан неча метр чиқиб туриши мумкин?",
            "ru": "На сколько метров может выступать груз за габариты автомобиля?"
        }
    },
    {
        "order": 27,
        "category_id": 27,
        "category_ids": [27],
        "badge": {"uz_latn": "Velosiped", "uz_cyrl": "Велосипед", "ru": "Велосипеды и мопеды"},
        "duration_min": 5,
        "title": {
            "uz_latn": "Velosiped, moped va aravalar harakati",
            "uz_cyrl": "Велосипед, мопед ва аравалар ҳаракати",
            "ru": "Движение на велосипедах и мопедах"
        },
        "summary": {
            "uz_latn": "Yosh chegaralari (velosiped 14 yosh, moped 16 yosh), rulni ushlab haydash va chapga burilish cheklovlari.",
            "uz_cyrl": "Ёш чегаралари (велосипед 14 ёш, мопед 16 ёш), рулни ушлаб ҳайдаш ва чапга бурилиш чекловлари.",
            "ru": "Возрастные ограничения (14 и 16 лет), правила поворота налево и безопасность."
        },
        "key_rules": {
            "uz_latn": [
                "Velosipedni yo‘lda boshqarishga — 14 yoshdan, mopedni boshqarishga — 16 yoshdan ruxsat beriladi.",
                "Velosiped va mopedlar yo‘lning faqat o‘ng chekka bo‘lagida bir qatorda harakatlanishi shart.",
                "Rulni ushlamasdan haydash qat'iyan taqiqlanadi.",
                "Tramvay harakati bor yo‘llarda yoki bitta yo‘nalishda 2 va undan ortiq bo‘lagi bor yo‘llarda velosipedchiga chapga burilish yoki qayrilib olish TAQIQLANADI (velosipeddan tushib piyoda o‘tiladi)."
            ],
            "uz_cyrl": [
                "Велосипед — 14 ёшдан, мопед — 16 ёшдан рухсат этилади.",
                "Фақат ўнг чекка қаторда бир қатор бўлиб юрилади.",
                "Рулни ушламасдан ҳайдаш тақиқланади.",
                "Трамвай излари бор ёки 2 ва ундан ортиқ бўлакли йўлларда велосипедда ЧАПГА БУРИЛИШ ТАҚИҚЛАНАДИ (пиёда бўлиб ўтилади)."
            ],
            "ru": [
                "Управлять велосипедом по дорогам разрешается с 14 лет, мопедом — с 16 лет.",
                "Движение разрешается только по правому краю проезжей части в один ряд.",
                "Запрещается управлять велосипедом или мопедом, не держась за руль хотя бы одной рукой.",
                "Запрещается поворачивать налево или разворачиваться на дорогах с трамвайным движением и на дорогах с более чем одной полосой в данном направлении."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Tramvay izi bor yo‘lda velosipedchi chapga burila olmaydi — u velosipeddan tushib, piyodalar o‘tish joyidan yetaklab o‘tishi shart!",
                "⚠️ Velosipedchilar piyodalar o‘tish joyidan velosiped ustida emas, piyoda yetaklab o‘tishlari shart."
            ],
            "uz_cyrl": [
                "⚠️ Велосипедчи пиёдалар ўтиш жойидан велосипедда эмас, пиёда тушиб етаклаб ўтиши керак!",
                "⚠️ Трамвайли кўчада велосипедда чапга бурилиш тақиқланади."
            ],
            "ru": [
                "⚠️ На дороге с трамвайными путями или 2+ полосами велосипедист ДОЛЖЕН слезть с велосипеда и перейти переход пешком!",
                "⚠️ Переезжать пешеходный переход на велосипеде запрещено."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Velosipedchilar qaysi yo‘llarda chapga burila olmaydi va yosh chegaralari qanday?",
            "uz_cyrl": "Велосипедчилар қайси йўлларда чапга бурила олмайди ва ёш чегаралари қандай?",
            "ru": "На каких дорогах велосипедистам запрещен поворот налево и с какого возраста можно ездить?"
        }
    },
    {
        "order": 28,
        "category_id": 37,
        "category_ids": [37],
        "badge": {"uz_latn": "O‘rgatish", "uz_cyrl": "Ўргатиш", "ru": "Учебная езда"},
        "duration_min": 4,
        "title": {
            "uz_latn": "Boshqarishni o‘rgatish qoidalari",
            "uz_cyrl": "Бошқаришни ўргатиш қоидалари",
            "ru": "Учебная езда"
        },
        "summary": {
            "uz_latn": "O‘quv avtomobili talablari, instruktor majburiyatlari va o‘rganuvchining yosh chegaralari.",
            "uz_cyrl": "Ўқув автомобили талаблари, инструктор мажбуриятлари ва ўрганувчининг ёши.",
            "ru": "Требования к учебной езде, возраст обучающегося и оборудованию учебного авто."
        },
        "key_rules": {
            "uz_latn": [
                "Dastlabki haydash mashg‘ulotlari faqat yopiq maydoncha yoki avtodromlarda o‘tkaziladi.",
                "Yo‘llarda o‘quv haydashiga faqat dastlabki ko‘nikmalar o‘zlashtirilgach ruxsat beriladi.",
                "O‘rganuvchining yoshi: Yengil avtomobil uchun — kamida 16 yosh; Mototsikl uchun — kamida 14 yosh bo‘lishi lozim.",
                "O‘quv avtomobili qo‘shimcha tormoz va mufta pedallari, orqani ko‘rish ko‘zgusi hamda 'U' belgisi bilan jihozlangan bo‘lishi shart."
            ],
            "uz_cyrl": [
                "Дастлабки машғулотлар фақат ёпиқ автодромларда ўтказилади.",
                "Автомобиль ўрганувчисининг ёши камида 16 ёш бўлиши лозим.",
                "Ўқув машинасида қўшимча педаллар ва 'У' белгиси бўлиши шарт.",
                "Автомагистралларда ва турар жой даҳаларида ўқув ҳайдаши тақиқланади."
            ],
            "ru": [
                "Первоначальное обучение вождению проводится на закрытых площадках или автодромах.",
                "Обучаемому на автомобиле должно быть не менее 16 лет, на мотоцикле — не менее 14 лет.",
                "Учебный автомобиль должен быть оборудован дублирующими педалями, зеркалом заднего вида и знаком 'У'.",
                "Учебная езда запрещена на автомагистралях и в жилых зонах."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ O‘quv jarayonida YHQ buzilgan taqdirda javobgarlik o‘quvchiga emas, INSTRUKTORGA yuklatiladi!",
                "⚠️ O‘quv haydashi avtomagistrallarda va turar joy dahalarida qat'iyan taqiqlanadi."
            ],
            "uz_cyrl": [
                "⚠️ ЙТҲ ёки қоидабузарлик содир бўлганда жавобгарлик ИНСТРУКТОР зиммасига тушади!",
                "⚠️ Магистралда ўқув ҳайдаши тақиқланган."
            ],
            "ru": [
                "⚠️ Водителем при учебной езде юридически считается ОБУЧАЮЩИЙ (инструктор), и ответственность несет он!",
                "⚠️ Учебная езда запрещена на автомагистралях и в жилых зонах."
            ]
        },
        "ai_prompt": {
            "uz_latn": "O‘quv haydashida qoidabuzarlik uchun kim javobgar va yosh chegaralari qanday?",
            "uz_cyrl": "Ўқув ҳайдашида жавобгарлик кимга тушади ва ёш чегаралари қандай?",
            "ru": "Кто несет ответственность при учебной езде и минимальный возраст ученика?"
        }
    },
    {
        "order": 29,
        "category_id": 3,
        "category_ids": [3],
        "badge": {"uz_latn": "Texnik holat", "uz_cyrl": "Техник ҳолат", "ru": "Техническое состояние"},
        "duration_min": 7,
        "title": {
            "uz_latn": "Transport vositalaridan foydalanishni taqiqlovchi shartlar",
            "uz_cyrl": "Транспорт воситаларидан фойдаланишни тақиқловчи шартлар",
            "ru": "Условия, запрещающие эксплуатацию ТС"
        },
        "summary": {
            "uz_latn": "Tormoz, rul, g‘ildiraklar, protektor qoldiq balandligi (1.6 mm) va harakatlanish mutlaqo taqiqlanadigan 5 ta nosozlik.",
            "uz_cyrl": "Тормоз, руль, ғилдираклар, протектор баландлиги (1.6 мм) ва ҳаракатланиш мутлақо тақиқланган 5 та носозлик.",
            "ru": "Тормозная система, рулевое управление, остаточная глубина протектора (1.6 мм) и 5 критических неисправностей."
        },
        "key_rules": {
            "uz_latn": [
                "Harakatlanish MUTLAQO TAQIQLANADIGAN 5 nosozlik: Ishchi tormoz ishlamasa; Rul boshqaruvi ishlamasa; Tirkama ulagichi nosoz bo‘lsa; Qorong‘i vaqtda faralar yonmasa; Yomg‘ir/qor paytida haydovchi tomonidagi oyna tozalagich (dvornik) ishlamasa.",
                "Rul boshqaruvi lyukti (lyuft): Yengil avtomobillarda 10 gradusdan oshmasligi shart.",
                "Shinalar protektori qoldiq balandligi: Yengil avtomobillarda kamida 1.6 mm bo‘lishi lozim.",
                "Bitta o‘qqa har xil turdagi (radial va diagonal, tikanli va tikansiz) shinalar o‘rnatish taqiqlanadi."
            ],
            "uz_cyrl": [
                "Ҳаракатланиш МУТЛАҚО ТАҚИҚЛАНАДИГАН 5 та ҳолат: Тормоз ишламаса; Руль ишламаса; Тиркама улагичи бузилган бўлса; Қоронғида чироқлар ёнмаса; Ёғингарчиликда дворник ишламаса.",
                "Енгил машиналарда руль люфти кўпи билан 10 градус бўлиши керак.",
                "Енгил машиналар шинаси протектори баландлиги — камида 1.6 мм бўлиши шарт.",
                "Битта ўққа турли хил шиналар қўйиш тақиқланади."
            ],
            "ru": [
                "Запрещено движение ДАЖЕ ДО МЕСТА РЕМОНТА при: неисправности рабочей тормозной системы, рулевого управления, сцепного устройства (в составе поезда), негорящих фарах ночью и недействующем со стороны водителя стеклоочистителе во время осадков.",
                "Суммарный люфт в рулевом управлении легковых авто не должен превышать 10 градусов.",
                "Остаточная высота протектора для легковых авто — не менее 1.6 мм.",
                "Запрещается устанавливать на одну ось шины разных размеров и конструкций."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Qolgan nosozliklar (masalan, glushitel, signal) sodir bo‘lganda ehtiyotkorlik bilan TA'MIRLASH JOYIGA BORISHGA ruxsat beriladi.",
                "⚠️ Yengil avtomobilda majburiy bo‘lishi shart: Aptechka, o‘t o‘chirgich (ognetushitel), avariya to‘xtash belgisi va yorug‘lik qaytaruvchi jilet."
            ],
            "uz_cyrl": [
                "⚠️ Қолган майда носозликларда эҳтиёткорлик билан ТАЪМИРЛАШ ЖОЙИГА бориш мумкин.",
                "⚠️ Автомобилда аптечка, олов ўчиргич ва авария белгиси бўлиши шарт."
            ],
            "ru": [
                "⚠️ При возникновении прочих неисправностей разрешено следовать к месту стоянки или ремонта с соблюдением мер предосторожности.",
                "⚠️ В авто обязательно должны быть: аптечка, огнетушитель, знак аварийной остановки и светоотражающий жилет."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Qaysi 5 ta nosozlikda hatto ustaxonaga ham harakatlanish butunlay taqiqlanadi va protektor me'yori qancha?",
            "uz_cyrl": "Қайси 5 та носозликда ҳатто устахонага ҳам юриш тақиқланади ва протектор нормаси қанча?",
            "ru": "5 неисправностей, при которых запрещено даже ехать до ремонта, и нормы протектора"
        }
    },
    {
        "order": 30,
        "category_id": 10,
        "category_ids": [10],
        "badge": {"uz_latn": "Mansabdorlar", "uz_cyrl": "Мансабдорлар", "ru": "Должностные лица"},
        "duration_min": 4,
        "title": {
            "uz_latn": "Mansabdor shaxslarning majburiyatlari",
            "uz_cyrl": "Мансабдор шахсларнинг мажбуриятлари",
            "ru": "Обязанности должностных лиц"
        },
        "summary": {
            "uz_latn": "Yo‘l holati, nosoz transportni yo‘lga chiqarmaslik, to‘siqlar paydo bo‘lganda xavfsizlik choralari.",
            "uz_cyrl": "Йўл ҳолати, носоз транспортни йўлга чиқармаслик, хавфсизлик чоралари.",
            "ru": "Обязанности должностных лиц по обеспечению безопасности дорожного движения."
        },
        "key_rules": {
            "uz_latn": [
                "Mansabdor shaxslar texnik nosoz transport vositalarini yo‘lga chiqarishga yo‘l qo‘ymasliklari shart.",
                "Yo‘l qoplamasi shikastlanganda darhol ogohlantiruvchi belgilar o‘rnatish va ta'mirlash choralarini ko‘rish lozim.",
                "Yo‘lda to‘siqlar paydo bo‘lganda uni xavfsiz aylanib o‘tishni tashkil qilish shart."
            ],
            "uz_cyrl": [
                "Мансабдор шахслар носоз машиналарни йўлга чиқариши қатъиян тақиқланади.",
                "Йўлдаги хандақ ва тўсиқларга дарҳол белгилар ўрнатиш шарт."
            ],
            "ru": [
                "Должностным лицам запрещается выпускать на линию транспортные средства с техническими неисправностями.",
                "Лица, ответственные за состояние дорог, обязаны своевременно устранять помехи и выставлять знаки."
            ]
        },
        "exam_traps": {
            "uz_latn": ["⚠️ Nosoz mashinani yo‘lga chiqargan mansabdor shaxs qonuniy javobgarlikka tortiladi."],
            "uz_cyrl": ["⚠️ Носоз машинани йўлга чиқарган мансабдор шахс жавобгар бўлади."],
            "ru": ["⚠️ Должностные лица несут административную ответственность за выпуск неисправных ТС."]
        },
        "ai_prompt": {
            "uz_latn": "Yo‘l harakati xavfsizligida mansabdor shaxslarning qanday majburiyatlari bor?",
            "uz_cyrl": "Йўл ҳаракати хавфсизлигида мансабдор шахсларнинг қандай мажбуриятлари бор?",
            "ru": "Какие обязанности несут должностные лица по БДД?"
        }
    },
    {
        "order": 31,
        "category_id": 21,
        "category_ids": [21],
        "badge": {"uz_latn": "Belgilar", "uz_cyrl": "Белгилар", "ru": "Знаки"},
        "duration_min": 7,
        "title": {
            "uz_latn": "Ogohlantiruvchi belgilar (1-guruh)",
            "uz_cyrl": "Огоҳлантирувчи белгилар (1-гуруҳ)",
            "ru": "Предупреждающие знаки (Группа 1)"
        },
        "summary": {
            "uz_latn": "Uchburchak qizil hoshiyali belgilar. O‘rnatilish masofalari: aholi punktida 50-100 metr, tashqarida 150-300 metr.",
            "uz_cyrl": "Учбурчак қизил ҳошияли белгилар. Ўрнатилиш масофалари: шаҳарда 50-100 м, ташқарида 150-300 м.",
            "ru": "Треугольные знаки с красной каймой. Расстояния установки: 50–100 м в городе, 150–300 м вне города."
        },
        "key_rules": {
            "uz_latn": [
                "Ogohlantiruvchi belgilar haydovchiga oldinda xavfli yo‘l qismi boshlanayotgani haqida xabar beradi.",
                "O‘rnatilish masofasi: Aholi punktlarida xavfgacha 50–100 metr; Aholi punktlaridan tashqarida xavfgacha 150–300 metr masofada.",
                "1.1 va 1.2 (shlagbaumli va shlagbaumsiz temir yo‘l), 1.9, 1.10, 1.21 va 1.23 belgilari aholi punktidan tashqarida TAKRORAN o‘rnatiladi (ikkinchisi 50 metrdan kam bo‘lmagan masofada)."
            ],
            "uz_cyrl": [
                "Огоҳлантирувчи белгилар учбурчак бўлиб, хавф ҳақида олдиндан хабар беради.",
                "Ўрнатилиш масофалари: Аҳоли пунктида 50–100 метр қолганда; Аҳоли пунктидан ташқарида 150–300 метр қолганда.",
                "Темир йўл кесишмаси белгилари аҳоли пунктидан ташқарида икки марта (такроран) ўрнатилади."
            ],
            "ru": [
                "Предупреждающие знаки информируют водителей о приближении к опасному участку дороги.",
                "Расстояние установки: в населенных пунктах — за 50–100 м до опасности; вне населенных пунктов — за 150–300 м.",
                "Знаки 1.1, 1.2, 1.9, 1.10, 1.21 и 1.23 вне населенных пунктов устанавливаются повторно (второй раз не менее чем за 50 м)."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Ushbu belgilar hech qanday cheklov qo‘ymaydi, balki tezlikni kamaytirib, diqqatni oshirishni talab qiladi.",
                "⚠️ Sariq fonda bo‘lgan ogohlantiruvchi belgilar VAQTINCHALIK hisoblanadi va doimiylardan ustun turadi."
            ],
            "uz_cyrl": [
                "⚠️ Ушбу белгилар тўхташ ёки бурилишни тақиқламайди, фақат хавфдан огоҳлантиради.",
                "⚠️ Сариқ фонли белгилар вақтинчалик ҳисобланади."
            ],
            "ru": [
                "⚠️ Эти знаки ничего не запрещают, а требуют снизить скорость и повысить внимание.",
                "⚠️ Желтый фон знаков означает, что они являются временными и имеют приоритет перед постоянными."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Ogohlantiruvchi belgilar shahar ichida va tashqarisida necha metr masofada o‘rnatiladi?",
            "uz_cyrl": "Огоҳлантирувчи белгилар шаҳарда ва ташқарида неча метр масофада ўрнатилади?",
            "ru": "Расстояния установки предупреждающих знаков в городе и вне населенного пункта"
        }
    },
    {
        "order": 32,
        "category_id": 17,
        "category_ids": [17],
        "badge": {"uz_latn": "Imtiyoz", "uz_cyrl": "Имтиёз", "ru": "Знаки приоритета"},
        "duration_min": 6,
        "title": {
            "uz_latn": "Imtiyoz belgilari (2-guruh)",
            "uz_cyrl": "Имтиёз белгилари (2-гуруҳ)",
            "ru": "Знаки приоритета (Группа 2)"
        },
        "summary": {
            "uz_latn": "2.1 Asosiy yo‘l, 2.4 Yo‘l bering, 2.5 To‘xtamasdan harakatlanish taqiqlangan (STOP) va tor joylarda imtiyoz.",
            "uz_cyrl": "2.1 Асосий йўл, 2.4 Йўл беринг, 2.5 СТОП ва тор жойларда имтиёз белгилари.",
            "ru": "2.1 Главная дорога, 2.4 Уступите дорогу, 2.5 Движение без остановки запрещено (STOP)."
        },
        "key_rules": {
            "uz_latn": [
                "2.1 'Asosiy yo‘l' — tartibga solinmagan chorrahada birinchi bo‘lib o‘tish huquqini beradi.",
                "2.4 'Yo‘l bering' — kesishayotgan yo‘ldagi mashinalarga yo‘l berish shart, lekin to‘siq bo‘lmasa to‘xtash majburiy emas.",
                "2.5 'To‘xtamasdan harakatlanish taqiqlangan' (STOP) — to‘xtash chizig‘i (yoki belgi) oldida BIR LAHZA BO‘LSA HAM TO‘LIQ TO‘XTASH SHART!",
                "2.6 'Qarama-qarshi harakatlanishning ustunligi' (qizil doira) va 2.7 'Qarama-qarshi harakatlanishga nisbatan imtiyoz' (ko‘k to‘rtburchak) tor yo‘llarda qo‘llaniladi."
            ],
            "uz_cyrl": [
                "2.1 'Асосий йўл' — чорраҳадан биринчи ўтиш ҳуқуқини беради.",
                "2.4 'Йўл беринг' — йўл берилади, аммо йўл бўш бўлса тўхташ шарт эмас.",
                "2.5 'STOP' — ҳатто йўлда ҳеч ким бўлмаса ҳам ТЎХТАШ ШАРТ!",
                "2.6 (қизил доира) — қаршидагига йўл берилади; 2.7 (кўк квадрат) — сиз биринчи ўтасиз."
            ],
            "ru": [
                "Знак 2.1 'Главная дорога' предоставляет право преимущественного проезда нерегулируемых перекрестков.",
                "Знак 2.4 'Уступите дорогу' требует уступить дорогу ТС на пересекаемой дороге (полная остановка не обязательна).",
                "Знак 2.5 'Движение без остановки запрещено' (STOP) ТРЕБУЕТ ОБЯЗАТЕЛЬНОЙ ПОЛНОЙ ОСТАНОВКИ даже при отсутствии других ТС!",
                "Знак 2.6 (круглый с красной стрелкой) обязывает уступить; знак 2.7 (синий квадрат) дает приоритет."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ 2.4 belgisi oldida agar boshqa mashina bo‘lmasa TO‘XTAMASDAN o‘tish mumkin, ammo 2.5 (STOP) belgisi oldida albatta to‘liq to‘xtash shart!",
                "⚠️ Svetofor ishlayotgan chorrahada 2.1, 2.4 va 2.5 belgilari bekor qilinadi."
            ],
            "uz_cyrl": [
                "⚠️ 2.4 да тўхтамасдан ўтиш мумкин, 2.5 (STOP) да тўхташ мажбурий!",
                "⚠️ Светофор ишлаётганда ушбу белгиларга қаралмайди."
            ],
            "ru": [
                "⚠️ Знак 2.4 не требует обязательной остановки, а знак 2.5 ТРЕБУЕТ всегда!",
                "⚠️ При работающем светофоре знаки 2.1, 2.4, 2.5 не действуют."
            ]
        },
        "ai_prompt": {
            "uz_latn": "2.4 'Yo‘l bering' va 2.5 'STOP' belgilarining farqi nimada va qachon to‘xtash shart?",
            "uz_cyrl": "2.4 'Йўл беринг' ва 2.5 'STOP' белгиларининг фарқи нимада?",
            "ru": "В чем главное отличие знаков 2.4 'Уступите дорогу' и 2.5 'STOP'?"
        }
    },
    {
        "order": 33,
        "category_id": 23,
        "category_ids": [23],
        "badge": {"uz_latn": "Taqiqlovchi", "uz_cyrl": "Тақиқловчи", "ru": "Запрещающие знаки"},
        "duration_min": 8,
        "title": {
            "uz_latn": "Taqiqlovchi belgilar (3-guruh)",
            "uz_cyrl": "Тақиқловчи белгилар (3-гуруҳ)",
            "ru": "Запрещающие знаки (Группа 3)"
        },
        "summary": {
            "uz_latn": "Dumaloq qizil hoshiyali belgilar. Kirish taqiqlangan ('g‘isht'), harakatlanish taqiqlangan, to‘xtash va to‘xtab turish taqiqlangan.",
            "uz_cyrl": "Думалоқ қизил ҳошияли белгилар. 3.1 'Кириш тақиқланган', тўхташ ва тўхтаб туриш тақиқланган белгилари.",
            "ru": "Круглые знаки с красной каймой. 3.1 'Въезд запрещен' ('кирпич'), ограничения и исключения."
        },
        "key_rules": {
            "uz_latn": [
                "3.1 'Kirish taqiqlangan' (G‘isht) — barcha transport vositalarining kirishini taqiqlaydi (yo‘nalishli transportdan tashqari).",
                "3.2 'Harakatlanish taqiqlangan' (oq doira) — shu hududda yashovchi, ishlovchi va xizmat ko‘rsatuvchi transportlarga taalluqli emas.",
                "3.27 'To‘xtash taqiqlangan' (qizil X xoch) — to‘xtashni ham, to‘xtab turishni ham taqiqlaydi.",
                "3.28 'To‘xtab turish taqiqlangan' (bitta qizil chiziq) — to‘xtab turish taqiqlanadi, ammo 5 daqiqagacha odam mindirish/tushirish uchun to‘xtash mumkin."
            ],
            "uz_cyrl": [
                "3.1 'Кириш тақиқланган' (Ғишт) — йўналишли маршруткалардан ташқари ҳаммага тақиқланади.",
                "3.2 'Ҳаракатланиш тақиқланган' — шу ерда яшовчи ва ишлайдиганларга таъсир қилмайди.",
                "3.27 'Тўхташ тақиқланган' (Х ҳошия) — умуман тўхташ мумкин эмас.",
                "3.28 'Тўхтаб туриш тақиқланган' — 5 дақиқагача одам чиқариш/тушириш учун тўхташ мумкин."
            ],
            "ru": [
                "3.1 'Въезд запрещен' ('кирпич') запрещает въезд всех ТС (кроме маршрутных).",
                "3.2 'Движение запрещено' не распространяется на ТС граждан, проживающих или работающих в этой зоне.",
                "3.27 'Остановка запрещена' (крест) запрещает и остановку, и стоянку.",
                "3.28 'Стоянка запрещена' разрешает посадку/высадку пассажиров (остановку до 5 минут)."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ 3.27 va 3.28 belgilari faqat yo‘lning O‘ZI O‘RNATILGAN TOMONIGA amal qiladi!",
                "⚠️ Ushbu belgilarning ta'sir doirasi eng yaqin chorrahagacha, chorraha bo‘lmaganda aholi punkti oxirigacha davom etadi."
            ],
            "uz_cyrl": [
                "⚠️ Тўхташ ва тўхтаб туриш белгилари йўлнинг ҚАЙСИ ТОМОНИГА ўрнатилган бўлса, фақат ўша томонга амал қилади!",
                "⚠️ Белги таъсири энг яқин чорраҳагача давом этади."
            ],
            "ru": [
                "⚠️ Знаки 3.27 и 3.28 действуют ТОЛЬКО на ту сторону дороги, на которой они установлены!",
                "⚠️ Зона действия запрещающих знаков распространяется до ближайшего перекрестка или конца населенного пункта."
            ]
        },
        "ai_prompt": {
            "uz_latn": "3.27 'To‘xtash taqiqlangan' va 3.28 'To‘xtab turish taqiqlangan' belgilarining farqi va istisnolari",
            "uz_cyrl": "3.27 ва 3.28 белгиларининг фарқи ва кимларга амал қилмаслиги",
            "ru": "Различия знаков 3.27 и 3.28 и исключения для инвалидов и маршрутных ТС"
        }
    },
    {
        "order": 34,
        "category_id": 2,
        "category_ids": [2],
        "badge": {"uz_latn": "Buyuruvchi", "uz_cyrl": "Буюрувчи", "ru": "Предписывающие знаки"},
        "duration_min": 6,
        "title": {
            "uz_latn": "Buyuruvchi belgilar (4-guruh)",
            "uz_cyrl": "Буюрувчи белгилар (4-гуруҳ)",
            "ru": "Предписывающие знаки (Группа 4)"
        },
        "summary": {
            "uz_latn": "Dumaloq ko‘k fondagi belgilar. 4.1.1-4.1.6 harakat yo‘nalishlari, aylanma harakat va eng kam tezlik chegarasi.",
            "uz_cyrl": "Думалоқ кўк фонли белгилар. 4.1.1-4.1.6 ҳаракат йўналишлари, айланма ҳаракат ва энг кам тезлик.",
            "ru": "Круглые знаки на синем фоне. Обязательные направления движения, круговое движение и минимальная скорость."
        },
        "key_rules": {
            "uz_latn": [
                "Buyuruvchi belgilar faqat ularda ko‘rsatilgan yo‘nalishlardagina harakatlanishni buyuradi.",
                "Chapga burilishga ruxsat beruvchi har qanday buyuruvchi belgi QAYRILIB OLISHGA HAM ruxsat beradi.",
                "4.1.1 'Harakatlanish to‘g‘riga' belgisi chorraha oldiga o‘rnatilsa — faqat shu chorrahaning birinchi qatnov qismiga amal qiladi.",
                "4.1.1 yo‘l qismining boshiga o‘rnatilsa — eng yaqin chorrahagacha amal qiladi va o‘ngdagi hovlilarga kirishga ruxsat beradi (chapga esa taqiqlaydi)."
            ],
            "uz_cyrl": [
                "Буюрувчи белгилар фақат белгиланган йўналишда юришни талаб қилади.",
                "Чапга бурилишга рухсат берувчи белги ҚАЙРИЛИБ ОЛИШГА ҲАМ рухсат беради.",
                "4.1.1 'Тўғрига ҳаракат' йўл бошида турса — энг яқин чорраҳагача амал қилади ва ўнгга (ҳовлига) киришга рухсат беради."
            ],
            "ru": [
                "Предписывающие знаки разрешают движение только в указанных направлениях.",
                "Знаки, разрешающие поворот налево, РАЗРЕШАЮТ И РАЗВОРОТ.",
                "Знак 4.1.1 'Движение прямо', установленный в начале участка дороги, действует до ближайшего перекрестка и разрешает поворот направо во дворы."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ 4.1.1 'To‘g‘riga' belgisi yo‘l boshida turganda o‘ng tomondagi hovlilarga burilish MUMKIN, ammo chap tomondagi hovliga kirish TAQIQLANADI!",
                "⚠️ Ushbu belgilar yo‘nalishli transport vositalariga (avtobuslarga) taalluqli emas."
            ],
            "uz_cyrl": [
                "⚠️ 4.1.1 белгиси турганда ўнгга ҳовлига кириш мумкин, чапга ҳовлига кириш тақиқланади!",
                "⚠️ Маршрутли автобусларга бу белгилар таъсир қилмайди."
            ],
            "ru": [
                "⚠️ Знак 4.1.1 вне перекрестка РАЗРЕШАЕТ поворот направо во дворы, но ЗАПРЕЩАЕТ поворот налево во дворы и разворот!",
                "⚠️ Действие знаков 4.1.1–4.1.6 не распространяется на маршрутные ТС."
            ]
        },
        "ai_prompt": {
            "uz_latn": "4.1.1 'Harakatlanish to‘g‘riga' belgisi qachon hovliga kirishga ruxsat beradi?",
            "uz_cyrl": "4.1.1 'Тўғрига ҳаракат' белгиси қачон ҳовлига киришга рухсат беради?",
            "ru": "Когда знак 4.1.1 разрешает поворот во двор и куда?"
        }
    },
    {
        "order": 35,
        "category_id": 18,
        "category_ids": [18],
        "badge": {"uz_latn": "Axborot", "uz_cyrl": "Ахборот", "ru": "Информационные знаки"},
        "duration_min": 6,
        "title": {
            "uz_latn": "Axborot-ko‘rsatkich belgilari (5-guruh)",
            "uz_cyrl": "Ахборот-кўрсаткич белгилари (5-гуруҳ)",
            "ru": "Информационно-указательные знаки (Группа 5)"
        },
        "summary": {
            "uz_latn": "5.5 Bir tomonlama harakat, 5.8.1 Bo‘laklar bo‘yicha harakat yo‘nalishi, 5.15 To‘xtab turish joyi, 5.33 To‘xtash chizig‘i (STOP).",
            "uz_cyrl": "5.5 Бир томонлама ҳаракат, 5.8.1 Бўлаклар бўйича йўналиш, 5.15 Тўхтаб туриш joyi, 5.33 СТОП-чизиқ.",
            "ru": "5.5 Одностороннее движение, 5.8.1 Направления движения по полосам, парковка и стоп-линия."
        },
        "key_rules": {
            "uz_latn": [
                "5.8.1 va 5.8.2 'Bo‘laklar bo‘yicha harakatlanish yo‘nalishlari' — har bir qatordan qayerga burilish mumkinligini belgilaydi.",
                "Chap chekka bo‘lakdan chapga burilishga ruxsat beruvchi belgi QAYRILIB OLISHGA HAM ruxsat beradi.",
                "5.5 'Bir tomonlama harakatli yo‘l' — butun kenglik bo‘ylab bir tomonga yurish. Bu yo‘lda chap tomonda ham to‘xtashga ruxsat etiladi.",
                "5.33 'To‘xtash chizig‘i' (STOP) — taqiqlovchi ishorada to‘xtash joyini belgilaydi."
            ],
            "uz_cyrl": [
                "5.8.1 бўлаклар бўйича йўналишни белгилайди.",
                "Чап чекка бўлакдан чапга бурилишга рухсат берувчи белги қайрилишга ҳам рухсат беради.",
                "Бир томонлама йўлда чап томонда ҳам тўхташ мумкин."
            ],
            "ru": [
                "Знаки 5.8.1 и 5.8.2 указывают разрешенные направления движения по полосам.",
                "Знак, разрешающий поворот налево из крайней левой полосы, РАЗРЕШАЕТ И РАЗВОРОТ.",
                "На дорогах с односторонним движением остановка и стоянка легковых ТС разрешена и на левой стороне.",
                "Знак 5.33 'СТОП' указывает место остановки при запрещающем сигнале светофора."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Agar chapga burilishga ruxsat ikkinchi (o‘rta) bo‘lakdan berilgan bo‘lsa, u yerdan FAQAT CHAPGA burilish mumkin — o‘rta qatordan qayrilib olish TAQIQLANADI!",
                "⚠️ Qayrilib olish faqat chap chekka bo‘lakdan ruxsat etiladi."
            ],
            "uz_cyrl": [
                "⚠️ Агар чапга бурилишга ўрта бўлакдан рухсат берилган бўлса, у ердан ҚАЙРИЛИШ МУМКИН ЭМАС! Қайрилиш фақат чекка чап бўлакдан мумкин.",
                "⚠️ 5.33 оқ тўртбурчак СТОП белгиси фақат чизиқ ўрнида ишлайди, қизил доира 2.5 билан адаштирманг."
            ],
            "ru": [
                "⚠️ Если поворот налево разрешен со второй полосы, разворот с нее ЗАПРЕЩЕН! Разворот разрешен ТОЛЬКО из крайней левой полосы.",
                "⚠️ Не путайте белый прямоугольный знак 5.33 'СТОП' со знаком приоритета 2.5."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Bo‘laklar bo‘yicha harakatlanish belgisida o‘rta qatordan qayrilib olish mumkinmi?",
            "uz_cyrl": "Бўлаклар бўйича ҳаракат белгисида ўрта қатордан қайрилиш мумкинми?",
            "ru": "Можно ли разворачиваться со второй полосы, если с нее разрешен поворот налево?"
        }
    },
    {
        "order": 36,
        "category_id": 1,
        "category_ids": [1],
        "badge": {"uz_latn": "Tablichkalar", "uz_cyrl": "Табличкалар", "ru": "Таблички"},
        "duration_min": 6,
        "title": {
            "uz_latn": "Qo‘shimcha axborot belgilari (7-guruh tablichkalar)",
            "uz_cyrl": "Қўшимча ахборот белгилари (7-гуруҳ табличкалар)",
            "ru": "Знаки дополнительной информации (Группа 7)"
        },
        "summary": {
            "uz_latn": "7.1.1 Obyektgacha masofa, 7.2.1 Ta'sir oralig‘i (strelkali), 7.6.1-7.6.9 Mashinani to‘xtash joyiga qo‘yish usullari.",
            "uz_cyrl": "7.1.1 Масофа, 7.2.1 Таъсир оралиғи (стрелкали), 7.6.1-7.6.9 Машинани қўйиш усуллари.",
            "ru": "7.1.1 Расстояние до объекта, 7.2.1 Зона действия (со стрелками), 7.6.1–7.6.9 Способ постановки ТС на стоянку."
        },
        "key_rules": {
            "uz_latn": [
                "7.1.1 (masalan '300 m') — belgidan to xavfgacha yoki cheklov boshlanishigacha bo‘lgan masofani bildiradi.",
                "7.2.1 (yonida strelkalar bo‘lgan '↑ 300 m ↑') — belgining qancha masofaga TA'SIR QILISHINI (uzunligini) bildiradi.",
                "7.6.1 'Avtomobilni to‘xtash joyiga qo‘yish usuli' (trotuar chetida parallel) — barcha transport vositalariga taalluqli.",
                "7.6.2–7.6.9 (trotuarga chiqarib yoki ko‘ndalang qo‘yish) — FAQAT YENGIL AVTOMOBIL VA MOTOTSIKLLARGA ruxsat beradi (yuk mashinalariga taqiqlanadi)."
            ],
            "uz_cyrl": [
                "7.1.1 (стрелкасиз '300 м') — объектгача бўлган масофа.",
                "7.2.1 (стрелкали '↑ 300 м ↑') — белги таъсир қиладиган масофа узунлиги.",
                "7.6.2–7.6.9 тротуар устига чиқариб қўйиш табличкалари ФАҚАТ ЕНГИЛ МАШИНА ВА МОТОЦИКЛЛАРГА тегишли!"
            ],
            "ru": [
                "Табличка без стрелок ('300 м') указывает расстояние ОТ знака ДО начала опасного участка.",
                "Табличка со стрелками ('↑ 300 м ↑') указывает ПРОТЯЖЕННОСТЬ зоны действия знака.",
                "Способ 7.6.1 (параллельно у края) распространяется на все ТС.",
                "Способы 7.6.2–7.6.9 (с заездом на тротуар) разрешены ТОЛЬКО легковым автомобилям и мотоциклам!"
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Trotuarga chiqarib to‘xtash usullari (7.6.2–7.6.9) hatto kichik yuk avtomobillariga (Gazel, Labo) ham QAT'IYAN TAQIQLANADI!",
                "⚠️ Strelkali tablichka (7.2.1) bilan strelkasiz masofa tablichkasi (7.1.1) ni aslo adashtirmang."
            ],
            "uz_cyrl": [
                "⚠️ Тротуар четига чиқариб қўйиш ҳатто энг кичик юк машиналарига ҳам мутлақо мумкин эмас!",
                "⚠️ Стрелкали (таъсир оралиғи) ва стрелкасиз (масофа) табличкаларини адаштирманг."
            ],
            "ru": [
                "⚠️ Таблички с заездом на тротуар ЗАПРЕЩАЮТ стоянку любым грузовым автомобилям (даже до 3.5 т, Газель/Лабо)!",
                "⚠️ Табличка со стрелками указывает длину зоны действия, без стрелок — расстояние до объекта."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Trotuarga chiqarib to‘xtash tablichkalari qaysi mashinalarga ruxsat beradi va yuk mashinalariga mumkinmi?",
            "uz_cyrl": "Тротуар четига қўйиш табличкалари юк машиналарига мумкинми?",
            "ru": "Кому разрешают стоянку таблички со способом постановки ТС на тротуаре?"
        }
    },
    {
        "order": 37,
        "category_id": 12,
        "category_ids": [12],
        "badge": {"uz_latn": "Yotiq chiziqlar", "uz_cyrl": "Ётиқ чизиқлар", "ru": "Горизонтальная разметка"},
        "duration_min": 7,
        "title": {
            "uz_latn": "Yotiq chiziqlar (1-ilova)",
            "uz_cyrl": "Ётиқ чизиқлар (1-илова)",
            "ru": "Горизонтальная разметка"
        },
        "summary": {
            "uz_latn": "1.1 yaxlit chiziq, 1.3 qo‘shaloq yaxlit chiziq, 1.11 bir tomonlama uzuq chiziq, sariq chiziqlar va 'zebra'.",
            "uz_cyrl": "1.1 яхлит чизиқ, 1.3 қўшалоқ яхлит чизиқ, 1.11 бир томонлама узуқ чизиқ, сариқ чизиқлар.",
            "ru": "1.1 сплошная линия, 1.3 двойная сплошная, 1.11 прерывистая с одной стороны и желтая разметка."
        },
        "key_rules": {
            "uz_latn": [
                "1.1 (yakka yaxlit chiziq) va 1.3 (qo‘shaloq yaxlit chiziq) — bosib o‘tish va kesib o‘tish qat'iyan taqiqlanadi.",
                "1.11 (bir tomoni yaxlit, bir tomoni uzuq-uzuq) — faqat UZUQ-UZUQ CHIZIQ TOMONIDAN kesib o‘tishga ruxsat beriladi.",
                "Sariq yaxlit chiziq (1.4) trotuar chetida — to‘xtash taqiqlanganligini bildiradi.",
                "Sariq uzuq-uzuq chiziq (1.10) — to‘xtab turish taqiqlanganligini bildiradi."
            ],
            "uz_cyrl": [
                "1.1 ва 1.3 яхлит чизиқларни босиб ўтиш қатъиян тақиқланади.",
                "1.11 чизиғи фақат узуқ-узуқ томонидан кесиб ўтилиши мумкин.",
                "Сариқ яхлит чизиқ — тўхташ тақиқланган жой.",
                "Сариқ узуқ-узуқ чизиқ — тўхтаб туриш тақиқланган жой."
            ],
            "ru": [
                "Линии 1.1 (сплошная) и 1.3 (двойная сплошная) пересекать категорически запрещается.",
                "Линию 1.11 разрешается пересекать со стороны прерывистой линии.",
                "Желтая сплошная линия 1.4 запрещает остановку.",
                "Желтая прерывистая линия 1.10 запрещает стоянку."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Yo‘l belgisi va yotiq chiziq talabi bir-biriga zid kelsa — HAYDOVCHI YO‘L BELGISIGA amal qilishi shart!",
                "⚠️ Vaqtinchalik sariq chiziq doimiy oq chiziqlardan ustun turadi."
            ],
            "uz_cyrl": [
                "⚠️ Йўл белгиси ва чизиқ бир-бирига зид бўлса — ЙЎЛ БЕЛГИСИ УСТУН ТУРАДИ!",
                "⚠️ Сариқ яхлит чизиқ бўйлаб тўхташ мумкин эмас."
            ],
            "ru": [
                "⚠️ В случаях, когда значения дорожных знаков и линий разметки противоречат друг другу, водители должны руководствоваться ЗНАКАМИ!",
                "⚠️ Оранжевая (временная) разметка имеет приоритет перед постоянной белой."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Yo‘l belgisi va chiziqlar ziddiyatida qaysi biri ustun turadi va 1.11 chiziq qoidasi qanday?",
            "uz_cyrl": "Йўл белгиси ва чизиқ зид бўлса қайси бири устун ва 1.11 чизиғи қоидаси қандай?",
            "ru": "Что главнее: знак или разметка, и как пересекать линию 1.11?"
        }
    },
    {
        "order": 38,
        "category_id": 42,
        "category_ids": [42],
        "badge": {"uz_latn": "Tik chiziqlar", "uz_cyrl": "Тик чизиқлар", "ru": "Вертикальная разметка"},
        "duration_min": 4,
        "title": {
            "uz_latn": "Tik chiziqlar (2-ilova)",
            "uz_cyrl": "Тик чизиқлар (2-илова)",
            "ru": "Вертикальная разметка"
        },
        "summary": {
            "uz_latn": "Ko‘priklar, to‘siqlar, bordyurlar va xavfli inshootlardagi oq-qora chiziqlar.",
            "uz_cyrl": "Кўприклар, тўсиқлар, бордюрлар ва хавфли иншоотлардаги оқ-қора чизиқлар.",
            "ru": "Черно-белая разметка на опорах мостов, отбойниках и бордюрах."
        },
        "key_rules": {
            "uz_latn": [
                "Tik chiziqlar yo‘l inshootlari, ko‘prik ustunlari, to‘siqlar va xavfli joylarning gabaritlarini ko‘rsatish uchun xizmat qiladi.",
                "2.1.1–2.1.3 — ko‘prik va osma yo‘llarning harakatlanayotgan transportga xavf tug‘diruvchi elementlarini belgilaydi.",
                "2.5 — xavfli burilishlardagi to‘siqlarning yon sirtini belgilaydi.",
                "2.7 — xavfli joylardagi bort toshlarini (bordyurlarni) belgilaydi."
            ],
            "uz_cyrl": [
                "Тик чизиқлар йўл иншоотлари ва хавфли кўприк устунларини белгилайди.",
                "Оқ-қора чизиқлар хавфли элементларни билдиради."
            ],
            "ru": [
                "Вертикальная разметка обозначает элементы дорожных сооружений, представляющие опасность.",
                "Разметка 2.1 наносится на опоры мостов и путепроводов.",
                "Разметка 2.5 наносится на боковые поверхности дорожных ограждений на опасных участках."
            ]
        },
        "exam_traps": {
            "uz_latn": ["⚠️ Tik chiziqlar transport vositalarining harakat yo‘nalishini emas, inshootlarning o‘lcham va xavflilik darajasini ko‘rsatadi."],
            "uz_cyrl": ["⚠️ Тик чизиқлар йўналишни эмас, иншоот хавфини кўрсатади."],
            "ru": ["⚠️ Вертикальная разметка не указывает траекторию движения, а маркирует габариты сооружений."]
        },
        "ai_prompt": {
            "uz_latn": "Tik chiziqlar qayerlarga chiziladi va nima maqsadda qo‘llaniladi?",
            "uz_cyrl": "Тик чизиқлар қаерларга чизилади ва мақсади нима?",
            "ru": "Где применяется вертикальная разметка и что она обозначает?"
        }
    },
    {
        "order": 39,
        "category_id": 15,
        "category_ids": [15],
        "badge": {"uz_latn": "Xavfsizlik", "uz_cyrl": "Хавфсизлик", "ru": "Безопасность"},
        "duration_min": 7,
        "title": {
            "uz_latn": "Harakat xavfsizligi asoslari",
            "uz_cyrl": "Ҳаракат хавфсизлиги асослари",
            "ru": "Основы безопасности движения"
        },
        "summary": {
            "uz_latn": "Tormoz yo‘li, to‘xtash yo‘li, sirpanish (akvaplanning), sirpanchiq yo‘lda sirpanishdan chiqish va xavfsiz masofa.",
            "uz_cyrl": "Тормоз йўли, тўхташ йўли, аквапланирлаш, сирпанчиқ йўлда хавфсизлик ва масофа.",
            "ru": "Тормозной и остановочный путь, занос, аквапланирование и безопасная дистанция."
        },
        "key_rules": {
            "uz_latn": [
                "To‘xtash yo‘li = Haydovchining reaksiya vaqtidagi masofa + Tormozlanish yo‘li.",
                "Tezlik 2 baravar oshganda — tormoz yo‘li 4 BARAVAR ortadi (kvadratik bog‘liqlik!).",
                "Oldi yetakchi (peredneprivod) mashinada sirpanish boshlansa — gaz pedali biroz BOSILADI.",
                "Orqa yetakchi (zadneprivod) mashinada sirpanish boshlansa — gaz pedali darhol BO‘SHATILADI.",
                "Har qanday mashinada rul sirpanish tomoniga buriladi, tormoz qat'iyan BOSILMAYDI."
            ],
            "uz_cyrl": [
                "Тўхташ йўли = Ҳайдовчи реакцияси масофаси + Тормоз йўли.",
                "Тезлик 2 марта ошса — тормоз йўли 4 МАРТА ортади!",
                "Олд тортувчи (передний привод) машина сирпанса — газ бироз БОСИЛАДИ.",
                "Орқа тортувчи (задний привод) машина сирпанса — газ ДАРҲОЛ БЎШАТИЛАДИ.",
                "Руль сирпаниш йўналиши томонга бурилади, кескин тормоз БОСИЛМАЙДИ."
            ],
            "ru": [
                "Остановочный путь = путь за время реакции водителя + тормозной путь.",
                "При увеличении скорости в 2 раза тормозной путь увеличивается в 4 РАЗА!",
                "При заносе переднеприводного авто — плавно ДОБАВИТЬ газ.",
                "При заносе заднеприводного авто — плавно СБРОСИТЬ газ.",
                "В обоих случаях руль поворачивается в сторону заноса, резко тормозить ЗАПРЕЩЕНО."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Sirpanish vaqtida keskin tormoz bosish mashinani to‘liq boshqaruvsiz qilib, ag‘darilishiga olib keladi!",
                "⚠️ Akvaplanning (suv ustida sirpanish) sodir bo‘lganda rulni burmasdan, gazni sekin bo‘shatish kerak."
            ],
            "uz_cyrl": [
                "⚠️ Сирпанишда кескин тормоз босиш қатъиян тақиқланади!",
                "⚠️ Сув кўлмагидан ўтаётганда рулни бурмасдан тезлик камайтирилади."
            ],
            "ru": [
                "⚠️ Торможение при заносе только усугубляет занос! Тормоз нажимать категорически нельзя.",
                "⚠️ При аквапланировании нельзя резко тормозить и крутить руль — только плавный сброс газа."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Oldi va orqa yetakchi mashinalarda sirpanish (zanos) paytida gaz va rul bilan qanday to‘g‘ri harakat qilinadi?",
            "uz_cyrl": "Олд ва орқа приводли машиналарда занос бўлганда газ ва руль билан нима қилиш керак?",
            "ru": "Как правильно выходить из заноса на переднем и заднем приводе?"
        }
    },
    {
        "order": 40,
        "category_id": 9,
        "category_ids": [9],
        "badge": {"uz_latn": "Tibbiyot", "uz_cyrl": "Тиббиёт", "ru": "Первая помощь"},
        "duration_min": 6,
        "title": {
            "uz_latn": "Birinchi tibbiy yordam ko‘rsatish",
            "uz_cyrl": "Биринчи тиббий ёрдам кўрсатиш",
            "ru": "Первая медицинская помощь при ДТП"
        },
        "summary": {
            "uz_latn": "Qon ketishini to‘xtatish (jgut qo‘yish), yurak-o‘pka reanimatsiyasi (30:2), suyak sinishida shina qo‘yish va hushsiz bemor holati.",
            "uz_cyrl": "Қон кетишини тўхтатиш (жгут), сунъий нафас ва юрак массажи (30:2), синишда шина ва ҳушсиз бемор.",
            "ru": "Остановка кровотечений (жгут), сердечно-легочная реанимация (30:2) и шинирование."
        },
        "key_rules": {
            "uz_latn": [
                "Arterial qon ketishi (och qizil favvora) — jgut jarohatdan YUQORIGA qo‘yiladi. Yozda ko‘pi bilan 1 soat, qishda 30 daqiqa (vaqt yozilgan qog‘oz qistirib qo‘yiladi).",
                "Yurak-o‘pka reanimatsiyasi: 30 marta ko‘krak qafasini bosish va 2 marta sun'iy nafas berish (30:2 proporsiyasi).",
                "Singan suyaklarga shina qo‘yganda kamida IKKITA qo‘shni bo‘g‘im harakatsizlantirilishi shart.",
                "Hushsiz, lekin nafas olayotgan jabrlanuvchini yonbosh holatiga yotqizish shart (til orqaga ketib bo‘g‘ilmasligi uchun)."
            ],
            "uz_cyrl": [
                "Артериал қон кетишида (фавворасимон) — жгут жароҳатдан ЮҚОРИГА қўйилади. Ёзда 1 соат, қишда 30 дақиқа.",
                "Юракни массаж қилиш ва нафас бериш нисбати — 30:2.",
                "Суяк синганда шина камида ИККИТА бўғимни қамраб олиши шарт.",
                "Ҳушсиз бемор ёнбош ҳолатга ётқизилади (тили нафас йўлини ёпиб қўймаслиги учун)."
            ],
            "ru": [
                "Артериальное кровотечение (алая пульсирующая струя) — жгут накладывается ВЫШЕ раны на 1 час летом и 30 мин зимой с запиской о времени.",
                "Сердечно-легочная реанимация проводится в соотношении 30 компрессий грудной клетки к 2 вдохам (30:2).",
                "При переломах шина должна обязательно обездвиживать не менее ДВУХ смежных суставов.",
                "Пострадавшего без сознания с наличием дыхания укладывают в устойчивое боковое положение."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ Ochiq sinishda suyak parchalarini ichkariga tiqish yoki to‘g‘rilash QAT'IYAN TAQIQLANADI!",
                "⚠️ Qorin bo‘shlig‘i jarohatlangan bemorga suv yoki dori ichirish taqiqlanadi."
            ],
            "uz_cyrl": [
                "⚠️ Очиқ синишда суякларни жойига солиш ёки босиш қатъиян ман этилади!",
                "⚠️ Қорнидан жароҳатланган одамга сув ичириш тақиқланади."
            ],
            "ru": [
                "⚠️ При открытых переломах вправлять костные обломки категорически запрещается!",
                "⚠️ Пострадавшим с травмой живота запрещено давать воду и пищу."
            ]
        },
        "ai_prompt": {
            "uz_latn": "YHQ imtihonidagi tibbiy savollar: jgut qo‘yish vaqti va yurak reanimatsiyasi proporsiyasini tushuntirib ber",
            "uz_cyrl": "ЙҲҚ имтиҳонидаги тиббий саволлар: жгут қўйиш вақти ва 30:2 қоидасини тушунтириб бер",
            "ru": "Правила наложения жгута по времени и пропорция сердечно-легочной реанимации 30:2"
        }
    },
    {
        "order": 41,
        "category_id": 24,
        "category_ids": [24],
        "badge": {"uz_latn": "Yakuniy test", "uz_cyrl": "Якуний тест", "ru": "Общие вопросы"},
        "duration_min": 6,
        "title": {
            "uz_latn": "Umumiy va aralash test savollari",
            "uz_cyrl": "Умумий ва аралаш тест саволлари",
            "ru": "Общие и комплексные экзаменационные вопросы"
        },
        "summary": {
            "uz_latn": "Barcha boblar bo‘yicha eng xarakterli, chigal va bir necha qoidalar kesishuvidan tashkil topgan murakkab savollar.",
            "uz_cyrl": "Барча боблар бўйича энг мураккаб, чигал ва бир нечта қоидалар кесишувидан иборат саволлар тўплами.",
            "ru": "Комплексные и смешанные вопросы по всем разделам ПДД."
        },
        "key_rules": {
            "uz_latn": [
                "Savolni oxirigacha sinchiklab o‘qing: savolda 'ruxsat etiladi' so‘ralyaptimi yoki 'taqiqlanadi'mi — diqqat qiling.",
                "Rasmdagi barcha belgilarni, svetofor chiroqlarini, yo‘l qoplamasini va avtomobillarning burilish chiroqlarini bir vaqtda tahlil qiling.",
                "Birinchi navbatda tartibga soluvchi, so‘ng svetofor, so‘ng imtiyoz belgilari, eng oxirida 'o‘ngdan xalaqit' qoidasi ishlaydi."
            ],
            "uz_cyrl": [
                "Саволни охиригача ўқинг: 'рухсат этилади'ми ёки 'тақиқланади'ми — аниқланг.",
                "Иерархия: Тартибга солувчи > Светофор > Белгилар > Чизиқлар > 'Ўнгдан халақит'."
            ],
            "ru": [
                "Внимательно читайте вопрос: 'разрешено' или 'запрещено'.",
                "Иерархия приоритетов: Регулировщик > Светофор > Знаки приоритета > Разметка > Помеха справа."
            ]
        },
        "exam_traps": {
            "uz_latn": [
                "⚠️ 'Barcha javoblar to‘g‘ri' varianti 36.7% holatda tuzoq bo‘ladi — savolda aniq bitta qoida so‘ralsa, shoshilmasdan tahlil qiling."
            ],
            "uz_cyrl": [
                "⚠️ 'Барча жавоблар тўғри' варианти ҳамма вақт ҳам тўғри бўлавермайди — 36.7% ҳолатда бу тузоқдир!"
            ],
            "ru": [
                "⚠️ Вариант 'Все ответы правильные' в 36.7% случаев является ловушкой — обязательно перепроверяйте условия вопроса."
            ]
        },
        "ai_prompt": {
            "uz_latn": "Avtotest imtihonida eng ko‘p yiqitadigan savollar turlari va ularni yechish strategiyasi",
            "uz_cyrl": "Автотест имтиҳонида энг кўп хато қилинадиган саволлар ва уларни ечиш стратегияси",
            "ru": "Стратегия решения самых коварных вопросов на экзамене по ПДД"
        }
    }
]

def get_theory_curriculum(language: str = "uz_latn") -> List[Dict[str, Any]]:
    """Returns curriculum modules tailored to language."""
    target_lang = language if language in ("uz_latn", "uz_cyrl", "ru") else "uz_latn"
    res = []
    for mod in THEORY_MODULES:
        res.append({
            "order": mod["order"],
            "category_id": mod["category_id"],
            "category_ids": mod.get("category_ids", [mod["category_id"]]),
            "badge": mod["badge"].get(target_lang, mod["badge"]["uz_latn"]),
            "duration_min": mod["duration_min"],
            "title": mod["title"].get(target_lang, mod["title"]["uz_latn"]),
            "summary": mod["summary"].get(target_lang, mod["summary"]["uz_latn"]),
            "key_rules": mod["key_rules"].get(target_lang, mod["key_rules"]["uz_latn"]),
            "exam_traps": mod["exam_traps"].get(target_lang, mod["exam_traps"]["uz_latn"]),
            "ai_prompt": mod["ai_prompt"].get(target_lang, mod["ai_prompt"]["uz_latn"])
        })
    return res

def get_module_lesson(order_or_cat_id: int, language: str = "uz_latn") -> Optional[Dict[str, Any]]:
    """Finds single module by order or category_id."""
    target_lang = language if language in ("uz_latn", "uz_cyrl", "ru") else "uz_latn"
    mod = next((m for m in THEORY_MODULES if m["order"] == order_or_cat_id or m["category_id"] == order_or_cat_id), None)
    if not mod:
        return None
    return {
        "order": mod["order"],
        "category_id": mod["category_id"],
        "category_ids": mod.get("category_ids", [mod["category_id"]]),
        "badge": mod["badge"].get(target_lang, mod["badge"]["uz_latn"]),
        "duration_min": mod["duration_min"],
        "title": mod["title"].get(target_lang, mod["title"]["uz_latn"]),
        "summary": mod["summary"].get(target_lang, mod["summary"]["uz_latn"]),
        "key_rules": mod["key_rules"].get(target_lang, mod["key_rules"]["uz_latn"]),
        "exam_traps": mod["exam_traps"].get(target_lang, mod["exam_traps"]["uz_latn"]),
        "ai_prompt": mod["ai_prompt"].get(target_lang, mod["ai_prompt"]["uz_latn"])
    }
