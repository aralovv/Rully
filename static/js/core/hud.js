/**
 * RULLY 2.0 HUD, Modal Manager, Haptic Feedback, Confirm Dialog & Zoom Lightbox
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});
  let toastTimer = null;
  let openModals = [];
  let confirmResolver = null;

  R.haptic = function (type) {
    const tg = window.Telegram && window.Telegram.WebApp;
    if (!tg || !tg.HapticFeedback) return;
    try {
      if (type === 'success' || type === 'error' || type === 'warning') {
        tg.HapticFeedback.notificationOccurred(type);
      } else {
        tg.HapticFeedback.impactOccurred(type || 'light');
      }
    } catch (e) {}
  };

  R.showToast = function (message, duration) {
    const el = document.getElementById('hud-toast');
    if (!el) return;
    el.textContent = message;
    el.classList.add('visible');
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function () {
      el.classList.remove('visible');
    }, duration || 2400);
  };

  R.syncTelegramBackButton = function () {
    const tg = window.Telegram && window.Telegram.WebApp;
    if (!tg || !tg.BackButton) return;
    try {
      const shouldShow = openModals.length > 0 || R.state.quiz.active || R.state.activeTab !== 'home';
      if (shouldShow) tg.BackButton.show();
      else tg.BackButton.hide();
    } catch (e) {}
  };

  R.openModal = function (id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.add('open');
    document.body.classList.add('modal-open');
    if (!openModals.includes(id)) openModals.push(id);
    R.syncTelegramBackButton();
  };

  R.closeModal = function (id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('open');
    openModals = openModals.filter(function (x) { return x !== id; });
    if (openModals.length === 0) {
      document.body.classList.remove('modal-open');
    }
    if (id === 'invoice-modal' && typeof R.stopInvoicePolling === 'function') {
      R.stopInvoicePolling();
    }
    R.syncTelegramBackButton();
  };

  R.closeTopModal = function () {
    if (openModals.length === 0) return false;
    const topId = openModals[openModals.length - 1];
    R.closeModal(topId);
    return true;
  };

  R.confirmDialog = function (title, text, confirmLabel) {
    return new Promise(function (resolve) {
      confirmResolver = resolve;
      const tEl = document.getElementById('confirm-modal-title');
      const pEl = document.getElementById('confirm-modal-text');
      const okBtn = document.getElementById('confirm-ok-btn');
      if (tEl) tEl.textContent = title || R.t('confirm_finish_title');
      if (pEl) pEl.textContent = text || R.t('confirm_finish_text');
      if (okBtn) okBtn.textContent = confirmLabel || R.t('btn_confirm');
      R.openModal('confirm-modal');
    });
  };

  R.openLightbox = function (src, caption) {
    const img = document.getElementById('lightbox-img');
    const cap = document.getElementById('lightbox-caption');
    if (img) img.src = src;
    if (cap) cap.textContent = caption || '';
    R.openModal('image-lightbox-modal');
  };

  R.isFullscreenActive = function () {
    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg && typeof tg.isFullscreen === 'boolean') {
      return tg.isFullscreen;
    }
    return Boolean(document.fullscreenElement || document.webkitFullscreenElement);
  };

  R.syncSafeAreas = function () {
    const tg = window.Telegram && window.Telegram.WebApp;
    const root = document.documentElement;
    let top = 0;
    let bottom = 0;
    let left = 0;
    let right = 0;

    if (tg) {
      const isFs = Boolean((typeof tg.isFullscreen === 'boolean' && tg.isFullscreen) || document.fullscreenElement || document.webkitFullscreenElement);
      const csai = tg.contentSafeAreaInset || {};
      const sai = tg.safeAreaInset || {};
      top = Math.max(Number(csai.top) || 0, Number(sai.top) || 0);
      bottom = Math.max(Number(csai.bottom) || 0, Number(sai.bottom) || 0);
      left = Math.max(Number(csai.left) || 0, Number(sai.left) || 0);
      right = Math.max(Number(csai.right) || 0, Number(sai.right) || 0);

      // In Telegram Fullscreen mode, Telegram floats native Back (<) and Close (X) buttons over the top area (~48px-54px).
      // If Telegram does not report content safe area (e.g. earlier clients or layout settling delay), ensure at least 48px.
      if (isFs && top < 48) {
        top = 48;
      }

      if (isFs) {
        document.body.classList.add('telegram-fullscreen');
      } else {
        document.body.classList.remove('telegram-fullscreen');
      }
    }

    if (top > 0) root.style.setProperty('--tg-safe-top', top + 'px');
    else root.style.removeProperty('--tg-safe-top');

    if (bottom > 0) root.style.setProperty('--tg-safe-bottom', bottom + 'px');
    else root.style.removeProperty('--tg-safe-bottom');

    if (left > 0) root.style.setProperty('--tg-safe-left', left + 'px');
    else root.style.removeProperty('--tg-safe-left');

    if (right > 0) root.style.setProperty('--tg-safe-right', right + 'px');
    else root.style.removeProperty('--tg-safe-right');
  };

  R.syncFullscreenUI = function () {
    const isFs = R.isFullscreenActive();
    const iconName = isFs ? 'minimize' : 'maximize';
    const label = isFs ? (R.t('btn_exit_fullscreen') || 'Oddiy ekran') : (R.t('btn_fullscreen') || 'Butun ekran');

    const mBtn = document.getElementById('mobile-fullscreen-btn');
    const mSlot = document.getElementById('fullscreen-icon-slot');
    if (mBtn) {
      mBtn.setAttribute('title', label);
      mBtn.setAttribute('aria-label', label);
    }
    if (mSlot) mSlot.innerHTML = R.icon(iconName, 'sm');

    const sBtn = document.getElementById('sidebar-fullscreen-btn');
    const sSlot = document.getElementById('sidebar-fullscreen-icon-slot');
    if (sBtn) {
      sBtn.setAttribute('title', label);
      sBtn.setAttribute('aria-label', label);
    }
    if (sSlot) sSlot.innerHTML = R.icon(iconName, 'sm');
  };

  R.toggleFullscreen = function () {
    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg && typeof tg.requestFullscreen === 'function') {
      try {
        if (tg.isFullscreen) {
          if (typeof tg.exitFullscreen === 'function') tg.exitFullscreen();
        } else {
          tg.requestFullscreen();
        }
        setTimeout(function () {
          R.syncSafeAreas();
          R.syncFullscreenUI();
        }, 120);
        return;
      } catch (e) {}
    }

    if (tg && typeof tg.expand === 'function') {
      try { tg.expand(); } catch (e) {}
    }

    try {
      if (!document.fullscreenElement && !document.webkitFullscreenElement) {
        const root = document.documentElement;
        if (root.requestFullscreen) {
          root.requestFullscreen().catch(function () {});
        } else if (root.webkitRequestFullscreen) {
          root.webkitRequestFullscreen();
        }
      } else {
        if (document.exitFullscreen) {
          document.exitFullscreen().catch(function () {});
        } else if (document.webkitExitFullscreen) {
          document.webkitExitFullscreen();
        }
      }
    } catch (e) {}
    setTimeout(function () {
      R.syncSafeAreas();
      R.syncFullscreenUI();
    }, 120);
  };

  R.openQuestionDetailModal = async function (qOrId) {
    let q = null;
    if (typeof qOrId === 'object' && qOrId !== null) {
      q = qOrId;
    } else if (typeof qOrId === 'string' || typeof qOrId === 'number') {
      const cid = String(qOrId);
      if (Array.isArray(R.state.bookmarksList)) {
        q = R.state.bookmarksList.find(function (x) { return String(x.canonical_id) === cid; });
      }
      if (!q || !q.options || !q.options.length) {
        try {
          const lang = R.state.lang || 'uz_latn';
          q = await R.api('/api/theory/questions/' + encodeURIComponent(cid) + '?lang=' + lang);
        } catch (e) {
          R.showToast(R.t('load_error') || 'Savolni yuklab bo‘lmadi');
          return;
        }
      }
    }
    if (!q) return;

    const modal = document.getElementById('question-detail-modal');
    if (!modal) return;

    const titleEl = document.getElementById('question-detail-modal-title');
    const bodyEl = document.getElementById('question-detail-modal-body');
    if (titleEl) {
      titleEl.innerHTML = '<span style="font-size:12.5px;color:var(--text-muted);font-weight:600;">#' + R.escHtml(q.canonical_id) + '</span>' +
        (q.category_name ? ' <span class="badge-pill badge-neutral font-mono" style="font-size:11px;margin-left:6px;">' + R.escHtml(q.category_name) + '</span>' : '');
    }

    let html = '';

    // Media / Image (if present)
    if (q.image_url) {
      html += '<div class="quiz-media-frame" style="max-height:240px;margin-bottom:12px;cursor:zoom-in;position:relative;" id="qdm-zoom-img">' +
        '<img src="' + R.escHtml(R.safeUrl(q.image_url)) + '" alt="Question diagram" style="max-height:230px;width:100%;object-fit:contain;border-radius:10px;">' +
        '<span style="position:absolute;bottom:8px;right:8px;background:rgba(0,0,0,0.65);backdrop-filter:blur(4px);color:#fff;border-radius:6px;padding:3px 8px;font-size:11px;display:flex;align-items:center;gap:4px;">' +
          R.icon('zoomIn', 'xs') + ' ' + R.escHtml(R.t('btn_view') || 'Kattalashtirish') +
        '</span>' +
      '</div>';
    }

    // Question Text
    html += '<div style="font-size:14.5px;font-weight:700;line-height:1.45;color:var(--text-primary);margin-bottom:14px;">' +
      R.escHtml(q.question_text || '') +
    '</div>';

    // Options List
    const options = q.options || [];
    if (options.length) {
      html += '<div class="list-stack" style="gap:8px;margin-bottom:14px;">';
      options.forEach(function (opt) {
        const isCorrect = (opt.option_key === q.correct_option_key);
        if (isCorrect) {
          html += '<div class="data-row-card is-correct" style="background:rgba(16,185,129,0.12);border:1.5px solid var(--accent-emerald,#10b981);border-radius:10px;padding:10px 12px;align-items:flex-start;gap:10px;">' +
            '<span class="badge-pill badge-emerald font-mono" style="font-weight:700;flex-shrink:0;">' + R.escHtml(opt.option_key) + '</span>' +
            '<div style="flex:1;font-size:13.5px;color:var(--text-primary);font-weight:600;line-height:1.4;">' + R.escHtml(opt.text || '') + '</div>' +
            '<span class="badge-pill badge-emerald" style="font-size:11px;padding:2px 8px;flex-shrink:0;display:inline-flex;align-items:center;gap:4px;">' +
              R.icon('check', 'xs') + ' ' + R.escHtml(R.t('badge_correct_answer') || 'To‘g‘ri javob') +
            '</span>' +
          '</div>';
        } else {
          html += '<div class="data-row-card" style="background:var(--surface-muted);border:1px solid var(--border-color);border-radius:10px;padding:10px 12px;align-items:flex-start;gap:10px;opacity:0.85;">' +
            '<span class="badge-pill badge-neutral font-mono" style="flex-shrink:0;">' + R.escHtml(opt.option_key) + '</span>' +
            '<div style="flex:1;font-size:13px;color:var(--text-secondary);line-height:1.4;">' + R.escHtml(opt.text || '') + '</div>' +
          '</div>';
        }
      });
      html += '</div>';
    }

    // Provenance / Law Reference Badge
    const provHtml = typeof R.renderProvenanceBadge === 'function' ? R.renderProvenanceBadge(q, q.canonical_id) : '';
    if (provHtml) {
      html += '<div style="margin-bottom:12px;">' + provHtml + '</div>';
    }

    // Explanation / Legal grounds
    if (q.explanation) {
      html += '<div class="surface-card" style="background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.22);border-radius:10px;padding:12px;margin-bottom:14px;">' +
        '<div style="display:flex;align-items:center;gap:6px;font-weight:700;font-size:12.5px;color:var(--accent-blue,#3b82f6);margin-bottom:6px;">' +
          R.icon('lightbulb', 'xs') + ' <span>' + R.escHtml(R.t('explanation_title') || 'Sharh va qonuniy asos') + '</span>' +
        '</div>' +
        '<div style="font-size:13px;line-height:1.5;color:var(--text-primary);">' + R.escHtml(q.explanation) + '</div>' +
      '</div>';
    }

    // Footer actions
    const isBookmarked = (q.is_bookmarked !== false);
    html += '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:8px;padding-top:12px;border-top:1px solid var(--border-color);">' +
      '<button type="button" class="btn btn-secondary btn-sm" id="qdm-toggle-bm-btn">' +
        (isBookmarked
          ? (R.icon('trash', 'xs') + ' ' + R.escHtml(R.t('btn_remove_bookmark') || 'Saqlangandan o‘chirish'))
          : (R.icon('bookmark', 'xs') + ' ' + R.escHtml(R.t('btn_save_bookmark') || 'Saqlash'))) +
      '</button>' +
      '<button type="button" class="btn btn-primary btn-sm" data-close-modal="question-detail-modal">' +
        R.escHtml(R.t('btn_modal_dismiss') || 'Yopish') +
      '</button>' +
    '</div>';

    if (bodyEl) {
      bodyEl.innerHTML = html;
      const zoomImg = bodyEl.querySelector('#qdm-zoom-img');
      if (zoomImg && q.image_url) {
        zoomImg.addEventListener('click', function () {
          R.openLightbox(q.image_url, q.question_text);
        });
      }
      const bmBtn = bodyEl.querySelector('#qdm-toggle-bm-btn');
      if (bmBtn) {
        bmBtn.addEventListener('click', async function () {
          try {
            await R.api('/api/bookmarks/toggle', { method: 'POST', body: { canonical_id: q.canonical_id } });
            R.state.bookmarksList = (R.state.bookmarksList || []).filter(function (x) { return String(x.canonical_id) !== String(q.canonical_id); });
            R.state.bookmarksCount = R.state.bookmarksList.length;
            R.state.bookmarksLoaded = false;
            R.closeModal('question-detail-modal');
            R.showToast(R.t('toast_bookmark_removed') || 'Saqlanganlardan o‘chirildi');
            if (typeof R.renderPrepare === 'function' && R.state.activeTab === 'tests') {
              R.renderPrepare();
            }
          } catch (e) {
            R.showToast(R.t('network_error') || 'Xatolik yuz berdi');
          }
        });
      }
      const closeBtn = bodyEl.querySelector('[data-close-modal="question-detail-modal"]');
      if (closeBtn) {
        closeBtn.addEventListener('click', function () {
          R.closeModal('question-detail-modal');
        });
      }
    }

    R.openModal('question-detail-modal');
  };

  R.initHudBindings = function () {
    document.querySelectorAll('.modal-overlay').forEach(function (overlay) {
      overlay.addEventListener('click', function (e) {
        if (e.target === overlay) R.closeModal(overlay.id);
      });
    });

    document.querySelectorAll('[data-close-modal]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.closeModal(btn.dataset.closeModal);
      });
    });

    const okBtn = document.getElementById('confirm-ok-btn');
    const cancelBtn = document.getElementById('confirm-cancel-btn');
    if (okBtn) {
      okBtn.addEventListener('click', function () {
        const res = confirmResolver;
        confirmResolver = null;
        R.closeModal('confirm-modal');
        if (res) res(true);
      });
    }
    if (cancelBtn) {
      cancelBtn.addEventListener('click', function () {
        const res = confirmResolver;
        confirmResolver = null;
        R.closeModal('confirm-modal');
        if (res) res(false);
      });
    }

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && openModals.length > 0) {
        R.closeTopModal();
      }
    });

    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg && tg.BackButton && typeof tg.BackButton.onClick === 'function') {
      tg.BackButton.onClick(function () {
        if (R.closeTopModal()) return;
        if (R.state.quiz.active && typeof R.confirmAbortQuiz === 'function') {
          R.confirmAbortQuiz();
          return;
        }
        if (R.state.activeTab !== 'home' && typeof R.navigateTo === 'function') {
          R.navigateTo('home');
        }
      });
    }

    R.syncSafeAreas();
    window.addEventListener('resize', R.syncSafeAreas);
    window.addEventListener('orientationchange', R.syncSafeAreas);

    function onFsChange() {
      R.syncSafeAreas();
      R.syncFullscreenUI();
    }

    document.addEventListener('fullscreenchange', onFsChange);
    document.addEventListener('webkitfullscreenchange', onFsChange);
    if (tg && typeof tg.onEvent === 'function') {
      try {
        tg.onEvent('safeAreaChanged', onFsChange);
        tg.onEvent('contentSafeAreaChanged', onFsChange);
        tg.onEvent('fullscreenChanged', onFsChange);
        tg.onEvent('fullscreenFailed', onFsChange);
      } catch (e) {}
    }
    R.syncFullscreenUI();
  };
})();
