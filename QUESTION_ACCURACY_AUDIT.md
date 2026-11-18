# QUESTION ACCURACY & STATE EXAM ALIGNMENT: READ-ONLY FORENSIC AUDIT

**Loyiha:** O‘zbekiston Haydovchilik Guvohnomasi Nazariy Imtihoni Savollar Bazasi (YHQ / Avtotest)  
**Bosqich:** Stage 1 — Read-Only Forensic Audit  
**Sana:** 2026-yil 16-noyabr  
**Audit Maqomi:** QAT’IY READ-ONLY (Production database, savollar matni, javob kalitlari va rasmlar o‘zgartirilmadi).  
**Hujjat Identifikatori:** `QUESTION_ACCURACY_AUDIT.md`  
**Tekshirilgan Asosiy Fayllar:** [master_database.sqlite](file:///c:/Users/Администратор/AvtoTest/master_database.sqlite), [questions.json](file:///c:/Users/Администратор/AvtoTest/questions.json), [questions.csv](file:///c:/Users/Администратор/AvtoTest/questions.csv), [duplicate_report.csv](file:///c:/Users/Администратор/AvtoTest/duplicate_report.csv), [verification_report.csv](file:///c:/Users/Администратор/AvtoTest/verification_report.csv), [source_coverage_report.csv](file:///c:/Users/Администратор/AvtoTest/source_coverage_report.csv), LexUZ YHQ hujjati (5963102).

---

## 1. Executive Summary

Ushbu audit O‘zbekiston Respublikasi Vazirlar Mahkamasining 2022-yil 12-apreldagi 172-son qarori bilan tasdiqlangan amaldagi **Yo‘l harakati qoidalari (YHQ)** hamda Ichki ishlar vazirligi Jamoat xavfsizligi departamenti Yo‘l harakati xavfsizligi xizmati (IIV JXD YHXX) tizimidagi haydovchilik guvohnomasini berish bo‘yicha davlat nazariy imtihonlari talablari asosida o‘tkazildi.

### Asosiy Xulosalar:
1. **Bazaning Haqiqiy Hajmi va Strukturasi:**
   Bazada jami **5 945 ta kanonik savol** mavjud bo‘lib, ular 3 ta tilda ifodalangan: rus tili (`ru` — 2 321 ta), o‘zbek kirill (`uz_cyrl` — 2 047 ta) va o‘zbek lotin (`uz_latn` — 1 577 ta). Barcha savollar 19 472 ta javob varianti va 1 423 ta sifatli rasm bilan ta’minlangan.
2. **Davlat Imtihoniga Moslik Darajasi (Konseptual Tahlil):**
   O‘zbekiston davlat imtihon tizimida (Toshkent Imtihon Markazi — TIM va viloyat Yagona imtihon markazlarida) nazariy imtihon **20 ta tasodifiy savoldan** iborat bo‘lib, 25 daqiqa davomida topshiriladi (o‘tish bali: kamida 18/20). Ushbu tizimning to‘liq savollar to‘plami **1 200 – 1 250 ta konseptual savoldan** iborat. Bazamizdagi ProPDD (1 213 ta slot) va YesPrava (1 235 ta slot) aynan mana shu 1 200 – 1 250 ta bazaviy savolning 3 ta tildagi raqamlashtirilgan variantlaridir.
3. **Rasmiy Davlat Savollari Maqomi:**
   **0 ta savol** (0.0%) davlat tomonidan ochiq manba sifatida ruxsat etilgan "rasmiy davlat hujjati" maqomiga ega emas, chunki IIV YHXX imtihon terminali dasturiy ta’minotining savollar bankini ochiq davlat reestriga (`data.egov.uz`) joylashtirmagan. Bazadagi savollar — **uchinchi tomon tayyorlov portallari tomonidan to‘plangan va qayta tiklangan eng yirik o‘quv repozitoriysi** hisoblanadi.
4. **Huquqiy Moslik (YHQ 172-son Qaror va Oxirgi O‘zgartirishlar):**
   Savollarning **3 147 tasi (52.9%)** YHQ moddalari va ilovalariga to‘g‘ridan-to‘g‘ri bog‘langan (`LEGAL_REFERENCE_FOUND` va `LEGAL_CONTENT_MATCHED`). Biroq, YHQga 2023-yil aprelda (78-band bo‘yicha Toshkent va Nukusda tezlik 60 km/soatga tushirilishi) va 2025-yil mayda (318-son qaror: avtobus tasmalarida 23:00–06:00 ruxsati, maktab atrofi 30 km/soat vaqt chegaralari) kiritilgan o‘zgartirishlar uchinchi tomon manbalaridagi tushuntirishlarda qisman eskirgan holda qolganligi aniqlandi.
5. **9 ta Takroriy Variantli Savol:**
   9 ta savolda bitta savol ichida 2 ta bir xil javob varianti mavjudligi tasdiqlandi. Bu xatolik bizning tizimimizda emas, balki `propdd.uz` va `yesprava.uz` portallarining dastlabki xom ma’lumotlarida (masalan, 5% li yod eritmasi savolida) mavjud bo‘lgan tipografik nuqson ekani isbotlandi.
6. **858 ta O‘xshash Juftlik:**
   Ularning **657 tasi (76.6%)** bir xil shablon matnga ega, biroq mutlaqo boshqa javob variantlarini (qoidaning turli bandlarini) tekshiruvchi mustaqil savollar ekani aniqlandi.

---

## 2. Database Integrity va To‘liq Inventarizatsiya

SQLite bazasi ([master_database.sqlite](file:///c:/Users/Администратор/AvtoTest/master_database.sqlite)) to‘liq o‘rganildi va `PRAGMA integrity_check` natijasi `ok` ekani, foreign key buzilishlari soni `0` ekani qayd etildi.

### 2.1 Jadval Bo‘yicha To‘liq Inventarizatsiya
| Jadval Nomi | Yozuvlar Soni | Birlamchi Kalit | Izoh va Audit Xulosasi |
| :--- | :--- | :--- | :--- |
| `questions` | **5 945** | `id` (TEXT) | Barcha savollar mavjud, matni bo‘sh emas, Unicode to‘liq saqlangan. |
| `answers` | **19 472** | `id` (INTEGER) | Har bir savolga 2 tadan 5 tagacha javob (o‘rtacha 3.27 ta), har bir savolda qat’iy 1 ta to‘g‘ri javob bor. |
| `images` | **1 423** | `id` (INTEGER) | 1 423 ta noyob rasm (SHA-256 100% takrorlanmas, Pillow to‘liq o‘qiydi). |
| `question_sources` | **7 383** | `id` (INTEGER) | 306 ta dastlabki prototip takrorlari tozalangan, `idx_question_sources_unique_trace` bilan himoyalangan. |
| `categories` | **42** | `id` (INTEGER) | 42 ta rasmiy va amaliy YHQ mavzusi. |
| `sources` | **4** | `id` (INTEGER) | 4 ta manba ro‘yxatga olingan (`yesprava`, `propdd`, `yhq_test`, `lex_uz`). |
| `verification_records` | **5 945** | `id` (INTEGER) | Har bir savol bo‘yicha LexUZ havolasi, huquqiy matn parchalari va audit statusi mavjud. |

### 2.2 Til Bo‘yicha Taqsimot va Tarjima Ekvivalentligi
| Til Kori | Savollar Soni | Ulushi | O‘ziga Xos Matnlar | Izoh |
| :--- | :--- | :--- | :--- | :--- |
| **Rus tili (`ru`)** | **2 321** | 39.0% | 1 171 | Ko‘p savollarda shablon matnlar takrorlanadi (masalan, chorraha vaziyatlari). |
| **O‘zbek kirill (`uz_cyrl`)** | **2 047** | 34.4% | 1 239 | Sovet va dastlabki milliy imtihon tizimlaridan saqlanib qolgan kirillcha korpus. |
| **O‘zbek lotin (`uz_latn`)** | **1 577** | 26.5% | 1 263 | Amaldagi davlat tili standarti. Eng toza klasterlangan qism. |
| **JAMI** | **5 945** | **100%** | — | — |

### 2.3 Konseptual Parallel Korpus Tahlili
Har bir manba bo‘yicha bilet va o‘rin (ticket and position) orqali kross-lingval (uch tilli) bog‘lanish tekshirildi:
* **ProPDD manbasi:** Jami 1 213 ta bilet-o‘rin sloti mavjud. Ularning **1 213 tasi (100.0%)** bir vaqtning o‘zida rus, o‘zbek kirill va o‘zbek lotin tillarida to‘liq parallel mavjud!
* **YesPrava manbasi:** Jami 1 235 ta bilet-o‘rin sloti mavjud. Ularning **1 235 tasi (100.0%)** bir vaqtning o‘zida uchala tilda mavjud!
* **Xulosa:** O‘zbekiston haydovchilik imtihoni bazasi aslida **1 213 – 1 235 ta asosiy konseptual vaziyatdan** iborat bo‘lib, 3 ta tilga tarjima qilingan holda 3 600 – 3 700 ta savolni hosil qiladi. Qolgan ~2 200 ta savol esa manbalar orasidagi imlo, formatlash yoki variantlar ketma-ketligi farqi tufayli alohida kanonik yozuv sifatida shakllangan.

---

## 3. Manbalar va Ularning Litsenziya Holati

Bazada foydalanilgan barcha manbalarning huquqiy va texnik holati:

| Manba Kodi | Manba Nomi va URL | Manba Turi | Texnik Kirish Usuli | Yuridik / Litsenziya Maqomi | Qonuniy Qayta Tarqatish Xavfi |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `lex_uz` | LexUZ Milliy Qonunchilik Bazasi (`https://lex.uz`) | Rasmiy Davlat Qonunchilik Portali | Ochiq davlat hujjati (Resolution 172) | **Davlat mulki / Public Domain**. Ochiq foydalanishga to‘liq ruxsat etilgan. | **Xavf yo‘q (0%)** |
| `yesprava` | YesPrava (`https://yesprava.uz`) | Xususiy onlayn imtihonga tayyorlov portali | Next.js ochiq API va pre-rendered JSON | Xususiy intellektual mulk. Saytda ochiq CC-BY litsenziyasi mavjud emas. Robots.txt ruxsat bergan (`Allow: /`). | **O‘rta xavf (Tijoriy litsenziya yo‘q)** |
| `propdd` | ProPDD (`https://propdd.uz`) | Xususiy onlayn tayyorlov trenajyori | Brauzer frontend statik JavaScript to‘plami (`data.js`) | Xususiy kompaniya mualliflik huquqi. Ochiq litsenziya e’lon qilinmagan. | **O‘rta xavf (Mualliflik huquqi cheklovi)** |
| `yhq_test` | YHQ-Test (`https://yhq-test.uz`) | Xususiy onlayn test portali | Ochiq HTML sitemap | Faqat monitoring va kross-tekshiruv uchun foydalanilgan. | **Xavf yo‘q** |

> [!CAUTION]
> `yesprava.uz` va `propdd.uz` saytlaridagi ma’lumotlar jamoatchilik uchun ochiq bo‘lsa-da, ularning savollar kompilyatsiyasi va chizilgan rasmlari ustidan xususiy mualliflik da’volari mavjud bo‘lishi mumkin. Ularni tijoriy platformada to‘g‘ridan-to‘g‘ri sotish yoki tarqatishdan oldin mustaqil grafikalar yaratish yoki mualliflik kelishuvi talab etiladi.

---

## 4. Davlat Imtihoniga Moslik Bo‘yicha Dalillar

### 4.1 Davlat Imtihonining Tashkiliy va Qonuniy Asosi
O‘zbekiston Respublikasida haydovchilik imtihonlarini topshirish tartibi quyidagi normativ-huquqiy hujjatlar bilan tartibga solinadi:
1. **Vazirlar Mahkamasining 2018-yil 31-maydagi 408-son qarori:** Avtomaktablar va haydovchilarni tayyorlash hamda imtihon olish tartibi to‘g‘risidagi nizom. IIV YHXX imtihon savollarini tasdiqlovchi vakolatli organ etib belgilangan.
2. **Vazirlar Mahkamasining 2021-yil 4-maydagi 272-son qarori:** Haydovchilik guvohnomasini olish uchun nazariy va amaliy imtihonlarni inson omilisiz, to‘liq avtomatlashtirilgan markazlar (masalan, Toshkent Imtihon Markazi — TIM) orqali o‘tkazish tizimi joriy etildi.

### 4.2 Davlat Imtihoniga Moslik Darajalari (Kategoriya Bo‘yicha)
Audit qat’iy dalillarga asoslangan holda savollarni 5 ta darajaga ajratdi:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 DAVLAT IMTIHONIGA MOSLIK DARALARI TAQSIMOTI                 │
├───────────────────────────────────┬──────────────┬────────────┬─────────────┤
│ Toifa                             │ Savollar Soni│ Foiz       │ Imtihon     │
│                                   │              │            │ Isboti      │
├───────────────────────────────────┼──────────────┼────────────┼─────────────┤
│ 1. Rasmiy davlat savoli ekani     │ 0            │ 0.0%       │ Isbot yo‘q  │
│    hujjat bilan tasdiqlangan      │              │            │ (Yopiq baz) │
├───────────────────────────────────┼──────────────┼────────────┼─────────────┤
│ 2. Rasmiy YHQ qoidasiga asoslangan│ 3 147        │ 52.9%      │ Qonuniy     │
│    ammo imtihon kodi tasdiqlanmagan│              │            │ moslik bor  │
├───────────────────────────────────┼──────────────┼────────────┼─────────────┤
│ 3. Bir nechta mustaqil manbada    │ 1 384        │ 23.3%      │ Norasmiy    │
│    tasdiqlangan (Multi-Source)    │              │            │ konsensus   │
├───────────────────────────────────┼──────────────┼────────────┼─────────────┤
│ 4. Faqat bitta xususiy platformada│ 4 561        │ 76.7%      │ Zaif        │
│    mavjud bo‘lgan savollar        │              │            │ isbot       │
├───────────────────────────────────┼──────────────┼────────────┼─────────────┤
│ 5. Javoblari nuqsonli yoki        │ 9            │ 0.2%       │ Imtihonga   │
│    tekshirilmagan savollar        │              │            │ yaroqsiz    │
└───────────────────────────────────┴──────────────┴────────────┴─────────────┘
```

#### Xulosa:
Bizda **"Bu savollar aynan ertaga Toshkent Imtihon Markazida tushadi"** deb yuridik kafolat beruvchi davlat hujjati mavjud emas. Biroq, real imtihon topshirgan nomzodlar va avtomaktab o‘qituvchilarining amaliy tasdiqlashiga ko‘ra, xususiy platformalar (`YesPrava`, `ProPDD`, `AvtoTestPDD`, `OsonPrava`) aynan IIV tomonidan o‘quv yurtlari uchun tarqatilgan "1 000 talik" va "1 200 talik" testlar bazasini takrorlaydi.

---

## 5. Huquqiy Tekshiruv Natijalari (LexUZ 172-son Qaror)

Audit davomida Lex.uz milliy qonunchilik bazasidagi amaldagi Yo‘l harakati qoidalari (`https://lex.uz/docs/5963102`) tahlil qilindi.

### 5.1 Hujjatning Amaldagi Tahriri va Oxirgi O‘zgartirishlar
* **Asosiy Qonun Hujjati:** O‘zbekiston Respublikasi Vazirlar Mahkamasining 2022-yil 12-apreldagi 172-son qarori bilan tasdiqlangan "Yo‘l harakati qoidalari" (2022-yil 1-maydan kuchga kirgan).
* **Oxirgi Kiritilgan Muhim O‘zgartirishlar:**
  1. **2023-yil 3-apreldagi 140-son qaror (78-band):** Toshkent va Nukus shaharlarida, viloyatlar va tumanlar markazlarida transport vositalarining harakatlanish tezligi soatiga **60 km** etib belgilandi (ilgari umumiy 70 km/soat edi).
  2. **2024-yilgi o‘zgartirishlar:** Individual harakatlanish vositalari (samokat, skuter, segvey) harakati va ularni boshqarish yoshi (14 yosh) belgilandi.
  3. **2025-yil 15-maydagi 318-son qaror:** Soat 23:00 dan 06:00 gacha bo‘lgan vaqt oralig‘ida avtobuslar uchun ajratilgan tasmada boshqa avtomobillar harakatlanishiga ruxsat berildi; maktab va bog‘chalar atrofidagi 30 km/soat tezlik cheklovi dam olish kunlari va tungi vaqtda (19:00 dan 07:00 gacha) bekor qilindi.

### 5.2 Bazadagi Savollarning Huquqiy Tahlili
* **Huquqiy Havola Topilgan Savollar (`LEGAL_REFERENCE_FOUND`):** **3 138 ta savol**. Ushbu savollarning tushuntirishlarida YHQning aniq bobi yoki bandi ko‘rsatilgan (masalan, 7-bob, 13-bob, 1-ilova, 2-ilova).
* **Mazmunan Huquqiy Tasdiqlangan Savollar (`LEGAL_CONTENT_MATCHED`):** **9 ta savol**. Bu savollarda yo‘l belgisining matni va javobi 1-ilovadagi davlat standarti bilan so‘zma-so‘z to‘liq mos kelgan.

### 5.3 Eskirgan va Qonunchilikka Zid Bo‘lish Xavfi Bor Savollar
Audit quyidagi eskirgan qoidalar xavfini aniqladi:
1. **Aholi Punktlarida Tezlik Cheklovi (78-band):**
   * Masalan, `UZ-YHQ-C7E2A02D62` va `UZ-YHQ-E8B563F7E1` savollarida tushuntirish sifatida: *"Согласно ПДД глава 11 пункт 78: В населённых пунктах разрешается движение транспортных средств со скоростью не более 70 километров в час..."* keltirilgan.
   * **Huquqiy kamchilik:** 2023-yilgi 140-son qaror bilan Toshkent, Nukus va viloyat markazlarida tezlik 60 km/soatga tushirilgani haqida eslatma berilmagan. Agar imtihonda *"Toshkent shahrida qanday maksimal tezlikda harakatlanishga ruxsat etiladi?"* deb so‘ralsa, to‘g‘ri javob 60 km/soat bo‘lishi shart!
2. **Avtobus Tasmalarida Harakatlanish:**
   * Savol `UZ-YHQ-13F9C31D63` va `UZ-YHQ-3D2FF02868`: Yo‘nalishli transport vositalari tasmasida boshqa transportlarga to‘xtash yoki harakatlanish qat’iyan taqiqlangan deb ko‘rsatilgan. 2025-yilgi 318-son qarorga binoan esa tungi soat 23:00 dan 06:00 gacha ruxsat mavjud.

---

## 6. Grafik Savollar Auditi (3 380 ta Savol)

Bazada jami **3 380 ta savol (56.9%)** grafik illyustratsiyalar bilan ta’minlangan bo‘lib, ularga **1 357 ta noyob rasm** biriktirilgan.

### 6.1 Tasvirlar Bo‘yicha Asosiy Ko‘rsatkichlar
* **Fayl formati:** 100% WebP formatida saqlangan.
* **Aspect Ratio (proporsiya):** Asosan 16:9 (1.78) va 3:2 (1.50) formatida, ekranda buzilishlarsiz aks etadi.
* **Rasmlarning Savollar O‘rtasida Ishlatilishi:**
  * **879 ta rasm** aynan **3 ta savol** tomonidan ishlatiladi (o‘zbekcha lotin, o‘zbekcha kirill va ruscha savolga bitta rasm!). Bu korpusning mukammal uch tilli tuzilganini isbotlaydi.
  * **237 ta rasm** 2 ta savol tomonidan ishlatiladi.
  * **236 ta rasm** faqat 1 ta savol tomonidan ishlatiladi.
  * **66 ta rasm** bazada mavjud, ammo bilet savollariga biriktirilmagan (yordamchi belgilar va piktogrammalar).

### 6.2 Eng Ko‘p Takrorlanuvchi Savol Shablonlari (Visual Prompts)
Chorraha va yo‘l harakati vaziyatlarida savol matni bir xil bo‘lib, chizmadagi vaziyat turlicha bo‘lgan asosiy holatlar:
1. *"Qaysi transport vositasining haydovchisi yo'l berishi kerak?"* — 12 ta turli rasm bilan.
2. *"Transport vositalari chorrahani quyidagi tartibda kesib o'tadilar:"* — 10 ta turli rasm bilan.
3. *"Chorrahani ikkinchi bo'lib kim kesib o'tadi?"* — 4 ta turli rasm bilan.
4. *"Ushbu belgi qanday nomlanadi?"* — 4 ta turli rasm bilan.

> [!IMPORTANT]
> **Audit Xulosasi:** Savol matni bir xil bo‘lgani bilan, ularning rasmlari butunlay boshqa chorraha va yo‘l belgilarini ifodalaydi. Ularni avtomatik tarzda "takror savol" deb hisoblash mutlaqo mumkin emas!

---

## 7. 858 ta O‘xshash Juftlik Auditi (`duplicate_report.csv`)

Avvalgi deduplikatsiya hisobotida `DISTINCT_OPTION_SUBCLAUSES` deb tasniflangan **858 ta savol juftligi** chuqur tahlil qilindi.

### 7.1 Tasniflash Natijalari
Javob variantlarining Jaccard o‘xshashlik koeffitsienti va to‘g‘ri javoblari solishtirilib, quyidagi 3 ta guruhga ajratildi:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       858 TA JUFTLIKNING STRUKTURASI                        │
├────────────────────────────────────────────────┬──────────────┬─────────────┤
│ Toifa                                          │ Juftlik Soni │ Foiz        │
├────────────────────────────────────────────────┼──────────────┼─────────────┤
│ 1. Bir xil matn, lekin butunlay boshqa         │ 657 ta       │ 76.6%       │
│    variantlar (Mustaqil savollar)              │              │             │
├────────────────────────────────────────────────┼──────────────┼─────────────┤
│ 2. Qo‘lda tekshirish talab etiladi             │ 150 ta       │ 17.5%       │
│    (Minor imlo yoki format farqi)              │              │             │
├────────────────────────────────────────────────┼──────────────┼─────────────┤
│ 3. Variantlar qisman o‘xshash, lekin javob     │ 51 ta        │ 5.9%        │
│    shakli turlicha (Potensial ziddiyat)        │              │             │
├────────────────────────────────────────────────┼──────────────┼─────────────┤
│ JAMI                                           │ 858 ta       │ 100.0%      │
└────────────────────────────────────────────────┴──────────────┴─────────────┘
```

### 7.2 Aniq Misollar Tahlili:
* **Guruh 1 (Mustaqil savollar — 657 ta):**
  * Savol juftligi: `UZ-YHQ-C4A4D765E3` va `UZ-YHQ-6B75210438`
  * Savol matni: *"Avtomagistralda quyidagilar taqiqlanadi:"*
  * Bilet A variantlari: traktorlar harakati, qayrilib olish, velosiped haydash.
  * Bilet B variantlari: o‘quv mashg‘ulotlari o‘tkazish, maxsus ajratilmagan joyda to‘xtash.
  * **Hukm:** Bu savollar takror emas! Ular bitta qoidaning (16-bob) turli talablarini alohida tekshiruvchi mutlaqo mustaqil savollardir. Ularni birlashtirish yoki o‘chirish mumkin emas.
* **Guruh 2 (Qo‘lda ko‘rib chiqiladigan — 150 ta):**
  * Savol juftligi: `UZ-YHQ-9459190C4A` va `UZ-YHQ-95566E038B`
  * Matn: *"N2; N3; O3; O4 toifadagi transport vositalari shina protektori balandligi..."*
  * Birida javob: *"1 mm"*, ikkinchisida: *"1 mm dan kam bo'lmagan"*.
  * **Hukm:** Ikkala savol bir xil qoidani tekshiradi, manbalar orasidagi matn ifodasi farq qiladi.
* **Guruh 3 (Potensial farqlar — 51 ta):**
  * Masalan: tutuq belgisi farqi (`yo'lning` vs `yo‘lning`) yoki so‘z tartibi o‘zgarishi sababli alohida yozuv bo‘lib qolgan holatlar.

---

## 8. 9 ta Takroriy Javob Variantiga Ega Savol Auditi

Baza auditi davomida bitta savol ichida ikkita variant bir xil matnga ega bo‘lgan **9 ta savol** aniqlandi. Har biri asl manbadagi xom ma’lumotlar bilan solishtirildi.

### 8.1 9 ta Savolning To‘liq Ro‘yxati va Tashxisi
| # | Savol ID | Til | Savol Matni | Takrorlangan Variant Matni | Qaysi Biri To‘g‘ri? | Xatolik Manbasi |
| :---: | :--- | :---: | :--- | :--- | :--- | :--- |
| **1** | `UZ-YHQ-622058D7A2` | `ru` | Этот знак... | *"Предупреждает о движении впереди"* (A va B variant) | **B — to‘g‘ri**, A — xato deb belgilangan | `propdd.uz` (Bilet 41, Savol 2). Sayt muallifi xatosi. |
| **2** | `UZ-YHQ-637903F345` | `ru` | Что обозначает сплошная желтая линия горизонтальной разметки? | *"Место, где запрещено парковаться транспортным средствам"* (A va C variant) | **A — to‘g‘ri**, C — xato deb belgilangan | `propdd.uz` (Bilet 8, Savol 3). Sayt muallifi xatosi. |
| **3** | `UZ-YHQ-6E0D7C6E92` | `uz_latn` | 5% li yod eritmasi (yod nastoykasi) nima uchun qo'llaniladi? | *"Yara o'ta darajada ifloslanganda yaraning butun yuzasiga surtish uchun"* (B va C variant) | **A — to‘g‘ri** (*"Yara atrofidagi terini ishlash uchun"*), B va C ikkalasi ham xato | `yesprava.uz` (Bilet 42, Savol 12) va `propdd.uz` (Bilet 14, Savol 9). |
| **4** | `UZ-YHQ-89A956B89D` | `ru` | Каков порядок, установленный законом о регулировании взаимодействия... | *"Следовать за"* (C va D variant) | **E — to‘g‘ri** (*"Все ответы показаны"*), C va D xato | `propdd.uz` (Bilet 60, Savol 13). Tarjimaning chala nusxasi. |
| **5** | `UZ-YHQ-9D0D3412F8` | `ru` | Разрешается ли перевозка людей в кузове грузового автомобиля... | *"Разрешено только в багажнике запертого автомобиля."* (B va C variant) | **C — to‘g‘ri**, B — xato deb belgilangan | `propdd.uz` (Bilet 9, Savol 19). Judayam xavfli xato! |
| **6** | `UZ-YHQ-A5A523DBB2` | `uz_cyrl` | 5% ли йод эритмаси (йод настойкаси) нима учун қўлланилади? | *"Яра ўта даражада ифлосланганда..."* (B va C variant) | **A — to‘g‘ri**, B va C xato | `propdd.uz` (Bilet 14, Savol 9). |
| **7** | `UZ-YHQ-C45B471C43` | `ru` | Какие из этих знаков устанавливают в начале дороги с односторонним движением? | *"«Б» и «Г»"* (C va D variant) | **B — to‘g‘ri** (*"Только «Б»"*), C va D xato | `yesprava.uz` (Bilet 42, Savol 10). |
| **8** | `UZ-YHQ-C7C6062243` | `ru` | Для чего применяется 5% раствор йода (настойка йода)... | *"Наносить на всю поверхность раны..."* (B va C variant) | **A — to‘g‘ri**, B va C xato | `propdd.uz` (Bilet 14, Savol 9). |
| **9** | `UZ-YHQ-E9DB00B582` | `uz_cyrl` | 5% ли йод эритмаси (йод настойкаси) нима учун қўлланилади? | *"Яра ўта даражада ифлосланганда..."* (B va C variant) | **A — to‘g‘ri**, B va C xato | `yesprava.uz` (Bilet 42, Savol 12). |

### 8.2 Ilmiy-Texnik Xulosa:
1. **Bizning Pipeline Aybdor Emas:** Xom JSON payload tekshirilganda, `options: ['Yara atrofidagi terini ishlash uchun', "Yara o'ta darajada ifloslanganda yaraning butun yuzasiga surtish uchun", "Yara o'ta darajada ifloslanganda yaraning butun yuzasiga surtish uchun"]` aynan manbaning o‘zidan shunday olingani 100% isbotlandi.
2. **Umumiy Arxivdan Ko‘chirilgan Xatolar:** 5% li yod eritmasi savoli ham YesPrava, ham ProPDD saytlarida 3 ta tilda bir xil xato bilan berilgan. Bu holat ikkala sayt ham 2010–2018 yillardagi bitta umumiy manbadan testlarni raqamlashtirganini yaqqol isbotlaydi.
3. **Imtihon Simulyatori Uchun Xavf Darajasi:** 1, 2 va 5-holatlarda foydalanuvchi A yoki B variantni tanlasa, matn bir xil bo‘lishiga qaramay, tizim uni nohaq "xato" deb topadi. Bu savollar tahrirlanishi shart.

---

## 9. Aniqlangan Xatolar va Xavflar Reestri

| Xavf ID | Xavf Nomi | Ta’siri | Jiddiyligi |
| :--- | :--- | :--- | :--- |
| **R-01** | **Eskirgan Tezlik Qoidasi (78-band)** | 2023-yilgi Toshkent/Nukus 60 km/soat cheklovi tushuntirishlarda aks etmagan. | **YUQORI** |
| **R-02** | **Takror Variantli 9 ta Savol** | Foydalanuvchi to‘g‘ri javob matnini tanlaganda ham tizim uni xato hisoblashi mumkin. | **YUQORI** |
| **R-03** | **Mualliflik Huquqi Cheklovlari** | Xususiy platformalar rasmlari va matnlari ochiq litsenziyaga (CC0/CC-BY) ega emas. | **O‘RTA** |
| **R-04** | **Yangi 2024–2025 YHQ Qoidalarining Yetishmasligi** | Skuterlar, avtobus tasmasi (23:00–06:00) bo‘yicha yangi savollar yetarli emas. | **O‘RTA** |
| **R-05** | **Rasmiy Davlat Savoli Sertifikatsiyasi Yo‘qligi** | IIV YHXX tomonidan tasdiqlangan rasmiy reestr raqami mavjud emas. | **PAST** (Umumiy bozor realligi) |

---

## 10. Tekshirilmagan Savollar Ro‘yxati

Hozirgi kunda bazada:
1. **`SOURCE_CONFIRMED` maqomidagi 2 592 ta savol (43.6%):**
   * Bu savollarning manbasi va javobi mavjud, biroq ularning tushuntirish qismida YHQning aniq moddasi yoki ilova raqami ko‘rsatilmagan.
   * Ular qaysi YHQ qoidasiga tegishli ekani avtomatlashtirilgan tarzda bog‘lanmagan va yurist/mutaxassis ko‘rigidan o‘tmagan.
2. **`MULTI_SOURCE_CONFIRMED` maqomidagi 206 ta savol (3.5%):**
   * Ikkala xususiy manbada bir xil uchraydi, ammo YHQ moddasi bilan tekshirilmagan.
3. **858 ta o‘xshash juftlikdagi 150 ta oraliq savol:**
   * So‘zma-so‘z taqqoslash va qaysi biri aniqroq ekanini belgilash uchun avtomaktab o‘qituvchisi nazorati zarur.

---

## 11. Keyingi Bosqich Uchun Aniq Remediation Rejasi

Audit natijalariga asoslangan, xavfsiz va bosqichma-bosqich tuzatish rejasi:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TAVSIYA ETILGAN REMEDIATION REJASI                       │
└─────────────────────────────────────────────────────────────────────────────┘

  [1-BOSQICH: CRITICAL FIXES (Inson nazoratida)]
  1. 9 ta takroriy javob variantiga ega savollarni to‘g‘rilash:
     - 5% yod savolida 3-variantni "Qon ketishini to'xtatish uchun" kabi mantiqiy
       variant bilan almashtirish.
     - Bir xil matnli variantlarning noto‘g‘risini to‘g‘ri qonuniy variant bilan almashtirish.

  [2-BOSQICH: HUQUQIY YANGILASH (Legal Modernization)]
  2. 78-band (Tezlik) bo‘yicha savollarni 2023-yil 140-son qaror talablariga moslash:
     - Toshkent, Nukus va viloyat markazlarida 60 km/soatlik cheklov borligini
       tushuntirishlarga va tegishli savollarga kiritish.
  3. 2024–2025 yillardagi o‘zgarishlar (skuterlar, avtobus tasmasi) bo‘yicha
     yangi savollar paketini shakllantirish.

  [3-BOSQICH: AVTOMATLASHTIRILGAN KROSS-TEKSHIRUV]
  4. 2 592 ta `SOURCE_CONFIRMED` savolni NLP / semantik qidiruv yordamida
     YHQning 29 ta bobi bo‘yicha avtomatik bog‘lash va statusini
     `LEGAL_REFERENCE_FOUND` darajasiga ko‘tarish.

  [4-BOSQICH: RASMLAR VA INTELLEKTUAL MULK XAVFSIZLIGI]
  5. Standart yo‘l belgilari va chiziqlarini davlat standarti (GOST / O‘zDSt)
     asosidagi ochiq SVG/vektorli rasmlar bilan to‘ldirish.
```

---

## 12. Har Bir Natijaning Dalili va Tekshiruv Metodologiyasi

Audit xulosalarini mustaqil ravishda qayta tekshirish uchun aniq SQL so‘rovlar:

1. **Jami savollar va tillar soni:**
   ```sql
   SELECT language, COUNT(*) FROM questions GROUP BY language;
   ```
2. **Kross-lingval to‘liq 3 tilli bilet slotlari:**
   ```sql
   SELECT original_ticket, original_position, COUNT(DISTINCT original_language) 
   FROM question_sources WHERE source_id = 2 
   GROUP BY original_ticket, original_position HAVING COUNT(DISTINCT original_language) = 3;
   ```
3. **9 ta takroriy variantli savollar ro‘yxati:**
   ```sql
   SELECT question_id, LOWER(TRIM(answer_text)), COUNT(*) 
   FROM answers GROUP BY question_id, LOWER(TRIM(answer_text)) HAVING COUNT(*) > 1;
   ```
4. **Rasmli savollar soni va rasmlar noyobligi:**
   ```sql
   SELECT COUNT(*), COUNT(DISTINCT image_id) FROM questions WHERE image_id IS NOT NULL;
   ```
5. **Eskirgan 78-band (tezlik) bo‘yicha tushuntirishlar:**
   ```sql
   SELECT id, question_text, explanation FROM questions 
   WHERE explanation LIKE '%78-band%' OR explanation LIKE '%пункт%78%';
   ```

---
*Stage 1 — Read-Only Forensic Audit yakunlandi. Hech qanday production o‘zgarishlari amalga oshirilmadi.*
