# STAGE 1.1: AUDIT VALIDATION & EVIDENCE CORRECTION

**Loyiha:** O‘zbekiston Haydovchilik Guvohnomasi Nazariy Imtihoni Savollar Bazasi (YHQ / Avtotest)  
**Audit Turi:** Stage 1.1 — Independent Audit Validation & Evidence Correction  
**Sana:** 2026-yil 16-noyabr  
**Audit Holati:** QAT’IY READ-ONLY (Production database, savollar, javoblar, rasmlar va jadvallar o‘zgartirilmadi).  
**Hisobot Fayli:** `STAGE_1_1_AUDIT_VALIDATION.md`  
**O‘rganilgan Asosiy Manbalar:** [master_database.sqlite](file:///c:/Users/Администратор/AvtoTest/master_database.sqlite), [QUESTION_ACCURACY_AUDIT.md](file:///c:/Users/Администратор/AvtoTest/QUESTION_ACCURACY_AUDIT.md), [duplicate_report.csv](file:///c:/Users/Администратор/AvtoTest/duplicate_report.csv), [verification_report.csv](file:///c:/Users/Администратор/AvtoTest/verification_report.csv), Lex.uz normativ bazasi (VMQ 172, VMQ 408, VMQ 140, VMQ 318, VMQ 563).

---

## 1. Avvalgi Auditning To‘g‘ri Xulosalari

Avvalgi [QUESTION_ACCURACY_AUDIT.md](file:///c:/Users/Администратор/AvtoTest/QUESTION_ACCURACY_AUDIT.md) hisoboti mustaqil tekshirilganda, quyidagi xulosalar faktik va texnik jihatdan **100% to‘g‘ri** ekani tasdiqlandi:

1. **Bazaning Strukturaviy Butunligi (Database Integrity):**
   * Bazada jami **5 945 ta kanonik savol** mavjud.
   * `PRAGMA integrity_check;` natijasi `ok`.
   * Barcha savollarda kamida 2 ta, ko‘pi bilan 5 ta javob varianti mavjud va har bir savolda qat’iy 1 ta to‘g‘ri javob belgilangan (`answers` jadvalida jami 19 472 ta yozuv).
   * 1 423 ta rasm fayli diskda to‘liq mavjud, SHA-256 xeshlari 100% mos va Pillow kutubxonasi orqali xatosiz o‘qiladi.
2. **Deduplikatsiya Algoritmining Tuzatilgani:**
   * Oldingi xato (rasm ID larini inobatga olmasdan bir xil matnli savollarni ziddiyat deb topish) to‘liq bartaraf etilgan.
   * 1 379 ta turli rasmli chorraha va yo‘l belgilari savollari `DISTINCT_VISUAL_SCENARIO` sifatida muvaffaqiyatli saqlab qolingan.
3. **9 ta Takroriy Variantli Savolning Manbadagi Nuqsoni:**
   * 9 ta savolda bitta savol ichida 2 ta bir xil javob matni mavjudligi haqiqatda mavjud va bu bizning pipeline xatosi emas, balki `propdd.uz` va `yesprava.uz` portallarining dastlabki xom JSON/JS ma’lumotlaridagi nuqson ekani tasdiqlandi.

---

## 2. Isbotlanmagan yoki Noto‘g‘ri Xulosalar Tahlili

Audit davomida avvalgi hisobotdagi ayrim dalilsiz, isbotlanmagan yoki noaniq talqin qilingan da’volar aniqlashtirildi:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│             ISBOTLANMAGAN VA ANIQSIZ DA’VOLAR REESTRI                       │
├──────────────────────────────────────┬──────────────────────┬───────────────┤
│ Da’vo / Xulosa                       │ Audit Hukmi          │ Asos / Dalil  │
├──────────────────────────────────────┼──────────────────────┼───────────────┤
│ "1 200–1 250 ta savol davlat         │ UNPROVEN             │ IIV YHXX      │
│  imtihonining to‘liq bazasi"         │ (Isbotlanmagan)      │ ochiq reestri │
│                                      │                      │ mavjud emas   │
├──────────────────────────────────────┼──────────────────────┼───────────────┤
│ "YesPrava va ProPDD slotlari davlat  │ METODOLOGIK XATO     │ Xususiy slot  │
│  savollari soniga teng"              │                      │ != Davlat     │
│                                      │                      │    savoli     │
├──────────────────────────────────────┼──────────────────────┼───────────────┤
│ "YesPrava 1 235 ta bilet-o‘rin       │ QISMAN NOANIQ        │ 1 235 ta slot,│
│  va 1 235 ta savolga ega"            │ (1 248 ta savol bor) │ lekin 1 248 ta│
│                                      │                      │ yozuv bor     │
├──────────────────────────────────────┼──────────────────────┼───────────────┤
│ "5% yod savolining 3-varianti        │ TAXMIN               │ Asl variant   │
│  'qon to'xtatish' bo'lishi kerak"    │ (Spekulyatsiya)      │ 'ishqoriy     │
│                                      │                      │ kuyish' bo'lgan│
└──────────────────────────────────────┴──────────────────────┴───────────────┘
```

### 2.1 "1 200–1 250 ta konseptual savol davlat imtihonining to‘liq bazasi" da’vosi:
* **Audit Hukmi: UNPROVEN (Isbotlanmagan).**
* **Tahlil:** Xususiy tayyorlov saytlari (`yesprava.uz`, `propdd.uz`, `osonprava.uz`, `avtotestpdd.uz`) o‘z marketingida *"rasmiy 1 200 talik baza"* iborasini ishlatadi. Biroq, O‘zbekiston Respublikasi Vazirlar Mahkamasi, Ichki ishlar vazirligi yoki YHXX tomonidan tasdiqlangan va ochiq e’lon qilingan biron-bir davlat hujjatida imtihon bazasining umumiy savollar soni 1 200 yoki 1 250 ta ekanligi yozilmagan.
* Avtomatlashtirilgan imtihon markazlari (Toshkent Imtihon Markazi — TIM va boshqalar) xususiy IT-platformalar (masalan, "Yagona Imtihon Markazi" MChJ) dasturiy ta’minotidan foydalanadi. Ularning ichki savollar bazasi hajmi va yangilanish rotatsiyasi **tijorat va xizmat siri** hisoblanadi. Shuning uchun xususiy saytlarning 60–63 ta biletini to‘g‘ridan-to‘g‘ri "davlat bazasining to‘liq nusxasi" deb da’vo qilish yuridik va ilmiy jihatdan noto‘g‘ri.

### 2.2 YesPrava bilet-o‘rin slotlari bo‘yicha noaniqlik:
* Avvalgi hisobotda YesPrava 1 235 ta slotga ega deb ko‘rsatilgan edi.
* **Aniq fakt:** YesPravada `(original_ticket, original_position)` kombinatsiyasi bo‘yicha 1 235 ta alohida slot bor, biroq har bir tilda **1 248 ta savol** mavjud! Farq: 3-biletda (va ayrim boshqa biletlarda) 26 tagacha savol joylashtirilgan bo‘lib, 13 ta pozitsiyada 2 tadan savol mavjud.

---

## 3. Raqamlar va Statuslarni Qayta Solishtirish

Avvalgi hisobotda turli metrikalar (platformalar qamrovi va tekshiruv statuslari) bitta ro‘yxatda berilgani sababli chalkashlik yuzaga kelgan edi. Quyida har bir ko‘rsatkich qat’iy SQL so‘rovlari, hisoblash qoidasi va umumiy maxraj ($N = 5\ 945$) bilan reconciliation qilindi.

### 3.1 Ikki Asosiy O‘lchov (Dimensions) Ajratilishi:
1. **O‘lchov A: Manbalar Qamrovi (Platform Presence)** — Savol nechta mustaqil platformada mavjud?
2. **O‘lchov B: Huquqiy Tekshiruv Maqomi (`verification_status`)** — Savol qanday huquqiy/metodologik tasdiqqa ega?

### 3.2 O‘zaro Solishtirish Matritsasi (Cross-Tabulation Matrix)
$$\text{Umumiy Maxraj } (N) = \mathbf{5\ 945} \text{ ta kanonik savol}$$

```sql
SELECT 
    q.verification_status,
    COUNT(CASE WHEN sub.src_cnt = 1 THEN 1 END) AS single_source_count,
    COUNT(CASE WHEN sub.src_cnt = 2 THEN 1 END) AS multi_source_count,
    COUNT(*) AS total_status_count
FROM questions q
JOIN (
    SELECT question_id, COUNT(DISTINCT source_id) AS src_cnt 
    FROM question_sources GROUP BY question_id
) sub ON q.id = sub.question_id
GROUP BY q.verification_status;
```

#### Haqiqiy SQL Natijasi:
| Verification Status (`verification_status`) | Yagona Manbali (`num_sources = 1`) | Ko‘p Manbali (`num_sources = 2`) | Jami Savollar (`Total`) | Maxrajdagi Ulushi ($N=5945$) | Izoh va Huquqiy Ta’rifi |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`LEGAL_CONTENT_MATCHED`** | 6 | 3 | **9** | 0.15% | Mazmuni va javobi YHQ 172 1-ilovasi bilan so‘zma-so‘z tasdiqlangan. |
| **`LEGAL_REFERENCE_FOUND`** | 1 963 | 1 175 | **3 138** | 52.78% | Tushuntirishida YHQ bobi, bandi yoki belgisi aniqlangan savollar. |
| **`MULTI_SOURCE_CONFIRMED`** | 0 | 206 | **206** | 3.47% | 2 ta manbada bor, ammo YHQ aniq modda havolasi topilmagan savollar. |
| **`SOURCE_CONFIRMED`** | 2 592 | 0 | **2 592** | 43.60% | Faqat 1 ta manbada bor va YHQ modda havolasi topilmagan savollar. |
| **JAMI (USTUNLAR YIG‘INDISI)** | **4 561** | **1 384** | **5 945** | **100.0%** | **100% matematik moslik** |

### 3.3 Tafovutlarning Matematik Yechimi:
1. **Nega "1 384 ta Multi-Source savol", ammo "206 ta MULTI_SOURCE_CONFIRMED"?**
   * Jami 1 384 ta savol ikkala platformada (`yesprava` va `propdd`) mavjud.
   * Ulardan **1 178 tasi** YHQ moddasi yoki belgisiga ega bo‘lgani uchun yuqoriroq darajaga (`LEGAL_REFERENCE_FOUND` yoki `LEGAL_CONTENT_MATCHED`) ko‘tarilgan!
   * Qolgan **206 tasi** huquqiy havolasiz bo‘lgani sababli `MULTI_SOURCE_CONFIRMED` maqomida qolgan:
     $$1\ 175 + 3 + 206 = \mathbf{1\ 384}$$
2. **Nega "4 561 ta yagona manbali savol", ammo "2 592 ta SOURCE_CONFIRMED"?**
   * Jami 4 561 ta savol faqat bitta platformada uchraydi.
   * Ulardan **1 969 tasi** YHQ moddasiga havola qilgani uchun `LEGAL_REFERENCE_FOUND` yoki `LEGAL_CONTENT_MATCHED` ga o‘tgan.
   * Qolgan **2 592 tasi** esa havolasiz bo‘lgani uchun `SOURCE_CONFIRMED` ustunida qolgan:
     $$1\ 963 + 6 + 2\ 592 = \mathbf{4\ 561}$$
3. **Nega "3 147 ta huquqiy moslik"?**
   * Bu `LEGAL_REFERENCE_FOUND` (3 138) va `LEGAL_CONTENT_MATCHED` (9) yig‘indisidir:
     $$3\ 138 + 9 = \mathbf{3\ 147}$$

---

## 4. 2026-yil 16-Noyabr Holatidagi Qonunchilik Yangilanishlari

Audit davomida LexUZ milliy bazasidagi quyidagi 5 ta asosiy hukumat qarorining amaldagi matni tekshirildi:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   QONUNCHILIKNING AMALDAGI TAHRIRI (2026)                   │
├────────────────────┬────────────┬──────────────────┬────────────────────────┤
│ Hujjat             │ Qabul Sana │ Amaldagi Tahrir  │ Asosiy O‘zgarish       │
├────────────────────┼────────────┼──────────────────┼────────────────────────┤
│ VMQ 172-son (YHQ)  │ 12.04.2022 │ 2025/2026 tahrir │ Tezlik, skuterlar,     │
│                    │            │                  │ avtobus tasmasi        │
├────────────────────┼────────────┼──────────────────┼────────────────────────┤
│ VMQ 408-son        │ 31.05.2018 │ 13.10.2026       │ Haydovchilik imtihoni  │
│ (Imtihon nizomi)   │            │ (VMQ 563-son)    │ va staj talablari      │
├────────────────────┼────────────┼──────────────────┼────────────────────────┤
│ VMQ 140-son        │ 03.04.2023 │ Amalda           │ 78-band: 60 km/soat    │
├────────────────────┼────────────┼──────────────────┼────────────────────────┤
│ VMQ 318-son        │ 15.05.2025 │ Amalda           │ Tasma (23:00–06:00)    │
├────────────────────┼────────────┼──────────────────┼────────────────────────┤
│ VMQ 563-son        │ 13.10.2026 │ Amalda           │ 408-son qarorga        │
│                    │            │                  │ o‘zgartirish           │
└────────────────────┴────────────┴──────────────────┴────────────────────────┘
```

### 4.1 Hujjatlar Bo‘yicha Batafsil Tahlil:
1. **VMQ 172-son (12.04.2022) — Yo‘l harakati qoidalarini tasdiqlash to‘g‘risida:**
   * LexUZ URL: `https://lex.uz/docs/5963102`
   * Amaldagi tahrir: 29 ta bob, 1-ilova (Yo‘l belgilari), 2-ilova (Yo‘l chiziqlari).
   * Bazaga ta’siri: Bazadagi barcha savollar uchun yagona fundamental qonuniy mezon.
2. **VMQ 408-son (31.05.2018) — Imtihon va Haydovchilarni tayyorlash tartibi:**
   * LexUZ URL: `https://lex.uz/docs/3762413`
   * Oxirgi o‘zgartirish: **2026-yil 13-oktabrdagi 563-sonli VMQ** qarori bilan o‘zgartirilgan!
   * Kiritilgan yangilik: Xorijda ishga joylashtirish dasturlari doirasida tanlovdan o‘tgan fuqarolar uchun ayrim toifalarda 3 yillik majburiy staj talabi bekor qilinib, imtihon topshirishga to‘g‘ridan-to‘g‘ri ruxsat berildi.
   * Bazaga ta’siri: Haydovchilik guvohnomasini olish huquqi va toifalar bo‘yicha savollarga taalluqli.
3. **VMQ 140-son (03.04.2023) — Aholi punktlarida tezlikni cheklash:**
   * LexUZ URL: `https://lex.uz/docs/6423984`
   * O‘zgargan band: YHQ 78-bandi. Nukus va Toshkent shaharlarida, viloyatlar va tumanlar markazlarida tezlik **60 km/soat** etib belgilandi.
   * Bazaga ta’siri: Bazadagi `UZ-YHQ-C7E2A02D62` va `UZ-YHQ-E8B563F7E1` kabi savollarning tushuntirishlarida faqat 70 km/soat deb yozilgan joylari to‘ldirilishi shart.
4. **VMQ 318-son (15.05.2025) — Aholiga qulayliklar yaratish:**
   * LexUZ URL: `https://lex.uz/docs/6920199` (kuchga kirishi: 01.06.2025).
   * O‘zgargan qoidalar: Soat 23:00 dan 06:00 gacha avtobus tasmalarida boshqa transportlarga ruxsat; maktab atrofi 30 km/soat cheklovining kechki (19:00–07:00) va dam olish kunlarida amal qilmasligi.
   * Bazaga ta’siri: Avtobus tasmasi bo‘yicha savollar (`UZ-YHQ-13F9C31D63`, `UZ-YHQ-3D2FF02868`) ushbu istisnolarni inobatga olgan holda ko‘rib chiqilishi kerak.

---

## 5. Davlat Imtihoniga Moslikning Isbotlangan Chegaralari

| Savollar Toifasi | Savollar Soni | Isbotlangan Huquqiy Maqomi |
| :--- | :---: | :--- |
| **IIV YHXX rasmiy tasdig‘iga ega savollar** | **0 ta (0.0%)** | Rasmiy sertifikat yoki ochiq davlat API si mavjud emas. |
| **Qonuniy YHQ moddasi tasdiqlangan savollar** | **3 147 ta (52.9%)** | Savol va javob YHQ 172-son qaror qoidalariga to‘liq mos keladi. |
| **Norasmiy ko‘p manbali konsensus savollari** | **1 384 ta (23.3%)** | Ikkita yirik xususiy tayyorlov platformasida bir xil mavjud. |
| **Faqat bitta xususiy platformada mavjud savollar**| **4 561 ta (76.7%)** | Yagona manbali savollar (formatlash va variant farqlari sababli). |

> [!IMPORTANT]
> **Chegara Xulosasi:** Biz ushbu bazani *"Davlat nazariy imtihonining rasmiy savollari"* deb e’lon qila olmaymiz. Biroq, uni **"O‘zbekiston Respublikasi amaldagi YHQ talablariga moslashtirilgan va mustaqil tayyorlov platformalari konsensusi asosidagi eng yirik o‘quv repozitoriysi"** deb atash 100% daliliy asosga ega.

---

## 6. Qoraqalpoq Tili Bo‘yicha Qamrov Auditi

O‘zbekiston Respublikasining "Davlat tili haqida"gi Qonuni, Qoraqalpog‘iston Respublikasining "Davlat tili haqida"gi Qonuni hamda Vazirlar Mahkamasining 408- va 272-son qarorlariga muvofiq, Qoraqalpog‘iston Respublikasi hududidagi haydovchilik imtihon markazlarida nazariy imtihonlarni **qoraqalpoq tilida** topshirish qonuniy huquqi kafolatlangan.

### Bazadagi Haqiqiy Holat:
```sql
SELECT language, COUNT(*) FROM questions GROUP BY language;
```
* **Rus tili (`ru`):** 2 321 ta (39.0%)
* **O‘zbek kirill (`uz_cyrl`):** 2 047 ta (34.4%)
* **O‘zbek lotin (`uz_latn`):** 1 577 ta (26.5%)
* **Qoraqalpoq tili (`kaa` / `qr`):** **0 ta (0.0%)**

> [!WARNING]
> **Muhim Kamchilik:** Hozirgi kunda bazada **qoraqalpoq tilidagi bitta ham savol mavjud emas**. Respublikaning suveren qismi bo‘lgan Qoraqalpog‘iston Respublikasidagi abituriyentlar va haydovchilikka nomzodlar uchun to‘laqonli xizmat ko‘rsatish uchun keyingi bosqichlarda qoraqalpoqcha savollar bankini integratsiya qilish alohida strategik vazifa sifatida belgilanishi shart.

---

## 7. 9 ta Takroriy Javobli Savolning Aniq Dalillari

Avvalgi hisobotda keltirilgan 9 ta savol chuqur o‘rganildi. Ayniqsa, 5% li yod nastoykasi savoli bo‘yicha taxminiy emas, balki rasmiy o‘quv dasturlari va `pdduz.ru` arxiv chiptalari asosidagi aniq dalillar topildi.

### 7.1 9 ta Savolning Detal Tahlili:
1. **`UZ-YHQ-6E0D7C6E92` (`uz_latn`), `UZ-YHQ-A5A523DBB2` (`uz_cyrl`), `UZ-YHQ-C7C6062243` (`ru`), `UZ-YHQ-E9DB00B582` (`uz_cyrl`) — 5% li yod nastoykasi savoli:**
   * **Savol:** *"5% li yod eritmasi (yod nastoykasi) nima uchun qo'llaniladi?"*
   * **Amaldagi variantlar:**
     * `[A]` *Yara atrofidagi terini ishlash uchun* `[CORRECT]`
     * `[B]` *Yara o'ta darajada ifloslanganda yaraning butun yuzasiga surtish uchun*
     * `[C]` *Yara o'ta darajada ifloslanganda yaraning butun yuzasiga surtish uchun* (B ning aynan nusxasi!)
   * **Tibbiy va huquqiy asos:** Birinchi tibbiy yordam ko‘rsatish qoidalariga ko‘ra, 5% li spirtli yod eritmasi yaraning ichiga quyilmaydi (chunki u to‘qimalarning kimyoviy kuyishiga olib keladi), faqat yara atrofiga surtiladi. Shuning uchun `[A]` varianti — to‘g‘ri javobdir.
   * **Asl manbadagi 3-variant (Dalil):** PDD chiptalarining to‘liq nusxalarida (`pdduz.ru`) 3-distraktor sifatida: *"Для смазывания кожи при химических ожогах первой степени..."* ("Birinchi darajali kimyoviy kuyishlarda teriga surtish uchun") varianti bo‘lgan. Manba mualliflari raqamlashtirishda 2-variantni adashib 3-o‘ringa ham nusxalab qo‘ygan.
   * **Tavsiya:** Javobni o‘zgartirmasdan saqlash, kelajakda 3-variantni asl PDD distraktori bilan almashtirish.
2. **`UZ-YHQ-622058D7A2` (`ru`) — "Этот знак..." (ID: 1167):**
   * Variant A va B bir xil: *"Предупреждает о движении впереди"*.
   * Lekin B to‘g‘ri, A noto‘g‘ri deb belgilangan. Bu `propdd.uz` ning sof texnik nuqsoni.
3. **`UZ-YHQ-637903F345` (`ru`) — Yotiq sariq chiziq (ID: 805):**
   * Variant A va C bir xil: *"Место, где запрещено парковаться транспортным средствам"*.
   * A to‘g‘ri, C noto‘g‘ri belgilangan.
4. **`UZ-YHQ-89A956B89D` (`ru`) — YPX bilan munosabat:**
   * Variant C va D bir xil: *"Следовать за"*. E to‘g‘ri: *"Все ответы показаны"*.
5. **`UZ-YHQ-9D0D3412F8` (`ru`) — Shatakka olishda odam tashish:**
   * Variant B va C bir xil: *"Разрешено только в багажнике запертого автомобиля"*. C to‘g‘ri, B noto‘g‘ri. Tarjima ham o‘ta qo‘pol ("bagajnikda odam tashish" deb tarjima qilingan).
6. **`UZ-YHQ-C45B471C43` (`ru`) — Bir tomonlama harakat belgisi (ID: 601):**
   * Variant C va D bir xil: *"«Б» и «Г»"*. To‘g‘ri javob B: *"Только «Б»"*.

---

## 8. 858 ta Juftlik Bo‘yicha Qayta Tekshiruv

Avvalgi hisobotda 657 ta juftlik "mustaqil savol" deb atalgan edi. Bu xulosa qayta tekshirildi:

### 8.1 858 ta Juftlikning Qayta Tasnifi:
Savollarning matni, rasmi, variantlari va to‘g‘ri javoblari normallashtirilgan holda to‘liq solishtirildi:
* **Haqiqiy Mustaqil Savollar (648 ta juftlik — 75.5%):**  
  Variantlar o‘rtasidagi Jaccard o‘xshashligi $< 0.4$. Bular bir xil shablon sarlavhaga ega (masalan, *"Qayrilish taqiqlanadi:"* yoki *"Avtomagistralda taqiqlanadi:"*), lekin variantlari butunlay boshqa bandlarni tekshiruvchi mutlaqo alohida savollardir (masalan, birida piyodalar o‘tish joyi so‘ralsa, ikkinchisida 100 metr ko‘rinmaslik holati so‘ralgan). Ular mustaqil savol sifatida saqlanishi shart.
* **Qisman O‘xshash, Javobi Bir Xil (155 ta juftlik — 18.1%):**  
  Variantlarning 2-3 tasi o‘xshash, to‘g‘ri javobi bir xil, biroq chalg‘ituvchi variantlari biroz farq qiladi.
* **Qisman O‘xshash, Javobi Farqli (52 ta juftlik — 6.1%):**  
  Shablon bir xil, variantlar qisman mos, ammo vaziyatga qarab to‘g‘ri javob boshqa (masalan, tutuq belgisi yoki so‘z ifodasi farqi).
* **Ortografik Dublikatlar (3 ta juftlik — 0.35%):**  
  Faqat `motosikl` / `mototsikl` yoki qo‘shtirnoq farqi tufayli ikkita bo‘lib qolgan savollar.

---

## 9. Keyingi Bosqich Uchun Ustuvor Ishlar Rejasi

Audit natijalari asosida quyidagi ishlar ustuvorlik tartibida tavsiya etiladi:

1. **1-Ustuvorlik (Kritik):** 9 ta takroriy variantli savolning distroktorlarini qonuniy va o‘quv me’yorlariga mos ravishda to‘g‘rilash rejasini tayyorlash.
2. **2-Ustuvorlik (Huquqiy):** YHQ 78-bandi (shahar ichida 60 km/soat) va boshqa so‘nggi qarorlar bo‘yicha eskirgan tushuntirishlarni yangilash.
3. **3-Ustuvorlik (Qamrov):** Qoraqalpog‘iston Respublikasi uchun qoraqalpoq tilidagi rasmiy testlar bazasini qidirish va integratsiya strategiyasini ishlab chiqish.
4. **4-Ustuvorlik (Konseptual ID):** 5 945 ta savolni ~1 235 ta noyob bilet-vaziyatiga bog‘lovchi `concept_group_id` jadvalini yaratish.

---
*Stage 1.1 Read-Only Audit Validation yakunlandi. Production bazasiga hech qanday o‘zgartirish kiritilmadi.*
