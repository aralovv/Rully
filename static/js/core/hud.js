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
  };
})();
