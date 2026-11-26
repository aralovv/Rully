/**
 * RULLY 2.0 Core Reactive State & Localization / Escaping Helpers
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});

  R.state = {
    authPending: true,
    isExternalWebBlocked: false,
    initData: '',
    lang: 'uz_latn',
    user: null,
    stats: null,
    streak: { current_streak: 1, daily_goal_questions: 20, today_questions_count: 0 },
    subscription: { is_pro: false, tier: 'free', days_left: 0 },
    freeTier: { has_access: true, remaining_exams: 2, allowed_exams: 2 },
    history: [],
    bookmarksCount: 0,
    categories: [],
    tickets: [],
    ticketsMeta: { total_tickets: 67, passed_tickets: 0, attempted_tickets: 0 },
    analytics: null,
    mistakesCount: 0,
    mistakesList: [],
    bookmarksList: [],
    modules: [],
    checklist: [],
    scenarios: [],
    activeTab: 'home',
    prepareSubtab: 'topics',
    topicFilter: 'all',
    topicSearch: '',
    ticketFilter: 'all',
    amaliySubtab: 'modules',
    customQuiz: {
      total_questions: 20,
      show_answer: true,
      show_explanation: true,
      time_limit_minutes: 0
    },
    quiz: {
      active: false,
      sessionId: null,
      sessionType: 'EXAM',
      ticketNumber: null,
      questions: [],
      currentIndex: 0,
      answers: {},
      timeRemaining: 25 * 60,
      timerInterval: null,
      startTime: null,
      showAnswer: true,
      showExplanation: true,
      isSubmitting: false
    },
    ai: {
      history: [],
      loaded: false,
      sending: false,
      contextQuestion: null,
      usage: { current: 0, max: 100 }
    }
  };

  R.t = function t(key, params) {
    const dict = (window.I18N && window.I18N[R.state.lang]) || (window.I18N && window.I18N.uz_latn) || {};
    let str = dict[key];
    if (str === undefined || str === null) {
      str = (window.I18N && window.I18N.uz_latn && window.I18N.uz_latn[key]) || key;
    }
    if (params && typeof str === 'string') {
      Object.keys(params).forEach(function (k) {
        str = str.replace(new RegExp('\\{' + k + '\\}', 'g'), String(params[k]));
      });
    }
    return str;
  };

  R.escHtml = function escHtml(val) {
    if (val === undefined || val === null) return '';
    return String(val)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  };

  R.icon = function icon(name, cls) {
    if (typeof window.renderIcon === 'function') {
      return window.renderIcon(name, ('r-svg ' + (cls || '')).trim());
    }
    return '';
  };

  R.fmtClock = function fmtClock(sec) {
    const s = Math.max(0, Math.floor(sec || 0));
    const m = Math.floor(s / 60);
    const r = s % 60;
    return String(m).padStart(2, '0') + ':' + String(r).padStart(2, '0');
  };

  R.normalizeLang = function normalizeLang(l) {
    if (l === 'ru' || l === 'uz_cyrl' || l === 'uz_latn') return l;
    return 'uz_latn';
  };
})();
