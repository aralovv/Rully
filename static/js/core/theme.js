/**
 * RULLY 2.0 Theme Controller (Auto Telegram / Daylight Light / Midnight Asphalt Dark)
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});
  const STORAGE_KEY = 'rully_theme_pref';

  R.theme = {
    pref: 'auto',

    getEffectiveTheme: function (pref) {
      const p = pref || R.theme.pref || 'auto';
      if (p === 'light' || p === 'dark') return p;
      const tgScheme = window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.colorScheme;
      if (tgScheme === 'light' || tgScheme === 'dark') return tgScheme;
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
      }
      return 'light';
    },

    apply: function (pref) {
      if (pref) {
        R.theme.pref = pref;
        try { localStorage.setItem(STORAGE_KEY, pref); } catch (e) {}
      }
      const resolved = R.theme.getEffectiveTheme(R.theme.pref);
      document.documentElement.dataset.theme = resolved;

      const tg = window.Telegram && window.Telegram.WebApp;
      const bg = resolved === 'dark' ? '#090B0E' : '#F1F2F4';
      const hdr = resolved === 'dark' ? '#11141B' : '#FFFFFF';
      const metaTheme = document.querySelector('meta[name="theme-color"]');
      if (metaTheme) metaTheme.setAttribute('content', bg);
      if (tg) {
        try {
          if (typeof tg.setHeaderColor === 'function') tg.setHeaderColor(hdr);
          if (typeof tg.setBackgroundColor === 'function') tg.setBackgroundColor(bg);
        } catch (e) {}
      }

      // Update header & sidebar quick theme icons
      const iconName = resolved === 'dark' ? 'sun' : 'moon';
      ['mobile-theme-btn', 'sidebar-theme-btn'].forEach(function (id) {
        const btn = document.getElementById(id);
        if (btn) {
          const iconSlot = btn.querySelector('.r-icon');
          if (iconSlot) iconSlot.innerHTML = R.icon(iconName, 'sm');
        }
      });

      document.querySelectorAll('[data-theme-opt]').forEach(function (btn) {
        btn.classList.toggle('active', btn.dataset.themeOpt === R.theme.pref);
      });
    },

    toggleLightDark: function () {
      const current = R.theme.getEffectiveTheme();
      R.theme.apply(current === 'dark' ? 'light' : 'dark');
    },

    init: function () {
      let saved = 'auto';
      try { saved = localStorage.getItem(STORAGE_KEY) || 'auto'; } catch (e) {}
      if (saved !== 'light' && saved !== 'dark' && saved !== 'auto') saved = 'auto';
      R.theme.pref = saved;
      R.theme.apply();

      const tg = window.Telegram && window.Telegram.WebApp;
      if (tg && typeof tg.onEvent === 'function') {
        tg.onEvent('themeChanged', function () {
          if (R.theme.pref === 'auto') R.theme.apply();
        });
      }
      if (window.matchMedia) {
        const mq = window.matchMedia('(prefers-color-scheme: dark)');
        if (mq.addEventListener) {
          mq.addEventListener('change', function () {
            if (R.theme.pref === 'auto') R.theme.apply();
          });
        }
      }
    }
  };
})();
