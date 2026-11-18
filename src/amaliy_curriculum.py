"""
RULLY Practical Driving Exam Curriculum & Scenarios Engine (Amaliy Imtihon).
Authored strictly based on Uzbekistan driver licensing standards and YHQ regulations.
Supports: uz_latn, uz_cyrl, ru.
Provides:
1. 10 Comprehensive Practical Training Modules with step-by-step guidance.
2. Common Exam Mistakes & Immediate Disqualification Traps.
3. Official Autodrome & City Driving Readiness Checklist.
4. Interactive Situational Decision Tests.
"""

from typing import List, Dict, Any, Optional

PRACTICAL_MODULES: List[Dict[str, Any]] = [
    {
        "id": "MOD-01",
        "order": 1,
        "title": {
            "uz_latn": "Avtomobilga o‘tirish va boshqaruv organlarini sozlash",
            "uz_cyrl": "Автомобилга ўтириш ва бошқарув органларини созлаш",
            "ru": "Посадка в автомобиль и настройка органов управления"
        },
        "description": {
            "uz_latn": "Imtihon topshiruvchining birinchi va eng muhim qadami: to‘g‘ri o‘tirish, ko‘zgular va xavfsizlik.",
            "uz_cyrl": "Имтиҳон топширувчининг биринчи ва энг муҳим қадами: тўғри ўтириш, кўзгулар ва хавфсизлик.",
            "ru": "Первый и важнейший шаг на экзамене: правильная посадка, зеркала и безопасность."
        },
        "badge": "Baza",
        "duration_min": 15,
        "steps": [
            {
                "step": 1,
                "title": {
                    "uz_latn": "O‘rindiqni sozlash",
                    "uz_cyrl": "Ўриндиқни созлаш",
                    "ru": "Регулировка сиденья"
                },
                "instruction": {
                    "uz_latn": "Pedallarni to‘liq bosganda tizzalar biroz bukilgan holatda qolishi kerak. O‘rindiq suyanchig‘i 90-100 gradus burchak ostida o‘rnatiladi.",
                    "uz_cyrl": "Педалларни тўлиқ босганда тиззалар бироз букилган ҳолатда қолиши керак. Ўриндиқ суянчиғи 90-100 градус бурчак остида ўрнатилади.",
                    "ru": "При полном нажатии педалей колени должны оставаться слегка согнутыми. Спинка сиденья устанавливается под углом 90-100 градусов."
                }
            },
            {
                "step": 2,
                "title": {
                    "uz_latn": "Ko‘zgularni sozlash",
                    "uz_cyrl": "Кўзгуларни созлаш",
                    "ru": "Настройка зеркал"
                },
                "instruction": {
                    "uz_latn": "Yon ko‘zgularda avtomobil orqa qanotining 10-15% qismi va ufq chizig‘i o‘rtada ko‘rinishi shart. Salon ko‘zgusi orqa oynani to‘liq qamrab olishi lozim.",
                    "uz_cyrl": "Ён кўзгуларда автомобиль орқа қанотининг 10-15% қисми ва уфқ чизиғи ўртада кўриниши шарт. Салон кўзгуси орқа ойнани тўлиқ қамраб олиши лозим.",
                    "ru": "В боковых зеркалах должно быть видно 10-15% заднего крыла и линия горизонта посередине. Салонное зеркало должно полностью охватывать заднее стекло."
                }
            },
            {
                "step": 3,
                "title": {
                    "uz_latn": "Xavfsizlik kamarini taqish",
                    "uz_cyrl": "Хавфсизлик камарини тақиш",
                    "ru": "Пристегивание ремня безопасности"
                },
                "instruction": {
                    "uz_latn": "Dvigatelni o‘t oldirishdan oldin xavfsizlik kamarini taqing va u qulflanganligiga ishonch hosil qiling.",
                    "uz_cyrl": "Двигателни ўт олдиришдан олдин хавфсизлик камарини тақинг ва у қулфланганлигига ишонч ҳосил қилинг.",
                    "ru": "Перед запуском двигателя пристегните ремень безопасности и убедитесь, что замок зафиксирован."
                }
            }
        ],
        "common_mistakes": {
            "uz_latn": [
                "Xavfsizlik kamarini taqishni unutish (Darhol 5 jarima bali yoki imtihondan chetlatish)",
                "Ko‘zgularni sozlamasdan harakatni boshlash",
                "Eshik to‘liq yopilmaganini sezmaslik"
            ],
            "uz_cyrl": [
                "Хавфсизлик камарини тақишни унутиш (Дарҳол 5 жарима бали ёки четлатиш)",
                "Кўзгуларни созламасдан ҳаракатни бошлаш",
                "Эшик тўлиқ ёпилмаганини сезмаслик"
            ],
            "ru": [
                "Непристегнутый ремень безопасности (штрафные баллы или незачет)",
                "Начало движения без регулировки зеркал",
                "Начало движения с незакрытой дверью"
            ]
        },
        "disqualification_trap": {
            "uz_latn": "Kamarsiz harakatlanish avtomatlashtirilgan tizimda imtihonni darhol to‘xtatadi!",
            "uz_cyrl": "Камарсиз ҳаракатланиш автоматлаштирилган тизимда имтиҳонни дарҳол тўхтатади!",
            "ru": "Движение без ремня безопасности мгновенно прекращает экзамен в автоматизированной системе!"
        }
    },
    {
        "id": "MOD-02",
        "order": 2,
        "title": {
            "uz_latn": "Joyidan qo‘zg‘alish va to‘xtash",
            "uz_cyrl": "Жойидан қўзғалиш ва тўхташ",
            "ru": "Начало движения и остановка"
        },
        "description": {
            "uz_latn": "Avtodrom va ko‘chada harakat boshlashdagi oltin qoidalar: ko‘zgu, signal, xavfsizlik va silliq tezlanish.",
            "uz_cyrl": "Автодром ва кўчада ҳаракат бошлашдаги олтин қоидалар: кўзгу, сигнал, хавфсизлик ва силлиқ тезланиш.",
            "ru": "Золотые правила начала движения: зеркало, поворотник, безопасность и плавный разгон."
        },
        "badge": "Asosiy",
        "duration_min": 20,
        "steps": [
            {
                "step": 1,
                "title": {
                    "uz_latn": "Burilish chirog‘ini yoqish",
                    "uz_cyrl": "Бурилиш чироғини ёқиш",
                    "ru": "Включение указателя поворота"
                },
                "instruction": {
                    "uz_latn": "Joyidan qo‘zg‘alishdan 3-5 soniya oldin chapga burilish chirog‘ini yoqing.",
                    "uz_cyrl": "Жойидан қўзғалишдан 3-5 сония олдин чапга бурилиш чироғини ёқинг.",
                    "ru": "За 3-5 секунд до начала движения включите левый указатель поворота."
                }
            },
            {
                "step": 2,
                "title": {
                    "uz_latn": "Ko‘zgular va ko‘rinmas hududni tekshirish",
                    "uz_cyrl": "Кўзгулар ва кўринмас ҳудудни текшириш",
                    "ru": "Проверка зеркал и слепой зоны"
                },
                "instruction": {
                    "uz_latn": "Chap ko‘zguga va yelka osha orqaga qarab, harakatlanayotgan boshqa transport vositalari yo‘qligiga ishonch hosil qiling.",
                    "uz_cyrl": "Чап кўзгуга ва елка оша орқага қараб, ҳаракатланаётган бошқа транспорт воситалари йўқлигига ишонч ҳосил қилинг.",
                    "ru": "Посмотрите в левое зеркало и через плечо, убедитесь в отсутствии помех."
                }
            },
            {
                "step": 3,
                "title": {
                    "uz_latn": "To‘xtash tormozini bo‘shatish",
                    "uz_cyrl": "Тўхташ тормозини бўшатиш",
                    "ru": "Снятие со стояночного тормоза"
                },
                "instruction": {
                    "uz_latn": "1-uzatmani yoqing, qo‘l tormozini to‘liq tushiring va debriyajni ulanish nuqtasigacha sekin qo‘yib yuboring.",
                    "uz_cyrl": "1-узатмани ёқинг, қўл тормозини тўлиқ туширинг ва дебрияжни уланиш нуқтасигача секин қўйиб юборинг.",
                    "ru": "Включите 1-ю передачу, снимите ручник и плавно подведите сцепление к точке схватывания."
                }
            }
        ],
        "common_mistakes": {
            "uz_latn": [
                "Burilish chirog‘ini yoqmaslik",
                "Qo‘l tormozi (ruchkik)ni tushirishni unutish",
                "Dvigatelni o‘chirib qo‘yish (dvigatel o‘chsa 5 jarima bali)"
            ],
            "uz_cyrl": [
                "Бурилиш чироғини ёқмаслик",
                "Қўл тормози (ручник)ни туширишни унутиш",
                "Двигателни ўчириб қўйиш (двигател ўчса 5 жарима бали)"
            ],
            "ru": [
                "Не включен сигнал поворота",
                "Движение на стояночном тормозе",
                "Остановка двигателя (заглохнуть — штрафные баллы)"
            ]
        },
        "disqualification_trap": {
            "uz_latn": "Yo‘ldan o‘tayotgan mashinaga xalaqit berib qo‘zg‘alish (avariya holatini yaratish) — qat’iy YIQILISH!",
            "uz_cyrl": "Йўлдан ўтаётган машинага халақит бериб қўзғалиш (авария ҳолатини яратиш) — қатъий ЙИҚИЛИШ!",
            "ru": "Создание аварийной обстановки при выезде — безусловный НЕЗАЧЕТ!"
        }
    },
    {
        "id": "MOD-03",
        "order": 3,
        "title": {
            "uz_latn": "Avtodrom: Estakada (Qiyalikda to‘xtash va qo‘zg‘alish)",
            "uz_cyrl": "Автодром: Эстакада (Қияликда тўхташ ва қўзғалиш)",
            "ru": "Автодром: Эстакада (Остановка и старт на подъеме)"
        },
        "description": {
            "uz_latn": "Qiyalikda orqaga 20 sm dan ortiq siljimasdan qo‘zg‘alish texnikasi va debriyaj-gaz balansi.",
            "uz_cyrl": "Қияликда орқага 20 см дан ортиқ силжимасдан қўзғалиш техникаси ва дебрияж-газ баланси.",
            "ru": "Техника трогания на подъеме без отката назад более чем на 20 см."
        },
        "badge": "Avtodrom",
        "duration_min": 25,
        "steps": [
            {
                "step": 1,
                "title": {
                    "uz_latn": "STOP chizig‘ida to‘xtash",
                    "uz_cyrl": "STOP чизиғида тўхташ",
                    "ru": "Остановка у линии СТОП"
                },
                "instruction": {
                    "uz_latn": "Estakadaning qiyaligiga chiqib, STOP belgisidan oldin to‘xtang. Qo‘l tormozini torting va neytralga oling.",
                    "uz_cyrl": "Эстакаданинг қиялигига чиқиб, STOP белгисидан олдин тўхтанг. Қўл тормозини тортинг ва нейтралга олинг.",
                    "ru": "Въехав на подъем эстакады, остановитесь перед линией СТОП. Затяните ручник и включите нейтраль."
                }
            },
            {
                "step": 2,
                "title": {
                    "uz_latn": "Debriyaj va gazni tayyorlash",
                    "uz_cyrl": "Дебрияж ва газни тайёрлаш",
                    "ru": "Подготовка газа и сцепления"
                },
                "instruction": {
                    "uz_latn": "1-uzatmani yoqing. Gaz pedalini 1500-2000 aylanishgacha bosing, debriyajni mashina old qismi ko‘tarilguncha (ulanish nuqtasigacha) chiqaring.",
                    "uz_cyrl": "1-узатмани ёқинг. Газ педалини 1500-2000 айланишгача босинг, дебрияжни машина олд қисми кўтарилгунча чиқаринг.",
                    "ru": "Включите 1-ю передачу. Поднимите обороты до 1500-2000, плавно отпустите сцепление до момента схватывания (нос машины приподнимется)."
                }
            },
            {
                "step": 3,
                "title": {
                    "uz_latn": "Qo‘l tormozini tushirish",
                    "uz_cyrl": "Қўл тормозини тушириш",
                    "ru": "Снятие ручника"
                },
                "instruction": {
                    "uz_latn": "Mashina oldinga talpinganida qo‘l tormozini silliq tushiring va gazni ushlab qolib qiyalikdan o‘ting.",
                    "uz_cyrl": "Машина олдинга талпинганида қўл тормозини силлиқ туширинг ва газни ушлаб қолиб қияликдан ўтинг.",
                    "ru": "Когда машина потянется вперед, плавно опустите ручник и преодолейте подъем."
                }
            }
        ],
        "common_mistakes": {
            "uz_latn": [
                "Orqaga 20 sm dan ortiq siljish (sensor darhol yiqitadi)",
                "Dvigatelni o‘chirish",
                "STOP chizig‘ini bosib ketish"
            ],
            "uz_cyrl": [
                "Орқага 20 см дан ортиқ силжиш (сенсор дарҳол йиқитади)",
                "Двигателни ўчириш",
                "STOP чизиғини босиб кетиш"
            ],
            "ru": [
                "Откат назад более 20 см (автоматическая фиксация незачета)",
                "Остановка двигателя",
                "Пересечение стоп-линии"
            ]
        },
        "disqualification_trap": {
            "uz_latn": "Orqaga 20 sm dan ortiq orqaga ketish yoki estakadada to‘xtay olmaslik — avtomatlashtirilgan tizimda to‘g‘ridan-to‘g‘ri YIQILISH!",
            "uz_cyrl": "Орқага 20 см дан ортиқ кетиш ёки эстакадада тўхтай олмаслик — тўғридан-тўғри ЙИҚИЛИШ!",
            "ru": "Откат более чем на 20 см — мгновенная дисквалификация!"
        }
    },
    {
        "id": "MOD-04",
        "order": 4,
        "title": {
            "uz_latn": "Avtodrom: Parallel to‘xtash (Parallel Parking)",
            "uz_cyrl": "Автодром: Параллел тўхташ (Parallel Parking)",
            "ru": "Автодром: Параллельная парковка"
        },
        "description": {
            "uz_latn": "Ikki avtomobil orasiga orqa uzatma orqali 45 gradus burchak ostida to‘xtash algoritmi.",
            "uz_cyrl": "Икки автомобиль орасига орқа узатма орқали 45 градус бурчак остида тўхташ алгоритми.",
            "ru": "Алгоритм параллельной парковки задним ходом под углом 45 градусов."
        },
        "badge": "Avtodrom",
        "duration_min": 30,
        "steps": [
            {
                "step": 1,
                "title": {
                    "uz_latn": "Pozitsiyani egallash",
                    "uz_cyrl": "Позицияни эгаллаш",
                    "ru": "Занятие исходной позиции"
                },
                "instruction": {
                    "uz_latn": "Parkovka cho‘ntagidan 0.5 - 1 metr yon masofa saqlab, oldingi ustuncha bilan orqa g‘ildirak tekislanguncha to‘xtang.",
                    "uz_cyrl": "Парковка чўнтагидан 0.5 - 1 метр ён масофа сақлаб, олдинги устунча билан орқа ғилдирак текисланганича тўхтанг.",
                    "ru": "Встаньте параллельно парковочному карману с интервалом 0.5-1 м, пока заднее колесо не поравняется с углом."
                }
            },
            {
                "step": 2,
                "title": {
                    "uz_latn": "Rulni to‘liq o‘ngga burish va 45 gradus",
                    "uz_cyrl": "Рулни тўлиқ ўнгга буриш ва 45 градус",
                    "ru": "Руль до упора вправо и угол 45°"
                },
                "instruction": {
                    "uz_latn": "Orqa uzatmani yoqing. Rulni oxirigacha o‘ngga buring. Chap ko‘zguda orqa ichki burchak ustunchasi ko‘ringuncha (45 gradus) orqaga yuring.",
                    "uz_cyrl": "Орқа узатмани ёқинг. Рулни охиригача ўнгга буринг. Чап кўзгуда орқа ички бурчак кўрингунча орқага юринг.",
                    "ru": "Включите задний ход. Выкрутите руль вправо до упора. Двигайтесь назад, пока в левом зеркале не увидите дальний внутренний угол."
                }
            },
            {
                "step": 3,
                "title": {
                    "uz_latn": "Rulni to‘g‘rilash va chapga burish",
                    "uz_cyrl": "Рулни тўғрилаш ва чапга буриш",
                    "ru": "Выравнивание и руль влево"
                },
                "instruction": {
                    "uz_latn": "Rulni to‘g‘rilang, o‘ng burchak ustunchasi old oynaning o‘ng pastki qismiga kelganda rulni to‘liq chapga burib mashinani boksga kiriting.",
                    "uz_cyrl": "Рулни тўғриланг, олд бурчак мос келганда рулни тўлиқ чапга буриб машинани боксга киритинг.",
                    "ru": "Выпрямите руль, сдайте назад, затем выкрутите руль влево и завершите заезд в габариты."
                }
            }
        ],
        "common_mistakes": {
            "uz_latn": [
                "Yon yoki orqa chiziqlarni (ustunchalarni) urib ketish",
                "Old g‘ildirak chiziqdan tashqarida qolib ketishi",
                "Manyovr davomida to‘xtab, ortiqcha urinish qilish"
            ],
            "uz_cyrl": [
                "Ён ёки орқа чизиқларни (устунчаларни) уриб кетиш",
                "Олд ғилдирак чизиқдан ташқарида қолиб кетиши",
                "Манёвр давомида тўхтаб, ортиқча уриниш қилиш"
            ],
            "ru": [
                "Сбивание стоек или наезд на контрольные линии",
                "Неполный заезд в парковочный карман",
                "Использование заднего хода повторно более разрешенного количества раз"
            ]
        },
        "disqualification_trap": {
            "uz_latn": "Chiziq ustiga chiqish yoki ustunchaga tegish sensor orqali darhol imtihonni to‘xtatadi!",
            "uz_cyrl": "Чизиқ устига чиқиш ёки устунчага тегиш дарҳол имтиҳонни тўхтатади!",
            "ru": "Наезд на разметку или сбивание стойки — моментальный незачет!"
        }
    },
    {
        "id": "MOD-05",
        "order": 5,
        "title": {
            "uz_latn": "Avtodrom: 90 gradusli boksga kirish (Garaj)",
            "uz_cyrl": "Автодром: 90 градусли боксга кириш (Гараж)",
            "ru": "Автодром: Заезд в бокс задним ходом (Гараж)"
        },
        "description": {
            "uz_latn": "Orqa uzatma yordamida to‘g‘ri burchak ostida garajga kirish va to‘xtash.",
            "uz_cyrl": "Орқа узатма ёрдамида тўғри бурчак остида гаражга кириш ва тўхташ.",
            "ru": "Заезд в бокс под прямым углом 90 градусов задним ходом."
        },
        "badge": "Avtodrom",
        "duration_min": 25,
        "steps": [
            {
                "step": 1,
                "title": {
                    "uz_latn": "Boks oldidan o‘tish",
                    "uz_cyrl": "Бокс олдидан ўтиш",
                    "ru": "Проезд мимо бокса"
                },
                "instruction": {
                    "uz_latn": "Boks chizig‘iga perpendikulyar holda o‘ting, o‘rindiq boksning uzoq ustunchasi bilan tekislanganda to‘xtang.",
                    "uz_cyrl": "Бокс чизиғига перпендикуляр ҳолда ўтинг, ўриндиқ бокс устунчаси билан текисланганда тўхтанг.",
                    "ru": "Проезжайте мимо бокса с интервалом около 1.5-2 м, пока плечо не поравняется с дальней стойкой."
                }
            },
            {
                "step": 2,
                "title": {
                    "uz_latn": "Rulni burish va orqaga harakat",
                    "uz_cyrl": "Рулни буриш ва орқага ҳаракат",
                    "ru": "Поворот руля и движение назад"
                },
                "instruction": {
                    "uz_latn": "Rulni to‘liq boks tomoniga buring, har ikkala ko‘zgu orqali oraliq masofani teng taqsimlab sekin orqaga kiring.",
                    "uz_cyrl": "Рулни тўлиқ бокс томонига буринг, иккала кўзгу орқали масофани тенг тақсимлаб киринг.",
                    "ru": "Выкрутите руль в сторону бокса, контролируйте по обоим зеркалам зазоры и плавно заезжайте."
                }
            },
            {
                "step": 3,
                "title": {
                    "uz_latn": "G‘ildiraklarni to‘g‘rilash va to‘liq kirish",
                    "uz_cyrl": "Ғилдиракларни тўғрилаш ва тўлиқ кириш",
                    "ru": "Выравнивание колес и фиксация"
                },
                "instruction": {
                    "uz_latn": "Mashina boks devorlariga parallel bo‘lganda g‘ildiraklarni to‘g‘rilang va old bamper chiziq ichiga kirguncha orqaga yuring.",
                    "uz_cyrl": "Машина параллел бўлганда ғилдиракларни тўғриланг ва олд бампер тўлиқ кирганда тўхтанг.",
                    "ru": "Когда авто встанет параллельно, выпрямите руль и доезжайте до полной фиксации внутри бокса."
                }
            }
        ],
        "common_mistakes": {
            "uz_latn": [
                "Boks burchagidagi ustunchalarni bosish",
                "Avtomobil old qismini boks chizig‘idan tashqarida qoldirish",
                "Neytral va qo‘l tormozini qo‘ymaslik"
            ],
            "uz_cyrl": [
                "Бокс бурчагидаги устунчаларни босиш",
                "Автомобиль олд қисмини ташқарида қолдириш",
                "Нейтрал ва қўл тормозини қўймаслик"
            ],
            "ru": [
                "Задевание стоек бокса",
                "Передний бампер остался за пределами контрольной линии",
                "Отказ от постановки на нейтраль и стояночный тормоз"
            ]
        },
        "disqualification_trap": {
            "uz_latn": "Old bamperning boks chegarasidan tashqarida qolib ketishi — vazifa bajarilmagan deb hisoblanadi!",
            "uz_cyrl": "Олд бампернинг чегарадан ташқарида қолиши — вазифа бажарилмаган!",
            "ru": "Передний габарит не пересек линию бокса — упражнение не зачтено!"
        }
    },
    {
        "id": "MOD-06",
        "order": 6,
        "title": {
            "uz_latn": "Shahar yo‘li: Tartibga solingan va solinmagan chorrahalar",
            "uz_cyrl": "Шаҳар йўли: Тартибга солинган ва солинмаган чорраҳалар",
            "ru": "Город: Регулируемые и нерегулируемые перекрестки"
        },
        "description": {
            "uz_latn": "Svetofor, yo‘l belgilari (2.1, 2.4, 2.5) va o‘ngdan kelayotgan transport vositasiga yo‘l berish qoidalari.",
            "uz_cyrl": "Светофор, йўл белгилари (2.1, 2.4, 2.5) ва ўнгдан келаётган транспорт воситасига йўл бериш қоидалари.",
            "ru": "Светофоры, знаки приоритета (2.1, 2.4, 2.5) и правило помехи справа."
        },
        "badge": "Shahar",
        "duration_min": 35,
        "steps": [
            {
                "step": 1,
                "title": {
                    "uz_latn": "Chorrahaga yaqinlashish va bo‘lak tanlash",
                    "uz_cyrl": "Чорраҳага яқинлашиш ва бўлак танлаш",
                    "ru": "Подъезд и выбор полосы"
                },
                "instruction": {
                    "uz_latn": "Chorrahaga 50 metr qolganda kerakli yo‘nalish bo‘lagini egallang. 1.18 yo‘nalish ko‘rsatkichlariga qat’iy rioya qiling.",
                    "uz_cyrl": "Чорраҳага 50 метр қолганда керакли йўналиш бўлагини эгалланг. 1.18 кўрсаткичларига риоя қилинг.",
                    "ru": "Заблаговременно займите соответствующую полосу для поворота согласно знакам и разметке 1.18."
                }
            },
            {
                "step": 2,
                "title": {
                    "uz_latn": "STOP 2.5 belgisida to‘xtash",
                    "uz_cyrl": "STOP 2.5 белгисида тўхташ",
                    "ru": "Остановка на знак 2.5 СТОП"
                },
                "instruction": {
                    "uz_latn": "2.5 belgisi oldida harakat tezligini pasaytirib emas, g‘ildiraklar to‘liq aylanishdan to‘xtaguncha (0 km/soat) 2 soniya to‘xtash shart!",
                    "uz_cyrl": "2.5 белгиси олдида ҳаракатни тўлиқ тўхтатиб (0 км/соат) 2 сония туриш шарт!",
                    "ru": "Перед знаком 2.5 обязательна полная фиксация остановки (0 км/ч) минимум на 2 секунды!"
                }
            },
            {
                "step": 3,
                "title": {
                    "uz_latn": "Chapga burilishda ro‘para harakatga yo‘l berish",
                    "uz_cyrl": "Чапга бурилишда рўпара ҳаракатга йўл бериш",
                    "ru": "Уступить встречным при повороте налево"
                },
                "instruction": {
                    "uz_latn": "Yashil chiroqda chapga burilishda chorraha markazigacha chiqib to‘xtang va to‘g‘riga hamda o‘ngga burilayotgan ro‘para transportga yo‘l bering.",
                    "uz_cyrl": "Яшил чироқда чапга бурилишда рўпарадан келаётганларга йўл беринг.",
                    "ru": "При повороте налево выезжайте к центру перекрестка и уступайте встречным ТС, идущим прямо и направо."
                }
            }
        ],
        "common_mistakes": {
            "uz_latn": [
                "2.5 STOP belgisida to‘liq to‘xtamasdan (sirpanib) o‘tib ketish",
                "Chorrahada to‘xtab qolgan tirbandlikka kirib to‘siq bo‘lish",
                "Chapga burilishda ro‘paradan kelayotganga yo‘l bermaslik"
            ],
            "uz_cyrl": [
                "2.5 STOP белгисида тўлиқ тўхтамасдан ўтиб кетиш",
                "Тирбандликка кириб чорраҳани тўсиб қўйиш",
                "Чапга бурилишда рўпарадагига йўл бермаслик"
            ],
            "ru": [
                "Проезд знака STOP без полной остановки колес",
                "Выезд на перекресток при образовавшемся заторе",
                "Непредоставление преимущества встречному движению"
            ]
        },
        "disqualification_trap": {
            "uz_latn": "Qizil chiroqda yoki STOP belgisida to‘xtamasdan o‘tish — darhol imtihondan yiqitadi!",
            "uz_cyrl": "Қизил чироқда ёки STOP белгисида тўхтамасдан ўтиш — дарҳол йиқитади!",
            "ru": "Проезд на запрещающий сигнал светофора — мгновенный незачет!"
        }
    },
    {
        "id": "MOD-07",
        "order": 7,
        "title": {
            "uz_latn": "Shahar yo‘li: Aylanma harakat chorrahalari (Roundabouts)",
            "uz_cyrl": "Шаҳар йўли: Айланма ҳаракат чорраҳалари",
            "ru": "Город: Круговое движение"
        },
        "description": {
            "uz_latn": "4.3 belgisi o‘rnatilgan aylanma chorrahalarga kirish, harakatlanish va xavfsiz chiqish qoidalari.",
            "uz_cyrl": "4.3 белгиси ўрнатилган айланма чорраҳаларга кириш ва чиқиш қоидалари.",
            "ru": "Въезд, движение по кольцу и безопасный съезд со знака 4.3."
        },
        "badge": "Shahar",
        "duration_min": 25,
        "steps": [
            {
                "step": 1,
                "title": {
                    "uz_latn": "Aylanaga kirishda ustunlik",
                    "uz_cyrl": "Айланага киришда устунлик",
                    "ru": "Приоритет на круге"
                },
                "instruction": {
                    "uz_latn": "O‘zbekiston YHQga muvofiq, agar boshqa belgilar bo‘lmasa, aylanada harakatlanayotgan transport vositalari aylanaga kirayotganlarga nisbatan ustunlikka ega.",
                    "uz_cyrl": "Ўзбекистон ЙҲҚга мувофиқ, айланада ҳаракатланаётганлар устунликка эга.",
                    "ru": "По ПДД Узбекистана круг является главным, если знаками не установлено иное."
                }
            },
            {
                "step": 2,
                "title": {
                    "uz_latn": "Aylanadan chiqish",
                    "uz_cyrl": "Айланадан чиқиш",
                    "ru": "Съезд с кругового движения"
                },
                "instruction": {
                    "uz_latn": "Aylanadan faqat chetki o‘ng bo‘lakdan o‘ngga burilish chirog‘ini yoqqan holda chiqish shart!",
                    "uz_cyrl": "Айланадан фақат четки ўнг бўлакдан чиқиш шарт!",
                    "ru": "Съезд с кольца разрешен только с крайней правой полосы с включенным правым поворотником!"
                }
            }
        ],
        "common_mistakes": {
            "uz_latn": [
                "Aylanadagi transport vositasiga yo‘l bermasdan kirish",
                "Aylanadan ichki (o‘rta yoki chap) bo‘lakdan chiqib ketish",
                "Chiqishda burilish chirog‘ini yoqmaslik"
            ],
            "uz_cyrl": [
                "Айланадаги транспортга йўл бермасдан кириш",
                "Айланадан ички бўлакдан чиқиб кетиш",
                "Чиқишда бурилиш чироғини ёқмаслик"
            ],
            "ru": [
                "Не уступил дорогу ТС, находящемуся на кольце",
                "Съезд с кольца со второй или левой полосы",
                "Невключение правого поворотника при выезде"
            ]
        },
        "disqualification_trap": {
            "uz_latn": "Aylanada harakatlanayotgan mashinaning to‘satdan tormoz berishiga sababchi bo‘lish — YIQILISH!",
            "uz_cyrl": "Айланадаги машинага халақит бериш — ЙИҚИЛИШ!",
            "ru": "Создание помехи автомобилю, двигающемуся по кольцу — незачет!"
        }
    },
    {
        "id": "MOD-08",
        "order": 8,
        "title": {
            "uz_latn": "Piyodalar o‘tish joylari va jamoat transporti",
            "uz_cyrl": "Пиёдалар ўтиш жойлари ва жамоат транспорти",
            "ru": "Пешеходные переходы и маршрутный транспорт"
        },
        "description": {
            "uz_latn": "5.16.1 / 5.16.2 belgilari oldida piyodalarga so‘zsiz yo‘l berish va bekatdan chiqayotgan avtobuslar imtiyozi.",
            "uz_cyrl": "Пиёдаларга сўзсиз йўл бериш ва бекатдаги автобуслар имтиёзи.",
            "ru": "Предоставление преимущества пешеходам и отъезжающим от остановки автобусам."
        },
        "badge": "Xavfsizlik",
        "duration_min": 20,
        "steps": [
            {
                "step": 1,
                "title": {
                    "uz_latn": "Piyoda qadam bosganda to‘xtash",
                    "uz_cyrl": "Пиёда қадам босганда тўхташ",
                    "ru": "Остановка при выходе пешехода"
                },
                "instruction": {
                    "uz_latn": "Piyodalar o‘tish joyiga piyoda qadam qo‘ygan zahoti avtomobil tezligini pasaytirib, to‘liq to‘xtashi shart.",
                    "uz_cyrl": "Пиёдалар ўтиш жойига пиёда қадам қўйган заҳоти тўлиқ тўхташ шарт.",
                    "ru": "Водитель обязан уступить дорогу пешеходам, ступившим на проезжую часть."
                }
            },
            {
                "step": 2,
                "title": {
                    "uz_latn": "Bekatdan chiqayotgan avtobus",
                    "uz_cyrl": "Бекатдан чиқаётган автобус",
                    "ru": "Отъезжающий автобус"
                },
                "instruction": {
                    "uz_latn": "Aholi punktlarida belgilangan bekatdan harakatni boshlayotgan avtobus va trolleybuslarga yo‘l berish shart.",
                    "uz_cyrl": "Аҳоли пунктларида бекатдан чиқаётган автобусларга йўл бериш шарт.",
                    "ru": "В населенных пунктах водители должны уступать дорогу троллейбусам и автобусам, начинающим движение от остановки."
                }
            }
        ],
        "common_mistakes": {
            "uz_latn": [
                "Piyodaning yo‘lidan tezroq o‘tib ketishga urinish",
                "O‘tish joyi oldida to‘xtagan qo‘shni qatordagi mashinani tekshirmasdan quvib o‘tish"
            ],
            "uz_cyrl": [
                "Пиёда олдидан тезроқ ўтиб кетишга уриниш",
                "Тўхтаган машинани текширмасдан қувиб ўтиш"
            ],
            "ru": [
                "Попытка проскочить перед пешеходом",
                "Опережение ТС, остановившегося перед пешеходным переходом"
            ]
        },
        "disqualification_trap": {
            "uz_latn": "Piyodaga yo‘l bermaslik — davlat imtihonida darhol yiqituvchi eng og‘ir qoidabuzarlik!",
            "uz_cyrl": "Пиёдага йўл бермаслик — дарҳол йиқитади!",
            "ru": "Не пропустил пешехода — безусловный и немедленный незачет!"
        }
    },
    {
        "id": "MOD-09",
        "order": 9,
        "title": {
            "uz_latn": "Quvib o‘tish va qatorni o‘zgartirish (Manevrlar)",
            "uz_cyrl": "Қувиб ўтиш ва қаторни ўзгартириш (Маневрлар)",
            "ru": "Обгон и перестроение (Маневрирование)"
        },
        "description": {
            "uz_latn": "Ko‘zgular, ko‘rinmas (ko‘r) hududlar va burilish chiroqlaridan to‘g‘ri foydalanish qoidalari.",
            "uz_cyrl": "Кўзгулар, кўринмас (кўр) ҳудудлар ва бурилиш чироқларидан тўғри фойдаланиш қоидалари.",
            "ru": "Правила оценки мертвых зон, зеркал и заблаговременного включения указателей поворота."
        },
        "badge": "Shahar",
        "duration_min": 25,
        "steps": [
            {
                "step": 1,
                "title": {
                    "uz_latn": "Atrofni va ko‘zgularni tekshirish",
                    "uz_cyrl": "Атрофни ва кўзгуларни текшириш",
                    "ru": "Контроль зеркал и мертвых зон"
                },
                "instruction": {
                    "uz_latn": "Manevr boshlashdan oldin salon va chap yon ko‘zguga qarang. Boshni chapga biroz burib ko‘r zonada transport yo‘qligini tekshiring.",
                    "uz_cyrl": "Маневр бошлашдан олдин салон ва чап ён кўзгуга қаранг. Кўр зонада машина йўқлигини текширинг.",
                    "ru": "Оцените обстановку по салонному и левому зеркалу. Быстрым взглядом через плечо проверьте слепую зону."
                }
            },
            {
                "step": 2,
                "title": {
                    "uz_latn": "Burilish chirog‘ini o‘z vaqtida yoqish",
                    "uz_cyrl": "Бурилиш чироғини ўз вақтида ёқиш",
                    "ru": "Своевременная подача сигнала"
                },
                "instruction": {
                    "uz_latn": "Manevrdan kamida 3-5 soniya oldin chap burilish chirog‘ini yoqing va harakatlanayotgan transportga xalaqit bermang.",
                    "uz_cyrl": "Маневрдан камида 3-5 сония олдин чап бурилиш чироғини ёқинг.",
                    "ru": "Включите левый указатель поворота заблаговременно (за 3-5 секунд до начала перестроения)."
                }
            },
            {
                "step": 3,
                "title": {
                    "uz_latn": "Silliq qayta tizilish va o‘z qatoriga qaytish",
                    "uz_cyrl": "Силлиқ қайта тизилиш ва қаторга қайтиш",
                    "ru": "Плавное перестроение и возврат"
                },
                "instruction": {
                    "uz_latn": "Tezlikni keskin oshirmasdan boshqa bo‘lakka o‘ting. Quvib o‘tilgan mashina salon ko‘zgusida to‘liq ko‘ringach o‘ng chiroqni yoqib o‘z bo‘lagingizga qayting.",
                    "uz_cyrl": "Тезликни кескин оширмасдан қўшни бўлакка ўтинг ва масофа етарли бўлгач ўз бўлагингизга қайтинг.",
                    "ru": "Плавно перестройтесь. Возвращайтесь на свою полосу только когда обгоняемое ТС полностью видно в салонном зеркале."
                }
            }
        ],
        "common_mistakes": {
            "uz_latn": [
                "Burilish chirog‘ini yoqmasdan qayta tizilish (5 jarima bali)",
                "Ko‘r hududdagi transportni ko‘rmay qolib xavfli vaziyat yaratish (Imtihondan chetlatish)",
                "Qarama-qarshi yo‘nalishga chiqish taqiqlangan joyda quvib o‘tish"
            ],
            "uz_cyrl": [
                "Бурилиш чироғини ёқмасдан қайта тизилиш (5 жарима бали)",
                "Кўр зонадаги машинани кўрмай қолиб хавфли вазият яратиш",
                "Тақиқланган жойда қувиб ўтиш"
            ],
            "ru": [
                "Перестроение без указателя поворота (штрафные баллы)",
                "Игнорирование слепой зоны и создание аварийной обстановки (незачет)",
                "Обгон в зоне действия знака 3.20 или сплошной линии 1.1"
            ]
        },
        "disqualification_trap": {
            "uz_latn": "1.1 yaxlit chiziqni bosib qarama-qarshi yo‘nalishga chiqish yoki 3.20 'Quvib o‘tish taqiqlangan' belgisi ostida quvib o‘tish darhol imtihondan chetlatadi!",
            "uz_cyrl": "1.1 чизиқни босиб қарама-қаршига чиқиш ёки 3.20 белгиси остида қувиб ўтиш дарҳол имтиҳондан четлатади!",
            "ru": "Выезд на встречную полосу через сплошную 1.1 или в зоне знака 3.20 влечет немедленную дисквалификацию!"
        }
    },
    {
        "id": "MOD-10",
        "order": 10,
        "title": {
            "uz_latn": "Avtomobilni to‘xtatish, xavfsizlik va imtihonni yakunlash",
            "uz_cyrl": "Автомобилни тўхтатиш, хавфсизлик ва имтиҳонни якунлаш",
            "ru": "Остановка, безопасность и завершение экзамена"
        },
        "description": {
            "uz_latn": "Yo‘l chetida to‘g‘ri to‘xtash, qo‘l tormozi, dvigatelni o‘chirish va avtomobildan xavfsiz tushish.",
            "uz_cyrl": "Йўл четида тўғри тўхташ, қўл тормози, двигателни ўчириш ва автомобилдан хавфсиз тушиш.",
            "ru": "Правильная парковка у края проезжей части, ручник, глушение двигателя и безопасный выход."
        },
        "badge": "Yakunlash",
        "duration_min": 15,
        "steps": [
            {
                "step": 1,
                "title": {
                    "uz_latn": "To‘xtash joyini to‘g‘ri tanlash va o‘ng chiroqni yoqish",
                    "uz_cyrl": "Тўхташ жойини тўғри танлаш ва ўнг чироқни ёқиш",
                    "ru": "Выбор места и правый поворотник"
                },
                "instruction": {
                    "uz_latn": "To‘xtash taqiqlanmagan joyni tanlang (chorrahadan kamida 5 metr, bekatdan 15 metr masofada). O‘ng burilish chirog‘ini yoqib chetga yaqinlashing.",
                    "uz_cyrl": "Тўхташ тақиқланмаган жойни танланг ва ўнг чироқни ёқиб йўл четига яқинлашинг.",
                    "ru": "Выберите разрешенное место (не ближе 5м от перекрестка, 15м от остановки). Включите правый поворотник."
                }
            },
            {
                "step": 2,
                "title": {
                    "uz_latn": "Avtomobilni to‘xtatish va fiksatsiya qilish",
                    "uz_cyrl": "Автомобилни тўхтатиш ва фиксация қилиш",
                    "ru": "Остановка и фиксация авто"
                },
                "instruction": {
                    "uz_latn": "Tormozni bosib to‘xtang. Uzatmani neytralga (N) yoki Parking (P) rejimiga o‘tkazing. Qo‘l tormozini (ruchnik) oxirigacha torting.",
                    "uz_cyrl": "Тормозни босиб тўхтанг. Узатмани нейтралга (N) ёки Parking (P) га олинг. Қўл тормозини тортинг.",
                    "ru": "Плавно остановитесь. Переведите КПП в нейтраль (N) или Parking (P). Полностью затяните стояночный тормоз."
                }
            },
            {
                "step": 3,
                "title": {
                    "uz_latn": "Xavfsizlik kamarini yechish va eshikni xavfsiz ochish",
                    "uz_cyrl": "Камарни ечиш ва эшикни очиш",
                    "ru": "Отстегивание ремня и выход"
                },
                "instruction": {
                    "uz_latn": "Dvigatelni o‘chiring, kamarni yeching. Yon ko‘zguga qarab orqadan velosipedchi yoki mashina kelmayotganiga to‘liq ishonch hosil qilib eshikni ehtiyotkorlik bilan oching.",
                    "uz_cyrl": "Двигателни ўчиринг, камарни ечинг ва кўзгуга қараб орқадан хавф йўқлигида эшикни очинг.",
                    "ru": "Заглушите мотор, отстегните ремень. Посмотрите в зеркало заднего вида перед открытием двери."
                }
            }
        ],
        "common_mistakes": {
            "uz_latn": [
                "Avtomobil to‘liq to‘xtamasdan oldin kamarni yechib yuborish (5 jarima bali)",
                "Qo‘l tormozini tortishni unutish (Avtomobilning orqaga yoki oldinga siljishi)",
                "Orqa ko‘zguga qaramasdan eshikni keng ochib yuborish (Xavfli vaziyat)"
            ],
            "uz_cyrl": [
                "Машина тўхтамасдан олдин камарни ечиш",
                "Қўл тормозини тортишни унутиш",
                "Орқага қарамасдан эшикни очиш"
            ],
            "ru": [
                "Отстегивание ремня до полной остановки (штрафной балл)",
                "Отказ от затягивания ручника при парковке",
                "Открытие двери без контроля зеркала заднего вида"
            ]
        },
        "disqualification_trap": {
            "uz_latn": "Avtomobilni qiyalikda yoki yo‘lda qo‘l tormozisiz qoldirib ketish va mashinaning siljib ketishiga sabab bo‘lish darhol imtihonni yakunlaydi!",
            "uz_cyrl": "Машинани қўл тормозисиз қолдириб кетиш ва силжиб кетишига йўл қўйиш дарҳол йиқитади!",
            "ru": "Оставление ТС без стояночного тормоза, приведшее к его самопроизвольному движению, карается немедленным незачетом!"
        }
    }
]

PRACTICAL_CHECKLIST: List[Dict[str, Any]] = [
    {
        "id": "chk_01",
        "category": "tayyorgarlik",
        "title": {
            "uz_latn": "O‘rindiq, suyanchiq va ko‘zgularni to‘g‘ri sozladim",
            "uz_cyrl": "Ўриндиқ, суянчиқ ва кўзгуларни тўғри созладим",
            "ru": "Отрегулировал сиденье, спинку и зеркала"
        }
    },
    {
        "id": "chk_02",
        "category": "tayyorgarlik",
        "title": {
            "uz_latn": "Dvigatelni o‘t oldirishdan oldin xavfsizlik kamarini taqdim",
            "uz_cyrl": "Двигателни ўт олдиришдан олдин хавфсизлик камарини тақдим",
            "ru": "Пристегнул ремень безопасности перед запуском"
        }
    },
    {
        "id": "chk_03",
        "category": "avtodrom",
        "title": {
            "uz_latn": "Estakadada orqaga 20 sm dan ortiq orqaga ketmasdan qo‘zg‘aldim",
            "uz_cyrl": "Эстакадада орқага 20 см дан ортиқ силжимасдан қўзғалдим",
            "ru": "Тронулся на эстакаде без отката более 20 см"
        }
    },
    {
        "id": "chk_04",
        "category": "avtodrom",
        "title": {
            "uz_latn": "Parallel parkovkada ustunchalarni bosmasdan to‘liq boksga kirdim",
            "uz_cyrl": "Параллел парковкада устунчаларни босмасдан боксга кирдим",
            "ru": "Заехал на параллельную парковку без наезда на стойки"
        }
    },
    {
        "id": "chk_05",
        "category": "avtodrom",
        "title": {
            "uz_latn": "90° boksga (garajga) orqa uzatmada to‘liq joylashdim",
            "uz_cyrl": "90° боксга (гаражга) тўлиқ жойлашдим",
            "ru": "Заехал в бокс под 90 градусов задним ходом"
        }
    },
    {
        "id": "chk_06",
        "category": "shahar",
        "title": {
            "uz_latn": "Har bir burilishdan 3-5 soniya oldin tegishli chiroqni yoqdim",
            "uz_cyrl": "Ҳар бир бурилишдан 3-5 сония олдин чироқни ёқдим",
            "ru": "Включал указатели поворота за 3-5 секунд до маневра"
        }
    },
    {
        "id": "chk_07",
        "category": "shahar",
        "title": {
            "uz_latn": "2.5 STOP belgisi oldida g‘ildiraklar to‘liq to‘xtaguncha kutdim",
            "uz_cyrl": "2.5 STOP белгиси олдида тўлиқ тўхтадим",
            "ru": "Выполнил полную остановку перед знаком 2.5 СТОП"
        }
    },
    {
        "id": "chk_08",
        "category": "shahar",
        "title": {
            "uz_latn": "Piyodalar o‘tish joyida qadam bosgan har bir piyodaga yo‘l berdim",
            "uz_cyrl": "Пиёдалар ўтиш жойида пиёдаларга тўлиқ йўл бердим",
            "ru": "Уступил дорогу пешеходам на переходе"
        }
    },
    {
        "id": "chk_09",
        "category": "shahar",
        "title": {
            "uz_latn": "Aylanma harakatda aylanadagi transportga yo‘l berib, faqat o‘ng bo‘lakdan chiqdim",
            "uz_cyrl": "Айланма ҳаракатда айланадагиларга йўл бериб, фақат ўнг бўлакдан чиқдим",
            "ru": "На круге уступил дорогу и съехал только с крайней правой полосы"
        }
    },
    {
        "id": "chk_10",
        "category": "yakunlash",
        "title": {
            "uz_latn": "Mashinani to‘xtatib, neytralga oldim va qo‘l tormozini tortdim",
            "uz_cyrl": "Машинани тўхтатиб, нейтралга олдим ва қўл тормозини тортдим",
            "ru": "Остановил авто, включил нейтраль и стояночный тормоз"
        }
    }
]

# Interactive Situational Decision Tests
PRACTICAL_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "SCEN-01",
        "title": {
            "uz_latn": "Chorrahada chapga burilish holati",
            "uz_cyrl": "Чорраҳада чапга бурилиш ҳолати",
            "ru": "Поворот налево на регулируемом перекрестке"
        },
        "situation": {
            "uz_latn": "Svetoforning asosiy yashil chirog‘i yondi. Siz chapga burilmoqchisiz. Ro‘paradan to‘g‘ri yo‘nalishda yuk avtomobili yaqinlashmoqda. Qanday harakat qilasiz?",
            "uz_cyrl": "Светофорнинг асосий яшил чироғи ёнди. Сиз чапга бурилмоқчисиз. Рўпарадан тўғри йўналишда юк автомобили яқинлашмоқда. Қандай ҳаракат қиласиз?",
            "ru": "Загорелся зеленый сигнал. Вы поворачиваете налево. Во встречном направлении прямо едет грузовой автомобиль. Ваши действия?"
        },
        "options": [
            {
                "id": 0,
                "text": {
                    "uz_latn": "Tezlikni oshirib, yuk mashinasidan oldinroq burilib olaman",
                    "uz_cyrl": "Тезликни ошириб, юк машинасидан олдинроқ бурилиб оламан",
                    "ru": "Ускорюсь и поверну быстрее грузовика"
                }
            },
            {
                "id": 1,
                "text": {
                    "uz_latn": "Chorraha markaziga chiqaman, to‘xtab yuk mashinasini o‘tkazib yuboraman va burilishni yakunlayman",
                    "uz_cyrl": "Чорраҳа марказига чиқаман, тўхтаб юк машинасини ўтказаман ва буриламан",
                    "ru": "Выеду на середину перекрестка, пропущу грузовик и завершу маневр"
                }
            },
            {
                "id": 2,
                "text": {
                    "uz_latn": "Svetofor to‘xtash chizig‘ida kutib turaman, yuk mashinasi o‘tgach harakatni boshlayman",
                    "uz_cyrl": "Светофор тўхташ чизиғида кутиб тураман",
                    "ru": "Останусь стоять у стоп-линии"
                }
            }
        ],
        "correct_option": 1,
        "explanation": {
            "uz_latn": "YHQ 102-bandiga ko‘ra: Svetoforning yashil ishorasida chapga burilishda ro‘paradan to‘g‘ri kelayotgan transportga yo‘l berish shart. Qoidalarga muvofiq, chorraha markaziga chiqib yo‘l beriladi.",
            "uz_cyrl": "ЙҲҚ 102-бандига кўра: яшил чироқда чапга бурилишда рўпарадан тўғри келаётганга йўл берилади. Чорраҳа марказига чиқиб кутилади.",
            "ru": "Пункт 102 ПДД: при повороте налево водитель обязан выехать на перекресток и уступить дорогу встречным ТС, движущимся прямо."
        }
    },
    {
        "id": "SCEN-02",
        "title": {
            "uz_latn": "Aylanma harakat chorrahasiga kirish",
            "uz_cyrl": "Айланма ҳаракат чорраҳасига кириш",
            "ru": "Въезд на кольцевой перекресток"
        },
        "situation": {
            "uz_latn": "4.3 'Aylanma harakat' belgisi o‘rnatilgan chorrahaga yaqinlashyapsiz. Aylana ichida oq yengil mashina harakatlanmoqda. Kim ustunlikka ega?",
            "uz_cyrl": "4.3 'Айланма ҳаракат' белгиси ўрнатилган чорраҳага яқинлашяпсиз. Айлана ичида оқ машина бор. Ким устунликка эга?",
            "ru": "Подъезжаете к круговому перекрестку (знак 4.3). По кольцу движется белый легковой автомобиль. У кого приоритет?"
        },
        "options": [
            {
                "id": 0,
                "text": {
                    "uz_latn": "Aylana ichidagi oq avtomobil ustunlikka ega, men yo‘l berishim shart",
                    "uz_cyrl": "Айлана ичидаги оқ автомобиль устунликка эга, мен йўл беришим шарт",
                    "ru": "У белого авто на кольце преимущество, я обязан уступить дорогу"
                }
            },
            {
                "id": 1,
                "text": {
                    "uz_latn": "Men o‘ng tomondan kirayotganim uchun menda o‘ng qo‘l qoidasi bo‘yicha ustunlik bor",
                    "uz_cyrl": "Мен ўнгдан кираётганим учун менда устунлик бор",
                    "ru": "У меня помеха справа, поэтому приоритет у меня"
                }
            }
        ],
        "correct_option": 0,
        "explanation": {
            "uz_latn": "O‘zbekiston YHQga ko‘ra 4.3 'Aylanma harakat' belgisida aylanada harakatlanayotgan transport vositasi ustunlikka ega.",
            "uz_cyrl": "Ўзбекистон ЙҲҚга кўра 4.3 белгисида айланадаги транспорт устунликка эга.",
            "ru": "Согласно ПДД Узбекистана, при въезде на перекресток с круговым движением (знак 4.3) преимущество имеют ТС, движущиеся по кольцу."
        }
    },
    {
        "id": "SCEN-03",
        "title": {
            "uz_latn": "Piyodalar o‘tish joyi va qo‘shni qatordagi to‘xtash",
            "uz_cyrl": "Пиёдалар ўтиш жойи ва қўшни қатордаги тўхташ",
            "ru": "Пешеходный переход и остановившееся авто"
        },
        "situation": {
            "uz_latn": "Tartibga solinmagan piyodalar o‘tish joyi oldida sizdan o‘ngdagi qatorda ketayotgan avtomobil to‘xtadi. Siz nima qilishingiz shart?",
            "uz_cyrl": "Пиёдалар ўтиш жойи олдида ўнгдаги машина тўхтади. Сиз нима қилишингиз шарт?",
            "ru": "Перед нерегулируемым пешеходным переходом в соседней правой полосе остановился автомобиль. Что вы обязаны сделать?"
        },
        "options": [
            {
                "id": 0,
                "text": {
                    "uz_latn": "Tezlikni pasaytirmasdan o‘tib ketaman, chunki mening bo‘lagimda piyoda ko‘rinmayapti",
                    "uz_cyrl": "Тезликни камайтирмасдан ўтиб кетаман",
                    "ru": "Проеду без снижения скорости, так как на моей полосе никого не видно"
                }
            },
            {
                "id": 1,
                "text": {
                    "uz_latn": "Faqat signal berib o‘taman",
                    "uz_cyrl": "Фақат сигнал бериб ўтаман",
                    "ru": "Подам звуковой сигнал и продолжу движение"
                }
            },
            {
                "id": 2,
                "text": {
                    "uz_latn": "To‘xtashim shart va o‘tish joyida piyodalar yo‘qligiga to‘liq ishonch hosil qilgach harakatni davom ettiraman",
                    "uz_cyrl": "Тўхташим шарт ва пиёда йўқлигига ишонч ҳосил қилгач давом этаман",
                    "ru": "Обязан остановиться и продолжить движение только убедившись в отсутствии пешеходов"
                }
            }
        ],
        "correct_option": 2,
        "explanation": {
            "uz_latn": "YHQ 113-bandiga ko‘ra: Piyodalar o‘tish joyi oldida transport to‘xtagan bo‘lsa, boshqa bo‘lakdagi haydovchilar ham to‘xtashi va piyoda yo‘qligiga ishonch hosil qilgandan keyingina harakatlanishi shart.",
            "uz_cyrl": "ЙҲҚ 113-бандига кўра: пиёдалар ўтиш жойи олдида қўшни машина тўхтаса, сиз ҳам тўхташингиз шарт.",
            "ru": "Пункт 113 ПДД: если перед нерегулируемым пешеходным переходом остановилось ТС, водители других полос также обязаны остановиться."
        }
    }
]
