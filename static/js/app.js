/**
 * RULLY — ELITE DIGITAL COCKPIT CONTROLLER & TELEGRAM MINI APP SPA
 * Orchestrates multi-view navigation, real-time readiness telemetry,
 * interactive exam simulation, SVG iconography, and 3-language hot switching.
 */

(function () {
  'use strict';

  // 1. Telegram WebApp Integration & Viewport Setup
  if (window.__NOT_TELEGRAM__) {
    try {
      document.body.innerHTML = '';
      document.documentElement.style.display = 'none';
    } catch (e) {}
    return;
  }

  const tg = window.Telegram?.WebApp;

  function resolveTelegramInitData() {
    // 1. Official WebApp object
    let data = window.Telegram?.WebApp?.initData || "";
    if (data && data.length > 5) {
      try { sessionStorage.setItem('rully_tg_init_data', data); } catch (e) {}
      return data;
    }

    // 2. URL hash search (e.g. #tgWebAppData=... or #...&tgWebAppData=...)
    try {
      const hashStr = window.location.hash.replace(/^#/, '');
      if (hashStr.includes('tgWebAppData=')) {
        const hashParams = new URLSearchParams(hashStr);
        const fromHash = hashParams.get('tgWebAppData');
        if (fromHash && fromHash.length > 5) {
          try { sessionStorage.setItem('rully_tg_init_data', fromHash); } catch (e) {}
          return fromHash;
        }
      }
    } catch (e) {}

    // 3. URL query search (?tgWebAppData=...)
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const fromQuery = urlParams.get('tgWebAppData');
      if (fromQuery && fromQuery.length > 5) {
        try { sessionStorage.setItem('rully_tg_init_data', fromQuery); } catch (e) {}
        return fromQuery;
      }
    } catch (e) {}

    // 4. Session Storage cache from earlier in this session
    try {
      const cached = sessionStorage.getItem('rully_tg_init_data');
      if (cached && cached.length > 5 && cached !== 'dev_user_8809526955') return cached;
    } catch (e) {}

    // Strict: not in Telegram, return empty string
    return "";
  }

  let initData = resolveTelegramInitData();

  if (!initData) {
    try {
      document.body.innerHTML = '';
      document.documentElement.style.display = 'none';
    } catch (e) {}
    return;
  }

  if (tg) {
    try {
      tg.ready();
      tg.expand();
      if (tg.disableVerticalSwipes) {
        tg.disableVerticalSwipes();
      }
      tg.headerColor = '#070a13';
      tg.backgroundColor = '#070a13';
    } catch (e) {}
  }

  // 2. Application Reactive State
  const state = {
    authPending: true,
    user: null,
    lang: 'uz_latn',
    stats: null,
    readinessScore: 0,
    categories: [],
    activeTab: 'home',
    // Quiz / Exam Engine State
    quiz: {
      active: false,
      sessionId: null,
      sessionType: 'EXAM',
      questions: [],
      currentIndex: 0,
      answers: {},
      timeRemaining: 25 * 60,
      timerInterval: null,
      startTime: null,
      isSubmitting: false
    },
    // Practical Curriculum State
    modules: [],
    // Subscription & Monetization State
    subscription: {
      is_pro: false,
      tier: 'free',
      tier_name: 'Oddiy tarif (Tekin)',
      expires_at: null,
      days_left: 0,
      is_active: false
    },
    selectedPlanId: 'pro_14',
    lastAuthAt: 0,
    history: null
  };

  // 3. Tactile Haptic Feedback Controller
  function triggerHaptic(type = 'impact', style = 'light') {
    if (!tg?.HapticFeedback) return;
    try {
      if (type === 'impact') tg.HapticFeedback.impactOccurred(style);
      else if (type === 'notification') tg.HapticFeedback.notificationOccurred(style);
    } catch (e) {}
  }

  // 4. Localization Engine
  function t(key, params = {}) {
    const dict = window.I18N?.[state.lang] || window.I18N?.['uz_latn'] || {};
    let str = dict[key] || key;
    for (const [k, v] of Object.entries(params)) {
      str = str.replace(new RegExp(`\\{${k}\\}`, 'g'), v);
    }
    return str;
  }

  function renderAiChips() {
    const chipsWrap = document.getElementById('ai-quick-chips');
    if (!chipsWrap) return;
    chipsWrap.innerHTML = `
      <button type="button" class="ai-chip-btn" data-prompt="${t('ai_chip_1_prompt')}">
        ${t('ai_chip_1_label')}
      </button>
      <button type="button" class="ai-chip-btn" data-prompt="${t('ai_chip_2_prompt')}">
        ${t('ai_chip_2_label')}
      </button>
      <button type="button" class="ai-chip-btn" data-prompt="${t('ai_chip_3_prompt')}">
        ${t('ai_chip_3_label')}
      </button>
      <button type="button" class="ai-chip-btn" data-prompt="${t('ai_chip_4_prompt')}">
        ${t('ai_chip_4_label')}
      </button>
    `;
  }

  function applyLocalization() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      el.textContent = t(key);
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      el.setAttribute('placeholder', t(key));
    });

    document.querySelectorAll('[data-i18n-html]').forEach(el => {
      const key = el.getAttribute('data-i18n-html');
      el.innerHTML = t(key);
    });

    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      el.setAttribute('title', t(key));
    });

    // Update Language Pill Label
    const langLabel = document.getElementById('header-lang-label');
    if (langLabel) {
      langLabel.textContent = state.lang === 'uz_latn' ? 'UZ' : (state.lang === 'uz_cyrl' ? 'УЗ' : 'РУ');
    }

    // Refresh dynamic telemetry descriptors
    updateReadinessClusterUI();
    updateSubscriptionUI();
    if (typeof renderPlatformRulesModal === 'function' && document.getElementById('platform-rules-modal')?.classList.contains('active')) {
      renderPlatformRulesModal();
    }
    if (typeof renderVersionHistoryModal === 'function' && document.getElementById('version-history-modal')?.classList.contains('active')) {
      renderVersionHistoryModal();
    }
    renderCheatsheetContent();
    renderAiChips();
    if (typeof updateSavedQuestionsCount === 'function') {
      updateSavedQuestionsCount();
    }
  }
  function renderCheatsheetContent() {
    const bodyEl = document.getElementById('secrets-modal-body');
    if (!bodyEl || !window.CHEATSHEET_DATA) return;

    const lang = state.lang || 'uz_latn';
    const data = window.CHEATSHEET_DATA[lang] || window.CHEATSHEET_DATA['uz_latn'];
    if (!data) return;

    // Check currently active tab to keep user position
    const currentRules = document.getElementById('pane-rules');
    const isRulesActive = currentRules ? currentRules.classList.contains('active') : false;

    // 1. Tab 1: Keywords & Traps
    const c = data.collective || {};
    const colHtml = c.title ? `
      <div class="secret-card highlight-card" data-search="${(c.title + ' ' + (c.tag || '')).toLowerCase()}">
        <div class="secret-card-header">
          <span class="secret-badge emerald">${c.badge || ''}</span>
          <span class="secret-cat-tag">${c.tag || ''}</span>
        </div>
        <h4 class="secret-card-title">${c.title || ''}</h4>
        <p class="secret-card-desc">${c.desc || ''}</p>
        <div class="secret-alert-box amber">
          <strong>${c.strategy_title || ''}</strong>
          <p class="secret-card-desc" style="font-size: 11.5px; margin-top: 4px; color: #cbd5e1;">${c.strategy_desc || ''}</p>
        </div>
      </div>
    ` : '';

    const highProbItems = (data.high_prob_items || []).map(item => `
      <div class="secret-item-card" data-search="${item.search || ''}">
        <div class="secret-item-top">
          <span class="secret-term emerald">${item.term || ''}</span>
          <span class="secret-stat-chip emerald">${item.chip || ''}</span>
        </div>
        <div class="secret-item-meta">
          <span class="secret-domain">${item.domain || ''}</span>
        </div>
        <p class="secret-item-hint">${item.hint || ''}</p>
      </div>
    `).join('');

    const highProbHtml = `
      <h4 class="secrets-section-title">${data.high_prob_title || ''}</h4>
      <p class="secrets-section-sub">${data.high_prob_sub || ''}</p>
      <div class="secret-items-grid">
        ${highProbItems}
      </div>
    `;

    const trapItems = (data.trap_items || []).map(item => `
      <div class="secret-item-card trap-border" data-search="${item.search || ''}">
        <div class="secret-item-top">
          <span class="secret-term crimson">${item.term || ''}</span>
          <span class="secret-stat-chip crimson">${item.chip || ''}</span>
        </div>
        <p class="secret-item-hint">${item.hint || ''}</p>
      </div>
    `).join('');

    const trapHtml = `
      <h4 class="secrets-section-title">${data.trap_title || ''}</h4>
      <p class="secrets-section-sub">${data.trap_sub || ''}</p>
      <div class="secret-items-grid">
        ${trapItems}
      </div>
    `;

    // 2. Tab 2: Rules & Norms
    const rulesBoxesHtml = (data.rules_boxes || []).map(box => {
      const gridClass = box.layout === 'dense' ? 'cs-dense-grid' : `cs-dense-grid ${box.layout}`;
      const itemsHtml = (box.items || []).map(item => {
        const itemClass = item.item_class ? `cs-dense-item ${item.item_class}` : 'cs-dense-item';
        const kHtml = item.k ? `<span class="cs-k">${item.k}</span>` : '';
        const badgeHtml = item.badge_val ? `<span class="cs-badge-val ${item.badge_color || ''}">${item.badge_val}</span>` : '';
        const vHtml = item.v ? `<span class="cs-v">${item.v}</span>` : '';
        return `
          <div class="${itemClass}">
            ${kHtml}
            ${badgeHtml}
            ${vHtml}
          </div>
        `;
      }).join('');

      return `
        <div class="cs-box" data-search="${box.search || ''}">
          <div class="cs-box-header">
            <span class="cs-tag ${box.color || 'cyan'}">${box.tag || ''}</span>
          </div>
          <div class="${gridClass}">
            ${itemsHtml}
          </div>
        </div>
      `;
    }).join('');

    bodyEl.innerHTML = `
      <!-- TAB 1: KEYWORDS & TRAPS -->
      <div class="secrets-pane ${isRulesActive ? '' : 'active'}" id="pane-keywords" style="display: ${isRulesActive ? 'none' : 'flex'};">
        ${colHtml}
        ${highProbHtml}
        ${trapHtml}
      </div>

      <!-- TAB 2: RULES & NORMS -->
      <div class="secrets-pane cheat-sheet-dense ${isRulesActive ? 'active' : ''}" id="pane-rules" style="display: ${isRulesActive ? 'flex' : 'none'};">
        ${rulesBoxesHtml}
      </div>
    `;

    // Sync tab button states
    const secretsTabNav = document.getElementById('secrets-tab-nav');
    if (secretsTabNav) {
      const tabBtns = secretsTabNav.querySelectorAll('.secrets-tab-btn');
      tabBtns.forEach(btn => {
        const tab = btn.getAttribute('data-tab');
        const shouldBeActive = (tab === 'rules' && isRulesActive) || (tab === 'keywords' && !isRulesActive);
        btn.classList.toggle('active', shouldBeActive);
      });
    }

    // Re-apply search query if any
    const secretsFilterInput = document.getElementById('secrets-filter-input');
    if (secretsFilterInput && secretsFilterInput.value.trim()) {
      secretsFilterInput.dispatchEvent(new Event('input'));
    }
  }


  // 5. API Communications Layer (with automatic retry for cold-starts/network blips)
  async function apiFetch(endpoint, options = {}, retries = 1) {
    const headers = {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': initData,
      ...(options.headers || {})
    };
    try {
      const res = await fetch(endpoint, { ...options, headers });
      if (!res.ok) {
        if (retries > 0 && [502, 503, 504].includes(res.status)) {
          await new Promise(r => setTimeout(r, 1500));
          return apiFetch(endpoint, options, retries - 1);
        }
        const err = await res.json().catch(() => ({ detail: 'Server bilan aloqa uzildi. Iltimos, qayta urinib ko‘ring.' }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      return await res.json();
    } catch (e) {
      if (retries > 0 && (e.name === 'TypeError' || (e.message && e.message.includes('fetch')))) {
        await new Promise(r => setTimeout(r, 1500));
        return apiFetch(endpoint, options, retries - 1);
      }
      throw e;
    }
  }

  // 6. SVG Icon System Injector
  function injectSvgIcons() {
    if (!window.renderIcon) return;

    const slotMap = {
      'streak-icon-slot': 'flame',
      'channel-icon-slot': 'telegram',
      'lang-icon-slot': 'globe',
      'cluster-gauge-icon': 'gauge',
      'badge-status-icon': 'sparkles',
      'btn-exam-icon-slot': 'car',
      'heading-grid-icon': 'crosshair',
      'tile-icon-amaliy': 'amaliy',
      'tile-icon-categories': 'layers',
      'tile-icon-mistakes': 'target',
      'tile-icon-cheatsheet': 'lightbulb',
      'seg-icon-exam': 'trophy',
      'seg-icon-cats': 'layers',
      'seg-icon-quick': 'clock',
      'search-bar-icon-slot': 'search',
      'nav-icon-home': 'home',
      'nav-icon-tests': 'tests',
      'nav-icon-ai': 'bot',
      'nav-icon-amaliy': 'amaliy',
      'nav-icon-results': 'results',
      'nav-icon-profile': 'profile',
      'close-quiz-icon-slot': 'x',
      'exam-finish-icon-slot': 'checkCircle',
      'clock-timer-icon-slot': 'clock',
      'bookmark-icon-slot': 'bookmark',
      'zoom-icon-slot': 'zoomIn',
      'feedback-status-icon-slot': 'checkCircle',
      'prev-btn-icon-slot': 'arrowLeft',
      'next-btn-icon-slot': 'arrowRight',
      'retake-icon-slot': 'rotateCcw',
      'back-home-icon-slot': 'home',
      'close-module-icon-slot': 'x',
      'danger-trap-icon-slot': 'shieldAlert',
      'handbrake-icon-slot': 'shieldAlert',
      'results-heading-icon': 'results',
      'mistakes-tag-icon': 'target',
      'mistakes-btn-icon': 'rotateCcw',
      'history-heading-icon': 'clock',
      'profile-heading-icon': 'profile',
      'amaliy-heading-icon': 'steering'
    };

    for (const [id, iconName] of Object.entries(slotMap)) {
      const el = document.getElementById(id);
      if (el) {
        el.innerHTML = window.renderIcon(iconName);
      }
    }
  }

  // 7. Cockpit Smart 5-Pillar Readiness Telemetry & Diagnostics
  function computeReadinessDetails(stats) {
    if (!stats) return { score: 0, grade: 'NOT_READY', pillars: { exam_mastery: 0, accuracy: 0, coverage: 0, mistake_hygiene: 0, pace_and_streak: 0 } };

    const totalExams = stats.total_exams || 0;
    const passedExams = stats.passed_exams || 0;
    const passRate = stats.pass_rate || 0;
    const totalAns = stats.total_questions_answered || 0;
    const accuracy = stats.accuracy || 0;
    const uniqueQs = stats.unique_questions_tested || 0;
    const mistakes = stats.unresolved_mistakes || 0;
    const resolved = stats.resolved_mistakes || 0;
    const categoriesTested = stats.categories_tested || Math.min(43, Math.max(1, Math.floor(uniqueQs / 8)));
    const streak = stats.streak || (state.streak?.current_streak || 0);
    const avgTime = stats.avg_exam_time_seconds || 0;

    if (totalAns === 0 && totalExams === 0) {
      return { score: 0, grade: 'NOT_READY', pillars: { exam_mastery: 0, accuracy: 0, coverage: 0, mistake_hygiene: 0, pace_and_streak: 0 } };
    }

    // Pillar 1: Exam Mastery & Consistency (30% weight)
    let pExam = 0;
    if (passedExams > 0) {
      const consistency = Math.min(1.0, passedExams / 4.0);
      pExam = Math.min(100, passRate * (0.35 + 0.65 * consistency));
    }

    // Pillar 2: Knowledge Accuracy above 35% baseline (25% weight)
    let pAcc = 0;
    if (totalAns >= 10 && accuracy > 35) {
      pAcc = Math.min(100, Math.max(0, ((accuracy - 35) / 57) * 100));
    }

    // Pillar 3: Curriculum / Syllabus Coverage (25% weight)
    const qScore = Math.min(100, (uniqueQs / 160) * 100);
    const catScore = Math.min(100, (categoriesTested / 20) * 100);
    const pCov = (0.60 * qScore) + (0.40 * catScore);

    // Pillar 4: Mistake Bank Hygiene (10% weight)
    let pMistakes = 50;
    if (totalAns >= 5) {
      if (mistakes === 0) {
        pMistakes = 100;
      } else {
        const penalty = mistakes * 5.0;
        const totalM = resolved + mistakes;
        const resBonus = totalM > 0 ? (resolved / totalM * 20.0) : 0;
        pMistakes = Math.max(0, Math.min(100, 100 - penalty + resBonus));
      }
    }

    // Pillar 5: Exam Pace & Practice Regularity (10% weight)
    const sScore = streak > 0 ? Math.min(100, Math.max(30, streak * 25)) : (passedExams >= 4 ? 100 : (totalExams > 0 && passedExams === 0 ? 0 : 50));
    let tScore = 50;
    if (avgTime <= 0) {
      tScore = passedExams >= 4 ? 100 : (totalExams > 0 && passedExams === 0 ? 0 : 50);
    } else if (avgTime >= 200 && avgTime <= 1100) {
      tScore = 100;
    } else if (avgTime < 200) {
      tScore = 30;
    } else {
      tScore = Math.max(30, 100 - ((avgTime - 1100) / 400) * 50);
    }
    const pPace = (0.50 * sScore) + (0.50 * tScore);

    let raw = (0.30 * pExam) + (0.25 * pAcc) + (0.25 * pCov) + (0.10 * pMistakes) + (0.10 * pPace);

    if (totalAns < 100) {
      const confMultiplier = Math.min(1.0, Math.max(0.2, Math.sqrt(totalAns / 100)));
      raw = raw * confMultiplier;
    }

    let finalScore = raw;
    if (passedExams === 0) {
      finalScore = Math.min(finalScore, 15);
    } else if (passedExams === 1) {
      finalScore = Math.min(finalScore, 45);
    } else if (passedExams === 2) {
      finalScore = Math.min(finalScore, 68);
    }

    if (accuracy <= 30) {
      finalScore = Math.min(finalScore, 8);
    }

    if (mistakes >= 40) {
      finalScore = Math.min(finalScore, 20);
    } else if (mistakes >= 25) {
      finalScore = Math.min(finalScore, 35);
    } else if (mistakes >= 15) {
      finalScore = Math.min(finalScore, 55);
    }

    if (totalAns < 60) {
      finalScore = Math.min(finalScore, 30);
    }

    const score = Math.round(Math.min(100, Math.max(0, finalScore)));

    let grade = 'NOT_READY';
    if (score >= 85) grade = 'EXCELLENT';
    else if (score >= 75) grade = 'EXAM_READY';
    else if (score >= 45) grade = 'IN_PROGRESS';

    const pillars = {
      exam_mastery: Math.round(pExam),
      accuracy: Math.round(pAcc),
      coverage: Math.round(pCov),
      mistake_hygiene: Math.round(pMistakes),
      pace_and_streak: Math.round(pPace)
    };

    return { score, grade, pillars };
  }

  function computeReadinessScore(stats) {
    if (!stats) return 0;
    if (typeof stats.readiness_score === 'number') {
      return Math.round(stats.readiness_score);
    }
    return computeReadinessDetails(stats).score;
  }

  function setPillarDotStatus(itemId, val) {
    const el = document.getElementById(itemId);
    if (!el) return;
    const dot = el.querySelector('.pillar-mini-dot');
    if (!dot) return;
    dot.className = 'pillar-mini-dot ' + (val >= 75 ? 'ready' : (val >= 45 ? 'progress' : 'warn'));
  }

  function updateReadinessClusterUI() {
    const s = state.stats?.stats || {};
    const details = computeReadinessDetails(s);
    state.readinessScore = details.score;
    state.readinessPillars = details.pillars;
    state.readinessGrade = details.grade;

    // Numerical readout
    const scoreValEl = document.getElementById('stat-readiness-pct');
    if (scoreValEl) scoreValEl.textContent = `${details.score}%`;

    // SVG Arc Dashoffset (Arc length: ~172.8)
    const arcFill = document.getElementById('speedometer-arc-fill');
    if (arcFill) {
      const maxOffset = 172.8;
      const offset = maxOffset - (maxOffset * details.score / 100);
      arcFill.style.strokeDashoffset = `${offset}`;
    }

    // Contextual Description
    const descEl = document.getElementById('readiness-description');
    if (descEl) {
      if (details.score >= 80) {
        descEl.textContent = t('readiness_subtext_ready');
      } else if (details.score >= 40) {
        descEl.textContent = t('readiness_subtext_progress');
      } else {
        descEl.textContent = t('readiness_subtext_start');
      }
    }

    const badgeEl = document.getElementById('telemetry-readiness-badge');
    const statusTxtEl = document.getElementById('telemetry-readiness-status');
    if (badgeEl && statusTxtEl) {
      if (details.score >= 80) {
        badgeEl.className = 'telemetry-status-badge ready';
        statusTxtEl.textContent = t('status_ready');
      } else if (details.score >= 40) {
        badgeEl.className = 'telemetry-status-badge in_progress';
        statusTxtEl.textContent = t('status_in_progress');
      } else {
        badgeEl.className = 'telemetry-status-badge not_ready';
        statusTxtEl.textContent = t('status_not_ready');
      }
    }
  }

  function renderReadinessDiagnosticModal() {
    const body = document.getElementById('readiness-modal-body');
    if (!body) return;
    const lang = state.lang || 'uz_latn';
    const s = state.stats?.stats || {};
    const details = computeReadinessDetails(s);

    const gradeLabels = {
      EXCELLENT: t('grade_excellent') || '👑 Imtihonga To‘liq Tayyor (Aʼlo)',
      EXAM_READY: t('grade_ready') || '🟢 O‘tish Ehtimoli Yuqori (Yaxshi)',
      IN_PROGRESS: t('grade_progress') || '🟡 O‘rganish Jarayonida (Mashq zarur)',
      NOT_READY: t('grade_not_ready') || '🟠 Boshlang‘ich Bosqich (Tayyorgarlik kerak)'
    };
    const gradeClass = details.grade.toLowerCase();

    // AI Actionable Advice Calculation
    let adviceText = '';
    const totalExams = s.total_exams || 0;
    const passedExams = s.passed_exams || 0;
    const mistakes = s.unresolved_mistakes || 0;
    const uniqueQs = s.unique_questions_tested || 0;
    const accuracy = s.accuracy || 0;

    if (passedExams === 0) {
      adviceText = (lang === 'ru' 
        ? "<b>Совет AI:</b> Вы еще не сдали ни одного полного симулятора экзамена (20 вопросов, 25 минут). Пройдите минимум 2-3 экзамена без ошибок для закрепления навыка!"
        : (lang === 'uz_cyrl'
          ? "<b>AI Тавсияси:</b> Сиз ҳали бирорта ҳам 20 талик давлат имтиҳони симуляциясини муваффақиятли топширмадингиз. Натижани кўтариш учун камида 2-3 та тўлиқ имтиҳон топширинг!"
          : "<b>AI Tavsiyasi:</b> Siz hali birorta ham 20 talik davlat imtihoni simulyatsiyasini muvaffaqiyatli topshirmadingiz. Natijani ko‘tarish uchun kamida 2-3 ta to‘liq imtihon topshiring!"));
    } else if (mistakes >= 5) {
      adviceText = (lang === 'ru'
        ? `<b>Совет AI:</b> В банке ошибок накопилось <b>${mistakes} нерешенных вопросов</b>. Закройте их в разделе 'Банк ошибок', чтобы исключить случайный провал на госэкзамене!`
        : (lang === 'uz_cyrl'
          ? `<b>AI Тавсияси:</b> Хатолар банкида <b>${mistakes} та ҳал қилинмаган савол</b> мавжуд. Уларни қайта ишлаб тўғриланг, бу балингизни кескин оширади!`
          : `<b>AI Tavsiyasi:</b> Xatolar bankida <b>${mistakes} ta hal qilinmagan savol</b> mavjud. Ularni qayta ishlab to‘g‘rilang, bu balingizni keskin oshiradi!`));
    } else if (uniqueQs < 300) {
      adviceText = (lang === 'ru'
        ? `<b>Совет AI:</b> Вы изучили <b>${uniqueQs} из 1 327 вопросов</b> базы. Рекомендуется пройти темы ПДД и режим 'Смешанный тест' для расширения кругозора!`
        : (lang === 'uz_cyrl'
          ? `<b>AI Тавсияси:</b> Сиз 1 327 та саволдан <b>${uniqueQs} тасини</b> кўриб чиқдингиз. Қамровни кенгайтириш учун мавзули тестлар ва 'Аралаш тест'ни ечинг!`
          : `<b>AI Tavsiyasi:</b> Siz 1 327 ta savoldan <b>${uniqueQs} tasini</b> ko‘rib chiqdingiz. Qamrovni kengaytirish uchun mavzuli testlar va 'Aralash test'ni yeching!`));
    } else if (accuracy < 85) {
      adviceText = (lang === 'ru'
        ? `<b>Совет AI:</b> Точность ответов составляет <b>${accuracy}%</b>. На реальном экзамене допускается всего 2 ошибки (90%+). Читайте вопросы внимательнее и не спешите!`
        : (lang === 'uz_cyrl'
          ? `<b>AI Тавсияси:</b> Жавоблар аниқлиги <b>${accuracy}%</b>ни ташкил этмоқда. Ҳақиқий имтиҳонда фақат 2 та хатога йўл қўйилади (90%+). Саволларни диққат билан ўқинг!`
          : `<b>AI Tavsiyasi:</b> Javoblar aniqligi <b>${accuracy}%</b>ni tashkil etmoqda. Haqiqiy imtihonda faqat 2 ta xatoga yo‘l qo‘yiladi (90%+). Savollarni diqqat bilan o‘qing!`));
    } else {
      adviceText = (lang === 'ru'
        ? "<b>Совет AI:</b> Отличный результат! Ваши показатели полностью соответствуют государственным нормативам. Вы готовы к успешной сдаче официального экзамена СБДД!"
        : (lang === 'uz_cyrl'
          ? "<b>AI Тавсияси:</b> Аъло натижа! Сизнинг кўрсаткичларингиз давлат имтиҳони талабларига тўлиқ жавоб беради. Сиз расмий синовдан ўтишга тайёрсиз!"
          : "<b>AI Tavsiyasi:</b> Aʼlo natija! Sizning ko‘rsatkichlaringiz davlat imtihoni talablariga to‘liq javob beradi. Siz rasmiy sinovdan o‘tishga tayyorsiz!"));
    }

    const dismissText = t('btn_modal_dismiss') || (lang === 'ru' ? 'Понятно' : (lang === 'uz_cyrl' ? 'Тушунарли' : 'Tushunarli'));

    body.innerHTML = `
      <div class="diag-score-hero">
        <div class="diag-score-num">${details.score}%</div>
        <div class="diag-grade-badge ${gradeClass}">
          ${gradeLabels[details.grade] || gradeLabels.NOT_READY}
        </div>
        <div class="diag-advice-box">
          ${adviceText}
        </div>
      </div>

      <!-- 5 PILLARS CARDS -->
      <!-- Pillar 1: Exam Mastery -->
      <div class="diag-pillar-card">
        <div class="diag-pillar-header">
          <div class="diag-pillar-title-wrap">
            <span>🎯</span>
            <h4 class="diag-pillar-title">${t('pillar_exam_title')}</h4>
            <span class="diag-pillar-weight">30%</span>
          </div>
          <span class="diag-pillar-val">${details.pillars.exam_mastery}%</span>
        </div>
        <div class="diag-pillar-progress-track">
          <div class="diag-pillar-progress-fill" style="width: ${details.pillars.exam_mastery}%;"></div>
        </div>
        <p class="diag-pillar-desc">${t('pillar_exam_desc')}</p>
        <span class="diag-pillar-metric-tag">${s.passed_exams || 0} / ${s.total_exams || 0} ta imtihon o‘tildi (${s.pass_rate || 0}%)</span>
      </div>

      <!-- Pillar 2: Accuracy -->
      <div class="diag-pillar-card">
        <div class="diag-pillar-header">
          <div class="diag-pillar-title-wrap">
            <span>🧠</span>
            <h4 class="diag-pillar-title">${t('pillar_acc_title')}</h4>
            <span class="diag-pillar-weight">25%</span>
          </div>
          <span class="diag-pillar-val">${details.pillars.accuracy}%</span>
        </div>
        <div class="diag-pillar-progress-track">
          <div class="diag-pillar-progress-fill" style="width: ${details.pillars.accuracy}%;"></div>
        </div>
        <p class="diag-pillar-desc">${t('pillar_acc_desc')}</p>
        <span class="diag-pillar-metric-tag">${s.correct_answers || 0} / ${s.total_questions_answered || 0} ta to‘g‘ri javob (${s.accuracy || 0}%)</span>
        ${(s.total_questions_answered || 0) < 35 ? `<div class="diag-pillar-subhint" style="margin-top: 6px; font-size: 11px; color: var(--amber, #f59e0b); line-height: 1.4;">ℹ️ ${t('pillar_acc_warmup_hint')}</div>` : ''}
      </div>

      <!-- Pillar 3: Coverage -->
      <div class="diag-pillar-card">
        <div class="diag-pillar-header">
          <div class="diag-pillar-title-wrap">
            <span>📚</span>
            <h4 class="diag-pillar-title">${t('pillar_cov_title')}</h4>
            <span class="diag-pillar-weight">25%</span>
          </div>
          <span class="diag-pillar-val">${details.pillars.coverage}%</span>
        </div>
        <div class="diag-pillar-progress-track">
          <div class="diag-pillar-progress-fill" style="width: ${details.pillars.coverage}%;"></div>
        </div>
        <p class="diag-pillar-desc">${t('pillar_cov_desc')}</p>
        <span class="diag-pillar-metric-tag">${s.unique_questions_tested || 0} / 1 327 savol • ${s.categories_tested || 0} / 43 mavzu</span>
      </div>

      <!-- Pillar 4: Mistakes -->
      <div class="diag-pillar-card">
        <div class="diag-pillar-header">
          <div class="diag-pillar-title-wrap">
            <span>🛡️</span>
            <h4 class="diag-pillar-title">${t('pillar_err_title')}</h4>
            <span class="diag-pillar-weight">10%</span>
          </div>
          <span class="diag-pillar-val">${details.pillars.mistake_hygiene}%</span>
        </div>
        <div class="diag-pillar-progress-track">
          <div class="diag-pillar-progress-fill" style="width: ${details.pillars.mistake_hygiene}%;"></div>
        </div>
        <p class="diag-pillar-desc">${t('pillar_err_desc')}</p>
        <span class="diag-pillar-metric-tag">${s.unresolved_mistakes || 0} ta faol xato • ${s.resolved_mistakes || 0} ta tuzatilgan</span>
      </div>

      <!-- Pillar 5: Pace & Streak -->
      <div class="diag-pillar-card">
        <div class="diag-pillar-header">
          <div class="diag-pillar-title-wrap">
            <span>🔥</span>
            <h4 class="diag-pillar-title">${t('pillar_streak_title')}</h4>
            <span class="diag-pillar-weight">10%</span>
          </div>
          <span class="diag-pillar-val">${details.pillars.pace_and_streak}%</span>
        </div>
        <div class="diag-pillar-progress-track">
          <div class="diag-pillar-progress-fill" style="width: ${details.pillars.pace_and_streak}%;"></div>
        </div>
        <p class="diag-pillar-desc">${t('pillar_streak_desc')}</p>
        <span class="diag-pillar-metric-tag">${s.streak || state.streak?.current_streak || 0} kunlik seriya • o‘rtacha vaqt: ${s.avg_exam_time_seconds ? Math.round(s.avg_exam_time_seconds / 60) + ' daqiqa' : 'Mavjud emas'}</span>
      </div>

      <div class="custom-modal-footer-action">
        <button type="button" class="custom-modal-dismiss-btn" id="btn-done-readiness">${dismissText}</button>
      </div>
    `;

    const btnDone = document.getElementById('btn-done-readiness');
    if (btnDone) {
      btnDone.addEventListener('click', closeReadinessDiagnosticModal);
    }
  }

  function openReadinessDiagnosticModal() {
    triggerHaptic('impact', 'light');
    renderReadinessDiagnosticModal();
    const modal = document.getElementById('readiness-diagnostic-modal');
    if (modal) {
      modal.classList.add('active');
      document.body.style.overflow = 'hidden';
      updateNativeBackButton();
    }
  }

  function closeReadinessDiagnosticModal() {
    triggerHaptic('impact', 'light');
    const modal = document.getElementById('readiness-diagnostic-modal');
    if (modal) {
      modal.classList.remove('active');
      document.body.style.overflow = '';
      updateNativeBackButton();
    }
  }


  // 7.5. Subscription & Paywall Controller
  function isUserPro() {
    return !!(state.subscription && state.subscription.is_pro);
  }

  function updateCustomQuizChipsUI() {
    const isPro = isUserPro();
    const qCountChips = document.querySelectorAll('#chips-q-count .setting-chip');
    qCountChips.forEach(chip => {
      const val = parseInt(chip.getAttribute('data-val'), 10);
      if (!isPro && val > 20) {
        chip.classList.add('is-locked');
        chip.setAttribute('title', 'PRO tarif talab qilinadi');
        if (!chip.querySelector('.chip-lock-icon')) {
          const iconSpan = document.createElement('span');
          iconSpan.className = 'chip-lock-icon';
          iconSpan.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>';
          chip.appendChild(iconSpan);
        }
        if (chip.classList.contains('active')) {
          chip.classList.remove('active');
          const fallback = document.querySelector('#chips-q-count .setting-chip[data-val="20"]');
          if (fallback) fallback.classList.add('active');
        }
      } else {
        chip.classList.remove('is-locked');
        chip.removeAttribute('title');
        const lockIcon = chip.querySelector('.chip-lock-icon');
        if (lockIcon) lockIcon.remove();
      }
    });
  }

  function canAccessExam() {
    if (state.authPending) return true;
    if (isUserPro()) return true;
    if (state.free_tier && state.free_tier.remaining_exams > 0) return true;
    return false;
  }

  function updateSubscriptionUI() {
    const isPro = isUserPro();
    const canExam = canAccessExam();
    updateCustomQuizChipsUI();

    // 1. Lock Badges on Mistakes, Cheatsheet
    const mistakesBadge = document.getElementById('badge-mistakes-lock');
    if (mistakesBadge) mistakesBadge.classList.toggle('hidden', canExam);

    const cheatsheetBadge = document.getElementById('badge-cheatsheet-lock');
    if (cheatsheetBadge) cheatsheetBadge.classList.toggle('hidden', canExam);

    const practiceMistakesBadge = document.getElementById('badge-practice-mistakes-lock');
    if (practiceMistakesBadge) practiceMistakesBadge.classList.toggle('hidden', canExam);

    // 2. Unified Hero Exam & Telemetry Stats Lock (Single blur & unified lock for both cards)
    const heroWrap = document.getElementById('hero-exam-cockpit-wrap');
    const heroLock = document.getElementById('hero-cockpit-lock-overlay');
    if (heroWrap) heroWrap.classList.toggle('locked', !canExam);
    if (heroLock) heroLock.style.display = canExam ? 'none' : 'flex';

    // 3. Profile Subscription Card
    const subPill = document.getElementById('profile-sub-status-pill');
    const subPillText = document.getElementById('profile-sub-status-text');
    const subDesc = document.getElementById('profile-sub-desc');
    const profileSubPlansGrid = document.getElementById('profile-sub-plans-grid');
    const btnProfileSub = document.getElementById('btn-profile-subscribe');
    const btnProfileSubText = document.getElementById('btn-profile-sub-text');

    const planPriceStr = state.selectedPlanId === 'pro_30' ? '25 000 so‘m' : '14 000 so‘m';

    if (subPill && subPillText) {
      if (isPro) {
        subPill.style.display = 'inline-flex';
        subPill.className = 'sub-status-pill pro';
        subPillText.textContent = t('sub_tier_pro');
      } else {
        subPill.style.display = 'none';
        subPillText.textContent = '';
      }
    }

    if (subDesc) {
      if (isPro) {
        let formattedDate = '';
        if (state.subscription.expires_at) {
          const parts = state.subscription.expires_at.substring(0, 10).split('-');
          if (parts.length === 3) {
            formattedDate = `${parts[2]}.${parts[1]}.${parts[0]}`;
          } else {
            formattedDate = state.subscription.expires_at.substring(0, 10);
          }
        }
        const days = state.subscription.days_left !== undefined ? state.subscription.days_left : 0;
        subDesc.textContent = t('sub_pro_active_desc', { date: formattedDate, days: days });
      } else {
        subDesc.textContent = t('sub_free_desc');
      }
    }

    // Hide plan selection chips and subscribe button if already subscribed
    if (profileSubPlansGrid) {
      profileSubPlansGrid.style.display = isPro ? 'none' : 'grid';
    }
    if (btnProfileSub) {
      btnProfileSub.style.display = isPro ? 'none' : 'block';
    }

    if (btnProfileSubText) {
      btnProfileSubText.textContent = `${t('sub_btn_activate')} (${planPriceStr})`;
    }

    // Modal action button text
    const modalBtnText = document.getElementById('btn-modal-sub-text');
    if (modalBtnText) {
      const planName = state.selectedPlanId === 'pro_30' ? '30 kunlik PRO' : '14 kunlik PRO';
      modalBtnText.textContent = `${planName} faollashtirish (${planPriceStr})`;
    }

    // Refresh AI Pro Lock UI
    updateAiProLockState();
  }

  function selectSubscriptionPlan(planId) {
    state.selectedPlanId = planId;
    triggerHaptic('selection');

    // Update chips in profile
    document.querySelectorAll('#profile-sub-plans-grid .sub-plan-box').forEach(box => {
      box.classList.toggle('active', box.getAttribute('data-plan') === planId);
    });

    // Update chips in modal
    document.querySelectorAll('#modal-sub-plans-grid .sub-plan-box').forEach(box => {
      box.classList.toggle('active', box.getAttribute('data-plan') === planId);
    });

    updateSubscriptionUI();
  }

  // Native Telegram WebApp BackButton State Controller
  function updateNativeBackButton() {
    if (!window.Telegram?.WebApp?.BackButton) return;
    const bb = window.Telegram.WebApp.BackButton;
    const isInvoiceOpen = document.getElementById('payment-invoice-modal')?.classList.contains('active');
    const isPaywallOpen = document.getElementById('subscription-paywall-modal')?.classList.contains('active');
    const isQuizOpen = document.getElementById('quiz-overlay')?.classList.contains('active');
    const isSettingsOpen = document.getElementById('custom-quiz-settings-sheet')?.classList.contains('active');
    const isRulesOpen = document.getElementById('platform-rules-modal')?.classList.contains('active');
    const isChangelogOpen = document.getElementById('version-history-modal')?.classList.contains('active');
    const isReadinessOpen = document.getElementById('readiness-diagnostic-modal')?.classList.contains('active');
    const isSavedOpen = document.getElementById('saved-questions-modal')?.classList.contains('active');

    if (isInvoiceOpen || isPaywallOpen || isQuizOpen || isSettingsOpen || isRulesOpen || isChangelogOpen || isReadinessOpen || isSavedOpen) {
      bb.show();
    } else {
      bb.hide();
    }
  }

  function handleNativeBackClick() {
    triggerHaptic('impact', 'light');
    const savedModal = document.getElementById('saved-questions-modal');
    if (savedModal && savedModal.classList.contains('active')) {
      closeSavedQuestionsModal();
      return;
    }

    const readinessModal = document.getElementById('readiness-diagnostic-modal');
    if (readinessModal && readinessModal.classList.contains('active')) {
      closeReadinessDiagnosticModal();
      return;
    }

    const invoiceModal = document.getElementById('payment-invoice-modal');
    if (invoiceModal && invoiceModal.classList.contains('active')) {
      closePaymentInvoiceModal();
      return;
    }

    const paywallModal = document.getElementById('subscription-paywall-modal');
    if (paywallModal && paywallModal.classList.contains('active')) {
      closePaywallModal();
      return;
    }

    const rulesModal = document.getElementById('platform-rules-modal');
    if (rulesModal && rulesModal.classList.contains('active')) {
      closePlatformRulesModal();
      return;
    }

    const changelogModal = document.getElementById('version-history-modal');
    if (changelogModal && changelogModal.classList.contains('active')) {
      closeVersionHistoryModal();
      return;
    }

    const settingsSheet = document.getElementById('custom-quiz-settings-sheet');
    if (settingsSheet && settingsSheet.classList.contains('active')) {
      settingsSheet.classList.remove('active');
      document.body.style.overflow = '';
      updateNativeBackButton();
      return;
    }

    const quizOverlay = document.getElementById('quiz-overlay');
    if (quizOverlay && quizOverlay.classList.contains('active')) {
      confirmQuitQuiz();
      return;
    }
  }

  function openPaywallModal(feature = '') {
    triggerHaptic('notification', 'warning');
    const modal = document.getElementById('subscription-paywall-modal');
    if (modal) {
      modal.classList.add('active');
      document.body.style.overflow = 'hidden';
      updateSubscriptionUI();
      updateNativeBackButton();
    }
  }

  function closePaywallModal() {
    triggerHaptic('impact', 'light');
    const modal = document.getElementById('subscription-paywall-modal');
    if (modal) {
      modal.classList.remove('active');
      document.body.style.overflow = '';
      updateNativeBackButton();
    }
  }

  // =========================================================================
  // PLATFORM RULES & VERSION HISTORY CHANGELOG CONTROLLER (v2.1)
  // =========================================================================

  const CHANGELOG_HISTORY = [
    {
      version: "v2.1",
      date: {
        uz_latn: "2026-yil, Noyabr",
        uz_cyrl: "2026 йил, Ноябрь",
        ru: "Ноябрь, 2026"
      },
      isCurrent: true,
      title: {
        uz_latn: "Tezkorlik, Xavfsizlik va Qulaylik Yangilanishlari",
        uz_cyrl: "Тезкорлик, Хавфсизлик ва Қулайлик Янгиланишлари",
        ru: "Обновления Скорости, Безопасности и Удобства"
      },
      changes: {
        uz_latn: [
          "⚡ <b>Tezkorlik oshirildi:</b> Testlar va imtihon mashg‘ulotlari endi bir zumda tez ochiladi.",
          "🔒 <b>Xavfsizlik kuchaytirildi:</b> Foydalanuvchi hisobi va shaxsiy maʼlumotlari himoyasi mustahkamlandi.",
          "🛡️ <b>Tugmalar barqarorligi:</b> Tugmalarni qayta-qayta bosganda qotish va takrorlanishlar bartaraf etildi.",
          "⏱️ <b>To‘lov va test taymerlari:</b> Boshqa ilovaga o‘tib qaytganda ham vaqt to‘g‘ri va aniq hisoblanadi.",
          "📱 <b>Telegram 'Ortga' tugmasi:</b> Barcha oynalarni Telegramning o‘z ortga tugmasi orqali qulay yopish imkoniyati qo‘shildi.",
          "📋 <b>Karta raqamini nusxalash:</b> To‘lov sahifasida karta raqamini bir bosishda nusxalash yanada osonlashtirildi.",
          "📜 <b>Platforma qoidalari:</b> Foydalanuvchilar uchun rasmiy shartlar va qoidalar bo‘limi kiritildi."
        ],
        uz_cyrl: [
          "⚡ <b>Тезкорлик оширилди:</b> Тестлар ва имтиҳон машғулотлари энди бир зумда тез очилади.",
          "🔒 <b>Хавфсизлик кучайтирилди:</b> Фойдаланувчи ҳисоби ва шахсий маълумотлари ҳимояси мустаҳкамланди.",
          "🛡️ <b>Тугмалар барқарорлиги:</b> Тугмаларни қайта-қайта босганда қотиш ва такрорланишлар бартараф этилди.",
          "⏱️ <b>Тўлов ва тест таймерлари:</b> Бошқа иловага ўтиб қайтганда ҳам вақт тўғри ва аниқ ҳисобланади.",
          "📱 <b>Telegram 'Ортга' тугмаси:</b> Барча ойналарни Telegramнинг ўз ортга тугмаси орқали қулай ёпиш имконияти қўшилди.",
          "📋 <b>Карта рақамини нусхалаш:</b> Тўлов саҳифасида карта рақамини бир босишда нусхалаш янада осонлаштирилди.",
          "📜 <b>Платформа қоидалари:</b> Фойдаланувчилар учун расмий шартлар ва қоидалар бўлими киритилди."
        ],
        ru: [
          "⚡ <b>Увеличение скорости:</b> Тесты и экзаменационные модули теперь открываются мгновенно.",
          "🔒 <b>Повышение безопасности:</b> Усилена защита учетных записей и пользовательских данных.",
          "🛡️ <b>Стабильность кнопок:</b> Устранены случайные повторные нажатия и подвисания интерфейса.",
          "⏱️ <b>Точные таймеры:</b> Время оплаты и тестирования рассчитывается точно даже при сворачивании приложения.",
          "📱 <b>Кнопка 'Назад' Telegram:</b> Удобное закрытие любых окон с помощью штатной кнопки 'Назад'.",
          "📋 <b>Копирование карты:</b> Быстрое и безошибочное копирование номера карты в один клик.",
          "📜 <b>Правила платформы:</b> Добавлен официальный раздел с условиями и правилами сервиса."
        ]
      }
    },
    {
      version: "v2.0",
      date: {
        uz_latn: "2026-yil, Noyabr",
        uz_cyrl: "2026 йил, Ноябрь",
        ru: "Ноябрь, 2026"
      },
      isCurrent: false,
      title: {
        uz_latn: "Avtomatik To‘lov va Yangi Mini App Dizayni",
        uz_cyrl: "Автоматик Тўлов ва Янги Mini App Дизайни",
        ru: "Автоматическая Оплата и Новый Дизайн Mini App"
      },
      changes: {
        uz_latn: [
          "💳 <b>Avtomatik to‘lov:</b> To‘lov tushishi bilan PRO obuna darhol avtomatik faollashadi.",
          "🎨 <b>Yangi qulay interfeys:</b> Zamonaviy dizayn va bo‘limlar bo‘ylab qulay harakatlanish.",
          "🚗 <b>YHQ Davlat standarti:</b> 1 327 ta rasmiy test savollari, 64 ta bilet va 43 ta tematik toifalar to‘liq bazasi.",
          "📊 <b>Xatolar ustida ishlash:</b> Xato qilingan savollarni alohida mashq qilish va natijalarni kuzatish.",
          "💡 <b>Imtihon shpargalkasi:</b> YHQ qoidalari bo‘yicha muhim eslatmalar va yo‘l belgilari."
        ],
        uz_cyrl: [
          "💳 <b>Автоматик тўлов:</b> Тўлов тушиши билан PRO обуна дарҳол автоматик фаоллашади.",
          "🎨 <b>Янги қулай интерфейс:</b> Замонавий дизайн ва бўлимлар бўйлаб қулай ҳаракатланиш.",
          "🚗 <b>ЙҲҚ Давлат стандарти:</b> 1 327 та расмий тест саволлари, 64 та билет ва 43 та тематик бўлимлар тўлиқ базаси.",
          "📊 <b>Хатолар устида ишлаш:</b> Хато қилинган саволларни алоҳида машқ қилиш ва натижаларни кузатиш.",
          "💡 <b>Имтиҳон шпаргалкаси:</b> ЙҲҚ қоидалари бўйича муҳим эслатмалар ва йўл белгилари."
        ],
        ru: [
          "💳 <b>Автоматическая оплата:</b> Мгновенная активация PRO подписки после поступления оплаты.",
          "🎨 <b>Новый удобный интерфейс:</b> Современный темный дизайн и быстрое переключение разделов.",
          "🚗 <b>Стандарт ПДД:</b> Полная база из 1 327 официальных вопросов, 64 билетов и 43 тематических категорий.",
          "📊 <b>Работа над ошибками:</b> Отдельная тренировка неверных ответов и отслеживание прогресса.",
          "💡 <b>Шпаргалка к экзамену:</b> Полезные подсказки по правилам и дорожным знакам."
        ]
      }
    },
    {
      version: "v1.0",
      date: {
        uz_latn: "2026-yil, Dastlabki bosqich",
        uz_cyrl: "2026 йил, Дастлабки босқич",
        ru: "2026, Начальный этап"
      },
      isCurrent: false,
      title: {
        uz_latn: "Dastlabki Test Platformasi",
        uz_cyrl: "Дастлабки Тест Платформаси",
        ru: "Первоначальная Платформа Тестирования"
      },
      changes: {
        uz_latn: [
          "🤖 <b>Platformaning ishga tushirilishi:</b> Dastlabki test tizimi va Telegram bot xizmati."
        ],
        uz_cyrl: [
          "🤖 <b>Платформанинг ишга туширилиши:</b> Дастлабки тест тизими ва Telegram бот хизмати."
        ],
        ru: [
          "🤖 <b>Запуск сервиса:</b> Первоначальная система тестирования и Telegram бот."
        ]
      }
    }
  ];

  const PLATFORM_RULES_DATA = {
    uz_latn: [
      {
        icon: "🏛️",
        title: "1. Platforma haqida umumiy maʼlumot",
        text: "<b>RULLY</b> — haydovchilik guvohnomasini olishga tayyorlanayotgan fuqarolar va avtomaktab o‘quvchilari uchun O‘zbekiston Respublikasi IIV Jamoat xavfsizligi departamenti YHXX davlat imtihonlari andozasi asosida yaratilgan intellektual tayyorgarlik platformasi. Tizim 1 327 ta rasmiy test savollari, 64 ta bilet, 43 ta tematik toifalar, davlat imtihoni simulyatori, amaliy avtodrom ko‘nikmalari va AI Ustoz tahlillarini o‘z ichiga oladi."
      },
      {
        icon: "🎯",
        title: "2. Tayyorgarlik darajasi va O‘tish ko‘rsatkichi farqi",
        text: "• <b>Tayyorgarlik darajasi (Spidometr):</b> Bu sizning haqiqiy davlat imtihoniga umumiy tayyorlik ko‘rsatkichingiz. U 5 ta aqlli mezon (Imtihonlar dinamikasi 30%, Aniq bilim 25%, 1 327 ta savol qamrovi 25%, Xatolar banki gigiyenasi 10%, Muntazamlik va vaqt 10%) asosida yaxlit hisoblanadi.<br>• <b>O‘tish ko‘rsatkichi (Muvaffaqiyatli imtihonlar):</b> Bu siz topshirgan barcha imtihonlarning nechtasidan o‘tganingizni ko‘rsatuvchi sof statistik fakt (masalan: 12 ta imtihondan 1 tasidan o‘tgan bo‘lsangiz — 8.3%). Shu sababli bu ikki ko‘rsatkich bir xil bo‘lmaydi."
      },
      {
        icon: "🎓",
        title: "3. Davlat nazariy imtihoni meʼyorlari",
        text: "Rasmiy nazariy imtihon 20 ta tasodifiy savoldan iborat bo‘lib, sinov uchun 25 daqiqa vaqt ajratiladi. Imtihondan muvaffaqiyatli o‘tish uchun nomzod kamida 18 ta savolga (90%) to‘g‘ri javob berishi lozim (maksimal 2 ta xatoga ruxsat etiladi, 3-xatoda imtihon darhol to‘xtatiladi)."
      },
      {
        icon: "🛡️",
        title: "4. Xatolar banki va Qayta ishlash qoidalari",
        text: "Istalgan test yoki imtihonda noto‘g‘ri javob berilgan barcha savollar avtomatik tarzda <b>'Xatolar banki'</b>ga tushadi (o‘tkazib yuborilgan yoki javobsiz qolgan savollar xatolar bankiga qo‘shilmaydi). Savol faqat u qayta yechilib, to‘g‘ri javob belgilangandagina bankdan o‘chiriladi. Hal qilinmagan xatolar umumiy tayyorgarlik darajangizni pasaytiradi."
      },
      {
        icon: "🚗",
        title: "5. Amaliy imtihon (Avtodrom) va Jarima ballari",
        text: "Amaliy haydash bo‘limida davlat avtodromining 6 ta asosiy mashqi (Estakada, Parallel to‘xtash, 90° burilish, 'Ilon izi', Garajga kirish, To‘xtash chizig‘i) video-ko‘rgazmali tahlil qilingan. Davlat standarti bo‘yicha har bir xato uchun 5 dan 25 gacha jarima bali beriladi. Jami jarima ballari 100 ga yetsa, nomzod imtihondan o‘ta olmagan hisoblanadi."
      },
      {
        icon: "🤖",
        title: "6. AI Ustoz imkoniyatlari",
        text: "Sun’iy intellektga asoslangan <b>AI Ustoz</b> har bir savol bo‘yicha O‘zbekiston YHQ moddalariga havola bergan holda javobning tub mohiyatini sodda tilda tushuntirib beradi. PRO foydalanuvchilar har qanday chigal vaziyatni cheksiz tahlil qildirishlari mumkin."
      },
      {
        icon: "🔥",
        title: "7. Muntazamlik (Streak) va Xatcho‘plar",
        text: "• <b>Kunlik seriya (Streak):</b> Har kuni kamida bitta test yechish orqali o‘qish zanjiri mustahkamlanadi. Agar 24 soat davomida test yechilmasa, seriya nolga tushadi.<br>• <b>Xatcho‘plar (Saqlangan savollar):</b> O‘zingiz uchun qiyin yoki muhim deb bilgan savollarni yulduzcha orqali saqlab, istalgan paytda maxsus bo‘limdan qayta takrorlashingiz mumkin."
      },
      {
        icon: "💎",
        title: "8. Obuna (PRO) va Bepul Sinov (Free Tier)",
        text: "Har bir yangi foydalanuvchiga platforma imkoniyatlari bilan tanishish uchun <b>2 ta to‘liq Davlat Imtihoni sinovi bepul</b> taqdim etiladi. Sinovdan so‘ng, cheksiz davlat imtihonlari, AI Ustoz bilan muloqot, xatolar banki va barcha 1 327 ta savoldan to‘liq foydalanish uchun PRO tarifga ulanish mumkin. Barcha to‘lovlar rasmiy bank kartalari orqali xavfsiz qabul qilinadi va avtomatik ravishda faollashtiriladi."
      },
      {
        icon: "⚖️",
        title: "9. Foydalanish shartlari va Maxfiylik",
        text: "Barcha o‘quv materiallari faqat shaxsiy ta’lim maqsadida taqdim etiladi. Tizim ma’lumotlarini avtomatlashtirilgan vositalar orqali ko‘chirib olish yoki tijoriy maqsadda sotish qat’iyan taqiqlanadi. Foydalanuvchilarning shaxsiy ma’lumotlari shifrlangan va daxlsiz saqlanadi."
      },
      {
        icon: "📞",
        title: "10. Texnik yordam va Bog‘lanish",
        text: "Savollar, to‘lovlar yoki takliflar bo‘yicha rasmiy <b><a href=\"https://t.me/rully_admin\" target=\"_blank\" style=\"color: #38bdf8; text-decoration: none;\">@rully_admin</a></b> orqali ma’muriyat bilan bog‘lanishingiz mumkin. RULLY har bir bo‘lajak haydovchiga davlat imtihonidan birinchi urinishda o‘tishida ishonchli yordamchidir!"
      }
    ],
    uz_cyrl: [
      {
        icon: "🏛️",
        title: "1. Платформа ҳақида умумий маълумот",
        text: "<b>RULLY</b> — ҳайдовчилик гувоҳномасини олишга тайёрланаётган фуқаролар ва автомактаб ўқувчилари учун Ўзбекистон Республикаси ИИВ ЙҲХХ давлат имтиҳонлари андозаси асосида яратилган интеллектуал тайёргарлик платформаси. Тизим 1 327 та расмий тест саволлари, 64 та билет, 43 та тематик бўлимлар, давлат имтиҳони симулятори, амалий автодром кўникмалари ва AI Устоз таҳлилларини ўз ичига олади."
      },
      {
        icon: "🎯",
        title: "2. Тайёргарлик даражаси ва Ўтиш кўрсаткичи фарқи",
        text: "• <b>Тайёргарлик даражаси (Спидометр):</b> Бу сизнинг ҳақиқий давлат имтиҳонига умумий тайёрлик кўрсаткичингиз. У 5 та ақлли мезон (Имтиҳонлар динамикаси 30%, Аниқ билим 25%, 1 327 та савол қамрови 25%, Хатолар банки гигиенаси 10%, Мунтазамлик ва вақт 10%) асосида яхлит ҳисобланади.<br>• <b>Ўтиш кўрсаткичи (Муваффақиятли имтиҳонлар):</b> Бу сиз топширган барча имтиҳонларнинг нечтасидан ўтганингизни кўрсатувчи соф статистик факт (масалан: 12 та имтиҳондан 1 тасидан ўтган бўлсангиз — 8.3%). Шу сабабли бу икки кўрсаткич бир хил бўлмайди."
      },
      {
        icon: "🎓",
        title: "3. Давлат назарий имтиҳони меъёрлари",
        text: "Расмий назарий имтиҳон 20 та тасодифий саволдан иборат бўлиб, синов учун 25 дақиқа вақт ажратилади. Имтиҳондан муваффақиятли ўтиш учун камида 18 та саволга (90%) тўғри жавоб бериш шарт (кўпи билан 2 та хатога йўл қўйилади, 3-хатода имтиҳон тўхтатилади)."
      },
      {
        icon: "🛡️",
        title: "4. Хатолар банки ва Қайта ишлаш қоидалари",
        text: "Исталган тест ёки имтиҳонда нотўғри жавоб берилган барча саволлар автоматик тарзда <b>'Хатолар банки'</b>га тушади (жавобсиз қолган саволлар хатолар банкига қўшилмайди). Савол фақат у қайта ечилиб, тўғри жавоб белгилангандагина банкдан ўчирилади. Ҳал қилинмаган хатолар умумий тайёргарлик даражангизни пасайтиради."
      },
      {
        icon: "🚗",
        title: "5. Амалий имтиҳон (Автодром) ва Жарима баллари",
        text: "Амалий ҳайдаш бўлимида давлат автодромининг 6 та асосий машқи (Эстакада, Параллел тўхташ, 90° бурилиш, 'Илон изи', Гаражга кириш, Тўхташ чизиғи) таҳлил қилинган. Ҳар бир хато учун 5 дан 25 гача жарима бали берилади. Жарима баллари 100 га етса, номзод имтиҳондан ўта олмаган ҳисобланади."
      },
      {
        icon: "🤖",
        title: "6. AI Устоз имкониятлари",
        text: "Сунъий интеллектга асосланган <b>AI Устоз</b> ҳар бир савол бўйича ЙҲҚ моддаларига ҳавола берган ҳолда жавобнинг асл моҳиятини тушунтириб беради. PRO фойдаланувчилар ҳар қандай саволни чексиз таҳлил қилдиришлари мумкин."
      },
      {
        icon: "🔥",
        title: "7. Мунтазамлик (Streak) ва Хатчўплар",
        text: "• <b>Кунлик серия (Streak):</b> Ҳар куни камида битта тест ечиш орқали ўқиш занжири мустаҳкамланади. Агар 24 соат давомида тест ечилмаса, серия нолга тушади.<br>• <b>Хатчўплар (Сақланган саволлар):</b> Мураккаб саволларни юлдузча орқали сақлаб, исталган пайтда қайта такрорлаш мумкин."
      },
      {
        icon: "💎",
        title: "8. Обуна (PRO) ва Бепул Синов (Free Tier)",
        text: "Ҳар бир янги фойдаланувчига платформа имкониятлари билан танишиш учун <b>2 та тўлиқ Давлат Имтиҳони синови бепул</b> тақдим этилади. Синовдан сўнг, чексиз давлат имтиҳонлари, AI Устоз билан таҳлил, хатолар банки ва барча 1 327 та саволдан тўлиқ фойдаланиш учун PRO тарифга уланиш мумкин. Барча тўловлар расмий банк карталари орқали хавфсиз қабул қилинади ва автоматик фаоллаштирилади."
      },
      {
        icon: "⚖️",
        title: "9. Фойдаланиш шартлари ва Махфийлик",
        text: "Барча материаллар фақат шахсий таълим мақсадида тақдим этилади. Тизим маълумотларини кўчириб олиш ёки сотиш қатъиян тақиқланади. Шахсий маълумотлар шифрланган ҳолда сақланади."
      },
      {
        icon: "📞",
        title: "10. Техник ёрдам ва Боғланиш",
        text: "Саволлар, таклифлар ёки тўлов масалалари бўйича расмий <b><a href=\"https://t.me/rully_admin\" target=\"_blank\" style=\"color: #38bdf8; text-decoration: none;\">@rully_admin</a></b> орқали маъмурият билан боғланишингиз мумкин."
      }
    ],
    ru: [
      {
        icon: "🏛️",
        title: "1. Общая информация о платформе",
        text: "<b>RULLY</b> — интеллектуальная интерактивная платформа для подготовки к экзаменам на получение водительского удостоверения по стандартам СБДД МВД Республики Узбекистан. Включает 1 327 официальных вопросов, 64 билета, 43 тематические категории, симулятор экзамена, модуль автодрома и аналитику от AI Наставника."
      },
      {
        icon: "🎯",
        title: "2. Разница между Уровнем готовности и Процентом сдачи",
        text: "• <b>Уровень готовности (Спидометр):</b> Комплексная оценка готовности к госэкзамену по 5 критериям (Динамика экзаменов 30%, Точность знаний 25%, Охват 1 327 вопросов 25%, Гигиена банка ошибок 10%, Регулярность и темп 10%).<br>• <b>Процент сдачи (Успешные попытки):</b> Сухой исторический процент успешно сданных экзаменов от общего числа попыток (например: сдан 1 из 12 экзаменов = 8.3%). Поэтому эти две цифры различаются."
      },
      {
        icon: "🎓",
        title: "3. Нормативы государственного теоретического экзамена",
        text: "Официальный экзамен состоит из 20 случайных вопросов, выделяемое время — 25 минут. Для успешной сдачи необходимо ответить верно минимум на 18 вопросов (допускается не более 2 ошибок; при 3-й ошибке экзамен немедленно прекращается)."
      },
      {
        icon: "🛡️",
        title: "4. Банк ошибок и правила работы над ними",
        text: "Все вопросы, на которые дан неверный ответ, автоматически попадают в <b>Банк ошибок</b> (пропущенные без ответа вопросы не добавляются). Вопрос удаляется из банка только после того, как вы решите его повторно и укажете правильный ответ. Нерешенные ошибки снижают общий уровень готовности."
      },
      {
        icon: "🚗",
        title: "5. Практический экзамен (Автодром) и Штрафные баллы",
        text: "Раздел практики содержит детальный разбор 6 основных упражнений автодрома (Эстакада, Параллельная парковка, Разворот 90°, 'Змейка', Въезд в бокс, Стоп-линия). За ошибки начисляются от 5 до 25 штрафных баллов. При сумме 100 штрафных баллов кандидат считается не сдавшим."
      },
      {
        icon: "🤖",
        title: "6. Возможности AI Наставника",
        text: "<b>AI Наставник</b> детально разъясняет суть каждого вопроса со ссылками на пункты ПДД Узбекистана простым и понятным языком. Пользователи тарифа PRO имеют безлимитный доступ к персональному разбору любых ситуаций."
      },
      {
        icon: "🔥",
        title: "7. Серия занятий (Streak) и Закладки",
        text: "• <b>Ежедневная серия (Streak):</b> Поддерживается решением хотя бы одного теста каждый день. Если занятий нет более 24 часов, серия обнуляется.<br>• <b>Закладки:</b> Любые сложные вопросы можно сохранить в избранное и повторить в любое удобное время."
      },
      {
        icon: "💎",
        title: "8. Подписка (PRO) и Пробный период (Free Tier)",
        text: "Каждому новому пользователю для ознакомления предоставляется <b>2 полных пробных Госэкзамена бесплатно</b>. После их прохождения для безлимитной сдачи экзаменов, общения с AI Наставником, банка ошибок и доступа ко всем 1 327 вопросам доступна подписка PRO. Все платежи принимаются безопасно через банковские карты с мгновенной активацией."
      },
      {
        icon: "⚖️",
        title: "9. Условия использования и Конфиденциальность",
        text: "Все материалы предоставляются исключительно для личного обучения. Парсинг, копирование или перепродажа строго запрещены. Персональные данные зашифрованы и надежно защищены."
      },
      {
        icon: "📞",
        title: "10. Техническая поддержка и Обратная связь",
        text: "По любым вопросам и предложениям обращайтесь к администратору <b><a href=\"https://t.me/rully_admin\" target=\"_blank\" style=\"color: #38bdf8; text-decoration: none;\">@rully_admin</a></b>. Желаем успешной сдачи экзамена с первой попытки!"
      }
    ]
  };

  function renderPlatformRulesModal() {
    const body = document.getElementById('rules-modal-body');
    if (!body) return;
    const lang = state.lang || 'uz_latn';
    const sections = PLATFORM_RULES_DATA[lang] || PLATFORM_RULES_DATA['uz_latn'];
    const dismissText = t('btn_modal_dismiss') || (lang === 'ru' ? 'Понятно' : (lang === 'uz_cyrl' ? 'Тушунарли' : 'Tushunarli'));

    body.innerHTML = `
      ${sections.map(sec => `
        <div class="rules-section-card">
          <div class="rules-section-head">
            <span class="rules-section-icon">${sec.icon}</span>
            <h4 class="rules-section-title">${sec.title}</h4>
          </div>
          <p class="rules-section-text">${sec.text}</p>
        </div>
      `).join('')}
      <div class="custom-modal-footer-action">
        <button type="button" class="custom-modal-dismiss-btn" id="btn-done-rules">${dismissText}</button>
      </div>
    `;

    const btnDone = document.getElementById('btn-done-rules');
    if (btnDone) {
      btnDone.addEventListener('click', closePlatformRulesModal);
    }
  }

  function openPlatformRulesModal() {
    triggerHaptic('impact', 'light');
    renderPlatformRulesModal();
    const modal = document.getElementById('platform-rules-modal');
    if (modal) {
      modal.classList.add('active');
      document.body.style.overflow = 'hidden';
      updateNativeBackButton();
    }
  }

  function closePlatformRulesModal() {
    triggerHaptic('impact', 'light');
    const modal = document.getElementById('platform-rules-modal');
    if (modal) {
      modal.classList.remove('active');
      document.body.style.overflow = '';
      updateNativeBackButton();
    }
  }

  function renderVersionHistoryModal() {
    const body = document.getElementById('changelog-modal-body');
    if (!body) return;
    const lang = state.lang || 'uz_latn';
    const dismissText = t('btn_modal_dismiss') || (lang === 'ru' ? 'Понятно' : (lang === 'uz_cyrl' ? 'Тушунарли' : 'Tushunarli'));

    body.innerHTML = `
      ${CHANGELOG_HISTORY.map(ver => {
        const title = ver.title[lang] || ver.title['uz_latn'];
        const date = (typeof ver.date === 'object' ? (ver.date[lang] || ver.date['uz_latn']) : ver.date);
        const changes = ver.changes[lang] || ver.changes['uz_latn'];
        const currentBadge = ver.isCurrent ? `<span class="changelog-current-pill">${t('changelog_current_badge') || (lang === 'ru' ? 'Текущая' : (lang === 'uz_cyrl' ? 'Жорий' : 'Joriy'))}</span>` : '';

        return `
          <div class="changelog-ver-card ${ver.isCurrent ? 'current' : ''}">
            <div class="changelog-ver-header">
              <div class="changelog-ver-badges">
                <span class="changelog-ver-tag">${ver.version}</span>
                ${currentBadge}
              </div>
              <span class="changelog-ver-date">${date}</span>
            </div>
            <h4 class="changelog-ver-title">${title}</h4>
            <ul class="changelog-ver-list">
              ${changes.map(ch => `
                <li class="changelog-ver-item">
                  <span class="changelog-bullet-dot"></span>
                  <div class="changelog-item-content">${ch}</div>
                </li>
              `).join('')}
            </ul>
          </div>
        `;
      }).join('')}
      <div class="custom-modal-footer-action">
        <button type="button" class="custom-modal-dismiss-btn" id="btn-done-changelog">${dismissText}</button>
      </div>
    `;

    const btnDone = document.getElementById('btn-done-changelog');
    if (btnDone) {
      btnDone.addEventListener('click', closeVersionHistoryModal);
    }
  }

  function openVersionHistoryModal() {
    triggerHaptic('impact', 'light');
    renderVersionHistoryModal();
    const modal = document.getElementById('version-history-modal');
    if (modal) {
      modal.classList.add('active');
      document.body.style.overflow = 'hidden';
      updateNativeBackButton();
    }
  }

  function closeVersionHistoryModal() {
    triggerHaptic('impact', 'light');
    const modal = document.getElementById('version-history-modal');
    if (modal) {
      modal.classList.remove('active');
      document.body.style.overflow = '';
      updateNativeBackButton();
    }
  }

  // Payment Order State & Timer
  let paymentPollingTimer = null;
  let paymentCountdownTimer = null;
  let activeOrderData = null;
  let isActivatingSubscription = false;

  async function activateUserSubscription(planId) {
    if (isActivatingSubscription) return;
    isActivatingSubscription = true;

    triggerHaptic('impact', 'medium');
    const selectedPlan = planId || state.selectedPlanId || 'pro_14';

    // Visual button debounce locking
    const btnModalActivate = document.getElementById('btn-modal-activate-sub');
    const btnProfileSub = document.getElementById('btn-profile-sub');
    const origModalText = btnModalActivate ? btnModalActivate.textContent : '';
    const origProfileText = btnProfileSub ? btnProfileSub.textContent : '';

    if (btnModalActivate) {
      btnModalActivate.style.pointerEvents = 'none';
      btnModalActivate.style.opacity = '0.7';
      btnModalActivate.textContent = 'Yuklanmoqda...';
    }
    if (btnProfileSub) {
      btnProfileSub.style.pointerEvents = 'none';
      btnProfileSub.style.opacity = '0.7';
      btnProfileSub.textContent = 'Yuklanmoqda...';
    }

    try {
      // Call create order endpoint
      const res = await apiFetch('/api/payment/orders/create', {
        method: 'POST',
        body: JSON.stringify({ plan_id: selectedPlan })
      });

      if (!res.ok || !res.order) {
        throw new Error(res.detail || "Buyurtma yaratib bo'lmadi");
      }

      // Close paywall modal once invoice is prepared
      closePaywallModal();
      openPaymentInvoiceModal(res.order);
    } catch (e) {
      console.error("Payment order creation failed:", e);
      if (window.Telegram?.WebApp?.showAlert) {
        window.Telegram.WebApp.showAlert(e.message || "To‘lov buyurtmasini yaratishda xatolik yuz berdi.");
      } else {
        alert(e.message || "To‘lov buyurtmasini yaratishda xatolik yuz berdi.");
      }
    } finally {
      isActivatingSubscription = false;
      if (btnModalActivate) {
        btnModalActivate.style.pointerEvents = '';
        btnModalActivate.style.opacity = '';
        btnModalActivate.textContent = origModalText;
      }
      if (btnProfileSub) {
        btnProfileSub.style.pointerEvents = '';
        btnProfileSub.style.opacity = '';
        btnProfileSub.textContent = origProfileText;
      }
    }
  }

  function openPaymentInvoiceModal(order) {
    activeOrderData = order;
    const modal = document.getElementById('payment-invoice-modal');
    if (!modal) return;

    // Fill details
    const elPlan = document.getElementById('inv-plan-name');
    const elHolder = document.getElementById('inv-cardholder-name');
    const elCard = document.getElementById('inv-card-number');
    const elBase = document.getElementById('inv-base-price');
    const elSuffix = document.getElementById('inv-suffix');
    const elTotal = document.getElementById('inv-total-amount');
    const elRef = document.getElementById('inv-order-ref');

    if (elPlan) elPlan.textContent = order.plan_name || (order.plan_id === 'pro_30' ? '30 kunlik PRO' : '14 kunlik PRO');
    if (elHolder) elHolder.textContent = order.cardholder_name || 'ANVARJON ARALOV';
    let fullCard = order.card_number_raw || order.card_number_formatted || order.card_number_masked || '';
    if (fullCard) {
      const digitsOnly = fullCard.replace(/\D/g, '');
      if (digitsOnly.length === 16) {
        fullCard = digitsOnly.replace(/(.{4})/g, '$1 ').trim();
      }
    }
    if (elCard) elCard.textContent = fullCard || '9860 0000 0000 5370';
    if (elBase) elBase.textContent = Number(order.base_price_uzs).toLocaleString() + ' so‘m';
    if (elSuffix) elSuffix.textContent = '+' + Number(order.suffix_uzs) + ' so‘m';
    if (elTotal) elTotal.textContent = Number(order.final_amount_uzs).toLocaleString();
    if (elRef) elRef.textContent = order.order_id;

    // Start 15-min countdown
    let remainingSec = order.remaining_seconds != null ? order.remaining_seconds : 900;
    startInvoiceCountdown(remainingSec);

    // Start Polling every 3s
    startPaymentStatusPolling(order.order_id);

    // Open Modal
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    updateNativeBackButton();
  }

  function closePaymentInvoiceModal() {
    const modal = document.getElementById('payment-invoice-modal');
    if (modal) modal.classList.remove('active');
    document.body.style.overflow = '';
    updateNativeBackButton();

    if (paymentPollingTimer) {
      clearInterval(paymentPollingTimer);
      paymentPollingTimer = null;
    }
    if (paymentCountdownTimer) {
      clearInterval(paymentCountdownTimer);
      paymentCountdownTimer = null;
    }
    activeOrderData = null;
  }

  function startInvoiceCountdown(seconds) {
    if (paymentCountdownTimer) clearInterval(paymentCountdownTimer);
    const timerEl = document.getElementById('invoice-countdown-timer');

    function updateDisplay(s) {
      if (!timerEl) return;
      const m = Math.floor(s / 60);
      const rem = s % 60;
      timerEl.textContent = `${String(m).padStart(2, '0')}:${String(rem).padStart(2, '0')}`;
    }

    // Precise wall-clock target deadline immune to mobile backgrounding/sleep drift
    const targetEnd = Date.now() + (seconds * 1000);
    function tickInvoice() {
      const remaining = Math.max(0, Math.round((targetEnd - Date.now()) / 1000));
      updateDisplay(remaining);
      if (remaining <= 0) {
        clearInterval(paymentCountdownTimer);
        paymentCountdownTimer = null;
        if (paymentPollingTimer) {
          clearInterval(paymentPollingTimer);
          paymentPollingTimer = null;
        }
        if (timerEl) timerEl.textContent = "00:00";
        closePaymentInvoiceModal();
        if (window.Telegram?.WebApp?.showAlert) {
          window.Telegram.WebApp.showAlert("Invoys muddati tugadi (15 daqiqa). Yangi buyurtma yarating.");
        } else {
          alert("Invoys muddati tugadi (15 daqiqa). Yangi buyurtma yarating.");
        }
      }
    }

    tickInvoice();
    paymentCountdownTimer = setInterval(tickInvoice, 1000);
  }

  function startPaymentStatusPolling(orderId) {
    if (paymentPollingTimer) clearInterval(paymentPollingTimer);

    paymentPollingTimer = setInterval(async () => {
      try {
        const res = await apiFetch(`/api/payment/orders/${orderId}/status`);
        if (res && res.is_paid) {
          // Success!
          clearInterval(paymentPollingTimer);
          paymentPollingTimer = null;
          if (paymentCountdownTimer) {
            clearInterval(paymentCountdownTimer);
            paymentCountdownTimer = null;
          }

          closePaymentInvoiceModal();
          triggerHaptic('notification', 'success');

          // Update subscription state
          state.lastAuthAt = 0;
          state.subscription = {
            tier: 'pro',
            is_pro: true,
            active: true,
            plan: activeOrderData?.plan_id || 'pro'
          };
          updateSubscriptionUI();
          await loadTelemetryData();

          if (window.Telegram?.WebApp?.showAlert) {
            window.Telegram.WebApp.showAlert("Tabriklaymiz! To‘lovingiz muvaffaqiyatli tasdiqlandi. PRO obunangiz faollashtirildi!");
          } else {
            alert("Tabriklaymiz! To‘lovingiz muvaffaqiyatli tasdiqlandi. PRO obunangiz faollashtirildi!");
          }
        } else if (res && (res.status === 'EXPIRED' || res.status === 'CANCELLED' || res.is_expired)) {
          clearInterval(paymentPollingTimer);
          paymentPollingTimer = null;
          if (paymentCountdownTimer) {
            clearInterval(paymentCountdownTimer);
            paymentCountdownTimer = null;
          }
          closePaymentInvoiceModal();
          if (window.Telegram?.WebApp?.showAlert) {
            window.Telegram.WebApp.showAlert("Ushbu buyurtma bekor qilingan yoki muddati tugagan.");
          } else {
            alert("Ushbu buyurtma bekor qilingan yoki muddati tugagan.");
          }
        }
      } catch (e) {
        console.warn("Polling payment status check error:", e);
      }
    }, 4000);
  }

  // --- RULLY Cobalt Engine Start Loading Controller ---
  function initLoadingScreen() {
    const screenEl = document.getElementById('rully-loading-screen');
    const statusTextEl = document.getElementById('loading-status-text');
    const progressBarEl = document.getElementById('loading-progress-bar');
    const arcProgressEl = document.getElementById('steering-arc-progress');
    const wheelWrapEl = document.querySelector('.wheel-disc-wrap');

    if (!screenEl) return () => {};

    const startTime = Date.now();
    const MIN_DISPLAY_MS = 650; // smooth engine start animation window (reduced for ultra-snappy load)

    // Step 1: Initial state & smooth arc progression
    if (arcProgressEl) {
      setTimeout(() => {
        arcProgressEl.style.strokeDashoffset = '0';
      }, 50);
    }
    if (progressBarEl) {
      setTimeout(() => {
        progressBarEl.style.width = '100%';
      }, 50);
    }

    // Step 2: Ignition Haptic at 250ms
    setTimeout(() => {
      try {
        window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('medium');
      } catch (e) {}
    }, 250);

    // Step 3: Status phase updates
    setTimeout(() => {
      if (statusTextEl) statusTextEl.textContent = t('loading_status_check');
    }, 450);

    setTimeout(() => {
      if (statusTextEl) statusTextEl.textContent = t('loading_status_rules');
    }, 950);

    // Interactive Klaxon Easter Egg on steering wheel tap
    if (wheelWrapEl) {
      wheelWrapEl.addEventListener('click', () => {
        try {
          window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('heavy');
        } catch (e) {}
        if (statusTextEl) {
          const prev = statusTextEl.textContent;
          statusTextEl.textContent = t('loading_beep');
          setTimeout(() => { statusTextEl.textContent = prev; }, 600);
        }
      });
    }

    // Safety watchdog: guarantee dismissal within 3500ms even on degraded networks
    let isDismissed = false;
    const safetyWatchdog = setTimeout(() => {
      dismissLoadingScreen();
    }, 3500);

    // Return completion function
    function dismissLoadingScreen() {
      if (isDismissed) return;
      isDismissed = true;
      clearTimeout(safetyWatchdog);
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, MIN_DISPLAY_MS - elapsed);

      setTimeout(() => {
        if (statusTextEl) statusTextEl.textContent = t('loading_status_ready');
        try {
          window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success');
        } catch (e) {}

        setTimeout(() => {
          screenEl.classList.add('loaded');
          setTimeout(() => {
            screenEl.style.display = 'none';
          }, 550);
        }, 220);
      }, remaining);
    }

    return dismissLoadingScreen;
  }

  // 8. Application Bootstrap
  async function initApp() {
    // 1. Immediate pre-auth trilingual detection for instant localized loading screen
    try {
      const cachedLang = localStorage.getItem('rully_lang');
      const tgLang = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code;
      if (cachedLang && ['uz_latn', 'uz_cyrl', 'ru'].includes(cachedLang)) {
        state.lang = cachedLang;
      } else if (tgLang === 'ru') {
        state.lang = 'ru';
      }
    } catch (e) {}

    // 2. 0ms Synchronous Hydration from Telegram WebApp SDK (never flash default names)
    const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
    if (tgUser && (tgUser.first_name || tgUser.username)) {
      state.user = {
        first_name: tgUser.first_name || tgUser.username,
        username: tgUser.username || '',
        user_id: tgUser.id,
        language: state.lang
      };
      updateDriverProfileUI();
    }

    // 3. 0ms Synchronous Hydration from local cached profile & stats (instant PRO restore)
    try {
      const cachedBundle = localStorage.getItem('rully_auth_bundle');
      if (cachedBundle) {
        const bundle = JSON.parse(cachedBundle);
        if (bundle.user) state.user = { ...(state.user || {}), ...bundle.user };
        if (bundle.subscription) state.subscription = bundle.subscription;
        if (bundle.free_tier) state.free_tier = bundle.free_tier;
        if (bundle.stats) state.stats = { stats: bundle.stats, streak: bundle.streak };
        updateDriverProfileUI();
        updateSubscriptionUI();
        applyTelemetryUI(bundle);
      }
    } catch (e) {}

    // 4. Initial localization with hydrated user and optimistic subscription
    applyLocalization();

    const dismissLoading = initLoadingScreen();
    injectSvgIcons();
    setupEventListeners();

    // Re-resolve in case Telegram WebApp bridge took a few ms to populate initData
    if (initData.startsWith("dev_user_") && window.Telegram?.WebApp?.initData) {
      initData = window.Telegram.WebApp.initData;
    }

    try {
      const authRes = await apiFetch('/api/auth/telegram', {
        method: 'POST',
        body: JSON.stringify({ init_data: initData })
      });

      state.authPending = false;
      state.user = authRes.user;
      state.subscription = authRes.subscription || authRes.user?.subscription || { is_pro: false, tier: 'free' };
      state.free_tier = authRes.free_tier || { is_pro: false, has_access: true, remaining_exams: 2 };
      state.lang = authRes.user.language || state.lang || 'uz_latn';
      state.lastAuthAt = Date.now();
      if (authRes.history) {
        state.history = authRes.history;
      }
      try { localStorage.setItem('rully_lang', state.lang); } catch (e) {}
      try { localStorage.setItem('rully_auth_bundle', JSON.stringify(authRes)); } catch (e) {}
      state.stats = {
        stats: authRes.stats,
        streak: authRes.streak
      };
      updateSubscriptionUI();
      updateAiProLockState();
      applyTelemetryUI(authRes);

      try { sessionStorage.setItem('rully_tg_init_data', initData); } catch (e) {}
      updateDriverProfileUI();
    } catch (e) {
      console.warn("Auth initialization error, using fallback session:", e);
      state.authPending = false;
      if (!state.user) {
        initData = "dev_user_8809526955";
        state.user = { first_name: "Haydovchi", username: "kurs_savdo", language: state.lang || "uz_latn" };
        state.subscription = { is_pro: false, tier: 'free' };
        updateDriverProfileUI();
        updateSubscriptionUI();
        updateAiProLockState();
      }
    }

    applyLocalization();

    // Dismiss loading screen immediately - cockpit dashboard is fully ready!
    dismissLoading();

    // Background warm-up (non-blocking SWR)
    Promise.allSettled([
      loadCategories(),
      updateSavedQuestionsCount()
    ]);
  }

  function applyTelemetryUI(data) {
    if (!data) return;
    const s = data.stats || {};
    const passRateEl = document.getElementById('stat-pass-rate-val');
    if (passRateEl) passRateEl.textContent = `${s.pass_rate || 0}%`;
    const testsEl = document.getElementById('stat-tests-val');
    if (testsEl) testsEl.textContent = s.total_exams || 0;
    const accEl = document.getElementById('stat-accuracy-val');
    if (accEl) accEl.textContent = `${s.accuracy || 0}%`;

    const streakEl = document.getElementById('user-streak-text');
    if (data.streak && streakEl) {
      streakEl.textContent = `${data.streak.current_streak} kun`;
    }

    updateReadinessClusterUI();
  }

  function updateDriverProfileUI() {
    const avatarEl = document.getElementById('user-avatar');
    const nameEl = document.getElementById('user-name');
    const profileNameEl = document.getElementById('profile-name');
    const profileTgIdEl = document.getElementById('profile-tg-id');

    if (state.user) {
      const initial = (state.user.first_name || 'R').charAt(0).toUpperCase();
      if (avatarEl) avatarEl.textContent = initial;
      if (nameEl) nameEl.textContent = state.user.first_name || 'Haydovchi';
      if (profileNameEl) profileNameEl.textContent = state.user.first_name || 'Haydovchi';
      if (profileTgIdEl) profileTgIdEl.textContent = `Telegram ID: ${state.user.user_id || '8809526955'}`;
    }
  }

  async function loadTelemetryData() {
    try {
      const data = await apiFetch('/api/user/me');
      state.stats = data;
      if (data.subscription) {
        state.subscription = data.subscription;
      }
      updateSubscriptionUI();
      applyTelemetryUI(data);
    } catch (e) {
      console.error("Telemetry fetch failed", e);
    }
  }

  // 9. Categories Engine (with SWR Session Cache)
  async function loadCategories() {
    const cacheKey = `rully_categories_${state.lang}`;
    try {
      const cached = sessionStorage.getItem(cacheKey);
      if (cached) {
        state.categories = JSON.parse(cached);
        renderCategoriesList();
      }
    } catch (e) {}

    try {
      const data = await apiFetch(`/api/categories?lang=${state.lang}`);
      state.categories = data.categories || [];
      try { sessionStorage.setItem(cacheKey, JSON.stringify(state.categories)); } catch (e) {}
      renderCategoriesList();
    } catch (e) {
      console.error("Categories fetch failed", e);
    }
  }

  function renderCategoriesList(filterText = "") {
    const listEl = document.getElementById('categories-list');
    if (!listEl) return;

    const filtered = state.categories.filter(c =>
      c.name.toLowerCase().includes(filterText.toLowerCase())
    );

    listEl.innerHTML = filtered.map(cat => `
      <div class="category-row-card" data-cat-id="${cat.category_id}">
        <div class="cat-row-left">
          <div class="cat-badge-number">${cat.category_id !== null ? cat.category_id : '#'}</div>
          <div class="cat-info-block">
            <div class="cat-name-txt">${cat.name}</div>
            <div class="cat-count-txt">${t('questions_count', { n: cat.question_count })}</div>
          </div>
        </div>
        <span class="r-icon sm" style="color: var(--apex-emerald);">${window.renderIcon ? window.renderIcon('chevronRight') : '➔'}</span>
      </div>
    `).join('');

    listEl.querySelectorAll('.category-row-card').forEach(card => {
      card.addEventListener('click', () => {
        triggerHaptic('impact', 'light');
        const catId = card.getAttribute('data-cat-id');
        const parsed = parseInt(catId, 10);
        startQuizSession('CATEGORY', isNaN(parsed) ? 0 : parsed);
      });
    });
  }

  // 10. Navigation View Switching
  function switchTab(tabName, subSection = null) {
    if (tabName === 'results') {
      tabName = 'profile';
    }

    state.activeTab = tabName;
    triggerHaptic('impact', 'light');

    // Toggle full-viewport chat layout for AI Ustoz
    const isAi = tabName === 'ai';
    document.documentElement.classList.toggle('tab-ai-active', isAi);
    document.body.classList.toggle('tab-ai-active', isAi);
    document.body.classList.remove('keyboard-open');
    document.documentElement.style.removeProperty('--keyboard-inset');
    document.documentElement.style.removeProperty('--ai-viewport-height');
    document.documentElement.style.removeProperty('--ai-viewport-top');
    document.documentElement.style.removeProperty('--ai-keyboard-offset');
    if (isAi && window.Telegram?.WebApp?.expand) {
      try { window.Telegram.WebApp.expand(); } catch (_) {}
    }
    window.scrollTo(0, 0);
    document.body.scrollTop = 0;
    document.documentElement.scrollTop = 0;

    document.querySelectorAll('.view-pane').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-bar-item').forEach(el => el.classList.remove('active'));

    const targetPane = document.getElementById(`view-${tabName}`);
    const targetNav = document.getElementById(`nav-${tabName}`);

    if (targetPane) targetPane.classList.add('active');
    if (targetNav) targetNav.classList.add('active');

    // Section specific loaders
    if (tabName === 'amaliy') {
      loadPracticalModules();
    } else if (tabName === 'profile') {
      renderProfileSettings();
      loadResultsHistory();
      updateSubscriptionUI();
    } else if (tabName === 'tests') {
      updateSavedQuestionsCount();
    } else if (tabName === 'ai') {
      updateAiProLockState();
      if (!state.subscription?.is_pro) {
        openPaywallModal('ai');
      } else {
        initAiChat();
        setTimeout(() => {
          scrollAiToBottom(false);
        }, 80);
      }
    }
  }

  // 11. Interactive Quiz Player & Exam Simulation Engine
  let isStartingQuizSession = false;

  async function startQuizSession(sessionType, categoryId = null, totalQuestions = 20, options = {}) {
    if (isStartingQuizSession) return;
    isStartingQuizSession = true;

    triggerHaptic('impact', 'medium');
    const heroBtn = document.getElementById('hero-start-btn');
    if (heroBtn && sessionType === 'EXAM') {
      heroBtn.style.opacity = '0.75';
      heroBtn.style.transform = 'scale(0.97)';
    }
    try {
      // In Official State Exam mode: 20 questions, 25 minutes, no statutory explanations
      if (sessionType === 'EXAM') {
        options.showExplanation = false;
        totalQuestions = 20;
      }

      const timeLimitSeconds = options.timeLimitSeconds !== undefined ? options.timeLimitSeconds : (sessionType === 'EXAM' ? 25 * 60 : 0);
      const showAnswer = options.showAnswer !== undefined ? options.showAnswer : true;
      const showExplanation = sessionType === 'EXAM' ? false : (options.showExplanation !== undefined ? options.showExplanation : true);

      const payload = {
        session_type: sessionType,
        category_id: categoryId,
        total_questions: totalQuestions,
        language: state.lang,
        time_limit_seconds: timeLimitSeconds,
        show_answer: showAnswer,
        show_explanation: showExplanation
      };

      const res = await apiFetch('/api/session/start', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      const serverTimeLimit = res.time_limit_seconds !== undefined ? res.time_limit_seconds : timeLimitSeconds;

      state.quiz = {
        active: true,
        sessionId: res.session_id,
        sessionType: res.session_type,
        categoryId: categoryId,
        totalQuestions: res.total_questions || totalQuestions,
        questions: res.questions,
        currentIndex: 0,
        answers: {},
        timeLimit: serverTimeLimit,
        timeRemaining: serverTimeLimit,
        showAnswer: res.show_answer !== undefined ? res.show_answer : showAnswer,
        showExplanation: sessionType === 'EXAM' ? false : (res.show_explanation !== undefined ? res.show_explanation : showExplanation),
        timerInterval: null,
        startTime: Date.now(),
        isSubmitting: false
      };

      // Background preload all 20 question images across multi-CDN network
      if (Array.isArray(res.questions)) {
        preloadQuizImages(res.questions);
      }

      const overlay = document.getElementById('quiz-overlay');
      overlay.classList.add('active');
      const isTerminalMode = (sessionType === 'EXAM' || sessionType === 'CUSTOM');
      if (isTerminalMode) {
        overlay.classList.add('exam-mode');
        if (state.quiz.showExplanation === false) {
          overlay.classList.add('no-explanation');
        } else {
          overlay.classList.remove('no-explanation');
        }
      } else {
        overlay.classList.remove('exam-mode');
        overlay.classList.remove('no-explanation');
      }

      updateNativeBackButton();

      startCountdownTimer();
      renderCurrentQuestion();
    } catch (e) {
      alert("Sinovni boshlashda xatolik: " + e.message);
    } finally {
      isStartingQuizSession = false;
      const heroBtn = document.getElementById('hero-start-btn');
      if (heroBtn) {
        heroBtn.style.opacity = '';
        heroBtn.style.transform = '';
      }
    }
  }

  function startCountdownTimer() {
    clearInterval(state.quiz.timerInterval);
    const timerPill = document.getElementById('quiz-timer-pill');
    const timerVal = document.getElementById('quiz-timer-val');

    // If unlimited time (0 seconds)
    if (!state.quiz.timeLimit || state.quiz.timeLimit <= 0) {
      if (timerPill) {
        timerPill.style.display = 'none';
        timerPill.classList.remove('danger');
      }
      if (timerVal) timerVal.textContent = '';
      return;
    }

    if (timerPill) {
      timerPill.style.display = 'inline-flex';
      timerPill.classList.remove('danger');
    }

    // Precise wall-clock deadline immune to mobile backgrounding/sleep drift
    const quizDeadline = Date.now() + (state.quiz.timeRemaining * 1000);
    function tickQuiz() {
      const remaining = Math.max(0, Math.round((quizDeadline - Date.now()) / 1000));
      state.quiz.timeRemaining = remaining;

      const mins = Math.floor(remaining / 60);
      const secs = remaining % 60;
      if (timerVal) {
        timerVal.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
      }

      // Warning pulse below 2 minutes
      if (remaining <= 120) {
        timerPill?.classList.add('danger');
      } else {
        timerPill?.classList.remove('danger');
      }

      if (remaining <= 0) {
        clearInterval(state.quiz.timerInterval);
        finishQuiz();
      }
    }

    tickQuiz();
    state.quiz.timerInterval = setInterval(tickQuiz, 1000);
  }

  // ==========================================================================
  // MULTI-CDN RESILIENT IMAGE DELIVERY & PRELOAD PIPELINE
  // Candidate fallback chain:
  // 1. Primary cdn.jsdelivr.net URL
  // 2. Fastly jsDelivr Edge CDN
  // 3. GitHub Raw direct origin
  // 4. Statically Global CDN
  // 5. Same-origin Vercel serverless proxy (/images/{filename})
  // ==========================================================================
  const _imgResolvedCache = new Map();

  function getCdnCandidateUrls(primaryUrl) {
    if (!primaryUrl) return [];
    const filename = primaryUrl.split('?')[0].split('/').pop();
    if (!filename) return [primaryUrl];

    const candidates = [
      primaryUrl,
      `https://rully-app.onrender.com/images/${filename}`,
      `https://fastly.jsdelivr.net/gh/aralovv/Rully@main/data/images/original/${filename}`,
      `https://raw.githubusercontent.com/aralovv/Rully/main/data/images/original/${filename}`,
      `https://cdn.statically.io/gh/aralovv/Rully/main/data/images/original/${filename}`,
      `/images/${filename}`
    ];
    return Array.from(new Set(candidates));
  }

  function preloadImage(url) {
    if (!url || _imgResolvedCache.has(url)) return;
    const candidates = getCdnCandidateUrls(url);
    const tryNext = (idx) => {
      if (idx >= candidates.length) return;
      const testImg = new Image();
      testImg.onload = () => {
        _imgResolvedCache.set(url, candidates[idx]);
      };
      testImg.onerror = () => {
        tryNext(idx + 1);
      };
      testImg.src = candidates[idx];
    };
    tryNext(0);
  }

  function preloadQuizImages(questions) {
    if (!Array.isArray(questions)) return;
    questions.forEach(q => {
      if (q && q.has_image && q.image_url) {
        preloadImage(q.image_url);
      }
    });
  }

  function loadImageWithFallback(imgEl, primaryUrl, onLoaded, onError) {
    if (!imgEl || !primaryUrl) return;

    const resolvedUrl = _imgResolvedCache.get(primaryUrl);
    const candidates = resolvedUrl
      ? [resolvedUrl, ...getCdnCandidateUrls(primaryUrl).filter(u => u !== resolvedUrl)]
      : getCdnCandidateUrls(primaryUrl);

    let candidateIdx = 0;

    const tryLoad = () => {
      if (candidateIdx >= candidates.length) {
        if (typeof onError === 'function') onError();
        return;
      }
      const candidateUrl = candidates[candidateIdx];
      const loader = new Image();
      loader.onload = () => {
        _imgResolvedCache.set(primaryUrl, candidateUrl);
        imgEl.src = candidateUrl;
        if (typeof onLoaded === 'function') onLoaded(candidateUrl);
      };
      loader.onerror = () => {
        candidateIdx++;
        tryLoad();
      };
      loader.src = candidateUrl;
    };

    tryLoad();
  }

  window.handleSavedImgError = function(imgEl, originalUrl) {
    if (!imgEl || imgEl._hasTriedFallback) return;
    imgEl._hasTriedFallback = true;
    loadImageWithFallback(imgEl, originalUrl, (workingUrl) => {
      imgEl.src = workingUrl;
    });
  };

  function renderCurrentQuestion() {
    state.quiz.questionRenderedAt = Date.now();
    state.quiz.isSubmitting = false;

    const q = state.quiz.questions[state.quiz.currentIndex];
    if (!q) return;

    const total = state.quiz.questions.length;
    const curIdx = state.quiz.currentIndex + 1;
    const isTerminalMode = (state.quiz.sessionType === 'EXAM' || state.quiz.sessionType === 'CUSTOM');

    // Reset overlay scroll position when switching to a different question
    const overlay = document.getElementById('quiz-overlay');
    if (overlay && state.quiz._lastRenderedIndex !== state.quiz.currentIndex) {
      overlay.scrollTop = 0;
      state.quiz._lastRenderedIndex = state.quiz.currentIndex;
    }

    document.getElementById('quiz-counter-text').textContent = `${curIdx.toString().padStart(2, '0')} / ${total.toString().padStart(2, '0')}`;

    const pct = (curIdx / total) * 100;
    const progressFill = document.getElementById('quiz-progress-fill');
    if (progressFill) progressFill.style.width = `${pct}%`;

    // Terminal Mode (EXAM & CUSTOM) vs Practice Mode Layout Switches
    const matrixNav = document.getElementById('exam-matrix-nav');
    const progressTrack = document.getElementById('quiz-progress-track');
    const standardActions = document.getElementById('quiz-standard-actions');
    const finishBar = document.getElementById('exam-finish-bar');
    const fbBox = document.getElementById('quiz-feedback-box');

    if (isTerminalMode) {
      if (matrixNav) matrixNav.style.display = 'grid';
      if (progressTrack) progressTrack.style.display = 'none';
      if (standardActions) standardActions.style.display = 'none';
      if (finishBar) finishBar.style.display = 'block';

      // Update finish button label depending on session type
      const finishBtnLabel = document.querySelector('#btn-exam-finish [data-i18n="btn_finish_quiz"]');
      if (finishBtnLabel) {
        if (state.quiz.sessionType === 'CUSTOM') {
          finishBtnLabel.textContent = t('btn_finish_test') || 'Yakunlash';
        } else {
          finishBtnLabel.textContent = t('btn_finish_quiz') || 'Imtihonni yakunlash';
        }
      }

      renderExamMatrix();
    } else {
      if (matrixNav) matrixNav.style.display = 'none';
      if (progressTrack) progressTrack.style.display = 'block';
      if (standardActions) standardActions.style.display = 'flex';
      if (finishBar) finishBar.style.display = 'none';
      if (fbBox) fbBox.style.display = '';
    }

    // Metadata & Bookmark
    let catBadgeText = q.category_name || "Yo‘l Harakati Qoidalari";
    if (state.quiz.sessionType === 'MISTAKES') {
      catBadgeText = t('card_mistakes_title');
    } else if (state.quiz.sessionType === 'CUSTOM') {
      catBadgeText = t('custom_quiz_card_title');
    } else if (state.quiz.sessionType === 'EXAM') {
      catBadgeText = t('hero_title');
    }
    document.getElementById('quiz-cat-name').textContent = catBadgeText;
    const bookmarkBtn = document.getElementById('btn-quiz-bookmark');
    if (bookmarkBtn) {
      bookmarkBtn.classList.toggle('active', !!q.is_bookmarked);
      bookmarkBtn.innerHTML = window.renderIcon ? window.renderIcon(q.is_bookmarked ? 'bookmarkFill' : 'bookmark') : '★';
      bookmarkBtn.onclick = () => toggleBookmark(q.canonical_id);
    }

    // Illustration Viewport with Multi-CDN Resilient Pipeline
    const imgWrap = document.getElementById('quiz-image-wrap');
    const imgEl = document.getElementById('quiz-image');
    const imgSpinner = document.getElementById('quiz-image-spinner');
    const imgRetry = document.getElementById('quiz-image-retry');
    const imgZoomHint = document.getElementById('quiz-zoom-hint');

    if (q.has_image && q.image_url) {
      imgWrap.style.display = 'flex';
      imgEl.classList.remove('loaded');
      if (imgSpinner) imgSpinner.style.display = 'flex';
      if (imgRetry) imgRetry.style.display = 'none';
      if (imgZoomHint) imgZoomHint.style.display = 'none';
      imgWrap.onclick = null;

      const triggerLoad = () => {
        if (imgSpinner) imgSpinner.style.display = 'flex';
        if (imgRetry) imgRetry.style.display = 'none';
        imgEl.classList.remove('loaded');

        loadImageWithFallback(
          imgEl,
          q.image_url,
          (workingUrl) => {
            if (imgSpinner) imgSpinner.style.display = 'none';
            if (imgRetry) imgRetry.style.display = 'none';
            if (imgZoomHint) imgZoomHint.style.display = 'flex';
            imgEl.classList.add('loaded');
            imgWrap.onclick = () => openLightbox(workingUrl);
          },
          () => {
            if (imgSpinner) imgSpinner.style.display = 'none';
            if (imgRetry) {
              imgRetry.style.display = 'flex';
              imgRetry.onclick = (e) => {
                e.stopPropagation();
                triggerLoad();
              };
            }
          }
        );
      };

      triggerLoad();
    } else {
      imgWrap.style.display = 'none';
      imgEl.src = '';
      imgEl.classList.remove('loaded');
    }

    // Question Editorial Prompt
    document.getElementById('quiz-question-text').textContent = q.question_text;

    // Tactical Option Cards
    const optionsWrap = document.getElementById('quiz-options-list');
    const existingAns = state.quiz.answers[q.canonical_id];

    optionsWrap.innerHTML = q.options.map((opt, optIdx) => {
      let extraClass = "";
      if (existingAns) {
        if (state.quiz.showAnswer !== false) {
          if (existingAns.is_correct === true) {
            if (opt.option_key === existingAns.selected_key) extraClass = "correct";
          } else if (existingAns.is_correct === false) {
            if (opt.option_key === existingAns.correct_key) extraClass = "correct";
            else if (opt.option_key === existingAns.selected_key) extraClass = "wrong";
          } else {
            // Pending answer confirmation: keep neutral selected
            if (opt.option_key === existingAns.selected_key) extraClass = "selected";
          }
        } else {
          // If showAnswer is disabled, only show what was selected
          if (opt.option_key === existingAns.selected_key) {
            extraClass = "selected";
          }
        }
      }

      // F1, F2, F3... in Terminal Mode (EXAM and CUSTOM)
      const badgeHtml = isTerminalMode
        ? `<div class="option-fkey-badge">F${optIdx + 1}</div>`
        : `<div class="option-disc-badge">${opt.option_key}</div>`;

      return `
        <div class="tactical-option-card ${extraClass}" data-key="${opt.option_key}">
          ${badgeHtml}
          <div class="option-body-txt">${opt.text}</div>
        </div>
      `;
    }).join('');

    optionsWrap.querySelectorAll('.tactical-option-card').forEach(card => {
      card.onclick = () => {
        if (state.quiz.answers[q.canonical_id] || state.quiz.isSubmitting) return;
        submitAnswer(q.canonical_id, card.getAttribute('data-key'));
      };
    });

    // Statutory Reference Drawer
    // Never in EXAM, and in CUSTOM only if showExplanation !== false
    if (existingAns && state.quiz.sessionType !== 'EXAM' && state.quiz.showExplanation !== false) {
      fbBox.classList.add('active');
      fbBox.style.display = 'block';
      const headerTitle = fbBox.querySelector('.statutory-header');
      if (headerTitle) {
        const iconSvg = window.renderIcon ? window.renderIcon(existingAns.is_correct ? 'checkCircle' : 'xCircle') : '';
        headerTitle.innerHTML = `<span class="r-icon sm">${iconSvg}</span> <span>${existingAns.is_correct ? t('correct_badge') : t('wrong_badge')}</span>`;
      }
      if (existingAns.is_correct) {
        fbBox.classList.remove('wrong');
        fbBox.classList.add('correct');
      } else {
        fbBox.classList.remove('correct');
        fbBox.classList.add('wrong');
      }
      document.getElementById('feedback-clause-text').textContent = existingAns.legal_reference ? `${t('rule_clause')} ${existingAns.legal_reference}` : '';
      document.getElementById('feedback-desc-text').textContent = existingAns.explanation || '';
    } else {
      fbBox.classList.remove('active');
      fbBox.style.display = 'none';
    }

    // Bottom Navigation Buttons (Only shown in non-terminal mode)
    if (!isTerminalMode) {
      const prevBtn = document.getElementById('btn-quiz-prev');
      const nextBtn = document.getElementById('btn-quiz-next');
      if (prevBtn && nextBtn) {
        prevBtn.style.visibility = state.quiz.currentIndex > 0 ? 'visible' : 'hidden';

        if (state.quiz.currentIndex === total - 1) {
          nextBtn.innerHTML = `<span>${t('btn_finish_quiz')}</span> ${window.renderIcon ? window.renderIcon('check') : ''}`;
          nextBtn.onclick = () => finishQuiz();
        } else {
          nextBtn.innerHTML = `<span>${t('btn_next')}</span> ${window.renderIcon ? window.renderIcon('arrowRight') : ''}`;
          nextBtn.onclick = () => {
            triggerHaptic('impact', 'light');
            state.quiz.currentIndex++;
            renderCurrentQuestion();
          };
        }

        prevBtn.onclick = () => {
          triggerHaptic('impact', 'light');
          state.quiz.currentIndex--;
          renderCurrentQuestion();
        };
      }
    }
  }

  function renderExamMatrix() {
    const matrixNav = document.getElementById('exam-matrix-nav');
    const isTerminalMode = (state.quiz.sessionType === 'EXAM' || state.quiz.sessionType === 'CUSTOM');
    if (!matrixNav || !isTerminalMode) return;

    const total = state.quiz.questions.length;
    if (total > 20) {
      matrixNav.classList.add('matrix-dense');
    } else {
      matrixNav.classList.remove('matrix-dense');
    }

    let html = '';
    for (let i = 0; i < total; i++) {
      const qItem = state.quiz.questions[i];
      const ans = state.quiz.answers[qItem.canonical_id];
      let statusClass = 'unanswered';
      if (ans) {
        if (ans.is_correct === true) {
          statusClass = (state.quiz.showAnswer !== false) ? 'correct' : 'answered';
        } else if (ans.is_correct === false) {
          statusClass = (state.quiz.showAnswer !== false) ? 'wrong' : 'answered';
        } else {
          // ans.is_correct is null or undefined (syncing with backend): keep clean 'answered' (blue)
          statusClass = 'answered';
        }
      }
      const isCurrent = (i === state.quiz.currentIndex);
      const isThreeDigit = (i + 1 >= 100);
      html += `
        <div class="exam-box-item ${statusClass} ${isCurrent ? 'current' : ''} ${isThreeDigit ? 'three-digits' : ''}" data-idx="${i}">
          ${i + 1}
        </div>
      `;
    }
    matrixNav.innerHTML = html;

    matrixNav.querySelectorAll('.exam-box-item').forEach(box => {
      box.onclick = () => {
        const idx = parseInt(box.getAttribute('data-idx'));
        if (idx !== state.quiz.currentIndex) {
          triggerHaptic('impact', 'light');
          state.quiz.currentIndex = idx;
          renderCurrentQuestion();
        }
      };
    });

    // Auto scroll the active box into view inside matrixNav only
    const currentBox = matrixNav.querySelector('.exam-box-item.current');
    if (currentBox && matrixNav.scrollHeight > matrixNav.clientHeight) {
      const boxTop = currentBox.offsetTop;
      const boxBottom = boxTop + currentBox.offsetHeight;
      if (boxTop < matrixNav.scrollTop) {
        matrixNav.scrollTop = Math.max(0, boxTop - 4);
      } else if (boxBottom > matrixNav.scrollTop + matrixNav.clientHeight) {
        matrixNav.scrollTop = boxBottom - matrixNav.clientHeight + 4;
      }
    }
  }

  const MIN_ANSWER_COOLDOWN_MS = 70; // 70ms debounce avoids duplicate rapid taps without lagging real user action

  async function submitAnswer(canonicalId, selectedKey) {
    if (!state.quiz.active) return;
    if (state.quiz.isSubmitting) return;
    if (state.quiz.answers && state.quiz.answers[canonicalId]) return;

    // Cooldown check: ignore taps that land within 70ms of question render
    const now = Date.now();
    if (state.quiz.questionRenderedAt && (now - state.quiz.questionRenderedAt < MIN_ANSWER_COOLDOWN_MS)) {
      return;
    }

    state.quiz.isSubmitting = true;

    // Resolve question & immediate answer verification in 0ms (no server wait!)
    const q = (state.quiz.questions && state.quiz.questions.find(item => item.canonical_id === canonicalId)) || (state.quiz.questions ? state.quiz.questions[state.quiz.currentIndex] : null);
    const correctKey = (q && q.correct_option_key) ? q.correct_option_key.toUpperCase() : null;
    const isCorrect = (correctKey !== null) ? (selectedKey.toUpperCase() === correctKey) : null;

    // 1. Instant visual feedback: immediately highlight clicked card & disable options
    const optionsWrap = document.getElementById('quiz-options-list');
    if (optionsWrap) {
      const cards = optionsWrap.querySelectorAll('.tactical-option-card');
      cards.forEach(c => {
        c.style.pointerEvents = 'none';
        const cardKey = c.getAttribute('data-key');
        if (state.quiz.showAnswer !== false && isCorrect !== null) {
          if (cardKey === selectedKey) {
            c.classList.add(isCorrect ? 'correct' : 'wrong');
          } else if (!isCorrect && cardKey === correctKey) {
            c.classList.add('correct');
          }
        } else {
          if (cardKey === selectedKey) {
            c.classList.add('selected');
          }
        }
      });
    }

    triggerHaptic(isCorrect === false ? 'notification' : 'impact', isCorrect === false ? 'error' : 'medium');

    // Optimistically record verified answer immediately (0ms)
    state.quiz.answers[canonicalId] = {
      canonical_id: canonicalId,
      selected_key: selectedKey,
      correct_key: correctKey,
      is_correct: isCorrect,
      explanation: q ? q.explanation : '',
      legal_reference: q ? q.legal_reference : ''
    };

    const isTerminalMode = (state.quiz.sessionType === 'EXAM' || (state.quiz.sessionType === 'CUSTOM' && !state.quiz.showExplanation));

    // Instantly mark current number box in matrix navigation as correct / wrong / answered
    const targetIdx = (state.quiz.questions && state.quiz.questions.length)
      ? state.quiz.questions.findIndex(item => item.canonical_id === canonicalId)
      : state.quiz.currentIndex;
    const curBox = document.querySelector(`.exam-box-item[data-idx="${targetIdx >= 0 ? targetIdx : state.quiz.currentIndex}"]`);
    if (curBox) {
      curBox.classList.remove('unanswered', 'answered', 'correct', 'wrong');
      if (state.quiz.showAnswer !== false && isCorrect !== null) {
        curBox.classList.add(isCorrect ? 'correct' : 'wrong');
      } else {
        curBox.classList.add('answered');
      }
    }

    // Track mistakes locally for instant termination
    if (isCorrect === false && state.quiz.sessionType === 'EXAM') {
      state.quiz.incorrectCount = (state.quiz.incorrectCount || 0) + 1;
      if (state.quiz.incorrectCount >= 3) {
        state.quiz.active = false;
        if (state.quiz.advanceTimeout) {
          clearTimeout(state.quiz.advanceTimeout);
          state.quiz.advanceTimeout = null;
        }
        triggerHaptic('notification', 'error');
        if (typeof showToast === 'function') {
          showToast(t('res_exam_terminated_toast') || 'Imtihon to‘xtatildi: 2 tadan ortiq xato qilindi!');
        }
        // Send answer and then finish session
        apiFetch('/api/session/answer', {
          method: 'POST',
          body: JSON.stringify({
            session_id: state.quiz.sessionId,
            canonical_id: canonicalId,
            selected_key: selectedKey,
            language: state.lang
          })
        }).finally(() => {
          finishQuiz(true);
        });
        return;
      }
    }

    // Background asynchronous sync to backend (non-blocking)
    apiFetch('/api/session/answer', {
      method: 'POST',
      body: JSON.stringify({
        session_id: state.quiz.sessionId,
        canonical_id: canonicalId,
        selected_key: selectedKey,
        language: state.lang
      })
    }).then(res => {
      if (state.quiz.answers) {
        state.quiz.answers[canonicalId] = {
          ...state.quiz.answers[canonicalId],
          ...res
        };
      }
      // Immediate termination if 3rd mistake confirmed by backend
      if (state.quiz.sessionType === 'EXAM' && res.is_exam_terminated && state.quiz.active) {
        state.quiz.active = false;
        if (state.quiz.advanceTimeout) {
          clearTimeout(state.quiz.advanceTimeout);
          state.quiz.advanceTimeout = null;
        }
        triggerHaptic('notification', 'error');
        if (typeof showToast === 'function') {
          showToast(t('res_exam_terminated_toast') || 'Imtihon to‘xtatildi: 2 tadan ortiq xato qilindi!');
        }
        finishQuiz(true);
      }
    }).catch(err => {
      console.warn("Background answer sync error:", err);
    });

    // 2. Terminal mode (Official EXAM or fast practice): instant advance after 100ms micro-delay
    if (isTerminalMode) {
      if (state.quiz.advanceTimeout) {
        clearTimeout(state.quiz.advanceTimeout);
        state.quiz.advanceTimeout = null;
      }

      state.quiz.advanceTimeout = setTimeout(() => {
        if (!state.quiz.active) return;
        let nextUnanswered = -1;
        for (let i = 1; i <= state.quiz.questions.length; i++) {
          const checkIdx = (state.quiz.currentIndex + i) % state.quiz.questions.length;
          const qCheck = state.quiz.questions[checkIdx];
          if (!state.quiz.answers[qCheck.canonical_id]) {
            nextUnanswered = checkIdx;
            break;
          }
        }

        if (nextUnanswered !== -1) {
          state.quiz.currentIndex = nextUnanswered;
          renderCurrentQuestion();
        } else {
          state.quiz.isSubmitting = false;
          const finishBtn = document.getElementById('btn-exam-finish');
          if (finishBtn) {
            finishBtn.classList.add('pulse-highlight');
          }
        }
      }, 100);
      return;
    }

    // 3. Regular practice mode: show explanation drawer immediately (0ms)
    state.quiz.isSubmitting = false;
    const fbBox = document.getElementById('quiz-feedback-box');
    if (fbBox && state.quiz.showExplanation !== false && state.quiz.sessionType !== 'EXAM') {
      fbBox.classList.add('active');
      fbBox.style.display = 'block';
      const headerTitle = fbBox.querySelector('.statutory-header');
      if (headerTitle) {
        const iconSvg = window.renderIcon ? window.renderIcon(isCorrect ? 'checkCircle' : 'xCircle') : '';
        headerTitle.innerHTML = `<span class="r-icon sm">${iconSvg}</span> <span>${isCorrect ? t('correct_badge') : t('wrong_badge')}</span>`;
      }
      if (isCorrect) {
        fbBox.classList.remove('wrong');
        fbBox.classList.add('correct');
      } else {
        fbBox.classList.remove('correct');
        fbBox.classList.add('wrong');
      }
      const clauseEl = document.getElementById('feedback-clause-text');
      if (clauseEl) clauseEl.textContent = q?.legal_reference ? `${t('rule_clause')} ${q.legal_reference}` : '';
      const descEl = document.getElementById('feedback-desc-text');
      if (descEl) descEl.textContent = q?.explanation || '';

      setTimeout(() => {
        const fbBoxEl = document.getElementById('quiz-feedback-box');
        if (fbBoxEl && fbBoxEl.classList.contains('active')) {
          fbBoxEl.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
      }, 120);
    }
  }

  let isTogglingBookmark = false;
  async function toggleBookmark(canonicalId) {
    if (isTogglingBookmark) return;
    isTogglingBookmark = true;
    triggerHaptic('impact', 'light');
    try {
      const res = await apiFetch('/api/bookmarks/toggle', {
        method: 'POST',
        body: JSON.stringify({ canonical_id: canonicalId })
      });
      const q = state.quiz.questions.find(item => item.canonical_id === canonicalId);
      if (q) q.is_bookmarked = res.is_bookmarked;
      const bookmarkBtn = document.getElementById('btn-quiz-bookmark');
      if (bookmarkBtn) {
        bookmarkBtn.classList.toggle('active', res.is_bookmarked);
        bookmarkBtn.innerHTML = window.renderIcon ? window.renderIcon(res.is_bookmarked ? 'bookmarkFill' : 'bookmark') : '★';
      }
      updateSavedQuestionsCount();
    } catch (e) {
      console.error("Bookmark toggle failed", e);
    } finally {
      isTogglingBookmark = false;
    }
  }

  function confirmQuitQuiz() {
    if (confirm(t('confirm_finish_text'))) {
      closeQuizOverlay();
    }
  }

  function closeQuizOverlay() {
    clearInterval(state.quiz.timerInterval);
    state.quiz.active = false;
    const overlay = document.getElementById('quiz-overlay');
    overlay.classList.remove('active');
    overlay.classList.remove('exam-mode');
    overlay.classList.remove('no-explanation');
    const finishBtn = document.getElementById('btn-exam-finish');
    if (finishBtn) finishBtn.classList.remove('pulse-highlight');
    updateNativeBackButton();
  }

  async function finishQuiz(isAutoTerminated = false) {
    state.quiz.active = false;
    if (state.quiz.advanceTimeout) {
      clearTimeout(state.quiz.advanceTimeout);
      state.quiz.advanceTimeout = null;
    }
    clearInterval(state.quiz.timerInterval);
    triggerHaptic('impact', 'heavy');
    state.lastAuthAt = 0; // Invalidate profile cache so fresh results/stats will be fetched

    const elapsed = (Date.now() - state.quiz.startTime) / 1000;
    try {
      const res = await apiFetch('/api/session/finish', {
        method: 'POST',
        body: JSON.stringify({
          session_id: state.quiz.sessionId,
          time_elapsed_seconds: elapsed
        })
      });

      if (isAutoTerminated) {
        res.is_terminated_mistakes = true;
      }
      showResultsCockpitModal(res);
    } catch (e) {
      console.error("Finish quiz error", e);
      closeQuizOverlay();
    }
  }

  function showResultsCockpitModal(result) {
    closeQuizOverlay();
    const modal = document.getElementById('results-modal');
    modal.classList.add('active');

    const iconBox = document.getElementById('result-icon-box');
    const titleEl = document.getElementById('result-title');
    const subtitleEl = document.getElementById('result-subtitle');
    const scorePctEl = document.getElementById('result-score-pct');
    const scoreFractionEl = document.getElementById('result-score-fraction');
    const timeSpentEl = document.getElementById('result-time-spent');
    const scoreCircleEl = document.getElementById('result-score-circle');

    const isCustom = (state.quiz.sessionType === 'CUSTOM');
    const pct = Math.round(result.percentage !== undefined ? result.percentage : 0);

    if (isCustom) {
      // Aralash test (Custom test): Never show "Test ne sdan" / "Afsuski, o'ta olmadingiz"
      if (pct >= 80) {
        iconBox.className = 'result-icon-container passed';
        iconBox.innerHTML = window.renderIcon ? window.renderIcon('trophy') : '🏆';
        titleEl.className = 'result-verdict-title passed';
        titleEl.textContent = t('res_custom_great_title') || 'Aʼlo natija!';
        subtitleEl.textContent = t('res_custom_passed_subtitle');
        scoreCircleEl.className = 'score-dial-badge';
        triggerHaptic('notification', 'success');
      } else if (pct >= 50) {
        iconBox.className = 'result-icon-container passed';
        iconBox.innerHTML = window.renderIcon ? window.renderIcon('checkCircle') : '⭐';
        titleEl.className = 'result-verdict-title passed';
        titleEl.textContent = t('res_custom_good_title') || 'Yaxshi natija!';
        subtitleEl.textContent = t('res_custom_failed_subtitle');
        scoreCircleEl.className = 'score-dial-badge';
        triggerHaptic('notification', 'success');
      } else {
        iconBox.className = 'result-icon-container neutral';
        iconBox.innerHTML = window.renderIcon ? window.renderIcon('clipboard') : '📊';
        titleEl.className = 'result-verdict-title neutral';
        titleEl.textContent = t('res_custom_complete_title') || 'Sinov yakunlandi';
        subtitleEl.textContent = t('res_custom_failed_subtitle');
        scoreCircleEl.className = 'score-dial-badge neutral';
        triggerHaptic('impact', 'medium');
      }

      scorePctEl.textContent = `${pct}%`;
      scoreFractionEl.textContent = t('lbl_correct_pct_val', { c: result.correct_count, p: pct }) || `${result.correct_count} ta to‘g‘ri (${pct}%)`;
    } else {
      // Official State Exam / Category / Mistakes
      if (result.passed) {
        iconBox.className = 'result-icon-container passed';
        iconBox.innerHTML = window.renderIcon ? window.renderIcon('trophy') : '🏆';
        titleEl.className = 'result-verdict-title passed';
        titleEl.textContent = t('res_passed_title');
        if (state.quiz.sessionType === 'MISTAKES') {
          subtitleEl.textContent = t('res_mistakes_passed_subtitle');
        } else if (state.quiz.sessionType === 'CATEGORY') {
          subtitleEl.textContent = t('res_practice_passed_subtitle');
        } else {
          subtitleEl.textContent = t('res_passed_subtitle');
        }
        scoreCircleEl.className = 'score-dial-badge';
        triggerHaptic('notification', 'success');
      } else {
        iconBox.className = 'result-icon-container failed';
        iconBox.innerHTML = window.renderIcon ? window.renderIcon('alertTriangle') : '⚠️';
        titleEl.className = 'result-verdict-title failed';
        titleEl.textContent = t('res_failed_title');
        if (state.quiz.sessionType === 'MISTAKES') {
          subtitleEl.textContent = t('res_mistakes_failed_subtitle');
        } else if (state.quiz.sessionType === 'CATEGORY') {
          subtitleEl.textContent = t('res_practice_failed_subtitle');
        } else {
          if (state.quiz.sessionType === 'EXAM' && (result.incorrect_count > 2 || result.is_terminated_mistakes || result.terminated_reason === 'MAX_MISTAKES_EXCEEDED')) {
            subtitleEl.textContent = t('res_failed_mistakes_limit') || "2 tadan ortiq (3 ta) xatoga yo‘l qo‘yilgani sababli imtihon avtomatik to‘xtatildi (DYHXX VMQ 408 qoidasi).";
          } else {
            subtitleEl.textContent = t('res_failed_subtitle');
          }
        }
        scoreCircleEl.className = 'score-dial-badge failed';
        triggerHaptic('notification', 'error');
      }

      scorePctEl.textContent = `${pct}%`;
      scoreFractionEl.textContent = `${result.correct_count} / ${result.total_questions}`;
    }

    const mins = Math.floor(result.time_elapsed_seconds / 60);
    const secs = Math.round(result.time_elapsed_seconds % 60);
    timeSpentEl.textContent = `${mins} daq ${secs} son`;

    document.getElementById('result-correct-count').textContent = result.correct_count;
    document.getElementById('result-incorrect-count').textContent = result.incorrect_count;
    const unansweredEl = document.getElementById('result-unanswered-count');
    if (unansweredEl) {
      unansweredEl.textContent = result.unanswered_count !== undefined ? result.unanswered_count : (result.total_questions - result.correct_count - result.incorrect_count);
    }

    document.getElementById('btn-result-retake').onclick = () => {
      modal.classList.remove('active');
      startQuizSession(state.quiz.sessionType, state.quiz.categoryId, state.quiz.totalQuestions, {
        timeLimitSeconds: state.quiz.timeLimit,
        showAnswer: state.quiz.showAnswer,
        showExplanation: state.quiz.showExplanation
      });
    };

    document.getElementById('btn-result-home').onclick = () => {
      modal.classList.remove('active');
      switchTab('home');
      loadTelemetryData();
    };
  }

  // 12. Practical Driving Curriculum Engine
  async function loadPracticalCurriculum() {
    loadPracticalModules();
  }

  async function loadPracticalModules() {
    const listEl = document.getElementById('modules-list');
    if (!listEl) return;
    try {
      const data = await apiFetch(`/api/amaliy/modules?lang=${state.lang}`);
      state.modules = data.modules || [];

      // Update modules progress cluster card
      const pctEl = document.getElementById('modules-pct-text');
      if (pctEl) {
        pctEl.textContent = `${data.completion_percentage}% (${data.completed_count}/${data.total})`;
      }
      const pBar = document.getElementById('modules-progress-bar');
      if (pBar) {
        pBar.style.width = `${data.completion_percentage}%`;
      }

      listEl.innerHTML = data.modules.map(mod => {
        const isDone = !!mod.is_completed;
        const checkBadge = isDone
          ? `<span class="module-completed-tag">${window.renderIcon ? window.renderIcon('check') : '✓'} ${t('badge_completed')}</span>`
          : '';

        return `
          <div class="module-entry-card ${isDone ? 'completed' : ''}" data-mod-id="${mod.id}">
            <div class="module-header-row">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span class="module-badge-tag">${mod.badge}</span>
                ${checkBadge}
              </div>
              <span class="module-duration-tag">
                ${window.renderIcon ? window.renderIcon('clock') : ''}
                <span>${t('duration_mins', { n: mod.duration_min })}</span>
              </span>
            </div>
            <h4 class="module-title-h3">${mod.order}. ${mod.title}</h4>
            <p class="module-caption-p">${mod.description}</p>
          </div>
        `;
      }).join('');

      listEl.querySelectorAll('.module-entry-card').forEach(card => {
        card.onclick = () => openModuleDetail(card.getAttribute('data-mod-id'));
      });
    } catch (e) {
      console.error("Modules fetch failed", e);
    }
  }

  async function openModuleDetail(moduleId) {
    triggerHaptic('impact', 'medium');
    try {
      const mod = await apiFetch(`/api/amaliy/modules/${moduleId}?lang=${state.lang}`);
      const modal = document.getElementById('module-detail-modal');
      modal.classList.add('active');

      document.getElementById('module-detail-badge').textContent = mod.badge;
      document.getElementById('module-detail-title').textContent = `${mod.order}. ${mod.title}`;
      document.getElementById('module-detail-desc').textContent = mod.description;
      document.getElementById('module-trap-text').textContent = mod.disqualification_trap;

      const stepsWrap = document.getElementById('module-steps-list');
      stepsWrap.innerHTML = mod.steps.map(s => `
        <div class="curriculum-step-card">
          <div class="step-seq-pill">${t('step_pill', { n: s.step })}</div>
          <h5 class="step-heading">${s.title}</h5>
          <p class="step-body-inst">${s.instruction}</p>
        </div>
      `).join('');

      const mistakesWrap = document.getElementById('module-mistakes-list');
      mistakesWrap.innerHTML = mod.common_mistakes.map(m => `
        <li style="margin-bottom: 8px; font-size: 13px; color: var(--text-medium); line-height: 1.45;">${m}</li>
      `).join('');



      // Mastered / Completed toggle button
      const masterBtn = document.getElementById('btn-toggle-module-mastered');
      const masterBtnTxt = document.getElementById('module-mastered-btn-text');
      let isDone = !!mod.is_completed;

      function updateMasterBtnUI() {
        if (masterBtn && masterBtnTxt) {
          if (isDone) {
            masterBtn.style.background = 'linear-gradient(135deg, #059669 0%, #10b981 100%)';
            masterBtnTxt.textContent = `✓ ${t('module_btn_unmaster')}`;
          } else {
            masterBtn.style.background = '';
            masterBtnTxt.textContent = t('module_btn_mastered');
          }
        }
      }
      updateMasterBtnUI();

      if (masterBtn) {
        masterBtn.onclick = async () => {
          isDone = !isDone;
          updateMasterBtnUI();
          triggerHaptic('notification', isDone ? 'success' : 'warning');
          try {
            await apiFetch('/api/amaliy/modules/toggle', {
              method: 'POST',
              body: JSON.stringify({ module_id: moduleId })
            });
            loadPracticalModules();
          } catch (e) {
            console.error("Failed to toggle module", e);
          }
        };
      }

      // Close handlers (button and backdrop)
      const closeBtn = document.getElementById('btn-close-module');
      if (closeBtn) {
        closeBtn.onclick = () => modal.classList.remove('active');
      }
      modal.onclick = (e) => {
        if (e.target === modal) modal.classList.remove('active');
      };
    } catch (e) {
      console.error("Open module detail error", e);
    }
  }

  // 14. Telemetry History & Mistakes Bank
  function renderHistoryTable(history) {
    const histList = document.getElementById('history-table-body');
    if (!histList) return;
    if (!history || history.length === 0) {
      histList.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 18px;">${t('history_empty')}</td></tr>`;
    } else {
      histList.innerHTML = history.map(h => {
        const dateStr = h.created_at ? h.created_at.substring(0, 10) : '';
        const statusClass = h.passed ? 'passed' : 'failed';
        const statusText = h.passed ? t('status_passed') : t('status_failed');
        return `
          <tr style="border-bottom: 1px solid var(--border-hairline);">
            <td style="padding: 12px 8px;">${dateStr}</td>
            <td style="padding: 12px 8px; font-weight: 800; font-variant-numeric: tabular-nums;">${h.correct_count}/${h.total_questions} (${h.percentage}%)</td>
            <td style="padding: 12px 8px;"><span class="telemetry-status-badge ${statusClass}" style="font-size: 11px;">${statusText}</span></td>
          </tr>
        `;
      }).join('');
    }
  }

  async function loadResultsHistory(force = false) {
    try {
      const isFresh = (state.lastAuthAt && (Date.now() - state.lastAuthAt) < 60000);
      if (!force && isFresh && state.history) {
        if (state.subscription) updateSubscriptionUI();
        renderHistoryTable(state.history);
        return;
      }

      const data = await apiFetch('/api/user/me');
      state.lastAuthAt = Date.now();
      if (data.subscription) {
        state.subscription = data.subscription;
      }
      if (data.history) {
        state.history = data.history;
      }
      updateSubscriptionUI();
      renderHistoryTable(data.history || []);

      const mistakesData = await apiFetch(`/api/mistakes?lang=${state.lang}`);
      state.mistakesCount = mistakesData.count || 0;
      const mistakesCountEl = document.getElementById('mistakes-pool-count');
      if (mistakesCountEl) {
        mistakesCountEl.textContent = state.mistakesCount;
      }
    } catch (e) {
      console.error("Results history fetch error", e);
    }
  }

  // 15. Profile Settings & 3-Language Reactive Switcher
  function renderProfileSettings() {
    document.querySelectorAll('.lang-selector-tile').forEach(card => {
      const lang = card.getAttribute('data-lang');
      card.classList.toggle('active', lang === state.lang);
      card.onclick = async () => {
        if (lang === state.lang) return;
        triggerHaptic('impact', 'medium');
        state.lang = lang;
        try { localStorage.setItem('rully_lang', lang); } catch (e) {}
        applyLocalization();
        await apiFetch('/api/user/language', {
          method: 'POST',
          body: JSON.stringify({ language: lang })
        });
        renderProfileSettings();
        loadCategories();
        loadPracticalModules();
      };
    });
  }

  // 16. Lightbox Image Lightframe
  function openLightbox(src) {
    const modal = document.getElementById('lightbox-modal');
    const img = document.getElementById('lightbox-img');
    if (modal && img) {
      modal.classList.add('active');
      modal.onclick = () => modal.classList.remove('active');
      loadImageWithFallback(img, src, (workingUrl) => {
        img.src = workingUrl;
      });
    }
  }
  window.openLightbox = openLightbox;

  // ==========================================================================
  // SAVED QUESTIONS (SAQLANGAN SAVOLLAR) - REVIEW MODE (NOT A TEST)
  // Displays question, correct answer, and statutory explanation.
  // ==========================================================================
  let savedQuestionsCache = [];
  let savedQuestionsCacheLang = '';
  let savedQuestionsLastFetched = 0;

  async function updateSavedQuestionsCount() {
    try {
      const data = await apiFetch(`/api/bookmarks?lang=${state.lang}`);
      const count = data.count || (data.questions ? data.questions.length : 0);
      savedQuestionsCache = data.questions || [];
      savedQuestionsCacheLang = state.lang;
      savedQuestionsLastFetched = Date.now();

      const countEl = document.getElementById('saved-questions-count');
      if (countEl) countEl.textContent = count;

      const badgePill = document.getElementById('saved-questions-badge-pill');
      if (badgePill) {
        badgePill.style.display = count > 0 ? 'inline-flex' : 'none';
      }

      const captionEl = document.getElementById('saved-questions-caption-text');
      if (captionEl) {
        if (count > 0) {
          captionEl.textContent = t('saved_questions_count_caption', { n: count });
        } else {
          captionEl.textContent = t('saved_questions_card_desc');
        }
      }

      const modalBadge = document.getElementById('saved-modal-count-badge');
      if (modalBadge) {
        modalBadge.textContent = t('saved_count_n', { n: count });
      }
    } catch (e) {
      console.error("Failed to update saved questions count", e);
    }
  }

  async function openSavedQuestionsModal() {
    triggerHaptic('impact', 'medium');
    const modal = document.getElementById('saved-questions-modal');
    if (!modal) return;
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    updateNativeBackButton();

    // Ensure all modal elements are translated to active language
    applyLocalization();

    const bodyEl = document.getElementById('saved-modal-body');
    const searchWrap = document.getElementById('saved-search-wrap');
    const searchInput = document.getElementById('saved-filter-input');
    if (searchInput) searchInput.value = '';

    // Fast path: render immediately from cache if valid for active language (< 60s fresh)
    const isCacheFresh = (savedQuestionsCacheLang === state.lang && (Date.now() - savedQuestionsLastFetched) < 60000 && Array.isArray(savedQuestionsCache));
    if (isCacheFresh) {
      renderSavedQuestionsList(savedQuestionsCache);
      if (searchWrap) {
        searchWrap.style.display = savedQuestionsCache.length > 2 ? 'block' : 'none';
      }
      const modalBadge = document.getElementById('saved-modal-count-badge');
      if (modalBadge) {
        modalBadge.textContent = t('saved_count_n', { n: savedQuestionsCache.length });
      }
      const countEl = document.getElementById('saved-questions-count');
      if (countEl) countEl.textContent = savedQuestionsCache.length;
      return;
    }

    if (bodyEl) {
      bodyEl.innerHTML = `
        <div style="text-align: center; padding: 48px 16px; color: var(--text-muted);">
          <div class="loader-spinner" style="margin: 0 auto 14px auto;"></div>
          <span style="font-size: 13px;">Yuklanmoqda...</span>
        </div>
      `;
    }

    try {
      const data = await apiFetch(`/api/bookmarks?lang=${state.lang}`);
      savedQuestionsCache = data.questions || [];
      savedQuestionsCacheLang = state.lang;
      savedQuestionsLastFetched = Date.now();
      renderSavedQuestionsList(savedQuestionsCache);

      if (searchWrap) {
        searchWrap.style.display = savedQuestionsCache.length > 2 ? 'block' : 'none';
      }

      const modalBadge = document.getElementById('saved-modal-count-badge');
      if (modalBadge) {
        modalBadge.textContent = t('saved_count_n', { n: savedQuestionsCache.length });
      }
      const countEl = document.getElementById('saved-questions-count');
      if (countEl) countEl.textContent = savedQuestionsCache.length;
    } catch (e) {
      console.error("Failed to load saved questions", e);
      if (bodyEl) {
        bodyEl.innerHTML = `<div style="text-align: center; padding: 30px; color: var(--crimson);">Yuklashda xatolik yuz berdi.</div>`;
      }
    }
  }

  function closeSavedQuestionsModal() {
    triggerHaptic('impact', 'light');
    const modal = document.getElementById('saved-questions-modal');
    if (modal) modal.classList.remove('active');
    document.body.style.overflow = '';
    updateNativeBackButton();
  }

  function filterSavedQuestions(query) {
    if (!query || !query.trim()) {
      renderSavedQuestionsList(savedQuestionsCache);
      return;
    }
    const q = query.toLowerCase().trim();
    const filtered = savedQuestionsCache.filter(item => 
      (item.question_text && item.question_text.toLowerCase().includes(q)) ||
      (item.explanation && item.explanation.toLowerCase().includes(q)) ||
      (item.legal_reference && item.legal_reference.toLowerCase().includes(q)) ||
      (item.category_name && item.category_name.toLowerCase().includes(q)) ||
      (item.correct_answer_text && item.correct_answer_text.toLowerCase().includes(q))
    );
    renderSavedQuestionsList(filtered);
  }

  function renderSavedQuestionsList(questions) {
    const bodyEl = document.getElementById('saved-modal-body');
    if (!bodyEl) return;

    if (!questions || questions.length === 0) {
      bodyEl.innerHTML = `
        <div class="saved-empty-state">
          <div class="saved-empty-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
          </div>
          <h4 class="saved-empty-title">${t('saved_empty_title')}</h4>
          <p class="saved-empty-desc">${t('saved_empty_desc')}</p>
        </div>
      `;
      return;
    }

    bodyEl.innerHTML = questions.map((q, idx) => {
      const imgHtml = (q.has_image && q.image_url) ? `
        <div class="saved-question-image-wrap" onclick="openLightbox('${q.image_url}')">
          <img src="${q.image_url}" alt="Savol rasmi" loading="lazy" onerror="window.handleSavedImgError && window.handleSavedImgError(this, '${q.image_url}')" />
          <span class="saved-image-zoom-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
            <span>${t('image_zoom_hint')}</span>
          </span>
        </div>
      ` : '';

      // Render all question options with the correct one highlighted
      const optionsHtml = (q.options && q.options.length > 0) ? `
        <div class="saved-options-stack">
          ${q.options.map(opt => {
            const isCorrect = opt.option_key === q.correct_option_key;
            return `
              <div class="saved-option-row ${isCorrect ? 'is-correct' : 'is-other'}">
                <div class="saved-option-left">
                  <div class="saved-option-key-badge">${opt.option_key}</div>
                  <div class="saved-option-text">${opt.text}</div>
                </div>
                ${isCorrect ? `
                  <div class="saved-option-correct-tag">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                    <span>${t('saved_correct_tag')}</span>
                  </div>
                ` : ''}
              </div>
            `;
          }).join('')}
        </div>
      ` : '';

      const expHtml = (q.explanation || q.legal_reference) ? `
        <div class="saved-explanation-box">
          <div class="saved-explanation-header">
            <span class="r-icon xs" style="color: #38bdf8; display: inline-flex;">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
            </span>
            <span class="saved-explanation-label">${t('saved_explanation_label')}</span>
            ${q.legal_reference ? `<span class="saved-legal-ref-tag">${q.legal_reference}</span>` : ''}
          </div>
          <div class="saved-explanation-text">${q.explanation || ''}</div>
        </div>
      ` : '';

      return `
        <div class="saved-question-card" id="saved-card-${q.canonical_id}">
          <div class="saved-card-top-bar">
            <div class="saved-cat-badge">
              <span class="r-icon xs" style="display:inline-flex;">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
              </span>
              <span>№${idx + 1} • ${q.category_name || t('ai_rule_badge')}</span>
            </div>
            <button class="btn-remove-saved" data-qid="${q.canonical_id}" aria-label="O‘chirish">
              <span class="r-icon xs" style="display:inline-flex;">
                <svg viewBox="0 0 24 24" fill="currentColor" stroke="none"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
              </span>
              <span>${t('btn_remove_saved')}</span>
            </button>
          </div>
          <div class="saved-question-text">${q.question_text}</div>
          ${imgHtml}

          <button type="button" class="btn-toggle-saved-details" data-qid="${q.canonical_id}" aria-expanded="false">
            <span class="btn-toggle-saved-left">
              <span class="btn-toggle-saved-icon-eye">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              </span>
              <span class="btn-toggle-saved-text">${t('btn_show_saved_details')}</span>
            </span>
            <span class="btn-toggle-saved-chevron">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </button>

          <div class="saved-card-details-collapse" id="saved-details-${q.canonical_id}" style="display: none;">
            ${optionsHtml}
            ${expHtml}
            <button class="btn-ask-ai-saved" data-qid="${q.canonical_id}">
              <span class="btn-ai-emoji">✨</span>
              <span>${t('btn_ask_ai_saved')}</span>
            </button>
          </div>
        </div>
      `;
    }).join('');

    bodyEl.querySelectorAll('.btn-toggle-saved-details').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        triggerHaptic('impact', 'light');
        const qid = btn.getAttribute('data-qid');
        const detailsEl = document.getElementById(`saved-details-${qid}`);
        const textEl = btn.querySelector('.btn-toggle-saved-text');
        if (!detailsEl) return;

        const isCurrentlyOpen = detailsEl.style.display !== 'none';
        if (isCurrentlyOpen) {
          detailsEl.style.display = 'none';
          btn.classList.remove('is-active');
          btn.setAttribute('aria-expanded', 'false');
          if (textEl) textEl.textContent = t('btn_show_saved_details');
        } else {
          detailsEl.style.display = 'block';
          btn.classList.add('is-active');
          btn.setAttribute('aria-expanded', 'true');
          if (textEl) textEl.textContent = t('btn_hide_saved_details');
        }
      };
    });

    bodyEl.querySelectorAll('.btn-ask-ai-saved').forEach(btn => {
      btn.onclick = (e) => {
        e.stopPropagation();
        const qid = btn.getAttribute('data-qid');
        const q = (questions || []).find(item => item.canonical_id === qid);
        if (!q) return;

        closeSavedQuestionsModal();

        if (!state.subscription?.is_pro) {
          openPaywallModal('ai');
          return;
        }

        switchTab('ai');
        const optList = (q.options || []).map(o => `${o.option_key}) ${o.text}`).join('\n');
        const prompt = state.lang === 'ru'
          ? `Пожалуйста, подробно разбери этот вопрос и дорожную ситуацию на картинке:\n\nВопрос: ${q.question_text}\nВарианты:\n${optList}\nПравильный ответ: ${q.correct_option_key}`
          : state.lang === 'uz_cyrl'
          ? `Илтимос, ушбу савол ва расмдаги йўл ҳаракати вазиятини батафсил таҳлил қилиб бер:\n\nСавол: ${q.question_text}\nВариантлар:\n${optList}\nТўғри жавоб: ${q.correct_option_key}`
          : `Iltimos, ushbu savol va rasmdagi yo‘l harakati vaziyatini batafsil tahlil qilib ber:\n\nSavol: ${q.question_text}\nVariantlar:\n${optList}\nTo‘g‘ri javob: ${q.correct_option_key}`;

        sendAiMessage(prompt, q.image_url, q.canonical_id);
      };
    });

    bodyEl.querySelectorAll('.btn-remove-saved').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const qid = btn.getAttribute('data-qid');
        if (!qid) return;
        triggerHaptic('impact', 'medium');

        try {
          await apiFetch('/api/bookmarks/toggle', {
            method: 'POST',
            body: JSON.stringify({ canonical_id: qid })
          });

          const card = document.getElementById(`saved-card-${qid}`);
          if (card) {
            card.style.opacity = '0';
            card.style.transform = 'scale(0.95)';
            setTimeout(() => {
              card.remove();
              savedQuestionsCache = savedQuestionsCache.filter(item => item.canonical_id !== qid);
              const newCount = savedQuestionsCache.length;
              const modalBadge = document.getElementById('saved-modal-count-badge');
              if (modalBadge) modalBadge.textContent = t('saved_count_n', { n: newCount });
              const countEl = document.getElementById('saved-questions-count');
              if (countEl) countEl.textContent = newCount;
              const badgePill = document.getElementById('saved-questions-badge-pill');
              if (badgePill) badgePill.style.display = newCount > 0 ? 'inline-flex' : 'none';
              const captionEl = document.getElementById('saved-questions-caption-text');
              if (captionEl) {
                captionEl.textContent = newCount > 0 ? t('saved_questions_count_caption', { n: newCount }) : t('saved_questions_card_desc');
              }
              if (newCount === 0) {
                renderSavedQuestionsList([]);
              }
            }, 200);
          }
        } catch (err) {
          console.error("Failed to remove saved question", err);
        }
      };
    });
  }

  // 17. AI COPILOT / AI USTOZ INTERACTIVE ASSISTANT
  let aiChatInitialized = false;
  let aiIsGenerating = false;

  function updateAiProLockState() {
    if (state.authPending) return;
    const isPro = !!(state.subscription && state.subscription.is_pro);
    const lockedBox = document.getElementById('ai-pro-locked-box');
    const inputEl = document.getElementById('ai-input-field');
    const chipsWrap = document.getElementById('ai-quick-chips');

    if (lockedBox) {
      lockedBox.style.display = isPro ? 'none' : 'flex';
      const activateBtn = document.getElementById('btn-ai-pro-activate');
      if (activateBtn) {
        activateBtn.onclick = (e) => {
          e.stopPropagation();
          openPaywallModal('ai');
        };
      }
    }

    if (inputEl) {
      if (!isPro) {
        inputEl.placeholder = t('ai_pro_locked_placeholder') || "🔒 AI Ustozdan foydalanish uchun PRO talab qilinadi";
        inputEl.setAttribute('readonly', 'readonly');
      } else {
        inputEl.placeholder = t('ai_input_placeholder') || "YHQ yoki savol haqida so‘rang...";
        inputEl.removeAttribute('readonly');
      }
    }

    if (chipsWrap) {
      chipsWrap.style.opacity = isPro ? '1' : '0.4';
      chipsWrap.style.pointerEvents = isPro ? 'auto' : 'none';
    }
  }

  async function initAiChat() {
    updateAiProLockState();
    loadAiChatStatus();
    if (!aiChatInitialized && state.subscription?.is_pro) {
      aiChatInitialized = true;
      loadAiChatHistory();
    }
  }

  async function loadAiChatStatus() {
    try {
      const data = await apiFetch('/api/ai/status');
      if (data && data.requires_pro && state.subscription) {
        state.subscription.is_pro = false;
      }
      updateAiProLockState();
    } catch (e) {
      console.warn("Failed to load AI status:", e);
    }
  }

  async function loadAiChatHistory() {
    try {
      const data = await apiFetch('/api/ai/history');
      if (data && data.ok && data.messages && data.messages.length > 0) {
        const container = document.getElementById('ai-chat-messages');
        if (!container) return;
        
        const chips = document.getElementById('ai-quick-chips');
        container.innerHTML = '';
        
        data.messages.forEach(msg => {
          let text = msg.text;
          if (msg.role !== 'user' && (text.includes("Mavzuli test") || text.includes("Saqlanganlarimdan test"))) {
            text = t('ai_welcome_bubble');
          }
          appendAiMessageToUI(msg.role, text, []);
        });

        if (chips) container.appendChild(chips);
        container.scrollTop = container.scrollHeight;
      }
    } catch (e) {
      console.warn("Failed to load AI history:", e);
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatAiMarkdown(text) {
    if (!text) return '';
    let escaped = escapeHtml(text);

    // Strip technical canonical IDs and "Canon yhq" artifacts from assistant output
    escaped = escaped.replace(/\b(?:Canon(?:ical)?\s*(?:yhq)?[:\-]?\s*)?UZ-YHQ-[A-Z0-9]+\b/gi, '');
    escaped = escaped.replace(/\bCanon\s*yhq\b/gi, t('ai_question_prefix') || 'Savol');
    escaped = escaped.replace(/\bCanon\b/gi, t('ai_question_prefix') || 'Savol');
    
    // Headings: ### Header or ## Header
    escaped = escaped.replace(/^###\s+(.+)$/gm, '<h4 class="ai-msg-h4">$1</h4>');
    escaped = escaped.replace(/^##\s+(.+)$/gm, '<h4 class="ai-msg-h4" style="font-size:15px;">$1</h4>');
    
    // Bold: **text**
    escaped = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    
    // Italic: *text*
    escaped = escaped.replace(/\*([^\*]+?)\*/g, '<em>$1</em>');
    
    // Inline code: `code`
    escaped = escaped.replace(/`([^`]+?)`/g, '<code class="ai-msg-code">$1</code>');
    
    // Bullet lists: lines starting with "- " or "* "
    escaped = escaped.replace(/^[-*]\s+(.+)$/gm, '<div class="ai-msg-list-item"><span class="ai-msg-bullet"></span><span>$1</span></div>');
    
    // Clean up newlines around headings/lists, then convert remainder to <br>
    escaped = escaped.replace(/(<\/h4>|<\/div>)\n/g, '$1');
    escaped = escaped.replace(/\n/g, '<br>');
    
    return escaped;
  }

  function scrollAiToBottom(smooth = true) {
    const container = document.getElementById('ai-chat-messages');
    if (!container) return;
    container.scrollTo({
      top: container.scrollHeight + 120,
      behavior: smooth ? 'smooth' : 'auto'
    });
  }

  function appendAiMessageToUI(role, text, cards = [], imageUrl = null) {
    const container = document.getElementById('ai-chat-messages');
    if (!container) return;

    const isBot = role === 'assistant' || role === 'model';
    const msgDiv = document.createElement('div');
    msgDiv.className = `ai-msg ${isBot ? 'ai-msg-bot' : 'ai-msg-user'}`;

    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    let imgHtml = '';
    if (imageUrl) {
      imgHtml = `
        <div class="ai-msg-image-wrap" onclick="openLightbox('${imageUrl}')">
          <img src="${imageUrl}" alt="Savol rasmi" class="ai-msg-attached-img" />
          <span class="ai-msg-image-zoom-hint">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 11px; height: 11px;"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
            <span>Kattalashtirish</span>
          </span>
        </div>
      `;
    }

    let cardsHtml = '';
    if (cards && cards.length > 0) {
      cardsHtml = cards.map((c, idx) => {
        const qNum = c.question_number || (idx + 1);
        const qPrefix = t('ai_question_prefix') || 'Savol';
        const catName = c.category_name || t('ai_rule_badge');
        return `
        <div class="ai-card-slot" id="ai-card-${c.canonical_id || idx}">
          <div class="ai-card-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 13px; height: 13px;"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>
            <span>${qPrefix} №${qNum} • ${catName}</span>
          </div>
          <div class="ai-card-q-text">${c.question}</div>
          <div class="ai-card-options">
            ${(c.options || []).map(opt => {
              const isCorrect = opt.key === c.correct_option_key;
              return `
                <div class="ai-card-opt-row ${isCorrect ? 'correct' : ''}">
                  <strong>${opt.key})</strong> ${opt.text}
                </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
      }).join('');
    }

    const formattedText = formatAiMarkdown(text);
    const botAvatarHtml = `<img src="/static/images/rully-avatar-128.png" alt="Rully" class="ai-avatar-thumb" onerror="this.onerror=null; this.src='https://rully-app.onrender.com/static/images/rully-avatar-128.png';">`;
    const userAvatarHtml = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 15px; height: 15px;"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;

    msgDiv.innerHTML = `
      <div class="ai-msg-avatar">${isBot ? botAvatarHtml : userAvatarHtml}</div>
      <div class="ai-msg-content">
        <div class="ai-msg-bubble">${imgHtml}${formattedText}${cardsHtml}</div>
        <span class="ai-msg-time">${timeStr}</span>
      </div>
    `;

    const chips = document.getElementById('ai-quick-chips');
    if (chips && chips.parentNode === container) {
      container.insertBefore(msgDiv, chips);
    } else {
      container.appendChild(msgDiv);
    }

    scrollAiToBottom(true);
  }

  function showAiTypingIndicator() {
    const container = document.getElementById('ai-chat-messages');
    if (!container) return;

    let typing = document.getElementById('ai-typing-indicator');
    if (!typing) {
      typing = document.createElement('div');
      typing.id = 'ai-typing-indicator';
      typing.className = 'ai-msg ai-msg-bot';
      typing.innerHTML = `
        <div class="ai-msg-avatar">
          <img src="/static/images/rully-avatar-128.png" alt="Rully" class="ai-avatar-thumb" onerror="this.onerror=null; this.src='https://rully-app.onrender.com/static/images/rully-avatar-128.png';">
        </div>
        <div class="ai-msg-content">
          <div class="ai-typing-bubble">
            <span class="ai-typing-dot"></span>
            <span class="ai-typing-dot"></span>
            <span class="ai-typing-dot"></span>
          </div>
        </div>
      `;
      const chips = document.getElementById('ai-quick-chips');
      if (chips && chips.parentNode === container) {
        container.insertBefore(typing, chips);
      } else {
        container.appendChild(typing);
      }
      scrollAiToBottom(true);
    }
  }

  function hideAiTypingIndicator() {
    const typing = document.getElementById('ai-typing-indicator');
    if (typing) typing.remove();
  }

  async function sendAiMessage(promptText = null, imageUrl = null, canonicalId = null) {
    if (!state.subscription?.is_pro) {
      openPaywallModal('ai');
      return;
    }
    if (aiIsGenerating) return;

    const inputEl = document.getElementById('ai-input-field');
    const text = promptText || (inputEl ? inputEl.value.trim() : '');
    if (!text) return;

    if (!promptText && inputEl) {
      inputEl.value = '';
      inputEl.style.height = 'auto';
    }

    aiIsGenerating = true;
    const sendBtn = document.getElementById('btn-ai-send');
    if (sendBtn) sendBtn.disabled = true;

    triggerHaptic('impact', 'medium');
    appendAiMessageToUI('user', text, [], imageUrl);
    showAiTypingIndicator();

    try {
      const res = await apiFetch('/api/ai/chat', {
        method: 'POST',
        body: JSON.stringify({
          message: text,
          language: state.lang || 'uz_latn',
          image_url: imageUrl || null,
          canonical_id: canonicalId || null
        })
      });

      hideAiTypingIndicator();

      if (res && res.requires_pro) {
        if (state.subscription) state.subscription.is_pro = false;
        updateAiProLockState();
        openPaywallModal('ai');
        appendAiMessageToUI('assistant', res.reply);
        return;
      }

      if (res && res.ok) {
        appendAiMessageToUI('assistant', res.reply || t('ai_cleared_reply'), res.cards || []);
        loadAiChatStatus();
        triggerHaptic('notification', 'success');
      } else {
        appendAiMessageToUI('assistant', res.reply || t('ai_generic_error'));
      }
    } catch (e) {
      hideAiTypingIndicator();
      console.error("AI chat error:", e);
      appendAiMessageToUI('assistant', t('ai_net_error'));
    } finally {
      aiIsGenerating = false;
      if (sendBtn) sendBtn.disabled = false;
    }
  }

  async function clearAiChat() {
    const doClear = async () => {
      try {
        await apiFetch('/api/ai/clear', { method: 'POST' });
        const container = document.getElementById('ai-chat-messages');
        if (container) {
          const chips = document.getElementById('ai-quick-chips');
          container.innerHTML = `
            <div class="ai-msg ai-msg-bot">
              <div class="ai-msg-avatar">
                <img src="/static/images/rully-avatar-128.png" alt="Rully" class="ai-avatar-thumb" onerror="this.onerror=null; this.src='https://rully-app.onrender.com/static/images/rully-avatar-128.png';">
              </div>
              <div class="ai-msg-content">
                <div class="ai-msg-bubble">
                  ${t('ai_cleared_reply')}
                </div>
                <span class="ai-msg-time">${t('ai_msg_time_now')}</span>
              </div>
            </div>
          `;
          if (chips) container.appendChild(chips);
          renderAiChips();
        }
        loadAiChatStatus();
        triggerHaptic('notification', 'success');
      } catch (e) {
        console.error("Failed to clear chat:", e);
      }
    };

    const confirmMsg = t('ai_confirm_clear');
    if (window.Telegram?.WebApp?.showConfirm) {
      window.Telegram.WebApp.showConfirm(confirmMsg, (ok) => {
        if (ok) doClear();
      });
    } else {
      if (confirm(confirmMsg)) {
        doClear();
      }
    }
  }

  // 18. Master Event Listener Bindings
  function setupEventListeners() {
    // Native Telegram BackButton Listener
    if (window.Telegram?.WebApp?.BackButton) {
      window.Telegram.WebApp.BackButton.onClick(handleNativeBackClick);
    }

    // Navigation bar tabs
    document.querySelectorAll('.nav-bar-item').forEach(item => {
      item.addEventListener('click', () => {
        const tab = item.getAttribute('data-tab');
        if (tab === 'ai' && !state.subscription?.is_pro) {
          switchTab('ai');
          openPaywallModal('ai');
          return;
        }
        switchTab(tab);
      });
    });

    // Top Bar Channel Button Action (@rully_avtotest)
    const headerChannelBtn = document.getElementById('header-channel-btn');
    if (headerChannelBtn) {
      headerChannelBtn.onclick = () => {
        triggerHaptic('impact', 'medium');
        const channelUrl = 'https://t.me/rully_avtotest';
        if (window.Telegram?.WebApp?.openTelegramLink) {
          try {
            window.Telegram.WebApp.openTelegramLink(channelUrl);
            return;
          } catch (e) {
            console.warn('openTelegramLink error:', e);
          }
        }
        window.open(channelUrl, '_blank');
      };
    }

    // Header Quick Language Action
    const headerLangBtn = document.getElementById('header-lang-btn');
    if (headerLangBtn) {
      headerLangBtn.onclick = () => switchTab('profile');
    }

    // Apex Primary Exam Button
    const heroBtn = document.getElementById('btn-hero-start-exam');
    if (heroBtn) {
      heroBtn.onclick = () => {
        if (!canAccessExam()) {
          openPaywallModal('exam');
          return;
        }
        startQuizSession('EXAM', null, 20);
      };
    }

    // Tactical Tiles Actions
    const quickAmaliy = document.getElementById('quick-amaliy');
    if (quickAmaliy) quickAmaliy.onclick = () => switchTab('amaliy');

    const quickCategories = document.getElementById('quick-categories');
    if (quickCategories) quickCategories.onclick = () => switchTab('tests');

    async function handleStartMistakesPractice() {
      triggerHaptic('impact', 'medium');
      if (!canAccessExam()) {
        openPaywallModal('mistakes');
        return;
      }
      try {
        const mData = await apiFetch(`/api/mistakes?lang=${state.lang}`);
        state.mistakesCount = mData.count || 0;
        const countEl = document.getElementById('mistakes-pool-count');
        if (countEl) countEl.textContent = state.mistakesCount;
      } catch (e) {
        console.error("Mistakes count fetch error", e);
      }
      if (!state.mistakesCount || state.mistakesCount === 0) {
        if (window.Telegram?.WebApp?.showAlert) {
          window.Telegram.WebApp.showAlert(t('mistakes_empty_desc'));
        } else {
          alert(t('mistakes_empty_desc'));
        }
        return;
      }
      startQuizSession('MISTAKES', null, state.mistakesCount);
    }

    const quickMistakes = document.getElementById('quick-mistakes');
    if (quickMistakes) quickMistakes.onclick = handleStartMistakesPractice;

    // Test Secrets & Cheatsheet Modal Controller
    const quickCheatsheet = document.getElementById('quick-cheatsheet');
    const secretsModal = document.getElementById('test-secrets-modal');
    const closeSecretsBtn = document.getElementById('btn-close-secrets-modal');
    const secretsTabNav = document.getElementById('secrets-tab-nav');
    const secretsFilterInput = document.getElementById('secrets-filter-input');
    const secretsSearchClear = document.getElementById('secrets-search-clear');

    function openSecretsModal() {
      triggerHaptic('impact', 'medium');
      if (!canAccessExam()) {
        openPaywallModal('cheatsheet');
        return;
      }
      renderCheatsheetContent();
      if (secretsModal) {
        secretsModal.classList.add('active');
        document.body.style.overflow = 'hidden';
        if (secretsTabNav) {
          const tabBtns = secretsTabNav.querySelectorAll('.secrets-tab-btn');
          tabBtns.forEach((b, idx) => b.classList.toggle('active', idx === 0));
        }
        document.querySelectorAll('.secrets-pane').forEach((p, idx) => {
          p.classList.toggle('active', idx === 0);
          p.style.display = idx === 0 ? 'flex' : 'none';
        });
        const bodyEl = document.getElementById('secrets-modal-body');
        if (bodyEl) bodyEl.scrollTop = 0;
      }
    }

    function closeSecretsModal() {
      triggerHaptic('impact', 'light');
      if (secretsModal) {
        secretsModal.classList.remove('active');
        document.body.style.overflow = '';
      }
    }

    if (quickCheatsheet) quickCheatsheet.onclick = openSecretsModal;
    if (closeSecretsBtn) closeSecretsBtn.onclick = closeSecretsModal;
    if (secretsModal) {
      secretsModal.onclick = (e) => {
        if (e.target === secretsModal) closeSecretsModal();
      };
    }

    // Tabs switching inside secrets modal
    if (secretsTabNav) {
      const tabBtns = secretsTabNav.querySelectorAll('.secrets-tab-btn');
      tabBtns.forEach(btn => {
        btn.onclick = () => {
          triggerHaptic('selection');
          tabBtns.forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          const targetTab = btn.getAttribute('data-tab');
          document.querySelectorAll('.secrets-pane').forEach(p => {
            p.classList.remove('active');
            p.style.display = 'none';
          });
          const targetPane = document.getElementById(`pane-${targetTab}`);
          if (targetPane) {
            targetPane.classList.add('active');
            targetPane.style.display = 'flex';
          }
        };
      });
    }

    // Live search filter inside secrets modal
    if (secretsFilterInput) {
      secretsFilterInput.oninput = () => {
        const query = secretsFilterInput.value.trim().toLowerCase();
        if (secretsSearchClear) {
          secretsSearchClear.style.display = query ? 'flex' : 'none';
        }

        const searchableItems = document.querySelectorAll('[data-search]');
        if (!query) {
          searchableItems.forEach(item => item.style.display = '');
          return;
        }

        let firstMatchingPane = null;
        searchableItems.forEach(item => {
          const searchAttr = item.getAttribute('data-search') || '';
          const text = item.textContent || '';
          const isMatch = searchAttr.toLowerCase().includes(query) || text.toLowerCase().includes(query);
          item.style.display = isMatch ? '' : 'none';

          if (isMatch && !firstMatchingPane) {
            const parentPane = item.closest('.secrets-pane');
            if (parentPane) firstMatchingPane = parentPane;
          }
        });

        if (firstMatchingPane && !firstMatchingPane.classList.contains('active')) {
          const paneId = firstMatchingPane.id;
          const tabName = paneId.replace('pane-', '');
          document.querySelectorAll('.secrets-pane').forEach(p => {
            p.classList.remove('active');
            p.style.display = 'none';
          });
          firstMatchingPane.classList.add('active');
          firstMatchingPane.style.display = 'flex';
          if (secretsTabNav) {
            secretsTabNav.querySelectorAll('.secrets-tab-btn').forEach(btn => {
              btn.classList.toggle('active', btn.getAttribute('data-tab') === tabName);
            });
          }
        }
      };

      if (secretsSearchClear) {
        secretsSearchClear.onclick = () => {
          secretsFilterInput.value = '';
          secretsSearchClear.style.display = 'none';
          document.querySelectorAll('[data-search]').forEach(item => item.style.display = '');
          secretsFilterInput.focus();
        };
      }
    }

    // Custom Quiz Settings Modal Logic
    const settingsModal = document.getElementById('custom-quiz-settings-modal');
    const openSettingsBtn = document.getElementById('btn-open-custom-quiz-settings');
    const openSettingsInline = document.getElementById('btn-trigger-settings-inline');
    const closeSettingsBtn = document.getElementById('btn-close-settings-modal');

    function openCustomQuizSettings() {
      updateCustomQuizChipsUI();
      triggerHaptic('impact', 'light');
      if (settingsModal) settingsModal.classList.add('active');
    }

    function closeCustomQuizSettings() {
      if (settingsModal) settingsModal.classList.remove('active');
    }

    if (openSettingsBtn) {
      openSettingsBtn.addEventListener('click', () => {
        openCustomQuizSettings();
      });
    }

    if (openSettingsInline) {
      openSettingsInline.addEventListener('click', (e) => {
        e.stopPropagation();
        openCustomQuizSettings();
      });
    }

    if (closeSettingsBtn) {
      closeSettingsBtn.addEventListener('click', closeCustomQuizSettings);
    }

    // Saved Questions (Review Mode) Bindings
    const openSavedBtn = document.getElementById('btn-open-saved-questions');
    const closeSavedBtn = document.getElementById('btn-close-saved-modal');
    const savedModal = document.getElementById('saved-questions-modal');

    if (openSavedBtn) {
      openSavedBtn.addEventListener('click', openSavedQuestionsModal);
    }

    if (closeSavedBtn) {
      closeSavedBtn.addEventListener('click', closeSavedQuestionsModal);
    }

    if (savedModal) {
      savedModal.addEventListener('click', (e) => {
        if (e.target === savedModal) {
          closeSavedQuestionsModal();
        }
      });
    }

    const savedFilterInput = document.getElementById('saved-filter-input');
    const savedClearBtn = document.getElementById('saved-search-clear');
    if (savedFilterInput) {
      savedFilterInput.addEventListener('input', (e) => {
        const val = e.target.value;
        if (savedClearBtn) savedClearBtn.style.display = val ? 'flex' : 'none';
        filterSavedQuestions(val);
      });
    }

    if (savedClearBtn) {
      savedClearBtn.addEventListener('click', () => {
        if (savedFilterInput) {
          savedFilterInput.value = '';
          savedClearBtn.style.display = 'none';
          filterSavedQuestions('');
        }
      });
    }

    if (settingsModal) {
      settingsModal.addEventListener('click', (e) => {
        if (e.target === settingsModal) {
          closeCustomQuizSettings();
        }
      });
    }

    // Question count chips
    const qCountChips = document.querySelectorAll('#chips-q-count .setting-chip');
    qCountChips.forEach(chip => {
      chip.addEventListener('click', () => {
        const val = parseInt(chip.getAttribute('data-val'), 10);
        if (!isUserPro() && val > 20) {
          triggerHaptic('notification', 'warning');
          openPaywallModal('custom_quiz');
          return;
        }
        triggerHaptic('selection', null);
        qCountChips.forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
      });
    });

    // Telegram Style Range Slider for Time Limit
    const timeLimitValues = [300, 600, 900, 1200, 1500, 1800, 0];
    const timeLimitSlider = document.getElementById('time-limit-slider');
    const timeLimitBadge = document.getElementById('slider-time-val-badge');
    const tickLabels = document.querySelectorAll('#slider-tick-labels span');

    function updateTimeSlider(val) {
      const idx = parseInt(val, 10);
      const pct = (idx / 6) * 100;
      if (timeLimitSlider) {
        timeLimitSlider.style.setProperty('--slider-pct', `${pct}%`);
      }
      const secs = timeLimitValues[idx];
      let label = "";
      if (secs === 0) {
        label = t('opt_unlimited') + " (∞)";
      } else {
        const mins = secs / 60;
        label = t('opt_minutes', { m: mins });
      }
      if (timeLimitBadge) timeLimitBadge.textContent = label;

      tickLabels.forEach(sp => {
        sp.classList.toggle('active', parseInt(sp.getAttribute('data-idx'), 10) === idx);
      });
    }

    if (timeLimitSlider) {
      timeLimitSlider.addEventListener('input', (e) => {
        triggerHaptic('selection', null);
        updateTimeSlider(e.target.value);
      });
      updateTimeSlider(timeLimitSlider.value);
    }

    tickLabels.forEach(sp => {
      sp.addEventListener('click', () => {
        triggerHaptic('selection', null);
        const idx = sp.getAttribute('data-idx');
        if (timeLimitSlider) {
          timeLimitSlider.value = idx;
          updateTimeSlider(idx);
        }
      });
    });

    // Start Custom Quiz Button
    const btnStartCustomQuiz = document.getElementById('btn-start-custom-quiz');
    if (btnStartCustomQuiz) {
      btnStartCustomQuiz.addEventListener('click', () => {
        const activeQChip = document.querySelector('#chips-q-count .setting-chip.active');
        let qCount = activeQChip ? parseInt(activeQChip.getAttribute('data-val'), 10) : 20;
        if (!isUserPro() && qCount > 20) {
          qCount = 20;
        }

        const sliderVal = timeLimitSlider ? parseInt(timeLimitSlider.value, 10) : 3;
        const timeLimit = timeLimitValues[sliderVal] !== undefined ? timeLimitValues[sliderVal] : 1200;

        const showExplanation = document.getElementById('toggle-show-explanation')?.checked ?? true;
        const showAnswer = document.getElementById('toggle-show-answer')?.checked ?? true;

        closeCustomQuizSettings();
        startQuizSession('CUSTOM', null, qCount, {
          timeLimitSeconds: timeLimit,
          showExplanation: showExplanation,
          showAnswer: showAnswer
        });
      });
    }


    // Category Instant Search
    const searchInput = document.getElementById('category-search-input');
    if (searchInput) {
      searchInput.oninput = (e) => renderCategoriesList(e.target.value);
    }

    // Quiz Close Action
    const quizCloseBtn = document.getElementById('btn-close-quiz');
    if (quizCloseBtn) quizCloseBtn.onclick = () => confirmQuitQuiz();

    // Official State Exam Finish Action
    const examFinishBtn = document.getElementById('btn-exam-finish');
    if (examFinishBtn) {
      examFinishBtn.onclick = () => {
        triggerHaptic('impact', 'medium');
        const answeredCount = Object.keys(state.quiz.answers || {}).length;
        const totalCount = state.quiz.questions?.length || state.quiz.totalQuestions || 20;
        if (answeredCount < totalCount) {
          if (confirm(`${t('confirm_finish_text')} (${answeredCount}/${totalCount})`)) {
            finishQuiz();
          }
        } else {
          finishQuiz();
        }
      };
    }

    // Practice All Mistakes Action
    const btnPracMistakes = document.getElementById('btn-practice-all-mistakes');
    if (btnPracMistakes) {
      btnPracMistakes.onclick = handleStartMistakesPractice;
    }

    // Unified Hero Exam & Cockpit Stats Lock Click (opens paywall when free)
    const heroWrap = document.getElementById('hero-exam-cockpit-wrap');
    if (heroWrap) {
      heroWrap.onclick = (e) => {
        if (!canAccessExam()) {
          e.preventDefault();
          e.stopPropagation();
          openPaywallModal('exam');
        }
      };
    }

    // Profile Subscription Plan Chips
    document.querySelectorAll('#profile-sub-plans-grid .sub-plan-box').forEach(box => {
      box.onclick = () => {
        const plan = box.getAttribute('data-plan');
        selectSubscriptionPlan(plan);
      };
    });

    const btnProfileSub = document.getElementById('btn-profile-subscribe');
    if (btnProfileSub) {
      btnProfileSub.onclick = () => activateUserSubscription(state.selectedPlanId);
    }

    // Modal Subscription Plan Chips
    document.querySelectorAll('#modal-sub-plans-grid .sub-plan-box').forEach(box => {
      box.onclick = () => {
        const plan = box.getAttribute('data-plan');
        selectSubscriptionPlan(plan);
      };
    });

    const btnModalActivate = document.getElementById('btn-modal-activate-sub');
    if (btnModalActivate) {
      btnModalActivate.onclick = () => activateUserSubscription(state.selectedPlanId);
    }

    const btnClosePaywall = document.getElementById('btn-close-paywall-modal');
    if (btnClosePaywall) btnClosePaywall.onclick = closePaywallModal;

    const paywallModal = document.getElementById('subscription-paywall-modal');
    if (paywallModal) {
      paywallModal.onclick = (e) => {
        if (e.target === paywallModal) closePaywallModal();
      };
    }

    // Invoice Modal Listeners
    const btnCloseInvoice = document.getElementById('btn-close-invoice-modal');
    if (btnCloseInvoice) {
      btnCloseInvoice.onclick = closePaymentInvoiceModal;
    }

    const invoiceModal = document.getElementById('payment-invoice-modal');
    if (invoiceModal) {
      invoiceModal.onclick = (e) => {
        if (e.target === invoiceModal) closePaymentInvoiceModal();
      };
    }

    const copySvg = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>`;
    const checkSvg = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;

    function markCopied(btn) {
      if (!btn) return;
      btn.innerHTML = checkSvg;
      btn.classList.add('copied');
      setTimeout(() => {
        btn.innerHTML = copySvg;
        btn.classList.remove('copied');
      }, 2000);
    }

    function safeCopy(text, btn) {
      triggerHaptic('impact', 'light');
      const cleanText = String(text || '').trim();
      if (!cleanText) return;

      const fallback = () => {
        try {
          const ta = document.createElement('textarea');
          ta.value = cleanText;
          ta.style.position = 'fixed';
          ta.style.top = '0';
          ta.style.left = '0';
          ta.style.opacity = '0';
          document.body.appendChild(ta);
          ta.focus();
          ta.select();
          document.execCommand('copy');
          document.body.removeChild(ta);
          markCopied(btn);
        } catch (err) {
          markCopied(btn);
        }
      };

      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(cleanText)
          .then(() => markCopied(btn))
          .catch(fallback);
      } else {
        fallback();
      }
    }

    const btnCopyCard = document.getElementById('btn-copy-card');
    if (btnCopyCard) {
      btnCopyCard.onclick = () => {
        const textToCopy = (activeOrderData?.card_number_raw || document.getElementById('inv-card-number')?.textContent || '').replace(/\s+/g, '');
        safeCopy(textToCopy, btnCopyCard);
      };
    }

    const btnCopyAmount = document.getElementById('btn-copy-amount');
    if (btnCopyAmount) {
      btnCopyAmount.onclick = () => {
        const amountVal = activeOrderData?.final_amount_uzs || document.getElementById('inv-total-amount')?.textContent?.replace(/\s+/g, '');
        safeCopy(amountVal, btnCopyAmount);
      };
    }

    // Wire AI Copilot / AI Ustoz listeners
    const aiSendBtn = document.getElementById('btn-ai-send');
    const aiInput = document.getElementById('ai-input-field');
    const aiClearBtn = document.getElementById('btn-ai-clear');
    const aiChipsWrap = document.getElementById('ai-quick-chips');
    const btnAiSavedTutor = document.getElementById('btn-ai-saved-tutor');

    if (aiSendBtn && aiInput) {
      aiSendBtn.onclick = () => sendAiMessage();
      aiInput.addEventListener('keydown', (e) => {
        if ((e.key === 'Enter' || e.keyCode === 13) && !e.shiftKey) {
          e.preventDefault();
          const val = aiInput.value.trim();
          if (!val) {
            aiInput.blur();
            return;
          }
          sendAiMessage();
        }
      });
      aiInput.addEventListener('input', () => {
        aiInput.style.height = 'auto';
        aiInput.style.height = Math.min(aiInput.scrollHeight, 100) + 'px';
      });

      // Viewport & Keyboard Handling for Mobile (Telegram WebApp & Touch)
      const updateAiViewport = () => {
        if (state.activeTab !== 'ai') return;

        const isFocused = (document.activeElement === aiInput);
        document.body.classList.toggle('keyboard-open', isFocused);

        const viewAi = document.getElementById('view-ai');

        if (!isFocused) {
          document.documentElement.style.removeProperty('--keyboard-inset');
          if (viewAi) {
            viewAi.style.height = '';
            viewAi.style.bottom = '';
          }
          return;
        }

        const vv = window.visualViewport;
        const tg = window.Telegram?.WebApp;

        if (vv && typeof vv.height === 'number') {
          // On iOS Safari / WKWebView:
          // Directly pin #view-ai height to the visible viewport so the input bar sits right on top of keyboard
          if (viewAi) {
            viewAi.style.height = `${Math.round(vv.height)}px`;
            viewAi.style.bottom = 'auto';
          }
          window.scrollTo(0, 0);
        } else if (tg && typeof tg.viewportHeight === 'number') {
          if (viewAi) {
            viewAi.style.height = `${Math.round(tg.viewportHeight)}px`;
            viewAi.style.bottom = 'auto';
          }
        } else {
          document.documentElement.style.setProperty('--keyboard-inset', '300px');
        }

        scrollAiToBottom(true);
      };

      aiInput.addEventListener('focus', () => {
        document.body.classList.add('keyboard-open');
        updateAiViewport();
        setTimeout(updateAiViewport, 50);
        setTimeout(updateAiViewport, 150);
        setTimeout(updateAiViewport, 300);
        setTimeout(updateAiViewport, 500);
      });

      aiInput.addEventListener('blur', () => {
        document.body.classList.remove('keyboard-open');
        document.documentElement.style.removeProperty('--keyboard-inset');
        const viewAi = document.getElementById('view-ai');
        if (viewAi) {
          viewAi.style.height = '';
          viewAi.style.bottom = '';
        }
        setTimeout(() => {
          updateAiViewport();
          scrollAiToBottom(false);
        }, 120);
      });

      if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', updateAiViewport);
      }
      if (window.Telegram?.WebApp?.onEvent) {
        window.Telegram.WebApp.onEvent('viewportChanged', updateAiViewport);
      }
    }

    if (aiInput) {
      aiInput.addEventListener('click', () => {
        if (!state.subscription?.is_pro) {
          openPaywallModal('ai');
        }
      });
    }

    if (aiClearBtn) {
      aiClearBtn.onclick = () => clearAiChat();
    }

    if (aiChipsWrap) {
      aiChipsWrap.addEventListener('click', (e) => {
        if (!state.subscription?.is_pro) {
          openPaywallModal('ai');
          return;
        }
        const chip = e.target.closest('.ai-chip-btn');
        if (chip) {
          const prompt = chip.getAttribute('data-prompt');
          if (prompt) {
            triggerHaptic('impact', 'light');
            sendAiMessage(prompt);
          }
        }
      });
    }

    if (btnAiSavedTutor) {
      btnAiSavedTutor.onclick = () => {
        closeSavedQuestionsModal();
        if (!state.subscription?.is_pro) {
          openPaywallModal('ai');
          return;
        }
        switchTab('ai');
        if (savedQuestionsCache && savedQuestionsCache.length > 0) {
          const topQ = savedQuestionsCache[0];
          const optList = (topQ.options || []).map(o => `${o.option_key}) ${o.text}`).join('\n');
          const prompt = state.lang === 'ru'
            ? `Пожалуйста, объясни этот сохраненный вопрос и ПДД правило:\n\nВопрос: ${topQ.question_text}\nВарианты:\n${optList}\nПравильный ответ: ${topQ.correct_option_key}`
            : state.lang === 'uz_cyrl'
            ? `Илтимос, ушбу сақланган савол ва ЙҲҚ қоидасини батафсил тушунтириб бер:\n\nСавол: ${topQ.question_text}\nВариантлар:\n${optList}\nТўғри жавоб: ${topQ.correct_option_key}`
            : `Iltimos, ushbu saqlangan savol va YHQ qoidasini batafsil tushuntirib ber:\n\nSavol: ${topQ.question_text}\nVariantlar:\n${optList}\nTo'g'ri javob: ${topQ.correct_option_key}`;
          sendAiMessage(prompt);
        } else {
          sendAiMessage(t('btn_ai_saved_tutor_prompt'));
        }
      };
    }

    // Platform Rules & About Modal Listeners
    const btnOpenRules = document.getElementById('btn-open-rules');
    if (btnOpenRules) {
      btnOpenRules.addEventListener('click', openPlatformRulesModal);
    }
    const btnCloseRules = document.getElementById('btn-close-rules-modal');
    if (btnCloseRules) {
      btnCloseRules.addEventListener('click', closePlatformRulesModal);
    }
    const rulesOverlay = document.getElementById('platform-rules-modal');
    if (rulesOverlay) {
      rulesOverlay.addEventListener('click', (e) => {
        if (e.target === rulesOverlay) closePlatformRulesModal();
      });
    }

    // Version Changelog Modal Listeners
    const btnOpenChangelog = document.getElementById('btn-open-changelog');
    if (btnOpenChangelog) {
      btnOpenChangelog.addEventListener('click', openVersionHistoryModal);
    }
    const btnCloseChangelog = document.getElementById('btn-close-changelog-modal');
    if (btnCloseChangelog) {
      btnCloseChangelog.addEventListener('click', closeVersionHistoryModal);
    }
    const changelogOverlay = document.getElementById('version-history-modal');
    if (changelogOverlay) {
      changelogOverlay.addEventListener('click', (e) => {
        if (e.target === changelogOverlay) closeVersionHistoryModal();
      });
    }

    // Readiness 5-Pillar Diagnostic Modal Listeners
    const btnOpenReadiness = document.getElementById('btn-open-readiness-modal');
    if (btnOpenReadiness) {
      btnOpenReadiness.addEventListener('click', openReadinessDiagnosticModal);
    }
    const speedometerCluster = document.querySelector('.speedometer-visual-wrap');
    if (speedometerCluster) {
      speedometerCluster.style.cursor = 'pointer';
      speedometerCluster.addEventListener('click', openReadinessDiagnosticModal);
    }
    const readinessOverlay = document.getElementById('readiness-diagnostic-modal');
    if (readinessOverlay) {
      readinessOverlay.addEventListener('click', (e) => {
        if (e.target === readinessOverlay) closeReadinessDiagnosticModal();
      });
    }
  }

  // DOM Loaded Event
  window.addEventListener('DOMContentLoaded', initApp);

})();
