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

    if (tabName === 'home') {
      R.renderHome();
    } else if (tabName === 'tests') {
      R.renderPrepare();
      R.loadPrepareData();
    } else if (tabName === 'amaliy') {
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

  R.syncShellUI = function () {
    const u = R.state.user || {};
    const displayName = [u.first_name, u.last_name].filter(Boolean).join(' ') || u.username || 'RULLY';
    const av = document.getElementById('mobile-avatar');
    const nm = document.getElementById('mobile-user-name');
    const sb = document.getElementById('mobile-user-sub');
    if (av) av.textContent = (displayName[0] || 'R').toUpperCase();
    if (nm) nm.textContent = displayName;
    if (sb) {
      const days = (R.state.streak && R.state.streak.current_streak) || 1;
      sb.textContent = R.t('streak_badge', { days: days });
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
    R.syncShellUI();
    R.closeModal('lang-modal');
    R.navigateTo(R.state.activeTab);
    try {
      await R.api('/api/user/language', { method: 'POST', body: { language: valid } });
      await R.loadAnalyticsAsync();
    } catch (e) {}
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

  function showExternalWebGate() {
    const shell = document.getElementById('app-shell');
    const gate = document.getElementById('web-gate-container');
    if (shell) shell.classList.add('hidden');
    if (gate) {
      gate.classList.remove('hidden');
      gate.innerHTML =
        '<div class="web-gate-card">' +
        '  <div class="brand-mark" style="width:52px;height:52px;font-size:24px;margin:0 auto 14px;">R</div>' +
        '  <h1 style="font-family:var(--font-display);font-size:20px;font-weight:800;margin-bottom:8px;">' + R.escHtml(R.t('web_gate_title')) + '</h1>' +
        '  <p style="font-size:13.5px;color:var(--text-secondary);margin-bottom:20px;">' + R.escHtml(R.t('web_gate_desc')) + '</p>' +
        '  <a href="https://t.me/rully_uz_bot" target="_blank" rel="noopener" class="btn btn-primary btn-block">' +
        R.icon('telegram', 'sm') + '<span>' + R.escHtml(R.t('web_gate_btn')) + '</span>' +
        '  </a>' +
        '</div>';
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

      const keyMap = { '1': 'A', '2': 'B', '3': 'C', '4': 'D', 'a': 'A', 'b': 'B', 'c': 'C', 'd': 'D' };
      const k = keyMap[String(e.key).toLowerCase()];
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
      if (R.state.initData) {
        const auth = await R.api('/api/auth/telegram', {
          method: 'POST',
          body: { init_data: R.state.initData }
        });
        R.state.user = auth.user;
        R.state.lang = R.normalizeLang(auth.user && auth.user.language);
        R.state.subscription = auth.subscription || R.state.subscription;
        R.state.freeTier = auth.free_tier || R.state.freeTier;
        R.state.streak = auth.streak || R.state.streak;
        R.state.stats = auth.stats || {};
        R.state.authPending = false;
        R.refreshProfileSnapshot();
      } else {
        // Local dev server allows dev user 8809526955; production returns 401 -> branded Telegram gate
        const me = await R.api('/api/user/me');
        R.state.user = me.user;
        R.state.lang = R.normalizeLang(me.user && me.user.language);
        R.state.subscription = me.subscription || R.state.subscription;
        R.state.freeTier = me.free_tier || R.state.freeTier;
        R.state.streak = me.streak || R.state.streak;
        R.state.stats = me.stats || {};
        R.state.history = me.history || [];
        R.state.bookmarksCount = me.bookmarks_count || 0;
        R.state.authPending = false;
      }

      R.syncShellUI();
      R.renderHome();
      R.loadAnalyticsAsync();
    } catch (err) {
      R.state.authPending = false;
      if (err && err.status === 401) {
        showExternalWebGate();
      } else {
        R.showToast((err && err.message) || R.t('ai_net_error'));
        R.renderHome();
      }
    }
  }

  R.initApp = initApp;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
  } else {
    initApp();
  }
})();
