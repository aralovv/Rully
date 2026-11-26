/**
 * RULLY 2.0 Resilient HTTP API Client & Telegram Auth Bootstrap
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});

  R.resolveInitData = function () {
    const tgData = window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData;
    if (tgData && tgData.length > 5) {
      try { sessionStorage.setItem('rully_tg_init_data', tgData); } catch (e) {}
      return tgData;
    }
    try {
      const hashStr = window.location.hash.replace(/^#/, '');
      if (hashStr.includes('tgWebAppData=')) {
        const val = new URLSearchParams(hashStr).get('tgWebAppData');
        if (val && val.length > 5) {
          try { sessionStorage.setItem('rully_tg_init_data', val); } catch (e) {}
          return val;
        }
      }
    } catch (e) {}
    try {
      const val = new URLSearchParams(window.location.search).get('tgWebAppData');
      if (val && val.length > 5) {
        try { sessionStorage.setItem('rully_tg_init_data', val); } catch (e) {}
        return val;
      }
    } catch (e) {}
    try {
      const cached = sessionStorage.getItem('rully_tg_init_data');
      if (cached && cached.length > 5) return cached;
    } catch (e) {}
    return '';
  };

  R.api = async function (path, options) {
    const opts = options ? Object.assign({}, options) : {};
    const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
    if (R.state.initData) {
      headers['X-Telegram-Init-Data'] = R.state.initData;
    }
    opts.headers = headers;
    if (opts.body && typeof opts.body !== 'string') {
      opts.body = JSON.stringify(opts.body);
    }

    const resp = await fetch(path, opts);
    let data = {};
    try {
      data = await resp.json();
    } catch (e) {
      data = {};
    }

    if (!resp.ok) {
      const err = new Error(data.detail || ('HTTP ' + resp.status));
      err.status = resp.status;
      err.detail = data.detail;
      err.data = data;
      throw err;
    }
    return data;
  };
})();
