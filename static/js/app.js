/**
 * RULLY 2.0 Master SPA Coordinator
 * Boots cleanly in <50ms via progressive hydration, connects modular core/views,
 * and ensures safe external-web vs Telegram Mini App behavior.
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});

  R.showViewContainer = function (viewId) {
    document.querySelectorAll('.view-container').forEach(function (v) {
      v.classList.toggle('active', v.id === viewId);
    });
  };

  R.navigateTo = function (tabName) {
    if (!tabName) return;
    R.state.activeTab = tabName;
    document.body.classList.remove('focus-mode');

    document.querySelectorAll('[data-tab]').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    R.showViewContainer('view-' + tabName);
    R.syncTelegramBackButton();
    try {
      if (window.history && typeof window.history.replaceState === 'function' && window.location.protocol !== 'about:') {
        const curHash = String(window.location.hash || '');
        if (!curHash.includes('tgWebAppData=')) {
          const sub = R.state.prepareSubtab || 'tickets';
          const hashTarget = tabName === 'tests'
            ? '#tests/' + sub
            : '#' + tabName;
          window.history.replaceState(null, '', hashTarget);
        }
      }
    } catch (e) {}

    if (tabName === 'home') {
      R.renderHome();
    } else if (tabName === 'tests') {
      R.renderPrepare();
      R.loadPrepareData();
    } else if (tabName === 'amaliy') {
      R.state.amaliySubtab = R.state.isGuest ? 'penalty' : (R.state.amaliySubtab || 'modules');
      R.renderAmaliy();
      R.loadAmaliyData();
    } else if (tabName === 'ai') {
      R.renderAiView();
      if (!R.state.ai.loaded) R.loadAiStatusAndHistory();
    } else if (tabName === 'profile') {
      R.renderProfile();
      if (!R.state.analytics) R.loadAnalyticsAsync();
    }
  };

  R.resolveDeepLinkRoute = function () {
    try {
      const qRoute = new URLSearchParams(window.location.search).get('route');
      if (qRoute) return String(qRoute).trim().toLowerCase();
    } catch (e) {}
    try {
      const sp = window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initDataUnsafe && window.Telegram.WebApp.initDataUnsafe.start_param;
      if (sp) return String(sp).trim().toLowerCase();
    } catch (e) {}
    try {
      const rawHash = String(window.location.hash || '').replace(/^#/, '');
      if (rawHash && !rawHash.startsWith('tgWebAppData=')) {
        return rawHash.split('&')[0].trim().toLowerCase();
      }
    } catch (e) {}
    return '';
  };

  R.applyDeepLinkRoute = function (routeArg) {
    const route = String(routeArg !== undefined ? routeArg : R.resolveDeepLinkRoute() || '').trim().toLowerCase();
    if (!route) return false;

    const biletMatch = route.match(/^(?:bilet|ticket)[_-]?(\d{1,3})$/);
    if (biletMatch) {
      const ticketNo = parseInt(biletMatch[1], 10);
      R.state.prepareSubtab = 'tickets';
      R.navigateTo('tests');
      if (ticketNo >= 1 && typeof R.startSession === 'function') {
        R.startSession({ session_type: 'BILET', ticket_number: ticketNo });
      }
      return true;
    }

    if (route === 'home') {
      R.navigateTo('home');
      return true;
    }
    if (route === 'amaliy' || route === 'practical' || route === 'amaliy/modules') {
      R.state.amaliySubtab = R.state.isGuest ? 'penalty' : 'modules';
      R.navigateTo('amaliy');
      return true;
    }
    if (route === 'amaliy/penalty' || route === 'penalty' || route === 'jarima') {
      R.state.amaliySubtab = 'penalty';
      R.navigateTo('amaliy');
      return true;
    }
    if (route === 'ai' || route === 'ustoz') {
      R.navigateTo('ai');
      return true;
    }
    if (route === 'profile' || route === 'stats') {
      R.navigateTo('profile');
      return true;
    }
    if (route === 'exam' && typeof R.startSession === 'function') {
      R.startSession({ session_type: 'EXAM' });
      return true;
    }
    if (route === 'mistakes') {
      R.state.prepareSubtab = 'drill';
      if (typeof R.startSession === 'function' && !R.state.isGuest) {
        R.startSession({ session_type: 'MISTAKES', total_questions: 30 });
      } else {
        R.navigateTo('tests');
      }
      return true;
    }
    if (route === 'srs' || route === 'takrorlash' || route === 'adaptive' || route === 'saved' || route === 'custom' || route === 'drill' || route === 'tests/drill' || route === 'prepare/drill') {
      R.state.prepareSubtab = 'drill';
      R.navigateTo('tests');
      return true;
    }
    if (route === 'cheatsheet' || route === 'shpargalka' || route === 'tests/cheatsheet' || route === 'prepare/cheatsheet' || route === 'tests/shpargalka') {
      R.state.prepareSubtab = 'cheatsheet';
      R.navigateTo('tests');
      return true;
    }
    if (route === 'signs' || route === 'belgilar' || route === 'rules' || route === 'qoidalar' || route === 'law' || route === 'reference' || route.startsWith('tests/reference') || route.startsWith('prepare/reference')) {
      R.state.prepareSubtab = 'cheatsheet';
      R.navigateTo('tests');
      return true;
    }
    if (route === 'tickets' || route === 'bilets' || route === 'tests/tickets' || route === 'prepare/tickets' || route === 'prepare') {
      R.state.prepareSubtab = 'tickets';
      R.navigateTo('tests');
      return true;
    }
    if (route === 'topics' || route === 'categories' || route === 'mavzular' || route === 'tests/topics' || route === 'prepare/topics') {
      R.state.prepareSubtab = 'topics';
      R.navigateTo('tests');
      return true;
    }
    if (route === 'tests') {
      R.state.prepareSubtab = R.state.prepareSubtab || 'tickets';
      R.navigateTo('tests');
      return true;
    }
    return false;
  };

  R.syncShellUI = function () {
    const u = R.state.user || {};
    const displayName = [u.first_name, u.last_name].filter(Boolean).join(' ') || u.username || 'RULLY';
    const av = document.getElementById('mobile-avatar');
    const nm = document.getElementById('mobile-user-name');
    const sb = document.getElementById('mobile-user-sub');
    if (av) av.textContent = (displayName[0] || 'R').toUpperCase();
    if (nm) nm.textContent = displayName;
    if (sb) {
      const days = (R.state.streak && R.state.streak.current_streak) || 0;
      sb.textContent = R.state.isGuest ? R.t('guest_hero_badge') : R.t('streak_badge', { days: days });
    }

    const langCode = R.state.lang === 'ru' ? 'RU' : (R.state.lang === 'uz_cyrl' ? 'ЎЗ' : 'UZ');
    ['mobile-lang-code', 'sidebar-lang-code'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.textContent = langCode;
    });

    const streak = R.state.streak || { daily_goal_questions: 20, today_questions_count: 0 };
    const done = Number(streak.today_questions_count || 0);
    const goal = Math.max(5, Number(streak.daily_goal_questions || 20));
    const pct = Math.min(100, Math.round((done / goal) * 100));
    const gv = document.getElementById('sidebar-goal-val');
    const gb = document.getElementById('sidebar-goal-bar');
    if (gv) gv.textContent = done + ' / ' + goal;
    if (gb) gb.style.width = pct + '%';

    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      const key = el.dataset.i18n;
      if (key) el.textContent = R.t(key);
    });
  };

  R.changeLanguage = async function (newLang) {
    const valid = R.normalizeLang(newLang);
    R.state.lang = valid;
    R.state.categories = [];
    R.state.tickets = [];
    R.state.analytics = null;
    R.state.refSigns = null;
    R.state.refLaw = null;
    R.state.srsQueue = null;
    if (typeof R.loadLocaleJson === 'function') await R.loadLocaleJson(valid);
    R.syncShellUI();
    R.closeModal('lang-modal');
    R.navigateTo(R.state.activeTab);
    if (R.state.isGuest) {
      try {
        R.state.publicOverview = await R.api('/api/public/overview?lang=' + valid);
        if (R.state.activeTab === 'home') R.renderHome();
      } catch (e) {}
      return;
    }
    try {
      await R.api('/api/user/language', { method: 'POST', body: { language: valid } });
      await R.loadAnalyticsAsync();
    } catch (e) {}
  };

  function applyBootBundle(data) {
    if (!data) return;
    if (data.user) R.state.user = data.user;
    R.state.lang = R.normalizeLang(data.language || (data.user && data.user.language) || R.state.lang);
    if (data.subscription) R.state.subscription = data.subscription;
    if (data.free_tier) R.state.freeTier = data.free_tier;
    if (data.streak) R.state.streak = data.streak;
    if (data.stats) R.state.stats = data.stats;
    if (Array.isArray(data.history)) R.state.history = data.history;
    if (data.bookmarks_count !== undefined) R.state.bookmarksCount = data.bookmarks_count;
    if (Array.isArray(data.categories) && data.categories.length) R.state.categories = data.categories;
    if (data.analytics) R.state.analytics = data.analytics;
    if (data.ai_usage_today) R.state.ai.usage = data.ai_usage_today;
    R.state.isGuest = false;
    R.state.authPending = false;
  }

  R.bootRefresh = async function () {
    try {
      const boot = await R.api('/api/miniapp/boot', {
        method: 'POST',
        body: { init_data: R.state.initData || R.resolveInitData() || null, lang: R.state.lang }
      });
      applyBootBundle(boot);
      R.syncShellUI();
      if (R.state.activeTab === 'home') R.renderHome();
      else if (R.state.activeTab === 'tests') R.renderPrepare();
      else if (R.state.activeTab === 'profile') R.renderProfile();
      else if (R.state.activeTab === 'ai') R.renderAiView();
    } catch (e) {
      await R.refreshProfileSnapshot();
    }
  };

  R.loadAnalyticsAsync = async function () {
    try {
      const data = await R.api('/api/learning/analytics?lang=' + R.state.lang);
      R.state.analytics = data;
      if (R.state.activeTab === 'home') R.renderHome();
      else if (R.state.activeTab === 'profile') R.renderProfile();
    } catch (e) {}
  };

  R.refreshProfileSnapshot = async function () {
    try {
      const me = await R.api('/api/user/me');
      if (me.user) R.state.user = me.user;
      if (me.subscription) R.state.subscription = me.subscription;
      if (me.free_tier) R.state.freeTier = me.free_tier;
      if (me.stats) R.state.stats = me.stats;
      if (me.streak) R.state.streak = me.streak;
      if (me.history) R.state.history = me.history;
      if (me.bookmarks_count !== undefined) R.state.bookmarksCount = me.bookmarks_count;
      R.syncShellUI();
    } catch (e) {}
  };

  async function enterPublicFreemiumWeb() {
    R.state.isGuest = true;
    R.state.authPending = false;
    if (typeof R.loadLocaleJson === 'function') await R.loadLocaleJson(R.state.lang);
    try {
      R.state.publicOverview = await R.api('/api/public/overview?lang=' + R.state.lang);
      R.state.categories = (R.state.publicOverview && R.state.publicOverview.categories) || [];
    } catch (e) {}
    R.syncShellUI();
    const dl = R.resolveDeepLinkRoute();
    const guestAllowed = new Set([
      'tests', 'tests/tickets', 'tests/topics', 'tests/drill', 'tests/cheatsheet',
      'prepare', 'prepare/tickets', 'prepare/topics', 'prepare/drill', 'prepare/cheatsheet',
      'tickets', 'topics', 'drill', 'cheatsheet', 'shpargalka',
      'amaliy', 'practical', 'amaliy/modules', 'amaliy/penalty', 'penalty', 'jarima', 'profile'
    ]);
    if (guestAllowed.has(dl)) {
      R.applyDeepLinkRoute(dl);
    } else {
      R.renderHome();
    }
  }

  function hydrateIconsAndBindings() {
    const iconBindings = {
      'channel-icon-slot': ['telegram', 'sm'],
      'sidebar-exam-icon': ['zap', 'sm'],
      'nav-icon-home': ['home', 'sm'],
      'nav-icon-tests': ['bookOpen', 'sm'],
      'nav-icon-ai': ['bot', 'sm'],
      'nav-icon-amaliy': ['steeringWheel', 'sm'],
      'nav-icon-profile': ['profile', 'sm'],
      'snav-icon-home': ['home', 'sm'],
      'snav-icon-tests': ['bookOpen', 'sm'],
      'snav-icon-ai': ['bot', 'sm'],
      'snav-icon-amaliy': ['steeringWheel', 'sm'],
      'snav-icon-profile': ['profile', 'sm']
    };
    Object.keys(iconBindings).forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.innerHTML = R.icon(iconBindings[id][0], iconBindings[id][1]);
    });

    document.querySelectorAll('[data-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.haptic('light');
        R.navigateTo(btn.dataset.tab);
      });
    });

    document.getElementById('sidebar-exam-btn')?.addEventListener('click', function () {
      R.startSession({ session_type: 'EXAM' });
    });

    document.getElementById('sidebar-goal-box')?.addEventListener('click', R.openDailyGoalModal);

    ['mobile-theme-btn', 'sidebar-theme-btn'].forEach(function (id) {
      document.getElementById(id)?.addEventListener('click', function () {
        R.haptic('light');
        R.theme.toggleLightDark();
        if (R.state.activeTab === 'profile') R.renderProfile();
      });
    });

    ['mobile-lang-btn', 'sidebar-lang-btn'].forEach(function (id) {
      document.getElementById(id)?.addEventListener('click', function () {
        document.querySelectorAll('[data-modal-lang]').forEach(function (b) {
          b.classList.toggle('active', b.dataset.modalLang === R.state.lang);
        });
        R.openModal('lang-modal');
      });
    });

    document.querySelectorAll('[data-modal-lang]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.changeLanguage(btn.dataset.modalLang);
      });
    });

    document.getElementById('mobile-channel-btn')?.addEventListener('click', function () {
      const url = 'https://t.me/rully_avtotest';
      const tg = window.Telegram && window.Telegram.WebApp;
      if (tg && typeof tg.openTelegramLink === 'function') tg.openTelegramLink(url);
      else window.open(url, '_blank', 'noopener');
    });

    // Keyboard shortcuts during quiz mode (1-4 / A-D / Arrows)
    document.addEventListener('keydown', function (e) {
      if (!R.state.quiz.active) return;
      const tag = (e.target && e.target.tagName) || '';
      if (tag === 'INPUT' || tag === 'TEXTAREA') return;

      const keyMap = { '1': 'A', '2': 'B', '3': 'C', '4': 'D', 'a': 'A', 'b': 'B', 'c': 'C', 'd': 'D', 'f1': 'A', 'f2': 'B', 'f3': 'C', 'f4': 'D' };
      const rawKey = String(e.key).toLowerCase();
      const k = keyMap[rawKey];
      if (rawKey.startsWith('f') && k) e.preventDefault();
      if (k) {
        const curQ = R.state.quiz.questions[R.state.quiz.currentIndex];
        if (curQ && (curQ.options || []).some(function (o) { return o.option_key === k; })) {
          R.submitQuizAnswer(k);
        }
      } else if (e.key === 'ArrowRight') {
        if (R.state.quiz.currentIndex < R.state.quiz.questions.length - 1) {
          R.state.quiz.currentIndex += 1;
          R.renderQuizQuestion();
        }
      } else if (e.key === 'ArrowLeft') {
        if (R.state.quiz.currentIndex > 0) {
          R.state.quiz.currentIndex -= 1;
          R.renderQuizQuestion();
        }
      }
    });
  }

  async function initApp() {
    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg) {
      try {
        tg.ready();
        tg.expand();
        if (typeof tg.disableVerticalSwipes === 'function') tg.disableVerticalSwipes();
      } catch (e) {}
    }

    R.state.initData = R.resolveInitData();
    R.theme.init();
    R.initHudBindings();
    hydrateIconsAndBindings();

    // Render 0ms skeleton Home right away
    R.renderHome();

    try {
      const boot = await R.api('/api/miniapp/boot', {
        method: 'POST',
        body: { init_data: R.state.initData || null }
      });
      applyBootBundle(boot);
      if (R.state.lang !== 'uz_latn') {
        await R.loadLocaleJson(R.state.lang);
      }

      R.syncShellUI();
      if (!R.applyDeepLinkRoute()) {
        R.renderHome();
      }
      if (typeof R.maybeShowOnboarding === 'function') {
        R.maybeShowOnboarding();
      }
      window.addEventListener('hashchange', function () {
        R.applyDeepLinkRoute();
      });
    } catch (err) {
      R.state.authPending = false;
      if (err && err.status === 401) {
        await enterPublicFreemiumWeb();
      } else {
        R.showToast((err && err.message) || R.t('ai_net_error'));
        R.renderHome();
      }
    }

    if (typeof navigator !== 'undefined' && 'serviceWorker' in navigator && (window.location.protocol === 'https:' || window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost')) {
      navigator.serviceWorker.register('/static/sw.js').catch(function () {});
    }
  }

  R.initApp = initApp;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
  } else {
    initApp();
  }
})();
