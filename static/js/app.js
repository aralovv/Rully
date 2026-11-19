/**
 * RULLY — ELITE DIGITAL COCKPIT CONTROLLER & TELEGRAM MINI APP SPA
 * Orchestrates multi-view navigation, real-time readiness telemetry,
 * interactive exam simulation, SVG iconography, and 3-language hot switching.
 */

(function () {
  'use strict';

  // 1. Telegram WebApp Integration & Viewport Setup
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
      if (cached && cached.length > 5) return cached;
    } catch (e) {}

    // 5. Development fallback for desktop browser testing
    return "dev_user_8809526955";
  }

  let initData = resolveTelegramInitData();

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
    selectedPlanId: 'pro_14'
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

  function applyLocalization() {
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      el.textContent = t(key);
    });

    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      el.setAttribute('placeholder', t(key));
    });

    // Update Language Pill Label
    const langLabel = document.getElementById('header-lang-label');
    if (langLabel) {
      langLabel.textContent = state.lang === 'uz_latn' ? 'UZ' : (state.lang === 'uz_cyrl' ? 'УЗ' : 'РУ');
    }

    // Refresh dynamic telemetry descriptors
    updateReadinessClusterUI();
    updateSubscriptionUI();
    renderCheatsheetContent();
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


  // 5. API Communications Layer
  async function apiFetch(endpoint, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': initData,
      ...(options.headers || {})
    };
    const res = await fetch(endpoint, { ...options, headers });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'API request failed' }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  // 6. SVG Icon System Injector
  function injectSvgIcons() {
    if (!window.renderIcon) return;

    const slotMap = {
      'streak-icon-slot': 'flame',
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
      'nav-icon-ai': 'instructor',
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

  // 7. Cockpit Readiness Score Calculation & Arc Meter
  function computeReadinessScore(stats) {
    if (!stats) return 0;
    if (typeof stats.readiness_score === 'number') {
      return Math.round(stats.readiness_score);
    }
    const totalExams = stats.total_exams || 0;
    const passedExams = stats.passed_exams || 0;
    const passRate = stats.pass_rate || 0;
    const totalAns = stats.total_questions_answered || 0;
    const accuracy = stats.accuracy || 0;
    const uniqueQs = stats.unique_questions_tested || 0;
    const mistakes = stats.unresolved_mistakes || 0;

    if (totalAns === 0 && totalExams === 0) return 0;

    // Pillar 1: Exam Passing Mastery & Consistency (35% weight)
    let pExam = 0;
    if (passedExams > 0) {
      const consistency = Math.min(1.0, passedExams / 5.0);
      pExam = Math.min(100, passRate * (0.40 + 0.60 * consistency));
    }

    // Pillar 2: Knowledge Accuracy above 35% baseline (25% weight)
    let pAcc = 0;
    if (totalAns >= 10 && accuracy > 35) {
      pAcc = Math.min(100, Math.max(0, ((accuracy - 35) / 57) * 100));
    }

    // Pillar 3: Curriculum / Syllabus Coverage (20% weight)
    const pCov = Math.min(100, (uniqueQs / 160) * 100);

    // Pillar 4: Mistake Bank Health (20% weight)
    let pMistakes = 0;
    if (totalAns >= 5) {
      pMistakes = mistakes === 0 ? 100 : Math.max(0, 100 - (mistakes * 5));
    }

    let raw = (0.35 * pExam) + (0.25 * pAcc) + (0.20 * pCov) + (0.20 * pMistakes);

    // Statistical Confidence Multiplier for low volume (< 100 questions)
    if (totalAns < 100) {
      const confMultiplier = Math.min(1.0, Math.max(0.2, Math.sqrt(totalAns / 100)));
      raw = raw * confMultiplier;
    }

    // Intelligent Safeguard Gates
    let finalScore = raw;
    if (passedExams === 0) {
      finalScore = Math.min(finalScore, 15);
    } else if (passedExams === 1) {
      finalScore = Math.min(finalScore, 45);
    } else if (passedExams === 2) {
      finalScore = Math.min(finalScore, 70);
    }

    if (mistakes >= 10) {
      finalScore = Math.min(finalScore, 60);
    }

    if (totalAns < 60) {
      finalScore = Math.min(finalScore, 30);
    }

    return Math.round(Math.min(100, Math.max(0, finalScore)));
  }

  function updateReadinessClusterUI() {
    const s = state.stats?.stats || {};
    const score = computeReadinessScore(s);
    state.readinessScore = score;

    // Numerical readout
    const scoreValEl = document.getElementById('stat-readiness-pct');
    if (scoreValEl) scoreValEl.textContent = `${score}%`;

    // SVG Arc Dashoffset (Arc length: ~172.8)
    const arcFill = document.getElementById('speedometer-arc-fill');
    if (arcFill) {
      const maxOffset = 172.8;
      const offset = maxOffset - (maxOffset * score / 100);
      arcFill.style.strokeDashoffset = `${offset}`;
    }

    // Contextual Description
    const descEl = document.getElementById('readiness-description');
    if (descEl) {
      if (score >= 80) {
        descEl.textContent = t('readiness_subtext_ready');
      } else if (score >= 40) {
        descEl.textContent = t('readiness_subtext_progress');
      } else {
        descEl.textContent = t('readiness_subtext_start');
      }
    }

    const badgeEl = document.getElementById('telemetry-readiness-badge');
    const statusTxtEl = document.getElementById('telemetry-readiness-status');
    if (badgeEl && statusTxtEl) {
      if (score >= 80) {
        badgeEl.className = 'telemetry-status-badge ready';
        statusTxtEl.textContent = t('status_ready');
      } else if (score >= 40) {
        badgeEl.className = 'telemetry-status-badge in_progress';
        statusTxtEl.textContent = t('status_in_progress');
      } else {
        badgeEl.className = 'telemetry-status-badge not_ready';
        statusTxtEl.textContent = t('status_not_ready');
      }
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

  function updateSubscriptionUI() {
    const isPro = isUserPro();
    updateCustomQuizChipsUI();

    // 1. Lock Badges on Mistakes, Cheatsheet
    const mistakesBadge = document.getElementById('badge-mistakes-lock');
    if (mistakesBadge) mistakesBadge.classList.toggle('hidden', isPro);

    const cheatsheetBadge = document.getElementById('badge-cheatsheet-lock');
    if (cheatsheetBadge) cheatsheetBadge.classList.toggle('hidden', isPro);

    const practiceMistakesBadge = document.getElementById('badge-practice-mistakes-lock');
    if (practiceMistakesBadge) practiceMistakesBadge.classList.toggle('hidden', isPro);

    // 2. Unified Hero Exam & Telemetry Stats Lock (Single blur & unified lock for both cards)
    const heroWrap = document.getElementById('hero-exam-cockpit-wrap');
    const heroLock = document.getElementById('hero-cockpit-lock-overlay');
    if (heroWrap) heroWrap.classList.toggle('locked', !isPro);
    if (heroLock) heroLock.style.display = isPro ? 'none' : 'flex';

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

  function openPaywallModal(feature = '') {
    triggerHaptic('notification', 'warning');
    const modal = document.getElementById('subscription-paywall-modal');
    if (modal) {
      modal.classList.add('active');
      document.body.style.overflow = 'hidden';
      updateSubscriptionUI();
    }
  }

  function closePaywallModal() {
    triggerHaptic('impact', 'light');
    const modal = document.getElementById('subscription-paywall-modal');
    if (modal) {
      modal.classList.remove('active');
      document.body.style.overflow = '';
    }
  }

  // Payment Order State & Timer
  let paymentPollingTimer = null;
  let paymentCountdownTimer = null;
  let activeOrderData = null;

  async function activateUserSubscription(planId) {
    triggerHaptic('impact', 'medium');
    const selectedPlan = planId || state.selectedPlanId || 'pro_14';
    
    // Close the initial paywall preview modal
    closePaywallModal();

    try {
      // Call create order endpoint
      const res = await apiFetch('/api/payment/orders/create', {
        method: 'POST',
        body: JSON.stringify({ plan_id: selectedPlan })
      });

      if (!res.ok || !res.order) {
        throw new Error(res.detail || "Buyurtma yaratib bo'lmadi");
      }

      openPaymentInvoiceModal(res.order);
    } catch (e) {
      console.error("Payment order creation failed:", e);
      if (window.Telegram?.WebApp?.showAlert) {
        window.Telegram.WebApp.showAlert(e.message || "To‘lov buyurtmasini yaratishda xatolik yuz berdi.");
      } else {
        alert(e.message || "To‘lov buyurtmasini yaratishda xatolik yuz berdi.");
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
  }

  function closePaymentInvoiceModal() {
    const modal = document.getElementById('payment-invoice-modal');
    if (modal) modal.classList.remove('active');
    document.body.style.overflow = '';

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

    let left = seconds;
    updateDisplay(left);

    paymentCountdownTimer = setInterval(() => {
      left--;
      if (left <= 0) {
        clearInterval(paymentCountdownTimer);
        paymentCountdownTimer = null;
        if (timerEl) timerEl.textContent = "00:00";
        if (paymentPollingTimer) {
          clearInterval(paymentPollingTimer);
          paymentPollingTimer = null;
        }
        if (window.Telegram?.WebApp?.showAlert) {
          window.Telegram.WebApp.showAlert("Invoys muddati tugadi (15 daqiqa). Yangi buyurtma yarating.");
        } else {
          alert("Invoys muddati tugadi (15 daqiqa). Yangi buyurtma yarating.");
        }
        closePaymentInvoiceModal();
      } else {
        updateDisplay(left);
      }
    }, 1000);
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
    }, 3000);
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
    const MIN_DISPLAY_MS = 1350; // smooth engine start animation minimum window

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
      if (statusTextEl) statusTextEl.textContent = "Gidrousilitel va tizimlar tekshirilmoqda...";
    }, 450);

    setTimeout(() => {
      if (statusTextEl) statusTextEl.textContent = "Qoidalar va savollar yuklanmoqda...";
    }, 950);

    // Interactive Klaxon Easter Egg on steering wheel tap
    if (wheelWrapEl) {
      wheelWrapEl.addEventListener('click', () => {
        try {
          window.Telegram?.WebApp?.HapticFeedback?.impactOccurred('heavy');
        } catch (e) {}
        if (statusTextEl) {
          const prev = statusTextEl.textContent;
          statusTextEl.textContent = "🚗 Bib-bip!";
          setTimeout(() => { statusTextEl.textContent = prev; }, 600);
        }
      });
    }

    // Return completion function
    return function dismissLoadingScreen() {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, MIN_DISPLAY_MS - elapsed);

      setTimeout(() => {
        if (statusTextEl) statusTextEl.textContent = "Tizim tayyor. Oq yo‘l!";
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
    };
  }

  // 8. Application Bootstrap
  async function initApp() {
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

      state.user = authRes.user;
      state.subscription = authRes.subscription || authRes.user?.subscription || { is_pro: false, tier: 'free' };
      state.lang = authRes.user.language || 'uz_latn';
      state.stats = {
        stats: authRes.stats,
        streak: authRes.streak
      };
      updateSubscriptionUI();

      try { sessionStorage.setItem('rully_tg_init_data', initData); } catch (e) {}
      updateDriverProfileUI();
    } catch (e) {
      console.warn("Auth initialization error, using fallback session:", e);
      initData = "dev_user_8809526955";
      state.user = { first_name: "Haydovchi", username: "kurs_savdo", language: "uz_latn" };
      state.lang = "uz_latn";
      state.subscription = { is_pro: false, tier: 'free' };
      updateDriverProfileUI();
      updateSubscriptionUI();
    }

    applyLocalization();
    await loadTelemetryData();
    await loadCategories();
    await updateSavedQuestionsCount();

    // Dismiss loading screen seamlessly
    dismissLoading();
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
      const s = data.stats || {};

      document.getElementById('stat-pass-rate-val').textContent = `${s.pass_rate || 0}%`;
      document.getElementById('stat-tests-val').textContent = s.total_exams || 0;
      document.getElementById('stat-accuracy-val').textContent = `${s.accuracy || 0}%`;

      const streakEl = document.getElementById('user-streak-text');
      if (data.streak && streakEl) {
        streakEl.textContent = `${data.streak.current_streak} kun`;
      }

      updateReadinessClusterUI();
    } catch (e) {
      console.error("Telemetry fetch failed", e);
    }
  }

  // 9. Categories Engine
  async function loadCategories() {
    try {
      const data = await apiFetch(`/api/categories?lang=${state.lang}`);
      state.categories = data.categories || [];
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
    document.body.classList.toggle('tab-ai-active', isAi);
    document.body.classList.remove('keyboard-open');
    document.documentElement.style.removeProperty('--ai-keyboard-offset');
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
      initAiChat();
      setTimeout(() => {
        scrollAiToBottom(false);
      }, 80);
    }
  }

  // 11. Interactive Quiz Player & Exam Simulation Engine
  async function startQuizSession(sessionType, categoryId = null, totalQuestions = 20, options = {}) {
    triggerHaptic('impact', 'medium');
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

      if (tg?.BackButton) {
        tg.BackButton.show();
        tg.BackButton.onClick(() => confirmQuitQuiz());
      }

      startCountdownTimer();
      renderCurrentQuestion();
    } catch (e) {
      alert("Sinovni boshlashda xatolik: " + e.message);
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

    state.quiz.timerInterval = setInterval(() => {
      state.quiz.timeRemaining--;

      const mins = Math.floor(state.quiz.timeRemaining / 60);
      const secs = state.quiz.timeRemaining % 60;
      if (timerVal) {
        timerVal.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
      }

      // Warning pulse below 2 minutes
      if (state.quiz.timeRemaining <= 120) {
        timerPill?.classList.add('danger');
      } else {
        timerPill?.classList.remove('danger');
      }

      if (state.quiz.timeRemaining <= 0) {
        clearInterval(state.quiz.timerInterval);
        finishQuiz();
      }
    }, 1000);
  }

  function renderCurrentQuestion() {
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

    // Illustration Viewport
    const imgWrap = document.getElementById('quiz-image-wrap');
    const imgEl = document.getElementById('quiz-image');
    if (q.has_image && q.image_url) {
      imgEl.src = q.image_url;
      imgWrap.style.display = 'flex';
      imgWrap.onclick = () => openLightbox(q.image_url);
    } else {
      imgWrap.style.display = 'none';
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
          if (opt.option_key === existingAns.correct_key) extraClass = "correct";
          else if (opt.option_key === existingAns.selected_key) extraClass = "wrong";
        } else {
          // If showAnswer is disabled, only show what was selected
          if (opt.option_key === existingAns.selected_key) {
            extraClass = existingAns.is_correct ? "correct" : "wrong";
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
        statusClass = ans.is_correct ? 'correct' : 'wrong';
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

  async function submitAnswer(canonicalId, selectedKey) {
    triggerHaptic('impact', 'medium');
    state.quiz.isSubmitting = true;
    try {
      const res = await apiFetch('/api/session/answer', {
        method: 'POST',
        body: JSON.stringify({
          session_id: state.quiz.sessionId,
          canonical_id: canonicalId,
          selected_key: selectedKey,
          language: state.lang
        })
      });

      state.quiz.answers[canonicalId] = res;

      if (res.is_correct) {
        triggerHaptic('notification', 'success');
      } else {
        triggerHaptic('notification', 'error');
      }

      renderCurrentQuestion();

      // Check auto-termination on 3rd mistake in EXAM mode (Uzbekistan DYHXX VMQ 408: max 2 mistakes)
      if (state.quiz.sessionType === 'EXAM') {
        const mistakeAnswers = Object.values(state.quiz.answers).filter(a => !a.is_correct);
        if (mistakeAnswers.length > 2 || res.is_exam_terminated) {
          triggerHaptic('notification', 'error');
          if (typeof showToast === 'function') {
            showToast(t('res_exam_terminated_toast') || 'Imtihon to‘xtatildi: 2 tadan ortiq xato qilindi!');
          }
          setTimeout(() => {
            if (!state.quiz.active) return;
            finishQuiz(true);
          }, 650);
          return;
        }
      }

      // In EXAM and CUSTOM terminal mode:
      if (state.quiz.sessionType === 'EXAM' || state.quiz.sessionType === 'CUSTOM') {
        // If explanation is off, automatically advance to next unanswered question after 380ms
        if (!state.quiz.showExplanation) {
          setTimeout(() => {
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
              const finishBtn = document.getElementById('btn-exam-finish');
              if (finishBtn) {
                finishBtn.classList.add('pulse-highlight');
              }
            }
          }, 380);
        } else {
          // If explanation is on, keep it on screen for reading. Highlight finish if all answered
          const answeredCount = Object.keys(state.quiz.answers).length;
          if (answeredCount >= state.quiz.questions.length) {
            const finishBtn = document.getElementById('btn-exam-finish');
            if (finishBtn) {
              finishBtn.classList.add('pulse-highlight');
            }
          }
          // Smoothly scroll explanation into view so user can comfortably read it to the end
          setTimeout(() => {
            const fbBoxEl = document.getElementById('quiz-feedback-box');
            if (fbBoxEl && fbBoxEl.classList.contains('active')) {
              fbBoxEl.scrollIntoView({ behavior: 'smooth', block: 'end' });
            }
          }, 120);
        }
      } else {
        // Practice modes (CATEGORY, MISTAKES): smoothly scroll to explanation if shown
        if (state.quiz.showExplanation !== false) {
          setTimeout(() => {
            const fbBoxEl = document.getElementById('quiz-feedback-box');
            if (fbBoxEl && fbBoxEl.classList.contains('active')) {
              fbBoxEl.scrollIntoView({ behavior: 'smooth', block: 'end' });
            }
          }, 120);
        }
      }
    } catch (e) {
      console.error("Submit answer error", e);
    } finally {
      state.quiz.isSubmitting = false;
    }
  }

  async function toggleBookmark(canonicalId) {
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
    if (tg?.BackButton) tg.BackButton.hide();
  }

  async function finishQuiz(isAutoTerminated = false) {
    clearInterval(state.quiz.timerInterval);
    triggerHaptic('impact', 'heavy');

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
          <div class="step-seq-pill">BOSQICH ${s.step}</div>
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
  async function loadResultsHistory() {
    try {
      const data = await apiFetch('/api/user/me');
      if (data.subscription) {
        state.subscription = data.subscription;
      }
      updateSubscriptionUI();
      const histList = document.getElementById('history-table-body');
      if (histList) {
        if (!data.history || data.history.length === 0) {
          histList.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-muted); padding: 18px;">${t('history_empty')}</td></tr>`;
        } else {
          histList.innerHTML = data.history.map(h => {
            const dateStr = h.created_at.substring(0, 10);
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
      img.src = src;
      modal.classList.add('active');
      modal.onclick = () => modal.classList.remove('active');
    }
  }
  window.openLightbox = openLightbox;

  // ==========================================================================
  // SAVED QUESTIONS (SAQLANGAN SAVOLLAR) - REVIEW MODE (NOT A TEST)
  // Displays question, correct answer, and statutory explanation.
  // ==========================================================================
  let savedQuestionsCache = [];

  async function updateSavedQuestionsCount() {
    try {
      const data = await apiFetch(`/api/bookmarks?lang=${state.lang}`);
      const count = data.count || (data.questions ? data.questions.length : 0);
      savedQuestionsCache = data.questions || [];

      const countEl = document.getElementById('saved-questions-count');
      if (countEl) countEl.textContent = count;

      const badgePill = document.getElementById('saved-questions-badge-pill');
      if (badgePill) {
        badgePill.style.display = count > 0 ? 'inline-flex' : 'none';
      }

      const captionEl = document.getElementById('saved-questions-caption-text');
      if (captionEl) {
        if (count > 0) {
          captionEl.textContent = `${count} ta savol • To‘g‘ri javob va izohlar`;
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

    const bodyEl = document.getElementById('saved-modal-body');
    const searchWrap = document.getElementById('saved-search-wrap');
    const searchInput = document.getElementById('saved-filter-input');
    if (searchInput) searchInput.value = '';

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
          <img src="${q.image_url}" alt="Savol rasmi" loading="lazy" />
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
              <span>№${idx + 1} • ${q.category_name || 'Yo‘l qoidasi'}</span>
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
          ${optionsHtml}
          ${expHtml}
        </div>
      `;
    }).join('');

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
                captionEl.textContent = newCount > 0 ? `${newCount} ta savol • To‘g‘ri javob va izohlar` : t('saved_questions_card_desc');
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

  async function initAiChat() {
    loadAiChatStatus();
    if (!aiChatInitialized) {
      aiChatInitialized = true;
      loadAiChatHistory();
    }
  }

  async function loadAiChatStatus() {
    try {
      await apiFetch('/api/ai/status');
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
          appendAiMessageToUI(msg.role, msg.text, []);
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

  function appendAiMessageToUI(role, text, cards = []) {
    const container = document.getElementById('ai-chat-messages');
    if (!container) return;

    const isBot = role === 'assistant' || role === 'model';
    const msgDiv = document.createElement('div');
    msgDiv.className = `ai-msg ${isBot ? 'ai-msg-bot' : 'ai-msg-user'}`;

    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    let cardsHtml = '';
    if (cards && cards.length > 0) {
      cardsHtml = cards.map(c => `
        <div class="ai-card-slot" id="ai-card-${c.canonical_id}">
          <div class="ai-card-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 13px; height: 13px;"><circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/></svg>
            <span>${c.canonical_id} • ${c.category_name || 'Yo‘l qoidasi'}</span>
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
      `).join('');
    }

    const formattedText = formatAiMarkdown(text);
    const botAvatarHtml = `<img src="/static/images/rully-avatar-128.png" alt="Rully" class="ai-avatar-thumb">`;
    const userAvatarHtml = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width: 15px; height: 15px;"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;

    msgDiv.innerHTML = `
      <div class="ai-msg-avatar">${isBot ? botAvatarHtml : userAvatarHtml}</div>
      <div class="ai-msg-content">
        <div class="ai-msg-bubble">${formattedText}${cardsHtml}</div>
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
          <img src="/static/images/rully-avatar-128.png" alt="Rully" class="ai-avatar-thumb">
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

  async function sendAiMessage(promptText = null) {
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
    appendAiMessageToUI('user', text);
    showAiTypingIndicator();

    try {
      const res = await apiFetch('/api/ai/chat', {
        method: 'POST',
        body: JSON.stringify({ message: text })
      });

      hideAiTypingIndicator();

      if (res && res.ok) {
        appendAiMessageToUI('assistant', res.reply || 'Javob qabul qilindi.', res.cards || []);
        loadAiChatStatus();
        triggerHaptic('notification', 'success');
      } else {
        appendAiMessageToUI('assistant', res.reply || 'Kechirasiz, xatolik yuz berdi.');
      }
    } catch (e) {
      hideAiTypingIndicator();
      console.error("AI chat error:", e);
      appendAiMessageToUI('assistant', "Aloqa xatosi yuz berdi. Iltimos qaytadan urinib ko'ring.");
    } finally {
      aiIsGenerating = false;
      if (sendBtn) sendBtn.disabled = false;
    }
  }

  async function clearAiChat() {
    if (!confirm("AI Ustoz bilan suhbat tarixini tozalashni xohlaysizmi?")) return;
    try {
      await apiFetch('/api/ai/clear', { method: 'POST' });
      const container = document.getElementById('ai-chat-messages');
      if (container) {
        const chips = document.getElementById('ai-quick-chips');
        container.innerHTML = `
          <div class="ai-msg ai-msg-bot">
            <div class="ai-msg-avatar">
              <img src="/static/images/rully-avatar-128.png" alt="Rully" class="ai-avatar-thumb">
            </div>
            <div class="ai-msg-content">
              <div class="ai-msg-bubble">
                Suhbat tarixi tozalandi. Qanday savolingiz bor? Men yordam berishga tayyorman! 🚗
              </div>
              <span class="ai-msg-time">Hozir</span>
            </div>
          </div>
        `;
        if (chips) container.appendChild(chips);
      }
      loadAiChatStatus();
      triggerHaptic('notification', 'success');
    } catch (e) {
      console.error("Failed to clear chat:", e);
    }
  }

  // 18. Master Event Listener Bindings
  function setupEventListeners() {
    // Navigation bar tabs
    document.querySelectorAll('.nav-bar-item').forEach(item => {
      item.addEventListener('click', () => {
        const tab = item.getAttribute('data-tab');
        switchTab(tab);
      });
    });

    // Header Quick Language Action
    const headerLangBtn = document.getElementById('header-lang-btn');
    if (headerLangBtn) {
      headerLangBtn.onclick = () => switchTab('profile');
    }

    // Apex Primary Exam Button
    const heroBtn = document.getElementById('btn-hero-start-exam');
    if (heroBtn) {
      heroBtn.onclick = () => {
        if (!state.subscription?.is_pro) {
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
      if (!state.subscription?.is_pro) {
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
      if (!state.subscription?.is_pro) {
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
        if (!state.subscription?.is_pro) {
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

    const btnCopyCard = document.getElementById('btn-copy-card');
    if (btnCopyCard) {
      btnCopyCard.onclick = () => {
        triggerHaptic('impact', 'light');
        const textToCopy = (activeOrderData?.card_number_raw || document.getElementById('inv-card-number')?.textContent || '').replace(/\s+/g, '');
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(textToCopy).then(() => {
            markCopied(btnCopyCard);
          }).catch(() => {
            markCopied(btnCopyCard);
          });
        } else {
          markCopied(btnCopyCard);
        }
      };
    }

    const btnCopyAmount = document.getElementById('btn-copy-amount');
    if (btnCopyAmount) {
      btnCopyAmount.onclick = () => {
        triggerHaptic('impact', 'light');
        const amountVal = activeOrderData?.final_amount_uzs || document.getElementById('inv-total-amount')?.textContent?.replace(/\s+/g, '');
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(String(amountVal)).then(() => {
            markCopied(btnCopyAmount);
          }).catch(() => {
            markCopied(btnCopyAmount);
          });
        } else {
          markCopied(btnCopyAmount);
        }
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
        window.scrollTo(0, 0);

        const isFocused = (document.activeElement === aiInput);
        if (!isFocused) {
          document.body.classList.remove('keyboard-open');
          document.documentElement.style.removeProperty('--ai-keyboard-offset');
          return;
        }

        const vv = window.visualViewport;
        const winH = window.innerHeight;
        const vh = vv ? vv.height : winH;
        const kbOffset = Math.max(0, winH - vh);

        document.body.classList.add('keyboard-open');
        if (kbOffset > 80) {
          document.documentElement.style.setProperty('--ai-keyboard-offset', `${kbOffset}px`);
        } else {
          document.documentElement.style.setProperty('--ai-keyboard-offset', '0px');
        }
      };

      aiInput.addEventListener('focus', () => {
        document.body.classList.add('keyboard-open');
        window.scrollTo(0, 0);
        updateAiViewport();
        setTimeout(() => {
          window.scrollTo(0, 0);
          scrollAiToBottom(true);
        }, 100);
        setTimeout(() => {
          window.scrollTo(0, 0);
          scrollAiToBottom(true);
        }, 300);
      });

      aiInput.addEventListener('blur', () => {
        document.body.classList.remove('keyboard-open');
        document.documentElement.style.removeProperty('--ai-keyboard-offset');
        window.scrollTo(0, 0);
        document.body.scrollTop = 0;
        document.documentElement.scrollTop = 0;
        setTimeout(() => {
          window.scrollTo(0, 0);
          scrollAiToBottom(false);
        }, 100);
      });

      window.addEventListener('scroll', () => {
        if (state.activeTab === 'ai' && (window.scrollX !== 0 || window.scrollY !== 0)) {
          window.scrollTo(0, 0);
        }
      });

      if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', updateAiViewport);
        window.visualViewport.addEventListener('scroll', () => {
          if (state.activeTab === 'ai') window.scrollTo(0, 0);
        });
      }
      if (window.Telegram?.WebApp?.onEvent) {
        window.Telegram.WebApp.onEvent('viewportChanged', updateAiViewport);
      }
    }

    if (aiClearBtn) {
      aiClearBtn.onclick = () => clearAiChat();
    }

    if (aiChipsWrap) {
      aiChipsWrap.addEventListener('click', (e) => {
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
        switchTab('ai');
        sendAiMessage("Mening saqlangan savollarimdan 3 tasini tushuntirib ber va meni sinovdan o‘tkaz");
      };
    }
  }

  // DOM Loaded Event
  window.addEventListener('DOMContentLoaded', initApp);

})();
