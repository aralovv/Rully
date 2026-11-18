/**
 * RULLY Mini App - Multilingual Exam Cheatsheet (Imtihon Shpargalkasi)
 * Authentic pedagogical data in 3 languages:
 * 1. Uzbek Latin (uz_latn)
 * 2. Uzbek Cyrillic (uz_cyrl)
 * 3. Russian (ru)
 */

window.CHEATSHEET_DATA = {
  uz_latn: {
    collective: {
      badge: "63.3% To‘g‘ri",
      tag: "Kollektiv javoblar",
      title: '"Barcha javoblar to‘g‘ri" / "Sanab o‘tilgan barcha..."',
      desc: 'Bazadagi <strong>98 ta savolda</strong> kollektiv variantlar mavjud. Ular <strong>62 ta savolda (63.3%) to‘g‘ri</strong> keladi, lekin <strong>36 ta savolda (36.7%) tuzoq</strong>!',
      strategy_title: "⚠️ Test yechish strategiyasi:",
      strategy_desc: 'Agar savolda bitta aniq va tor qoida (masalan, faqat bitta holatga ruxsat) so‘ralayotgan bo‘lsa, kollektiv variant <strong>36.7% holatda tuzoq</strong> bo‘ladi. Faqat vaziyat bir nechta to‘liq shartlarni birdek talab qilgandagina "Barcha javoblar to‘g‘ri" ni tanlang.'
    },
    high_prob_title: "🌟 Eng yuqori ehtimolli kalit so‘zlar (70% — 90% Win Rate)",
    high_prob_sub: "Agar savolda ikkilanib qolsangiz, variant matnidagi ushbu iboralarga qarang:",
    high_prob_items: [
      {
        search: "shuningdek murakkab me'yoriy qoidalarda",
        term: '"Shuningdek"',
        chip: "88.9% (8/9)",
        domain: "Murakkab meʼyoriy qoidalarda",
        hint: "Qonun bandini aniq va to‘liq tushuntiruvchi meʼyorda kelsa, deyarli har doim to‘g‘ri chiqadi."
      },
      {
        search: "xalaqit halaqit bermaslik manyovr burilish orqaga",
        term: '"Xalaqit / halaqit bermaslik"',
        chip: "80.0% (16/22)",
        domain: "Manyovr, burilish, orqaga yurish",
        hint: "Boshqa ishtirokchilarga xalaqit bermaslik sharti bilan qilingan harakatlar qoidaga muvofiq bo‘ladi."
      },
      {
        search: "ishonch hosil qilishi harakat boshlash qayta tizilish",
        term: '"Ishonch hosil [qilishi]"',
        chip: "71.4% (5/7)",
        domain: "Harakat boshlash va qayta tizilish",
        hint: "Manyovr xavfsizligiga ishonch hosil qilish majburiyati doim eng to‘g‘ri javobdir."
      },
      {
        search: "zarur zarur bo'lsa xavfsizlik shartlari",
        term: '"Zarur" / "Zarur bo‘lsa"',
        chip: "68.8% (11/16)",
        domain: "Xavfsizlik shartlari",
        hint: "Zarur bo‘lganda yordamdan foydalanish yoki to‘xtash haqidagi variantlar ustundir."
      }
    ],
    trap_title: "🚨 Xavfli tuzoq so‘zlar (0% — 15% Win Rate)",
    trap_sub: "Ushbu so‘zlar qatnashgan variantlar deyarli har doim XATO bo‘ladi:",
    trap_items: [
      {
        search: "agar boshqa mashina bo'lmasa transport vositasi bo'lmasa",
        term: '"Agar boshqa mashina yo‘q bo‘lsa..."',
        chip: "0.0% (100% Tuzoq)",
        hint: '<em>Misol: "...agar to‘xtab turish joyida boshqa mashina yo‘q bo‘lsa ruxsat etiladi"</em>. <strong>Tuzoq!</strong> Yo‘lda mashina yo‘qligi taqiqlangan amalni ruxsatga aylantirmaydi!'
      },
      {
        search: "alohida ehtiyotkorlik bilan o'tadi harakatlanadi",
        term: '"Alohida ehtiyotkorlik bilan o‘tadi"',
        chip: "0.0% (100% Tuzoq)",
        hint: 'YHQ qatʼiy qoidadir. "Ehtiyotkorlik bilan o‘tib ketaveradi" degan gap bo‘lmaydi — qoida aniq <strong>to‘xtashni</strong> yoki <strong>yo‘l berishni</strong> talab qiladi.'
      },
      {
        search: "yo'l qo'yilmaydi taqiqlanadi",
        term: '"Yo‘l qo‘yilmaydi"',
        chip: "0.0% To‘g‘ri",
        hint: 'YHQ rasmiy yuridik tilida doimo <strong>"Taqiqlanadi"</strong> so‘zi qo‘llaniladi. "Yo‘l qo‘yilmaydi" varianti chalg‘ituvchi sunʼiy variantdir.'
      },
      {
        search: "buzmadi haydovchi qoidani buzmadi",
        term: '"Buzmadi" (Qoidani buzmadi)',
        chip: "9.1% (91% Buzgan!)",
        hint: 'Savolda <em>"Haydovchi qoidani buzdimi?"</em> deb so‘ralsa, <strong>91% hollarda u buzgan</strong> bo‘ladi! "Buzmadi" varianti 11 ta savoldan faqat 1 tasida to‘g‘ri.'
      },
      {
        search: "faqat yakka o'zi cheklangan",
        term: '"Faqat" (yakka o‘zi kelganda)',
        chip: "22.3% To‘g‘ri",
        hint: '"Faqat" so‘zi ko‘pincha qoidani asossiz toraytirib qo‘yadi (masalan: "Faqat yuk avtomobillariga"). Shu sabab 78% hollarda xato bo‘ladi.'
      }
    ],
    rules_boxes: [
      {
        tag: "1. CHORRAHALAR & O‘TISH TARTIBI",
        color: "cyan",
        search: "chorraha tramvay aylanma krug o'ng qo'l chapga burilish seksiya strelka",
        layout: "dense",
        items: [
          {
            k: "🚋 Tramvay ustunligi:",
            v: "Teng sharoitda (har ikkisi asosiyda yoki yashil chiroqda) tramvay burilishidan qatʼi nazar <strong>har doim 1-o‘rinda</strong> o‘tadi! Faqat 2 holda yo‘l beradi: depodan chiqishda va \"Yo‘l bering\" belgisida."
          },
          {
            k: "🔄 Aylanma harakat (4.3):",
            v: "Aylanma harakatdagi avtomobil aylanmaga kirib kelayotganlarga nisbatan <strong>ustunlikka ega</strong> (aylanmadagi doim asosiy)."
          },
          {
            k: "👉 O‘ng qo‘l qoidasi:",
            v: "Teng ahamiyatli chorrahalarda va bir vaqtda o‘zaro qayta tizilishda doim <strong>o‘ng tomondan</strong> kelayotgan transportga yo‘l beriladi."
          },
          {
            k: "↩️ Chapga burilish / Qayrilish:",
            v: "Ro‘paradan to‘g‘riga va o‘ngga harakatlanayotgan barcha transport vositalariga <strong>yo‘l berish shart</strong>."
          },
          {
            k: "🟢 Yashil strelka + Qizil chiroq:",
            v: "Qo‘shimcha tarmoq yonganda burilish mumkin, lekin boshqa yo‘nalishdagi <strong>barcha transportlarga yo‘l berish shart</strong>!"
          },
          {
            k: "⏳ Kim oxirgi o‘tadi:",
            v: "Ikkinchi darajali yo‘lda turgan yoki chapga burilayotgan transport qarama-qarshi va asosiy yo‘ldagilarga yo‘l berib, chorrahadan <strong>oxirgi bo‘lib</strong> o‘tadi."
          },
          {
            k: "🛑 \"Yo‘l bering\" (2.4) belgisi:",
            v: "Boshqa yo‘nalishdagi barcha transport vositalariga <strong>yo‘l berish shart</strong> (hatto tramvay ham ushbu belgida boshqalarga yo‘l beradi)."
          }
        ]
      },
      {
        tag: "2. TARTIBGA SOLUVCHI (REGULYIROVSHIK) ISHORALARI",
        color: "amber",
        search: "tartibga soluvchi regulyirovshik ishoralari shlagbaum devor to'xta",
        layout: "three-col",
        items: [
          {
            item_class: "reg-red",
            k: "🛑 Qo‘li tepada:",
            v: "<strong>Qizil chiroqqa teng!</strong> Barcha transportlar va piyodalar uchun harakat qatʼiyan taqiqlanadi (hamma to‘xtaydi)."
          },
          {
            item_class: "reg-yellow",
            k: "🧍 Qo‘llar tushgan / Yonga:",
            v: "• <strong>Ko‘krak va orqa — Devor:</strong> Taqiqlanadi!<br>• <strong>Yon tomondan:</strong> To‘g‘riga va o‘ngga ruxsat. Tramvay faqat to‘g‘riga (\"yengdan kirib yengdan chiqadi\")."
          },
          {
            item_class: "reg-green",
            k: "👉 O‘ng qo‘l oldinga:",
            v: "• <strong>Ko‘krakdan:</strong> Faqat o‘ngga.<br>• <strong>Chap yondan:</strong> Hamma tomonga (to‘g‘ri, o‘ng, chap, qayrilish).<br>• <strong>Orqasi va o‘ng yoni:</strong> Qatʼiyan taqiqlangan!"
          }
        ]
      },
      {
        tag: "3. IMTIHONDA TUSHADIGAN ANIQ MASOFALAR",
        color: "cyan",
        search: "masofalar 2.5m 5m 15m 30m 50m 100m 150m metr",
        layout: "four-col",
        items: [
          { badge_val: "2.5 m", v: "To‘xtagan avtomobil va uzluksiz chiziq orasida kamida 3m bo‘lishi shart (2.5m bo‘lsa to‘xtash taqiqlanadi)." },
          { badge_val: "5 m", v: "Piyodalar o‘tish joyi oldida to‘xtash (orqasida emas!) va qatnov qismi kesishmasi chetidan masofa." },
          { badge_val: "15 m", v: "Bekatlar (avtobus/tramvay) va temir yo‘l relsi oldida to‘xtab turish; aholi punktida avariya belgisi." },
          { badge_val: "30 m", v: "Aholi punktidan tashqarida avariya to‘xtash belgisini o‘rnatish masofasi (kamida 30m)." },
          { badge_val: "50 m", v: "Temir yo‘l kesishmasidan oldin to‘xtab turish (stoyanka) taqiqlanadi." },
          { badge_val: "100 m", v: "Temir yo‘l kesishmasiga 100 metr qolganda quvib o‘tish qatʼiyan taqiqlanadi." },
          { badge_val: "50–100 m", v: "Aholi punktlarida ogohlantiruvchi yo‘l belgilari o‘rnatilish masofasi." },
          { badge_val: "150–300 m", v: "Aholi punktidan tashqarida ogohlantiruvchi yo‘l belgilari o‘rnatilish masofasi." }
        ]
      },
      {
        tag: "4. BELGILANGAN TEZLIK MEʼYORLARI (KM/SOAT)",
        color: "emerald",
        search: "tezlik me'yorlari 20 30 50 60 70 100 110 km/soat",
        layout: "four-col",
        items: [
          { badge_val: "20 km/s", badge_color: "emerald", v: "Turar joy dahasi (jiloy zona), hovlilar va velosiped zonalari." },
          { badge_val: "30 km/s", badge_color: "emerald", v: "Maktablar va maktabgacha taʼlim muassasalari oldidagi yo‘llarda." },
          { badge_val: "50 km/s", badge_color: "emerald", v: "Nosoz transport vositasini shatakka olishda (barcha yo‘llarda)." },
          { badge_val: "60 km/s", badge_color: "emerald", v: "Aholi punktlarida barcha transport vositalari uchun umumiy ruxsat etilgan tezlik." },
          { badge_val: "70 km/s", badge_color: "emerald", v: "Aholi punktidan tashqarida yuk (>3.5t), avtobus va tirkamali transportlar uchun." },
          { badge_val: "100 km/s", badge_color: "emerald", v: "Aholi punktidan tashqarida yengil avtomobillar va mototsikllar uchun." },
          { badge_val: "110 km/s", badge_color: "emerald", v: "Avtomagistralda yengil avtomobillar uchun ruxsat etilgan yuqori tezlik." },
          { badge_val: "< 40 km/s", badge_color: "emerald", v: "Texnik sabab bilan tezligi 40 dan kam transportlarga avtomagistralda yurish taqiqlanadi." },
          { badge_val: "⚠️ Xavf paydo bo‘lganda", badge_color: "amber", v: "Signal chalish emas — darhol <strong>tezlikni kamaytirish</strong> (zarur bo‘lsa to‘xtash) shart." }
        ]
      },
      {
        tag: "5. SHATAKKA OLISH (BUKSIR) TALABLARI",
        color: "purple",
        search: "shatakka olish buksir qattiq ulagich egiluvchan ulagich tros yaxmalak muzlama",
        layout: "dense",
        items: [
          {
            k: "📏 Ulagich uzunliklari:",
            v: "Qattiq ulagich (shtanga/truba) — <strong>4 metrdan oshmasligi</strong>; Egiluvchan ulagich (tros) — <strong>4 metrdan 6 metrgacha</strong> bo‘lishi va har 1 metriga qizil-oq bayroqcha taqilishi shart."
          },
          {
            k: "❄️ Muzlama (yaxmalak) holatida:",
            v: "Egiluvchan ulagichda (trosda) shatakka olish <strong>QATʼIYAN TAQIQLANADI!</strong> (Faqat qattiq ulagich yoki qisman yuklash usulida mumkin)."
          },
          {
            k: "🏍️ Mototsikllar cheklovi:",
            v: "Kajavasiz ikki g‘ildirakli mototsiklda shatakka olish va uni shatakka olish taqiqlanadi."
          },
          {
            k: "👥 Odam tashish:",
            v: "Shatakka olingan yengil avtomobilda odam bo‘lishi mumkin; avtobus, trolleybus va yuk avtomobili kuzovida odam tashish taqiqlanadi."
          }
        ]
      },
      {
        tag: "6. QATʼIYAN TAQIQLANGAN JOYLAR",
        color: "crimson",
        search: "quvib o'tish taqiqlanadi to'xtash to'xtab turish ostanovka stoyanka taqiqlangan",
        layout: "dense",
        items: [
          {
            k: "🚫 Quvib o‘tish taqiqlanadi:",
            v: "Tartibga solingan chorrahalarda; ikkinchi darajali yo‘lda; piyodalar o‘tish joyida; temir yo‘l kesishmasida va unga 100m qolganda; ko‘prik, yo‘l o‘tkazgich, estakada va ularning ostida; tunnelda; tik do‘ngliklar oxirida va ko‘rinishi cheklangan joylarda."
          },
          {
            k: "⏱️ To‘xtash vs To‘xtab turish:",
            v: "<strong>To‘xtash (ostanovka):</strong> 5 daqiqagacha (yoki yuk/odam uchun qancha zarur bo‘lsa). <strong>To‘xtab turish (stoyanka):</strong> 5 daqiqadan ortiq muddatga to‘xtab turish. \"To‘xtash taqiqlangan\" (X) belgisida stoyanka ham taqiqlanadi."
          },
          {
            k: "👶 Bolalarni tashish (12 yosh):",
            v: "12 yoshga to‘lmagan bolalarni old o‘rindiqda faqat bolalar maxsus o‘rindig‘i (avtokreslo) bilan tashish mumkin. Mototsikl orqa o‘rindig‘ida 12 yoshgacha taqiqlanadi."
          },
          {
            k: "🛣️ Avtomagistral taqiqlari:",
            v: "Orqa bilan harakatlanish; ajratuvchi bo‘lakdagi texnologik uzilishda qayrilib olish; yuk avtomobillariga (>3.5t) 2-bo‘lakdan chapga o‘tish; faqat maxsus maydonchalardan tashqarida to‘xtash."
          },
          {
            k: "📢 Tovush signali (aholi punktida):",
            v: "Faqat <strong>YTH (avariya)ning oldini olish</strong> uchungina ruxsat etiladi (quvib o‘tish yoki salomlashish uchun taqiqlanadi)."
          },
          {
            k: "🦓 Oq-qizil zebra (1.14.2):",
            v: "Faqat <strong>maktab va maktabgacha taʼlim muassasalari</strong> oldidagi xavfli piyodalar o‘tish joylariga chiziladi."
          }
        ]
      },
      {
        tag: "7. TEXNIK SOZLIK VA XAVFSIZLIK MEʼYORLARI",
        color: "purple",
        search: "rul lyufti erkin harakati shina protektori qoldiq balandligi mm gradus",
        layout: "four-col",
        items: [
          { k: "🛞 Rul lyufti (M1):", badge_val: "max 10°", badge_color: "purple", v: "Yengil avtomobillarda ruxsat etilgan erkin yurish." },
          { k: "🛞 Rul lyufti (M2, M3):", badge_val: "max 20°", badge_color: "purple", v: "Avtobuslar va yo‘lovchi tashuvchi transportlar." },
          { k: "🛞 Rul lyufti (N2, N3):", badge_val: "max 25°", badge_color: "purple", v: "To‘la vazni 3.5 t dan ortiq yuk avtomobillari." },
          { k: "🚗 Protektor (M1):", badge_val: "1.6 mm", badge_color: "purple", v: "Yengil avtomobil va kichik yuklar (M1, N1)." },
          { k: "🏍️ Protektor (L):", badge_val: "0.8 mm", badge_color: "purple", v: "Mototsikl va mopedlar uchun minimal chegara." },
          { k: "🚚 Protektor (N2, N3):", badge_val: "1.0 mm", badge_color: "purple", v: "Katta yuk avtomobillari (>3.5 tonna)." },
          { k: "🚌 Protektor (M2, M3):", badge_val: "2.0 mm", badge_color: "purple", v: "Avtobuslar va yo‘lovchi transportlari." },
          { k: "💡 Ko‘z qamashganda:", badge_val: "To‘xtash", badge_color: "amber", v: "Avariya chirog‘ini yoqib, bo‘lakni O‘ZGARTIRMAY to‘xtash!" }
        ]
      },
      {
        tag: "8. BIRINCHI TIBBIY YORDAM MEʼYORLARI",
        color: "emerald",
        search: "tibbiy yordam arterial qon ketish venoz jgut 30:2 reanimatsiya umurtqa",
        layout: "dense",
        items: [
          {
            k: "🩸 Arterial qon ketish (och qizil, favvora):",
            v: "Jgut yaradan <strong>10–15 sm yuqoriga</strong> qo‘yiladi. Muddat: yozda ko‘pi bilan <strong>1 soat</strong>, qishda <strong>30 daqiqa</strong> (vaqt yozilgan qog‘oz qoldiriladi)."
          },
          {
            k: "🩹 Venoz qon ketish (to‘q qizil, bir tekis oqish):",
            v: "Jgut emas, yaraga bevosita <strong>bosuvchi bog‘lam</strong> (davyaщaya povyazka) qo‘yiladi."
          },
          {
            k: "🫀 Jonlantirish (Reanimatsiya):",
            v: "Nisbat doimo <strong>30 ta bosishga 2 ta nafas (30:2)</strong>. Bir kishi bajarsa ham, ikki kishi bajarsa ham 30:2 nisbat o‘zgarmaydi!"
          },
          {
            k: "🦴 Umurtqa pog‘onasi shikastlanganda:",
            v: "Jabrlanuvchi faqat <strong>qattiq tekis taxtada orqasi bilan yotqizilgan holda</strong> tashiladi (yumshoq zambilda taqiqlanadi)."
          }
        ]
      }
    ]
  },

  uz_cyrl: {
    collective: {
      badge: "63.3% Тўғри",
      tag: "Коллектив жавоблар",
      title: '"Барча жавоблар тўғри" / "Санаб ўтилган барча..."',
      desc: 'Базадаги <strong>98 та саволда</strong> коллектив вариантлар мавжуд. Улар <strong>62 та саволда (63.3%) тўғри</strong> келади, лекин <strong>36 та саволда (36.7%) тузоқ</strong>!',
      strategy_title: "⚠️ Тест ечиш стратегияси:",
      strategy_desc: 'Агар саволда битта аниқ ва тор қоида (масалан, фақат битта ҳолатга рухсат) сўралаётган бўлса, коллектив вариант <strong>36.7% ҳолатда тузоқ</strong> бўлади. Фақат вазият бир нечта тўлиқ шартларни бирдек талаб қилгандагина "Барча жавоблар тўғри" ни танланг.'
    },
    high_prob_title: "🌟 Энг юқори эҳтимолли калит сўзлар (70% — 90% Win Rate)",
    high_prob_sub: "Агар саволда иккиланиб қолсангиз, вариант матнидаги ушбу ибораларга қаранг:",
    high_prob_items: [
      {
        search: "шунингдек мураккаб меъёрий қоидаларда",
        term: '"Шунингдек"',
        chip: "88.9% (8/9)",
        domain: "Мураккаб меъёрий қоидаларда",
        hint: "Қонун бандини аниқ ва тўлиқ тушунтирувчи меъёрда келса, деярли ҳар доим тўғри чиқади."
      },
      {
        search: "халақит ҳалақит бермаслик манёвр бурилиш орқага",
        term: '"Халақит / ҳалақит бермаслик"',
        chip: "80.0% (16/22)",
        domain: "Манёвр, бурилиш, орқага юриш",
        hint: "Бошқа иштирокчиларга халақит бермаслик шарти билан қилинган ҳаракатлар қоидага мувофиқ бўлади."
      },
      {
        search: "ишонч ҳосил қилиши ҳаракат бошлаш қайта тизилиш",
        term: '"Ишонч ҳосил [қилиши]"',
        chip: "71.4% (5/7)",
        domain: "Ҳаракат бошлаш ва қайта тизилиш",
        hint: "Манёвр хавфсизлигига ишонч ҳосил қилиш мажбурияти доим энг тўғри жавобдир."
      },
      {
        search: "зарур зарур бўлса хавфсизлик шартлари",
        term: '"Зарур" / "Зарур бўлса"',
        chip: "68.8% (11/16)",
        domain: "Хавфсизлик шартлари",
        hint: "Зарур бўлганда ёрдамдан фойдаланиш ёки тўхташ ҳақидаги вариантлар устундир."
      }
    ],
    trap_title: "🚨 Хавфли тузоқ сўзлар (0% — 15% Win Rate)",
    trap_sub: "Ушбу сўзлар қатнашган вариантлар деярли ҳар доим ХАТО бўлади:",
    trap_items: [
      {
        search: "агар бошқа машина йўқ бўлса транспорт воситаси бўлмаса",
        term: '"Агар бошқа машина йўқ бўлса..."',
        chip: "0.0% (100% Тузоқ)",
        hint: '<em>Мисол: "...агар тўхтаб туриш жойида бошқа машина йўқ бўлса рухсат этилади"</em>. <strong>Тузоқ!</strong> Йўлда машина йўқлиги тақиқланган амални рухсатга айлантирмайди!'
      },
      {
        search: "алоҳида эҳтиёткорлик билан ўтади ҳаракатланади",
        term: '"Алоҳида эҳтиёткорлик билан ўтади"',
        chip: "0.0% (100% Тузоқ)",
        hint: 'ЙҲҚ қатъий қоидадир. "Эҳтиёткорлик билан ўтиб кетаверади" деган гап бўлмайди — қоида аниқ <strong>тўхташни</strong> ёки <strong>йўл беришни</strong> талаб қилади.'
      },
      {
        search: "йўл қўйилмайди тақиқланади",
        term: '"Йўл қўйилмайди"',
        chip: "0.0% Тўғри",
        hint: 'ЙҲҚ расмий юридик тилида доимо <strong>"Тақиқланади"</strong> сўзи қўлланилади. "Йўл қўйилмайди" варианти чалғитувчи сунъий вариантдир.'
      },
      {
        search: "бузмади ҳайдовчи қоидани бузмади",
        term: '"Бузмади" (Қоидани бузмади)',
        chip: "9.1% (91% Бузган!)",
        hint: 'Саволда <em>"Ҳайдовчи қоидани буздими?"</em> деб сўралса, <strong>91% ҳолларда у бузган</strong> бўлади! "Бузмади" варианти 11 та саволдан фақат 1 тасида тўғри.'
      },
      {
        search: "фақат якка ўзи чекланган",
        term: '"Фақат" (якка ўзи келганда)',
        chip: "22.3% Тўғри",
        hint: '"Фақат" сўзи кўпинча қоидани асоссиз торайтириб қўяди (масалан: "Фақат юк автомобилларига"). Шу сабаб 78% ҳолларда хато бўлади.'
      }
    ],
    rules_boxes: [
      {
        tag: "1. ЧОРРАҲАЛАР & ЎТИШ ТАРТИБИ",
        color: "cyan",
        search: "чорраҳа трамвай айланма круг ўнг қўл чапга бурилиш секция стрелка",
        layout: "dense",
        items: [
          {
            k: "🚋 Трамвай устунлиги:",
            v: "Тенг шароитда (ҳар иккиси асосийда ёки яшил чироқда) трамвай бурилишидан қатъи назар <strong>ҳар доим 1-ўринда</strong> ўтади! Фақат 2 ҳолда йўл беради: деподан чиқишда ва \"Йўл беринг\" белгисида."
          },
          {
            k: "🔄 Айланма ҳаракат (4.3):",
            v: "Айланма ҳаракатдаги автомобиль айланмага кириб келаётганларга нисбатан <strong>устунликка эга</strong> (айланмадаги доим асосий)."
          },
          {
            k: "👉 Ўнг қўл қоидаси:",
            v: "Тенг аҳамиятли чорраҳаларда ва бир вақтда ўзаро қайта тизилишда доим <strong>ўнг томондан</strong> келаётган транспортга йўл берилади."
          },
          {
            k: "↩️ Чапга бурилиш / Қайрилиш:",
            v: "Рўпарадан тўғрига ва ўнгга ҳаракатланаётган барча транспорт воситаларига <strong>йўл бериш шарт</strong>."
          },
          {
            k: "🟢 Яшил стрелка + Қизил чироқ:",
            v: "Қўшимча тармоқ ёнганда бурилиш мумкин, лекин бошқа йўналишдаги <strong>барча транспортларга йўл бериш шарт</strong>!"
          },
          {
            k: "⏳ Ким охирги ўтади:",
            v: "Иккинчи даражали йўлда турган ёки чапга бурилаётган транспорт қарама-қарши ва асосий йўлдагиларга йўл бериб, чорраҳадан <strong>охирги бўлиб</strong> ўтади."
          },
          {
            k: "🛑 \"Йўл беринг\" (2.4) белгиси:",
            v: "Бошқа йўналишдаги барча транспорт воситаларига <strong>йўл бериш шарт</strong> (ҳатто трамвай ҳам ушбу белгида бошқаларга йўл беради)."
          }
        ]
      },
      {
        tag: "2. ТАРТИБГА СОЛУВЧИ (РЕГУЛИРОВЩИК) ИШОРАЛАРИ",
        color: "amber",
        search: "тартибга солувчи регулировщик ишоралари шлагбаум девор тўхта",
        layout: "three-col",
        items: [
          {
            item_class: "reg-red",
            k: "🛑 Қўли тепада:",
            v: "<strong>Қизил чироққа тенг!</strong> Барча транспортлар ва пиёдалар учун ҳаракат қатъиян тақиқланади (ҳамма тўхтайди)."
          },
          {
            item_class: "reg-yellow",
            k: "🧍 Қўллар тушган / Ёнга:",
            v: "• <strong>Кўкрак ва орқа — Девор:</strong> Тақиқланади!<br>• <strong>Ён томондан:</strong> Тўғрига ва ўнгга рухсат. Трамвай фақат тўғрига (\"енгдан кириб енгдан чиқади\")."
          },
          {
            item_class: "reg-green",
            k: "👉 Ўнг қўл олдинга:",
            v: "• <strong>Кўкракдан:</strong> Фақат ўнгга.<br>• <strong>Чап ёндан:</strong> Ҳамма томонга (тўғри, ўнг, чап, қайрилиш).<br>• <strong>Орқаси ва ўнг ёни:</strong> Қатъиян тақиқланган!"
          }
        ]
      },
      {
        tag: "3. ИМТИҲОНДА ТУШАДИГАН АНИҚ МАСОФАЛАР",
        color: "cyan",
        search: "масофалар 2.5м 5м 15м 30м 50м 100м 150м метр",
        layout: "four-col",
        items: [
          { badge_val: "2.5 м", v: "Тўхтаган автомобиль ва узлуксиз чизиқ орасида камида 3м бўлиши шарт (2.5м бўлса тўхташ тақиқланади)." },
          { badge_val: "5 м", v: "Пиёдалар ўтиш жойи олдида тўхташ (орқасида эмас!) ва қатнов қисми кесишмаси четидан масофа." },
          { badge_val: "15 м", v: "Бекатлар (автобус/трамвай) ва темир йўл рельси олдида тўхтаб туриш; аҳоли пунктида авария белгиси." },
          { badge_val: "30 м", v: "Аҳоли пунктидан ташқарида авария тўхташ белгисини ўрнатиш масофаси (камида 30м)." },
          { badge_val: "50 м", v: "Темир йўл кесишмасидан олдин тўхтаб туриш (стоянка) тақиқланади." },
          { badge_val: "100 м", v: "Темир йўл кесишмасига 100 метр қолганда қувиб ўтиш қатъиян тақиқланади." },
          { badge_val: "50–100 м", v: "Аҳоли пунктларида огоҳлантирувчи йўл белгилари ўрнатилиш масофаси." },
          { badge_val: "150–300 м", v: "Аҳоли пунктидан ташқарида огоҳлантирувчи йўл белгилари ўрнатилиш масофаси." }
        ]
      },
      {
        tag: "4. БЕЛГИЛАНГАН ТЕЗЛИК МЕЪЁРЛАРИ (КМ/СОАТ)",
        color: "emerald",
        search: "тезлик меъёрлари 20 30 50 60 70 100 110 км/соат",
        layout: "four-col",
        items: [
          { badge_val: "20 км/с", badge_color: "emerald", v: "Турар жой даҳаси (жилой зона), ҳовлилар ва велосипед зоналари." },
          { badge_val: "30 км/с", badge_color: "emerald", v: "Мактаблар ва мактабгача таълим муассасалари олдидаги йўлларда." },
          { badge_val: "50 км/с", badge_color: "emerald", v: "Носоз транспорт воситасини шатакка олишда (барча йўлларда)." },
          { badge_val: "60 км/с", badge_color: "emerald", v: "Аҳоли пунктларида барча транспорт воситалари учун умумий рухсат этилган тезлик." },
          { badge_val: "70 км/с", badge_color: "emerald", v: "Аҳоли пунктидан ташқарида юк (>3.5т), автобус ва тиркамали транспортлар учун." },
          { badge_val: "100 км/с", badge_color: "emerald", v: "Аҳоли пунктидан ташқарида енгил автомобиллар ва мотоцикллар учун." },
          { badge_val: "110 км/с", badge_color: "emerald", v: "Автомагистралда енгил автомобиллар учун рухсат этилган юқори тезлик." },
          { badge_val: "< 40 км/с", badge_color: "emerald", v: "Техник сабаб билан тезлиги 40 дан кам транспортларга автомагистралда юриш тақиқланади." },
          { badge_val: "⚠️ Хавф пайдо бўлганда", badge_color: "amber", v: "Сигнал чалиш эмас — дарҳол <strong>тезликни камайтириш</strong> (зарур бўлса тўхташ) шарт." }
        ]
      },
      {
        tag: "5. ШАТАККА ОЛИШ (БУКСИР) ТАЛАБЛАРИ",
        color: "purple",
        search: "шатакка олиш буксир қаттиқ улагич эгилувчан улагич трос яхмалак музлама",
        layout: "dense",
        items: [
          {
            k: "📏 Улагич узунликлари:",
            v: "Қаттиқ улагич (штанга/труба) — <strong>4 метрдан ошмаслиги</strong>; Эгилувчан улагич (трос) — <strong>4 метрдан 6 метргача</strong> бўлиши ва ҳар 1 метрига қизил-оқ байроқча тақилиши шарт."
          },
          {
            k: "❄️ Музлама (яхмалак) ҳолатида:",
            v: "Эгилувчан улагичда (тросда) шатакка олиш <strong>ҚАТЪИЯН ТАҚИҚЛАНАДИ!</strong> (Фақат қаттиқ улагич ёки қисман юклаш усулида мумкин)."
          },
          {
            k: "🏍️ Мотоцикллар чеклови:",
            v: "Кажавасиз икки ғилдиракли мотоциклда шатакка олиш ва уни шатакка олиш тақиқланади."
          },
          {
            k: "👥 Одам ташиш:",
            v: "Шатакка олинган енгил автомобилда одам бўлиши мумкин; автобус, троллейбус ва юк автомобили кузовида одам ташиш тақиқланади."
          }
        ]
      },
      {
        tag: "6. ҚАТЪИЯН ТАҚИҚЛАНГАН ЖОЙЛАР",
        color: "crimson",
        search: "қувиб ўтиш тақиқланади тўхташ тўхтаб туриш остановка стоянка тақиқланган",
        layout: "dense",
        items: [
          {
            k: "🚫 Қувиб ўтиш тақиқланади:",
            v: "Тартибга солинган чорраҳаларда; иккинчи даражали йўлда; пиёдалар ўтиш жойида; темир йўл кесишмасида ва унга 100м қолганда; кўприк, йўл ўтказгич, эстакада ва уларнинг остида; туннелда; тик дўнгликлар охирида ва кўриниши чекланган жойларда."
          },
          {
            k: "⏱️ Тўхташ vs Тўхтаб туриш:",
            v: "<strong>Тўхташ (остановка):</strong> 5 дақиқагача (ёки юк/одам учун қанча зарур бўлса). <strong>Тўхтаб туриш (стоянка):</strong> 5 дақиқадан ортиқ муддатга тўхтаб туриш. \"Тўхташ тақиқланган\" (X) белгисида стоянка ҳам тақиқланади."
          },
          {
            k: "👶 Болаларни ташиш (12 ёш):",
            v: "12 ёшга тўлмаган болаларни олд ўриндиқда фақат болалар махсус ўриндиғи (автокресло) билан ташиш мумкин. Мотоцикл орқа ўриндиғида 12 ёшгача тақиқланади."
          },
          {
            k: "🛣️ Автомагистрал тақиқлари:",
            v: "Орқа билан ҳаракатланиш; ажратувчи бўлакдаги технологик узилишда қайрилиб олиш; юк автомобилларига (>3.5т) 2-бўлакдан чапга ўтиш; фақат махсус майдончалардан ташқарида тўхташ."
          },
          {
            k: "📢 Товуш сигнали (аҳоли пунктида):",
            v: "Фақат <strong>ЙТҲ (авария)нинг олдини олиш</strong> учунгина рухсат этилади (қувиб ўтиш ёки саломлашиш учун тақиқланади)."
          },
          {
            k: "🦓 Оқ-қизил зебра (1.14.2):",
            v: "Фақат <strong>мактаб ва мактабгача таълим муассасалари</strong> олдидаги хавфли пиёдалар ўтиш жойларига чизилади."
          }
        ]
      },
      {
        tag: "7. ТЕХНИК СОЗЛИК ВА ХАВФСИЗЛИК МЕЪЁРЛАРИ",
        color: "purple",
        search: "рул люфти эркин ҳаракати шина протектори қолдиқ баландлиги мм градус",
        layout: "four-col",
        items: [
          { k: "🛞 Рул люфти (M1):", badge_val: "max 10°", badge_color: "purple", v: "Енгил автомобилларда рухсат этилган эркин юриш." },
          { k: "🛞 Рул люфти (M2, M3):", badge_val: "max 20°", badge_color: "purple", v: "Автобуслар ва йўловчи ташувчи транспортлар." },
          { k: "🛞 Рул люфти (N2, N3):", badge_val: "max 25°", badge_color: "purple", v: "Тўла вазни 3.5 т дан ортиқ юк автомобиллари." },
          { k: "🚗 Протектор (M1):", badge_val: "1.6 мм", badge_color: "purple", v: "Енгил автомобиль ва кичик юклар (M1, N1)." },
          { k: "🏍️ Протектор (L):", badge_val: "0.8 мм", badge_color: "purple", v: "Мотоцикл ва мопедлар учун минимал чегара." },
          { k: "🚚 Протектор (N2, N3):", badge_val: "1.0 мм", badge_color: "purple", v: "Катта юк автомобиллари (>3.5 тонна)." },
          { k: "🚌 Протектор (M2, M3):", badge_val: "2.0 мм", badge_color: "purple", v: "Автобуслар ва йўловчи транспортлари." },
          { k: "💡 Кўз қамашганда:", badge_val: "Тўхташ", badge_color: "amber", v: "Авария чироғини ёқиб, бўлакни ЎЗГАРТИРМАЙ тўхташ!" }
        ]
      },
      {
        tag: "8. БИРИНЧИ ТИББИЙ ЁРДАМ МЕЪЁРЛАРИ",
        color: "emerald",
        search: "тиббий ёрдам артериал қон кетиш веноз жгут 30:2 реанимация умуртқа",
        layout: "dense",
        items: [
          {
            k: "🩸 Артериал қон кетиш (оч қизил, фаввора):",
            v: "Жгут ярадан <strong>10–15 см юқорига</strong> қўйилади. Муддат: ёзда кўпи билан <strong>1 соат</strong>, қишда <strong>30 дақиқа</strong> (вақт ёзилган қоғоз қолдирилади)."
          },
          {
            k: "🩹 Веноз қон кетиш (тўқ қизил, бир текис оқиш):",
            v: "Жгут эмас, ярага бевосита <strong>босувчи боғлам</strong> (давящая повязка) қўйилади."
          },
          {
            k: "🫀 Жонлантириш (Реанимация):",
            v: "Нисбат доимо <strong>30 та босишга 2 та нафас (30:2)</strong>. Бир киши бажарса ҳам, икки киши бажарса ҳам 30:2 нисбат ўзгармайди!"
          },
          {
            k: "🦴 Умуртқа поғонаси шикастланганда:",
            v: "Жабрланувчи фақат <strong>қаттиқ текис тахтада орқаси билан ётқизилган ҳолда</strong> ташилади (юмшоқ замбилда тақиқланади)."
          }
        ]
      }
    ]
  },

  ru: {
    collective: {
      badge: "63.3% Верно",
      tag: "Коллективные ответы",
      title: '"Все ответы правильные" / "Все перечисленные..."',
      desc: 'В базе <strong>98 вопросов</strong> содержат коллективные варианты. Они являются <strong>правильными в 62 вопросах (63.3%)</strong>, но в <strong>36 вопросах (36.7%) это ловушка</strong>!',
      strategy_title: "⚠️ Стратегия решения теста:",
      strategy_desc: 'Если в вопросе спрашивается одно конкретное узкое правило (например, разрешение только в одном случае), коллективный ответ в <strong>36.7% случаев является ловушкой</strong>. Выбирайте "Все ответы верны" только тогда, когда ситуация равносильно требует нескольких условий одновременно.'
    },
    high_prob_title: "🌟 Ключевые слова с высокой вероятностью (70% — 90% Win Rate)",
    high_prob_sub: "Если вы сомневаетесь в ответе, обратите внимание на следующие фразы в тексте вариантов:",
    high_prob_items: [
      {
        search: "а также также сложных нормативных правилах",
        term: '"А также"',
        chip: "88.9% (8/9)",
        domain: "В сложных нормативных правилах",
        hint: "Если фраза формулирует точную и полную юридическую норму, она почти всегда является верной."
      },
      {
        search: "не создавая помех маневр поворот задний ход",
        term: '"Не создавая помех"',
        chip: "80.0% (16/22)",
        domain: "Манёвр, поворот, движение задним ходом",
        hint: "Действия, совершаемые при условии ненарушения движения других участников, соответствуют ПДД."
      },
      {
        search: "убедившись в безопасности начало движения перестроение",
        term: '"Убедившись [в безопасности]"',
        chip: "71.4% (5/7)",
        domain: "Начало движения и перестроение",
        hint: "Обязанность водителя убедиться в безопасности своего манёвра всегда является правильным ответом."
      },
      {
        search: "при необходимости необходимо условия безопасности",
        term: '"При необходимости" / "Необходимо"',
        chip: "68.8% (11/16)",
        domain: "Условия безопасности",
        hint: "Варианты, требующие прибегнуть к помощи или остановиться при необходимости, имеют приоритет."
      }
    ],
    trap_title: "🚨 Опасные слова-ловушки (0% — 15% Win Rate)",
    trap_sub: "Варианты, содержащие эти формулировки, практически всегда ОШИБОЧНЫ:",
    trap_items: [
      {
        search: "если нет других транспортных средств машин стоянка",
        term: '"Если нет других машин..."',
        chip: "0.0% (100% Ловушка)",
        hint: '<em>Пример: "...разрешается, если на стоянке нет других машин"</em>. <strong>Ловушка!</strong> Отсутствие транспорта не отменяет установленный запрет ПДД!'
      },
      {
        search: "с особой осторожностью двигается осторожно",
        term: '"С особой осторожностью"',
        chip: "0.0% (100% Ловушка)",
        hint: 'В ПДД нет размытых уступок вроде "проехать осторожно" — правило строго обязывает либо <strong>остановиться</strong>, либо <strong>уступить дорогу</strong>.'
      },
      {
        search: "не допускается запрещается запрещено",
        term: '"Не допускается"',
        chip: "0.0% Верно",
        hint: 'В официальном тексте ПДД всегда используется слово <strong>"Запрещается"</strong>. Вариант "Не допускается" — искусственная отвлекающая формулировка.'
      },
      {
        search: "не нарушил правила не нарушил водитель",
        term: '"Не нарушил" (Правила не нарушил)',
        chip: "9.1% (91% Нарушил!)",
        hint: 'Если в вопросе спрашивается: <em>"Нарушил ли водитель правила?"</em>, в <strong>91% случаев он нарушил</strong>! Вариант "Не нарушил" верен лишь в 1 из 11 вопросов.'
      },
      {
        search: "только исключительный сужает",
        term: '"Только" (при изолированном употреблении)',
        chip: "22.3% Верно",
        hint: 'Слово "Только" необоснованно сужает норму (напр.: "Только грузовым автомобилям"). Поэтому в 78% случаев этот ответ неверен.'
      }
    ],
    rules_boxes: [
      {
        tag: "1. ПЕРЕКРЁСТКИ И ПОРЯДОК ПРОЕЗДА",
        color: "cyan",
        search: "перекресток трамвай круговое движение помеха справа поворот налево секция стрелка уступите дорогу",
        layout: "dense",
        items: [
          {
            k: "🚋 Приоритет трамвая:",
            v: "При равных условиях (оба на главной или на зелёный сигнал) трамвай независимо от направления поворота <strong>всегда проезжает первым</strong>! Уступает лишь в 2 случаях: при выезде из депо и при знаке \"Уступите дорогу\"."
          },
          {
            k: "🔄 Круговое движение (4.3):",
            v: "Транспорт на круговом движении имеет <strong>приоритет</strong> перед въезжающими на круг (движущийся по кругу всегда на главной дороге)."
          },
          {
            k: "👉 Помеха справа:",
            v: "На равнозначных перекрёстках и при одновременном взаимном перестроении всегда уступают транспорту, приближающемуся <strong>справа</strong>."
          },
          {
            k: "↩️ Поворот налево / Разворот:",
            v: "Обязательно <strong>уступить дорогу</strong> всем транспортным средствам, движущимся со встречного направления прямо и направо."
          },
          {
            k: "🟢 Зелёная стрелка + Красный сигнал:",
            v: "Поворот при дополнительной секции разрешён, но с обязательным требованием <strong>уступить дорогу всем ТС</strong> других направлений!"
          },
          {
            k: "⏳ Кто проедет последним:",
            v: "Транспорт на второстепенной дороге или поворачивающий налево, уступая встречным и главной дороге, покидает перекрёсток <strong>последним</strong>."
          },
          {
            k: "🛑 Знак \"Уступите дорогу\" (2.4):",
            v: "Обязательно <strong>уступить дорогу всем ТС</strong> других направлений (даже трамвай при этом знаке обязан уступить дорогу другим участникам)."
          }
        ]
      },
      {
        tag: "2. СИГНАЛЫ РЕГУЛИРОВЩИКА",
        color: "amber",
        search: "регулировщик сигналы шлагбаум стена стой",
        layout: "three-col",
        items: [
          {
            item_class: "reg-red",
            k: "🛑 Рука поднята вверх:",
            v: "<strong>Равносильно красному сигналу!</strong> Движение всех транспортных средств и пешеходов строго запрещено (все останавливаются)."
          },
          {
            item_class: "reg-yellow",
            k: "🧍 Руки опущены / в стороны:",
            v: "• <strong>Со стороны груди и спины — Стена:</strong> Движение запрещено!<br>• <strong>С боков:</strong> Разрешено прямо и направо. Трамваю — только прямо (\"из рукава в рукав\")."
          },
          {
            item_class: "reg-green",
            k: "👉 Правая рука вытянута вперёд:",
            v: "• <strong>Со стороны груди:</strong> Только направо.<br>• <strong>С левого бока:</strong> Во всех направлениях (прямо, направо, налево, разворот).<br>• <strong>Со спины и правого бока:</strong> Категорически запрещено!"
          }
        ]
      },
      {
        tag: "3. ТОЧНЫЕ ДИСТАНЦИИ И РАССТОЯНИЯ НА ЭКЗАМЕНЕ",
        color: "cyan",
        search: "дистанции расстояния 2.5м 5м 15м 30м 50м 100м 150м метр метры",
        layout: "four-col",
        items: [
          { badge_val: "2.5 м", v: "Между остановившимся ТС и сплошной линией должно быть не менее 3м (если 2.5м — остановка запрещена)." },
          { badge_val: "5 м", v: "Остановка перед пешеходным переходом (не за ним!) и расстояние от края пересекаемой проезжей части." },
          { badge_val: "15 м", v: "Стоянка у остановок маршрутных ТС и ближе 15м до рельсов; знак аварийной остановки в населённом пункте." },
          { badge_val: "30 м", v: "Расстояние установки знака аварийной остановки вне населённого пункта (не менее 30м)." },
          { badge_val: "50 м", v: "Запрещается стоянка ближе 50 метров до железнодорожного переезда." },
          { badge_val: "100 м", v: "Обгон категорически запрещён ближе чем за 100 метров перед железнодорожным переездом." },
          { badge_val: "50–100 м", v: "Расстояние установки предупреждающих знаков в населённых пунктах." },
          { badge_val: "150–300 м", v: "Расстояние установки предупреждающих знаков вне населённых пунктов." }
        ]
      },
      {
        tag: "4. СКОРОСТНЫЕ ЛИМИТЫ (КМ/Ч)",
        color: "emerald",
        search: "скоростные лимиты скорость 20 30 50 60 70 100 110 км/ч",
        layout: "four-col",
        items: [
          { badge_val: "20 км/ч", badge_color: "emerald", v: "Жилые зоны, дворовые территории и велосипедные зоны." },
          { badge_val: "30 км/ч", badge_color: "emerald", v: "На участках дорог вблизи школ и дошкольных учреждений." },
          { badge_val: "50 км/ч", badge_color: "emerald", v: "При буксировке механических транспортных средств (на всех дорогах)." },
          { badge_val: "60 км/ч", badge_color: "emerald", v: "В населённых пунктах разрешённая скорость для всех транспортных средств." },
          { badge_val: "70 км/ч", badge_color: "emerald", v: "Вне населённых пунктов для грузовых (>3.5т), автобусов и ТС с прицепом." },
          { badge_val: "100 км/ч", badge_color: "emerald", v: "Вне населённых пунктов для легковых автомобилей и мотоциклов." },
          { badge_val: "110 км/ч", badge_color: "emerald", v: "На автомагистралях максимальная скорость для легковых автомобилей." },
          { badge_val: "< 40 км/ч", badge_color: "emerald", v: "ТС, скорость которых по техпричинам менее 40 км/ч, запрещено движение по автомагистрали." },
          { badge_val: "⚠️ При опасности", badge_color: "amber", v: "Не подавать звуковой сигнал, а немедленно <strong>снизить скорость</strong> (вплоть до остановки)." }
        ]
      },
      {
        tag: "5. ТРЕБОВАНИЯ К БУКСИРОВКЕ",
        color: "purple",
        search: "буксировка жесткая сцепка гибкая трос гололедица гололед",
        layout: "dense",
        items: [
          {
            k: "📏 Длина связующих звеньев:",
            v: "Жёсткая сцепка (штанга/труба) — <strong>не более 4 метров</strong>; Гибкая сцепка (трос) — <strong>от 4 до 6 метров</strong> с флажками/щитками через каждый 1 метр."
          },
          {
            k: "❄️ В условиях гололедицы:",
            v: "Буксировка на гибкой сцепке в гололедицу <strong>КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНА!</strong> (Разрешена только на жёсткой сцепке или методом частичной погрузки)."
          },
          {
            k: "🏍️ Ограничения для мотоциклов:",
            v: "Запрещается буксировка двухколёсными мотоциклами без бокового прицепа, а также буксировка таких мотоциклов."
          },
          {
            k: "👥 Перевозка людей:",
            v: "В буксируемом легковом автомобиле перевозка людей разрешена; в буксируемом автобусе, троллейбусе и кузове грузовика — запрещена."
          }
        ]
      },
      {
        tag: "6. МЕСТА СТРОГОГО ЗАПРЕТА",
        color: "crimson",
        search: "обгон запрещен остановка стоянка запрещена автомагистраль сигнал дети",
        layout: "dense",
        items: [
          {
            k: "🚫 Обгон запрещён:",
            v: "На регулируемых перекрёстках; на второстепенных дорогах; на пешеходных переходах; на ж/д переездах и за 100м до них; на мостах, путепроводах, эстакадах и под ними; в тоннелях; в конце подъёмов и на опасных поворотах."
          },
          {
            k: "⏱️ Остановка vs Стоянка:",
            v: "<strong>Остановка:</strong> преднамеренное прекращение движения до 5 минут (или более для посадки/высадки, погрузки). <strong>Стоянка:</strong> более 5 минут по иным причинам. При знаке \"Остановка запрещена\" запрещена и стоянка."
          },
          {
            k: "👶 Перевозка детей (до 12 лет):",
            v: "Перевозка детей до 12 лет на переднем сиденье разрешена только в специальном детском автокресле. На заднем сиденье мотоцикла детям до 12 лет находиться запрещено."
          },
          {
            k: "🛣️ Запреты на автомагистрали:",
            v: "Движение задним ходом; разворот в технологических разрывах разделительной полосы; выезд грузовых (>3.5т) далее второй полосы; остановка вне специально отведённых площадок."
          },
          {
            k: "📢 Звуковой сигнал (в населённых пунктах):",
            v: "Разрешён исключительно <strong>для предотвращения ДТП</strong> (для обгона или привлечения внимания запрещён)."
          },
          {
            k: "🦓 Красно-белая зебра (1.14.2):",
            v: "Наносится на опасных пешеходных переходах исключительно вблизи <strong>школ и детских дошкольных учреждений</strong>."
          }
        ]
      },
      {
        tag: "7. ТЕХНИЧЕСКОЕ СОСТОЯНИЕ И БЕЗОПАСНОСТЬ",
        color: "purple",
        search: "люфт руля рулевое управление протектор шины глубина ослепление фары",
        layout: "four-col",
        items: [
          { k: "🛞 Люфт руля (M1):", badge_val: "max 10°", badge_color: "purple", v: "Легковые автомобили (допустимый свободный ход)." },
          { k: "🛞 Люфт руля (M2, M3):", badge_val: "max 20°", badge_color: "purple", v: "Автобусы и пассажирский транспорт." },
          { k: "🛞 Люфт руля (N2, N3):", badge_val: "max 25°", badge_color: "purple", v: "Грузовые автомобили с разрешённой массой более 3.5 тонн." },
          { k: "🚗 Протектор (M1):", badge_val: "1.6 мм", badge_color: "purple", v: "Легковые автомобили и малые грузовые (M1, N1)." },
          { k: "🏍️ Протектор (L):", badge_val: "0.8 мм", badge_color: "purple", v: "Минимальный порог для мотоциклов и мопедов." },
          { k: "🚚 Протектор (N2, N3):", badge_val: "1.0 мм", badge_color: "purple", v: "Крупные грузовые автомобили (>3.5 тонн)." },
          { k: "🚌 Протектор (M2, M3):", badge_val: "2.0 мм", badge_color: "purple", v: "Автобусы и пассажирский транспорт." },
          { k: "💡 При ослеплении:", badge_val: "Остановка", badge_color: "amber", v: "Включить аварийную световую сигнализацию и, НЕ МЕНЯЯ полосы, остановиться!" }
        ]
      },
      {
        tag: "8. ПЕРВАЯ МЕДИЦИНСКАЯ ПОМОЩЬ",
        color: "emerald",
        search: "медицинская помощь артериальное кровотечение венозное жгут 30:2 реанимация позвоночник",
        layout: "dense",
        items: [
          {
            k: "🩸 Артериальное кровотечение (алая кровь, фонтан):",
            v: "Жгут накладывается <strong>на 10–15 см выше раны</strong>. Время: летом максимум <strong>1 час</strong>, зимой <strong>30 минут</strong> (с обязательной запиской точного времени)."
          },
          {
            k: "🩹 Венозное кровотечение (тёмно-вишнёвая кровь):",
            v: "Жгут не накладывается, на рану накладывается непосредственная <strong>давящая повязка</strong>."
          },
          {
            k: "🫀 Реанимация (СЛР):",
            v: "Соотношение всегда строго <strong>30 нажатий на грудину к 2 вдохам (30:2)</strong>, независимо от того, сколько спасателей оказывают помощь!"
          },
          {
            k: "🦴 При травме позвоночника:",
            v: "Пострадавшего транспортируют только на <strong>твёрдом ровном щите лёжа на спине</strong> (на мягких носилках транспортировка категорически запрещена)."
          }
        ]
      }
    ]
  }
};
