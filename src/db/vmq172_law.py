"""
Single Source of Truth for Republic of Uzbekistan VMQ No. 172 (12.04.2022,
including VMQ No. 140 60 km/h amendment and Chapter 17-1 BRT rules).

Used across:
- src/bot/category_localization.py
- src/verification_engine.py
- src/db/reference_catalog.py
- src/db/provenance_classifier.py
- src/ai/tools.py

Zero Latin characters are permitted in uz_cyrl or ru strings.
"""

from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple


CORPUS_JSON_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "vmq172_corpus.json"


# Official VMQ 172 Chapters (1..29 + 17-1 BRT + Annexes 1..4)
VMQ172_CHAPTERS_DATA: List[Dict[str, Any]] = [
    {
        "code": "1",
        "chapter_num": 1,
        "uz_latn": "Umumiy qoidalar",
        "uz_cyrl": "Умумий қоидалар",
        "ru": "Общие положения",
        "summary_uz": "O‘ng tomonlama harakat, asosiy atamalar (6-band) va Qoidalarning amal qilish doirasi.",
        "summary_uz_cyrl": "Ўнг томонлама ҳаракат, асосий атамалар (6-банд) ва Қоидаларнинг амал қилиш доираси.",
        "summary_ru": "Правостороннее движение, основные термины (п. 6) и область действия ПДД.",
        "category_ids": [39, 24],
    },
    {
        "code": "2",
        "chapter_num": 2,
        "uz_latn": "Haydovchilarning umumiy vazifalari",
        "uz_cyrl": "Ҳайдовчиларнинг умумий вазифалари",
        "ru": "Общие обязанности водителей",
        "summary_uz": "Guvohnoma va majburiy hujjatlar, xavfsizlik kamari, motoshlem va mastlik taqiqi.",
        "summary_uz_cyrl": "Гувоҳнома ва мажбурий ҳужжатлар, хавфсизлик камари, мотошлем ва мастлик тақиқи.",
        "summary_ru": "Обязательные документы, ремень безопасности, мотошлем и запрет вождения в опьянении.",
        "category_ids": [16, 15],
    },
    {
        "code": "3",
        "chapter_num": 3,
        "uz_latn": "Yo‘l-transport hodisasi sodir bo‘lganda haydovchining majburiyatlari",
        "uz_cyrl": "Йўл-транспорт ҳодисаси содир бўлганда ҳайдовчининг мажбуриятлари",
        "ru": "Обязанности водителя при дорожно-транспортном происшествии",
        "summary_uz": "YTH joyida to‘xtash, avariya ishorasini yoqish, jabrlanganlarga yordam va DYHXXga xabar berish.",
        "summary_uz_cyrl": "ЙТҲ жойида тўхташ, авария ишорасини ёқиш, жабрланганларга ёрдам ва ДЙҲХХга хабар бериш.",
        "summary_ru": "Остановка при ДТП, аварийная сигнализация, первая помощь и сообщение в ГСБДД.",
        "category_ids": [16, 9, 15],
    },
    {
        "code": "4",
        "chapter_num": 4,
        "uz_latn": "Piyodalarning majburiyatlari",
        "uz_cyrl": "Пиёдаларнинг мажбуриятлари",
        "ru": "Обязанности пешеходов",
        "summary_uz": "Trotuar va piyodalar yo‘lkasidan yurish, yo‘lni belgilangan joydan kesib o‘tish qoidalari.",
        "summary_uz_cyrl": "Тротуар ва пиёдалар йўлкасидан юриш, йўлни белгиланган жойдан кесиб ўтиш қоидалари.",
        "summary_ru": "Движение по тротуарам и правила перехода проезжей части пешеходами.",
        "category_ids": [28],
    },
    {
        "code": "5",
        "chapter_num": 5,
        "uz_latn": "Yo‘lovchilarning majburiyatlari",
        "uz_cyrl": "Йўловчиларнинг мажбуриятлари",
        "ru": "Обязанности пассажиров",
        "summary_uz": "Transportga chiqish-tushish, xavfsizlik kamarini taqish va haydovchini chalg‘itmaslik.",
        "summary_uz_cyrl": "Транспортга чиқиш-тушиш, хавфсизлик камарини тақиш ва ҳайдовчини чалғитмаслик.",
        "summary_ru": "Посадка и высадка, пристёгивание ремнём и запрет отвлечения водителя.",
        "category_ids": [40, 16],
    },
    {
        "code": "6",
        "chapter_num": 6,
        "uz_latn": "Maxsus transport vositalarining imtiyozlari",
        "uz_cyrl": "Махсус транспорт воситаларининг имтиёзлари",
        "ru": "Приоритет специальных транспортных средств",
        "summary_uz": "Ko‘k/qizil mayoqcha va maxsus tovushli transportlarga yo‘l berish, sariq mayoqcha qoidalari.",
        "summary_uz_cyrl": "Кўк/қизил маёқча ва махсус товушли транспортларга йўл бериш, сариқ маёқча қоидалари.",
        "summary_ru": "Предоставление преимущества ТС с проблесковыми маячками и звуковым сигналом.",
        "category_ids": [11],
    },
    {
        "code": "7",
        "chapter_num": 7,
        "uz_latn": "Svetofor va tartibga soluvchining ishoralari",
        "uz_cyrl": "Светофор ва тартибга солувчининг ишоралари",
        "ru": "Сигналы светофора и регулировщика",
        "summary_uz": "Svetofor ranglari, qo‘shimcha tarmoq, tramvay svetofori va tartibga soluvchining ishoralari.",
        "summary_uz_cyrl": "Светофор ранглари, қўшимча тармоқ, трамвай светофори ва тартибга солувчининг ишоралари.",
        "summary_ru": "Значения сигналов светофора, дополнительных секций и жестов регулировщика.",
        "category_ids": [34, 5],
    },
    {
        "code": "8",
        "chapter_num": 8,
        "uz_latn": "Ogohlantiruvchi va avariya (xavf-xatar) ishoralari",
        "uz_cyrl": "Огоҳлантирувчи ва авария (хавф-хатар) ишоралари",
        "ru": "Предупредительные и аварийные сигналы (опасности)",
        "summary_uz": "Burilish ko‘rsatkichlari, qo‘l bilan ishora berish, avariya chirog‘i va avariya belgisi (15 m / 30 m).",
        "summary_uz_cyrl": "Бурилиш кўрсаткичлари, қўл билан ишора бериш, авария чироғи ва авария белгиси (15 м / 30 м).",
        "summary_ru": "Указатели поворота, сигналы рукой, аварийная сигнализация и знак аварийной остановки (15 м / 30 м).",
        "category_ids": [29],
    },
    {
        "code": "9",
        "chapter_num": 9,
        "uz_latn": "Harakatlanishni boshlash, manyovr qilish",
        "uz_cyrl": "Ҳаракатланишни бошлаш, манёвр қилиш",
        "ru": "Начало движения, маневрирование",
        "summary_uz": "Qayta tizilish, chekka bo‘lakdan burilish, aylana harakat va orqaga harakatlanish qoidalari.",
        "summary_uz_cyrl": "Қайта тизилиш, чекка бўлакдан бурилиш, айлана ҳаракат ва орқага ҳаракатланиш қоидалари.",
        "summary_ru": "Перестроение, крайнее положение при повороте, круговое движение и движение задним ходом.",
        "category_ids": [8],
    },
    {
        "code": "10",
        "chapter_num": 10,
        "uz_latn": "Yo‘lning qatnov qismida transport vositalarining joylashuvi",
        "uz_cyrl": "Йўлнинг қатнов қисмида транспорт воситаларининг жойлашуви",
        "ru": "Расположение транспортных средств на проезжей части",
        "summary_uz": "Bo‘laklar bo‘yicha joylashuv, o‘ng chetga yaqin yurish, tramvay izi va xavfsiz oraliq masofa.",
        "summary_uz_cyrl": "Бўлаклар бўйича жойлашув, ўнг четга яқин юриш, трамвай изи ва хавфсиз оралиқ масофа.",
        "summary_ru": "Выбор полосы движения, расположение грузовых ТС, трамвайные пути и безопасная дистанция.",
        "category_ids": [14],
    },
    {
        "code": "11",
        "chapter_num": 11,
        "uz_latn": "Harakatlanish tezligi",
        "uz_cyrl": "Ҳаракатланиш тезлиги",
        "ru": "Скорость движения",
        "summary_uz": "Aholi punktlarida 60/70 km/soat (VMQ 140), maktablar oldida 30 km/soat, tashqarida 70–100 km/soat.",
        "summary_uz_cyrl": "Аҳоли пунктларида 60/70 км/соат (ВМҚ 140), мактаблар олдида 30 км/соат, ташқарида 70–100 км/соат.",
        "summary_ru": "Ограничения скорости: 60/70 км/ч в городах и населённых пунктах, 30 км/ч у школ, 70–100 км/ч за городом.",
        "category_ids": [26],
    },
    {
        "code": "12",
        "chapter_num": 12,
        "uz_latn": "Quvib o‘tish",
        "uz_cyrl": "Қувиб ўтиш",
        "ru": "Обгон",
        "summary_uz": "Quvib o‘tishni boshlash shartlari, qarama-qarshi bo‘lakka chiqish taqiqlangan joylar.",
        "summary_uz_cyrl": "Қувиб ўтишни бошлаш шартлари, қарама-қарши бўлакка чиқиш тақиқланган жойлар.",
        "summary_ru": "Условия начала обгона, перечень участков, где обгон категорически запрещён.",
        "category_ids": [33],
    },
    {
        "code": "13",
        "chapter_num": 13,
        "uz_latn": "To‘xtash va to‘xtab turish",
        "uz_cyrl": "Тўхташ ва тўхтаб туриш",
        "ru": "Остановка и стоянка",
        "summary_uz": "Piyodalar o‘tish joyidan 5 m, chorrahadan 30 m/5 m, bekatlardan 15 m masofa va taqiqlar.",
        "summary_uz_cyrl": "Пиёдалар ўтиш жойидан 5 м, чорраҳадан 30 м/5 м, бекатлардан 15 м масофа ва тақиқлар.",
        "summary_ru": "Минимальные расстояния (5 м, 15 м, 30 м) и запреты остановки и стоянки.",
        "category_ids": [7],
    },
    {
        "code": "14",
        "chapter_num": 14,
        "uz_latn": "Chorrahalarda harakatlanish",
        "uz_cyrl": "Чорраҳаларда ҳаракатланиш",
        "ru": "Проезд перекрестков",
        "summary_uz": "Chorrahalardan o‘tishning umumiy qoidalari, tirband chorrahaga chiqmaslik va piyoda/velosipedga yo‘l berish.",
        "summary_uz_cyrl": "Чорраҳалардан ўтишнинг умумий қоидалари, тирбанд чорраҳага чиқмаслик ва пиёда/велосипедга йўл бериш.",
        "summary_ru": "Общие правила проезда перекрёстков, уступка пешеходам и запрет выезда на затор.",
        "category_ids": [25],
    },
    {
        "code": "15",
        "chapter_num": 15,
        "uz_latn": "Tartibga solingan chorrahalar",
        "uz_cyrl": "Тартибга солинган чорраҳалар",
        "ru": "Регулируемые перекрестки",
        "summary_uz": "Chapga burilish/qayrilishda qarama-qarshiga yo‘l berish, qo‘shimcha sektsiya va harakatni yakunlash.",
        "summary_uz_cyrl": "Чапга бурилиш/қайрилишда қарама-қаршига йўл бериш, қўшимча секция ва ҳаракатни якунлаш.",
        "summary_ru": "Проезд по сигналам светофора, поворот по стрелке и завершение манёвра.",
        "category_ids": [6],
    },
    {
        "code": "16",
        "chapter_num": 16,
        "uz_latn": "Tartibga solinmagan chorrahalar",
        "uz_cyrl": "Тартибга солинмаган чорраҳалар",
        "ru": "Нерегулируемые перекрестки",
        "summary_uz": "Asosiy va ikkinchi darajali yo‘llar kesishuvi, teng ahamiyatli yo‘llarda «o‘ng qo‘l» qoidasi.",
        "summary_uz_cyrl": "Асосий ва иккинчи даражали йўллар кесишуви, тенг аҳамиятли йўлларда «ўнг қўл» қоидаси.",
        "summary_ru": "Главная и второстепенная дороги, правило «помехи справа» на равнозначных перекрёстках.",
        "category_ids": [4, 31, 38],
    },
    {
        "code": "17",
        "chapter_num": 17,
        "uz_latn": "Piyodalarning o‘tish joylari va yo‘nalishli transport vositalarining bekatlari",
        "uz_cyrl": "Пиёдаларнинг ўтиш жойлари ва йўналишли транспорт воситаларининг бекатлари",
        "ru": "Пешеходные переходы и остановки маршрутных транспортных средств",
        "summary_uz": "Tartibga solinmagan o‘tish joyida piyodalarga yo‘l berish va bekatdagi tramvay yo‘lovchilariga to‘xtash.",
        "summary_uz_cyrl": "Тартибга солинмаган ўтиш жойида пиёдаларга йўл бериш ва бекатдаги трамвай йўловчиларига тўхташ.",
        "summary_ru": "Преимущество пешеходов на переходах и остановка перед трамваем на посадке/высадке.",
        "category_ids": [30],
    },
    {
        "code": "17-1",
        "chapter_num": 17,
        "uz_latn": "Yo‘nalishli transport vositalari uchun alohida ajratilgan tasmasi bor yo‘l orqali harakatlanish",
        "uz_cyrl": "Йўналишли транспорт воситалари учун алоҳида ажратилган тасмаси бор йўл орқали ҳаракатланиш",
        "ru": "Движение по дороге с полосой, выделенной для маршрутных транспортных средств",
        "summary_uz": "Maxsus jamoat transporti tasmasi (A tasma) bo‘ylab harakatlanish, burilish va favqulodda to‘xtash cheklovlari.",
        "summary_uz_cyrl": "Махсус жамоат транспорти тасмаси (А тасма) бўйлаб ҳаракатланиш, бурилиш ва фавқулодда тўхташ чекловлари.",
        "summary_ru": "Режим движения по выделенной автобусной полосе (полоса А) и правила выезда при повороте.",
        "category_ids": [19, 30],
    },
    {
        "code": "18",
        "chapter_num": 18,
        "uz_latn": "Temir yo‘l kesishmalari orqali harakatlanish",
        "uz_cyrl": "Темир йўл кесишмалари орқали ҳаракатланиш",
        "ru": "Движение через железнодорожные пути",
        "summary_uz": "Kesishma oldida 5 m / 10 m to‘xtash, shlagbaum yopiq holatda kirish taqiqi va majburiy to‘xtash.",
        "summary_uz_cyrl": "Кесишма олдида 5 м / 10 м тўхташ, шлагбаум ёпиқ ҳолатда кириш тақиқи ва мажбурий тўхташ.",
        "summary_ru": "Остановка за 5 м / 10 м до рельса, запрет выезда при закрытом шлагбауме или пробке.",
        "category_ids": [36],
    },
    {
        "code": "19",
        "chapter_num": 19,
        "uz_latn": "Avtomagistrallarda harakatlanish",
        "uz_cyrl": "Автомагистралларда ҳаракатланиш",
        "ru": "Движение по автомагистралям",
        "summary_uz": "Tezlik 40 km/soatdan past transportlar, piyodalar, ortga qaytish va to‘xtash taqiqlari.",
        "summary_uz_cyrl": "Тезлик 40 км/соатдан паст транспортлар, пиёдалар, ортга қайтиш ва тўхташ тақиқлари.",
        "summary_ru": "Запреты на автомагистрали: тихоходные ТС, разворот в разрывах, учебная езда и стоянка.",
        "category_ids": [13],
    },
    {
        "code": "20",
        "chapter_num": 20,
        "uz_latn": "Turar joy dahalarida harakatlanish",
        "uz_cyrl": "Турар жой даҳаларида ҳаракатланиш",
        "ru": "Движение в жилых зонах",
        "summary_uz": "Piyodalar ustunligi, maksimal 20 km/soat tezlik, o‘tib ketish va yuk avtomobillari turishi taqiqi.",
        "summary_uz_cyrl": "Пиёдалар устунлиги, максимал 20 км/соат тезлик, ўтиб кетиш ва юк автомобиллари туриши тақиқи.",
        "summary_ru": "Приоритет пешеходов, ограничение 20 км/ч, запрет сквозного проезда и учебной езды.",
        "category_ids": [35],
    },
    {
        "code": "21",
        "chapter_num": 21,
        "uz_latn": "Tik balandlik va nishabliklarda harakatlanish",
        "uz_cyrl": "Тик баландлик ва нишабликларда ҳаракатланиш",
        "ru": "Движение на крутых подъемах и спусках",
        "summary_uz": "1.13/1.14 belgili qiyaliklardagi qarama-qarshi uchrashuvda nishablikka tushayotgan haydovchi yo‘l berishi.",
        "summary_uz_cyrl": "1.13/1.14 белгили қияликлардаги қарама-қарши учрашувда нишабликка тушаётган ҳайдовчи йўл бериши.",
        "summary_ru": "При встречном разъезде на крутых спусках и подъёмах уступает водитель, движущийся на спуск.",
        "category_ids": [14, 17],
    },
    {
        "code": "22",
        "chapter_num": 22,
        "uz_latn": "Yo‘nalishli transport vositalarining imtiyozlari",
        "uz_cyrl": "Йўналишли транспорт воситаларининг имтиёзлари",
        "ru": "Приоритет маршрутных транспортных средств",
        "summary_uz": "Aholi punktlarida belgilangan bekatdan qo‘zg‘alayotgan avtobus va trolleybusga yo‘l berish, tramvay ustunligi.",
        "summary_uz_cyrl": "Аҳоли пунктларида белгиланган бекатдан қўзғалаётган автобус ва троллейбусга йўл бериш, трамвай устунлиги.",
        "summary_ru": "Уступка автобусам/троллейбусам при отъезде от остановки и приоритет трамвая на перекрёстках.",
        "category_ids": [19],
    },
    {
        "code": "23",
        "chapter_num": 23,
        "uz_latn": "Tashqi yoritish asboblaridan foydalanish",
        "uz_cyrl": "Ташқи ёритиш асбобларидан фойдаланиш",
        "ru": "Пользование внешними световыми приборами",
        "summary_uz": "Qorong‘uda va ko‘rinish yetarli bo‘lmaganda uzoq/yaqin chiroqlar, tuman chirog‘i va kunduzgi chiroq.",
        "summary_uz_cyrl": "Қоронғуда ва кўриниш етарли бўлмаганда узоқ/яқин чироқлар, туман чироғи ва кундузги чироқ.",
        "summary_ru": "Ближний/дальний свет фар, переключение за 150 м, противотуманные фары и освещение в тёмное время.",
        "category_ids": [22],
    },
    {
        "code": "24",
        "chapter_num": 24,
        "uz_latn": "Mexanik transport vositalarini shatakka olish",
        "uz_cyrl": "Механик транспорт воситаларини шатакка олиш",
        "ru": "Буксировка механических транспортных средств",
        "summary_uz": "Egiluvchan (4–6 m), qattiq (4 m gacha) ulagichlar, qisman yuklab shatakka olish va taqiqlar.",
        "summary_uz_cyrl": "Эгилувчан (4–6 м), қаттиқ (4 м гача) улагичлар, қисман юклаб шатакка олиш ва тақиқлар.",
        "summary_ru": "Гибкая (4–6 м) и жёсткая (до 4 м) сцепка, частичная погрузка и запреты буксировки.",
        "category_ids": [32],
    },
    {
        "code": "25",
        "chapter_num": 25,
        "uz_latn": "Transport vositalarini boshqarishni o‘rgatish",
        "uz_cyrl": "Транспорт воситаларини бошқаришни ўргатиш",
        "ru": "Обучение вождению транспортных средств",
        "summary_uz": "O‘quv transporti talablari, instruktor malakasi va o‘quvchi yoshi/salomatlik talablari.",
        "summary_uz_cyrl": "Ўқув транспорти талаблари, инструктор малакаси ва ўқувчи ёши/саломатлик талаблари.",
        "summary_ru": "Требования к учебным автомобилям, инструкторам и начальной езде на автодроме.",
        "category_ids": [37],
    },
    {
        "code": "26",
        "chapter_num": 26,
        "uz_latn": "Odam tashish",
        "uz_cyrl": "Одам ташиш",
        "ru": "Перевозка людей",
        "summary_uz": "Avtobus va yuk avtomobili bortida odam tashish, bolalar o‘rindig‘i va maksimal son cheklovlari.",
        "summary_uz_cyrl": "Автобус ва юк автомобили бортида одам ташиш, болалар ўриндиғи ва максимал сон чекловлари.",
        "summary_ru": "Перевозка пассажиров в автобусе и кузове грузового автомобиля, детские удерживающие устройства.",
        "category_ids": [40],
    },
    {
        "code": "27",
        "chapter_num": 27,
        "uz_latn": "Yuk tashish",
        "uz_cyrl": "Юк ташиш",
        "ru": "Перевозка грузов",
        "summary_uz": "Yukni mahkamlash, oldi-orqadan 1 m / yondan 0,4 m chiqqan gabarit yuklarni belgilash.",
        "summary_uz_cyrl": "Юкни маҳкамлаш, олди-орқадан 1 м / ёндан 0,4 м чиққан габарит юкларни белгилаш.",
        "summary_ru": "Размещение и крепление груза, обозначение выступов >1 м спереди/сзади или >0,4 м сбоку.",
        "category_ids": [20],
    },
    {
        "code": "28",
        "chapter_num": 28,
        "uz_latn": "Velosiped, moped va aravalar harakatlanishiga, shuningdek, hayvonlarni haydab o‘tishga doir qo‘shimcha talablar",
        "uz_cyrl": "Велосипед, мопед ва аравалар ҳаракатланишига, шунингдек, ҳайвонларни ҳайдаб ўтишга доир қўшимча талаблар",
        "ru": "Дополнительные требования к движению велосипедов, мопедов и гужевых повозок, а также прогону животных",
        "summary_uz": "Velosiped/moped haydovchilari yosh chegarasi (14/16), burilish va podani haydab o‘tish tartibi.",
        "summary_uz_cyrl": "Велосипед/мопед ҳайдовчилари ёш чегараси (14/16), бурилиш ва подани ҳайдаб ўтиш тартиби.",
        "summary_ru": "Возрастной ценз (14/16 лет), движение по правому краю и правила прогона скота.",
        "category_ids": [27],
    },
    {
        "code": "29",
        "chapter_num": 29,
        "uz_latn": "Mansabdor shaxslarning va fuqarolarning yo‘l harakati xavfsizligini ta’minlash, transport vositalaridan foydalanishga ruxsat berish bo‘yicha majburiyatlari",
        "uz_cyrl": "Мансабдор шахсларнинг ва фуқароларнинг йўл ҳаракати хавфсизлигини таъминлаш, транспорт воситаларидан фойдаланишга рухсат бериш бўйича мажбуриятлари",
        "ru": "Обязанности должностных лиц и граждан по обеспечению безопасности дорожного движения, допуску транспортных средств к эксплуатации",
        "summary_uz": "Ro‘yxatdan o‘tkazish, texnik ko‘rik, taniqlik belgilari va nogironligi bor haydovchilar imtiyozlari.",
        "summary_uz_cyrl": "Рўйхатдан ўтказиш, техник кўрик, таниқлик белгилари ва ногиронлиги бор ҳайдовчилар имтиёзлари.",
        "summary_ru": "Регистрация ТС, техосмотр, опознавательные знаки и допуск транспортных средств.",
        "category_ids": [10, 3],
    },
    {
        "code": "annex-1",
        "chapter_num": 101,
        "uz_latn": "1-ilova. Yo‘l belgilari",
        "uz_cyrl": "1-илова. Йўл белгилари",
        "ru": "Приложение 1. Дорожные знаки",
        "summary_uz": "Ogohlantiruvchi, imtiyoz, taqiqlovchi, buyuruvchi, axborot-ko‘rsatkich, servis va qo‘shimcha axborot belgilari.",
        "summary_uz_cyrl": "Огоҳлантирувчи, имтиёз, тақиқловчи, буюрувчи, ахборот-кўрсаткич, сервис ва қўшимча ахборот белгилари.",
        "summary_ru": "Все группы дорожных знаков и табличек по ПДД РУз.",
        "category_ids": [21, 17, 23, 2, 18, 1],
    },
    {
        "code": "annex-2",
        "chapter_num": 102,
        "uz_latn": "2-ilova. Yo‘l chiziqlari",
        "uz_cyrl": "2-илова. Йўл чизиқлари",
        "ru": "Приложение 2. Дорожная разметка",
        "summary_uz": "Yotiq (1.1–1.30) va tik (2.1–2.7) yo‘l chiziqlari hamda ularni kesib o‘tish qoidalari.",
        "summary_uz_cyrl": "Ётиқ (1.1–1.30) ва тик (2.1–2.7) йўл чизиқлари ҳамда уларни кесиб ўтиш қоидалари.",
        "summary_ru": "Горизонтальная (1.1–1.30) и вертикальная (2.1–2.7) дорожная разметка.",
        "category_ids": [12, 42],
    },
    {
        "code": "annex-3",
        "chapter_num": 103,
        "uz_latn": "3-ilova. Transport vositalaridan foydalanishni taqiqlovchi shartlar",
        "uz_cyrl": "3-илова. Транспорт воситаларидан фойдаланишни тақиқловчи шартлар",
        "ru": "Приложение 3. Условия, при которых запрещается эксплуатация транспортных средств",
        "summary_uz": "Tormoz, rul boshqaruvi lyufti, tashqi yoritgichlar, shina protektori (1,6 mm) va dvigatel nosozliklari.",
        "summary_uz_cyrl": "Тормоз, руль бошқаруви люфти, ташқи ёритгичлар, шина протектори (1,6 мм) ва двигатель носозликлари.",
        "summary_ru": "Технические неисправности тормозов, рулевого управления (люфт), световых приборов и шин.",
        "category_ids": [3],
    },
    {
        "code": "annex-4",
        "chapter_num": 104,
        "uz_latn": "4-ilova. Xavflilik belgilari",
        "uz_cyrl": "4-илова. Хавфлилик белгилари",
        "ru": "Приложение 4. Знаки опасности",
        "summary_uz": "Xavfli yuklarni tashuvchi transport vositalarining maxsus ogohlantirish va markirovka belgilari.",
        "summary_uz_cyrl": "Хавфли юкларни ташувчи транспорт воситаларининг махсус огоҳлантириш ва маркировка белгилари.",
        "summary_ru": "Знаки опасности и маркировка при перевозке опасных грузов.",
        "category_ids": [20],
    },
]

CHAPTER_BY_CODE: Dict[str, Dict[str, Any]] = {ch["code"]: ch for ch in VMQ172_CHAPTERS_DATA}

NUMBERED_CHAPTERS_UZ_LATN: Dict[int, str] = {
    ch["chapter_num"]: ch["uz_latn"]
    for ch in VMQ172_CHAPTERS_DATA
    if ch["code"].isdigit()
}
NUMBERED_CHAPTERS_UZ_CYRL: Dict[int, str] = {
    ch["chapter_num"]: ch["uz_cyrl"]
    for ch in VMQ172_CHAPTERS_DATA
    if ch["code"].isdigit()
}
NUMBERED_CHAPTERS_RU: Dict[int, str] = {
    ch["chapter_num"]: ch["ru"]
    for ch in VMQ172_CHAPTERS_DATA
    if ch["code"].isdigit()
}


def get_chapter_title(chapter_code: str | int, lang: str = "uz_latn") -> str:
    """Return canonical official VMQ 172 chapter title by code ('1'..'29', '17-1', 'annex-1'..'annex-4')."""
    code_str = str(chapter_code).strip().replace("¹", "-1")
    entry = CHAPTER_BY_CODE.get(code_str)
    if not entry:
        if lang == "ru":
            return f"Глава {code_str}"
        if lang == "uz_cyrl":
            return f"{code_str}-боб"
        return f"{code_str}-bob"
    key = "ru" if lang == "ru" else ("uz_cyrl" if lang == "uz_cyrl" else "uz_latn")
    return entry[key]


@lru_cache(maxsize=1)
def _load_corpus() -> Dict[str, Any]:
    if not CORPUS_JSON_PATH.exists():
        return {"chapters": [], "articles": []}
    with open(CORPUS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _clause_index() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    corpus = _load_corpus()
    clauses: Dict[str, Dict[str, Any]] = {}
    signs: Dict[str, Dict[str, Any]] = {}
    markings: Dict[str, Dict[str, Any]] = {}
    for art in corpus.get("articles", []):
        etype = art.get("entry_type")
        cnum = art.get("clause_num")
        if not cnum:
            continue
        if etype == "clause":
            clauses[cnum] = art
        elif etype == "sign":
            signs[cnum] = art
        elif etype == "marking":
            markings[cnum] = art
    return clauses, signs, markings


def find_clause(clause_num: str | int) -> Optional[Dict[str, Any]]:
    """Lookup an exact official VMQ 172 clause ('78', '12-1', '12¹', '115-1', '115¹', etc.)."""
    norm = str(clause_num).strip().replace("¹", "-1").replace("²", "-2").replace("³", "-3")
    clauses, _, _ = _clause_index()
    return clauses.get(norm)


def find_sign_or_marking(code: str, kind: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Lookup an exact official sign (Annex 1) or marking (Annex 2)."""
    norm = str(code).strip()
    _, signs, markings = _clause_index()
    if kind == "marking":
        return markings.get(norm)
    if kind == "sign":
        return signs.get(norm)
    return signs.get(norm) or markings.get(norm)


def get_road_signs_canonical_map() -> Dict[str, Tuple[str, str]]:
    """Return {code: (title_uz, title_ru)} with official Annex 1 signs taking precedence over Annex 2 markings."""
    _, signs, markings = _clause_index()
    out: Dict[str, Tuple[str, str]] = {}
    for code, item in {**markings, **signs}.items():
        uz = re.sub(rf"^{re.escape(code)}\s*", "", item.get("title_uz", "")).strip(" .«»")
        ru = re.sub(rf"^{re.escape(code)}\s*", "", item.get("title_ru", "")).strip(" .«»")
        if len(re.sub(r"[^A-Za-z\u0400-\u04FF]", "", uz)) >= 3 and len(re.sub(r"[^A-Za-z\u0400-\u04FF]", "", ru)) >= 3:
            out[code] = (uz, ru)
    return out
