/**
 * RULLY 2.0 Profile, Milestones, Topic Analytics, Theme/Lang, Billing & Reference Modals
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});
  let invoicePollTimer = null;
  let invoiceTickTimer = null;

  R.stopInvoicePolling = function () {
    if (invoicePollTimer) { clearInterval(invoicePollTimer); invoicePollTimer = null; }
    if (invoiceTickTimer) { clearInterval(invoiceTickTimer); invoiceTickTimer = null; }
  };

  function copyWithToast(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(function () {});
    }
    R.haptic('light');
    R.showToast(text);
  }

  R.openPaywallModal = async function () {
    const body = document.getElementById('paywall-modal-body');
    if (!body) return;
    body.innerHTML = '<div class="skeleton-block" style="height:120px;"></div>';
    R.openModal('paywall-modal');

    let plans = [
      { id: 'pro_14', name: R.t('sub_plan_14_title'), duration_days: 14, price_formatted: R.t('sub_plan_14_price'), daily: R.t('sub_plan_14_daily') },
      { id: 'pro_30', name: R.t('sub_plan_30_title'), duration_days: 30, price_formatted: R.t('sub_plan_30_price'), daily: R.t('sub_plan_30_daily'), popular: true }
    ];
    try {
      const res = await R.api('/api/subscription/plans');
      if (Array.isArray(res.plans) && res.plans.length) {
        plans = res.plans.map(function (p) {
          return Object.assign({}, p, { popular: String(p.id).includes('30') });
        });
      }
    } catch (e) {}

    body.innerHTML =
      '<p style="font-size:13px;color:var(--text-secondary);">' + R.escHtml(R.t('sub_paywall_subtitle')) + '</p>' +
      '<div class="list-stack">' +
      '  <div class="surface-card" style="padding:12px 14px;display:flex;flex-direction:column;gap:6px;font-size:12.5px;">' +
      '    <div>' + R.icon('checkCircle', 'xs') + ' ' + R.escHtml(R.t('sub_feature_exam')) + '</div>' +
      '    <div>' + R.icon('checkCircle', 'xs') + ' ' + R.escHtml(R.t('sub_feature_ai')) + '</div>' +
      '    <div>' + R.icon('checkCircle', 'xs') + ' ' + R.escHtml(R.t('sub_feature_mistakes')) + '</div>' +
      '    <div>' + R.icon('checkCircle', 'xs') + ' ' + R.escHtml(R.t('sub_feature_cheatsheet')) + '</div>' +
      '  </div>' +
      plans.map(function (pl) {
        return '<div class="surface-card" style="' + (pl.popular ? 'border-color:var(--color-primary);' : '') + '">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px;">' +
          '  <div><strong>' + R.escHtml(pl.name) + '</strong>' + (pl.popular ? ' <span class="badge-pill badge-primary">' + R.escHtml(R.t('sub_popular_badge')) + '</span>' : '') + '</div>' +
          '  <strong class="font-mono" style="color:var(--color-primary);">' + R.escHtml(pl.price_formatted || (pl.base_price_uzs + ' so‘m')) + '</strong>' +
          '</div>' +
          '<button type="button" class="btn ' + (pl.popular ? 'btn-primary' : 'btn-secondary') + ' btn-block btn-sm" data-buy-plan="' + R.escHtml(pl.id) + '">' + R.escHtml(R.t('sub_btn_activate')) + '</button>' +
          '</div>';
      }).join('') +
      '</div>';

    body.querySelectorAll('[data-buy-plan]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.createPaymentOrder(btn.dataset.buyPlan);
      });
    });
  };

  R.createPaymentOrder = async function (planId) {
    try {
      const res = await R.api('/api/payment/orders/create', { method: 'POST', body: { plan_id: planId } });
      const ord = res.order;
      if (!ord) throw new Error('Order failed');
      R.closeModal('paywall-modal');

      const elPlan = document.getElementById('inv-plan-name');
      const elHolder = document.getElementById('inv-cardholder-name');
      const elCard = document.getElementById('inv-card-number');
      const elAmount = document.getElementById('inv-total-amount');
      const elRef = document.getElementById('inv-order-ref');
      const elTimer = document.getElementById('invoice-countdown-timer');

      if (elPlan) elPlan.textContent = ord.plan_name || planId;
      if (elHolder) elHolder.textContent = ord.cardholder_name || 'ANVARJON ARALOV';
      const rawCard = ord.card_number_raw || ord.card_number_masked || '9860 0000 0000 5370';
      if (elCard) elCard.textContent = rawCard;
      const amtFmt = String(ord.final_amount_uzs || 0).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
      if (elAmount) elAmount.textContent = amtFmt;
      if (elRef) elRef.textContent = ord.order_id;

      let rem = Number(ord.remaining_seconds || 900);
      if (elTimer) elTimer.textContent = R.fmtClock(rem);

      R.stopInvoicePolling();
      invoiceTickTimer = setInterval(function () {
        rem = Math.max(0, rem - 1);
        if (elTimer) elTimer.textContent = R.fmtClock(rem);
        if (rem <= 0) R.stopInvoicePolling();
      }, 1000);

      invoicePollTimer = setInterval(async function () {
        try {
          const st = await R.api('/api/payment/orders/' + encodeURIComponent(ord.order_id) + '/status');
          if (st.is_paid) {
            R.stopInvoicePolling();
            R.closeModal('invoice-modal');
            R.haptic('success');
            R.showToast(R.t('sub_success_msg'), 4000);
            await R.refreshProfileSnapshot();
          } else if (st.is_expired) {
            R.stopInvoicePolling();
            R.closeModal('invoice-modal');
          }
        } catch (e) {}
      }, 4500);

      document.getElementById('btn-copy-card')?.addEventListener('click', function () {
        copyWithToast(rawCard.replace(/\s+/g, ''));
      });
      document.getElementById('btn-copy-amount')?.addEventListener('click', function () {
        copyWithToast(String(ord.final_amount_uzs || 0));
      });

      R.openModal('invoice-modal');
    } catch (err) {
      R.showToast(err.detail || err.message || R.t('ai_generic_error'));
    }
  };

  R.openCheatsheetModal = function () {
    const isPro = Boolean(R.state.subscription && R.state.subscription.is_pro);
    if (!isPro) {
      R.openPaywallModal();
      return;
    }
    const cs = (window.CHEATSHEET_DATA && (window.CHEATSHEET_DATA[R.state.lang] || window.CHEATSHEET_DATA.uz_latn)) || null;
    const body = document.getElementById('cheatsheet-modal-body');
    if (!body || !cs) return;

    const hiHtml = (cs.high_prob_items || []).map(function (it) {
      return '<div class="surface-card" style="padding:12px;">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:4px;"><strong>' + R.escHtml(it.term) + '</strong><span class="badge-pill badge-emerald font-mono">' + R.escHtml(it.chip) + '</span></div>' +
        '<div style="font-size:12px;color:var(--text-secondary);">' + R.escHtml(it.hint) + '</div>' +
        '</div>';
    }).join('');

    const trapHtml = (cs.trap_items || []).map(function (it) {
      return '<div class="surface-card" style="padding:12px;border-color:rgba(239,68,68,0.3);">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:4px;"><strong>' + R.escHtml(it.term) + '</strong><span class="badge-pill badge-rose font-mono">' + R.escHtml(it.chip) + '</span></div>' +
        '<div style="font-size:12px;color:var(--text-secondary);">' + it.hint + '</div>' +
        '</div>';
    }).join('');

    body.innerHTML =
      (cs.collective
        ? '<div class="surface-card" style="background:var(--color-primary-soft);border-color:var(--color-primary-border);">' +
          '  <span class="badge-pill badge-primary" style="margin-bottom:6px;">' + R.escHtml(cs.collective.badge) + '</span>' +
          '  <div style="font-weight:700;margin-bottom:4px;">' + R.escHtml(cs.collective.title) + '</div>' +
          '  <p style="font-size:12.5px;">' + cs.collective.desc + '</p>' +
          '</div>'
        : '') +
      '<div class="section-heading" style="margin-top:8px;"><span>' + R.escHtml(cs.high_prob_title || '') + '</span></div>' +
      '<div class="list-stack">' + hiHtml + '</div>' +
      '<div class="section-heading" style="margin-top:8px;"><span>' + R.escHtml(cs.trap_title || '') + '</span></div>' +
      '<div class="list-stack">' + trapHtml + '</div>';

    R.openModal('cheatsheet-modal');
  };

  R.openInfoModal = function (mode) {
    const titleEl = document.getElementById('info-modal-title');
    const bodyEl = document.getElementById('info-modal-body');
    if (!bodyEl) return;

    if (mode === 'changelog') {
      if (titleEl) titleEl.textContent = R.t('changelog_modal_title');
      bodyEl.innerHTML =
        '<div class="surface-card">' +
        '  <span class="badge-pill badge-emerald">RULLY 2.0</span>' +
        '  <ul style="padding-left:18px;margin-top:8px;font-size:13px;line-height:1.6;">' +
        '    <li>Yorug‘ (Daylight Road) va Tungi (Midnight Asphalt) dual dizayn tizimi</li>' +
        '    <li>Kompyuter (Sidebar Bento) va Mobil moslashuvchan arxitektura</li>' +
        '    <li>67 ta tizimli biletlar (#01–#67) barcha 1 327 ta savol bo‘yicha</li>' +
        '    <li>Aqlli moslashuvchan mashq va Zaif mavzular analitikasi</li>' +
        '    <li>Har bir javob va xatodan AI Ustozga kontekstli o‘tish</li>' +
        '    <li>Topshirilgan imtihonlarni savolma-savol ko‘rib chiqish</li>' +
        '  </ul>' +
        '</div>';
    } else {
      if (titleEl) titleEl.textContent = R.t('rules_modal_title');
      bodyEl.innerHTML =
        '<div class="surface-card" style="font-size:13px;line-height:1.6;">' +
        '  <p>O‘zbekiston Respublikasi Yo‘l Harakati Qoidalari va DYHXX VMQ 408 rasmiy imtihon standartlari asosida ishlaydi: 20 ta savol, 25 daqiqa vaqt, kamida 18 ta to‘g‘ri javob (ko‘pi bilan 2 ta xato).</p>' +
        '</div>';
    }
    R.openModal('info-modal');
  };

  R.renderProfile = function () {
    const root = document.getElementById('view-profile');
    if (!root) return;

    const u = R.state.user || {};
    const sub = R.state.subscription || {};
    const stats = R.state.stats || {};
    const streak = R.state.streak || { daily_goal_questions: 20 };
    const analytics = R.state.analytics || {};
    const history = R.state.history || [];
    const displayName = [u.first_name, u.last_name].filter(Boolean).join(' ') || u.username || 'RULLY Driver';
    const initials = (displayName[0] || 'R').toUpperCase();

    const milestoneMap = {
      first_steps: R.t('milestone_first_steps'),
      streak_3: R.t('milestone_streak_3'),
      exam_passer: R.t('milestone_exam_passer'),
      mistake_slayer: R.t('milestone_mistake_slayer'),
      ticket_finisher: R.t('milestone_ticket_finisher'),
      avtodrom_pro: R.t('milestone_avtodrom_pro')
    };

    const milestonesHtml = (analytics.milestones || []).map(function (ms) {
      return '<div class="milestone-card ' + (ms.unlocked ? 'unlocked' : '') + '">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;">' +
        '  <span class="r-icon sm">' + R.icon(ms.unlocked ? 'award' : 'target', 'sm') + '</span>' +
        '  <span class="font-mono" style="font-size:11px;font-weight:700;">' + ms.progress + '/' + ms.target + '</span>' +
        '</div>' +
        '<div style="font-size:12px;font-weight:700;">' + R.escHtml(milestoneMap[ms.id] || ms.id) + '</div>' +
        '</div>';
    }).join('');

    const weakCatsHtml = (analytics.weak_categories || []).slice(0, 3).map(function (c) {
      return '<div style="display:flex;justify-content:space-between;font-size:12.5px;padding:6px 0;border-bottom:1px solid var(--border-hairline);">' +
        '<span style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + R.escHtml(c.name) + '</span>' +
        '<span class="badge-pill badge-rose font-mono">' + Math.round(c.accuracy_pct || 0) + '%</span>' +
        '</div>';
    }).join('');

    root.innerHTML =
      '<section class="surface-card" style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:14px;">' +
      '  <div style="display:flex;align-items:center;gap:12px;">' +
      '    <div class="avatar-circle" style="width:48px;height:48px;font-size:18px;">' + initials + '</div>' +
      '    <div>' +
      '      <div style="font-family:var(--font-display);font-size:17px;font-weight:800;">' + R.escHtml(displayName) + '</div>' +
      '      <div style="font-size:12px;color:var(--text-muted);">ID: ' + R.escHtml(u.user_id || '-') + (u.username ? ' • @' + R.escHtml(u.username) : '') + '</div>' +
      '    </div>' +
      '  </div>' +
      '  <span class="badge-pill ' + (sub.is_pro ? 'badge-emerald' : 'badge-neutral') + '">' + R.escHtml(sub.is_pro ? R.t('sub_tier_pro') : R.t('sub_tier_free')) + '</span>' +
      '</section>' +

      '<section class="surface-card" style="margin-bottom:14px;' + (sub.is_pro ? 'border-color:rgba(16,185,129,0.4);' : 'border-color:var(--color-primary-border);') + '">' +
      '  <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;">' +
      '    <div><strong>' + R.escHtml(R.t('sub_title')) + '</strong><p style="font-size:12.5px;color:var(--text-secondary);margin-top:3px;">' +
      R.escHtml(sub.is_pro ? R.t('sub_pro_active_desc', { date: (sub.expires_at || '').slice(0, 10), days: sub.days_left || 0 }) : R.t('sub_free_desc')) +
      '    </p></div>' +
      '    <button type="button" class="btn btn-primary btn-sm" id="prof-upgrade-btn">' + R.escHtml(sub.is_pro ? R.t('sub_btn_extend') : R.t('sub_btn_activate')) + '</button>' +
      '  </div>' +
      '</section>' +

      (analytics.total_bank_questions
        ? '<section class="surface-card" style="margin-bottom:14px;">' +
          '  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;"><strong>' + R.escHtml(R.t('analytics_coverage_label')) + '</strong><span class="font-mono" style="font-weight:700;">' + (analytics.unique_answered || 0) + ' / ' + analytics.total_bank_questions + ' (' + (analytics.overall_coverage_pct || 0) + '%)</span></div>' +
          '  <div class="progress-track" style="margin-bottom:10px;"><div class="progress-fill" style="width:' + Math.min(100, analytics.overall_coverage_pct || 0) + '%"></div></div>' +
          (weakCatsHtml ? '<div style="font-size:12px;font-weight:700;color:var(--text-muted);margin-bottom:4px;">' + R.escHtml(R.t('analytics_weak_title')) + '</div>' + weakCatsHtml : '') +
          '</section>'
        : '') +

      (milestonesHtml
        ? '<div class="section-heading"><span>' + R.escHtml(R.t('milestones_title')) + '</span></div>' +
          '<div class="milestones-grid" style="margin-bottom:14px;">' + milestonesHtml + '</div>'
        : '') +

      '<section class="surface-card" style="margin-bottom:14px;display:flex;flex-direction:column;gap:14px;">' +
      '  <div>' +
      '    <div style="font-size:13px;font-weight:700;margin-bottom:6px;">' + R.escHtml(R.t('theme_title')) + '</div>' +
      '    <div class="seg-pills" style="grid-template-columns:repeat(3,1fr);">' +
      '      <button type="button" class="seg-pill ' + (R.theme.pref === 'auto' ? 'active' : '') + '" data-theme-opt="auto">' + R.escHtml(R.t('theme_auto')) + '</button>' +
      '      <button type="button" class="seg-pill ' + (R.theme.pref === 'light' ? 'active' : '') + '" data-theme-opt="light">' + R.escHtml(R.t('theme_light')) + '</button>' +
      '      <button type="button" class="seg-pill ' + (R.theme.pref === 'dark' ? 'active' : '') + '" data-theme-opt="dark">' + R.escHtml(R.t('theme_dark')) + '</button>' +
      '    </div>' +
      '  </div>' +
      '  <div>' +
      '    <div style="font-size:13px;font-weight:700;margin-bottom:6px;">' + R.escHtml(R.t('language_select_title')) + '</div>' +
      '    <div class="seg-pills" style="grid-template-columns:repeat(3,1fr);">' +
      '      <button type="button" class="seg-pill ' + (R.state.lang === 'uz_latn' ? 'active' : '') + '" data-lang-opt="uz_latn">O‘zbekcha</button>' +
      '      <button type="button" class="seg-pill ' + (R.state.lang === 'uz_cyrl' ? 'active' : '') + '" data-lang-opt="uz_cyrl">Ўзбекча</button>' +
      '      <button type="button" class="seg-pill ' + (R.state.lang === 'ru' ? 'active' : '') + '" data-lang-opt="ru">Русский</button>' +
      '    </div>' +
      '  </div>' +
      '  <div>' +
      '    <div style="font-size:13px;font-weight:700;margin-bottom:6px;">' + R.escHtml(R.t('daily_goal_label')) + '</div>' +
      '    <div class="seg-pills">' +
      [10, 20, 30, 50].map(function (g) {
        return '<button type="button" class="seg-pill ' + (Number(streak.daily_goal_questions || 20) === g ? 'active' : '') + '" data-prof-goal="' + g + '">' + g + '</button>';
      }).join('') +
      '    </div>' +
      '  </div>' +
      '</section>' +

      '<div class="section-heading"><span>' + R.escHtml(R.t('history_section_title')) + '</span></div>' +
      '<div class="list-stack" style="margin-bottom:14px;">' +
      (!history.length
        ? '<div class="surface-card" style="font-size:13px;color:var(--text-muted);">' + R.escHtml(R.t('history_empty')) + '</div>'
        : history.map(function (h) {
            return '<div class="data-row-card">' +
              '  <div>' +
              '    <div style="font-weight:700;font-size:13.5px;">' + h.correct_count + ' / ' + h.total_questions + ' <span class="font-mono">(' + Math.round(h.percentage) + '%)</span></div>' +
              '    <div style="font-size:11.5px;color:var(--text-muted);">' + R.escHtml((h.created_at || '').slice(0, 10)) + ' • ' + (h.passed ? R.escHtml(R.t('status_passed')) : R.escHtml(R.t('status_failed'))) + '</div>' +
              '  </div>' +
              '  <button type="button" class="btn btn-sm btn-secondary" data-review-sid="' + R.escHtml(h.session_id) + '">' + R.icon('eye', 'xs') + '<span>' + R.escHtml(R.t('review_btn')) + '</span></button>' +
              '</div>';
          }).join('')) +
      '</div>' +

      '<div class="list-stack">' +
      '  <button type="button" class="data-row-card card-interactive" id="prof-cheatsheet-btn" style="width:100%;">' +
      '    <span style="font-weight:600;">' + R.escHtml(R.t('card_cheatsheet_title')) + '</span>' + R.icon('chevronRight', 'sm') +
      '  </button>' +
      '  <button type="button" class="data-row-card card-interactive" id="prof-rules-btn" style="width:100%;">' +
      '    <span style="font-weight:600;">' + R.escHtml(R.t('rules_tile_title')) + '</span>' + R.icon('chevronRight', 'sm') +
      '  </button>' +
      '  <button type="button" class="data-row-card card-interactive" id="prof-changelog-btn" style="width:100%;">' +
      '    <span style="font-weight:600;">RULLY 2.0</span>' + R.icon('chevronRight', 'sm') +
      '  </button>' +
      '</div>';

    document.getElementById('prof-upgrade-btn')?.addEventListener('click', R.openPaywallModal);
    document.getElementById('prof-cheatsheet-btn')?.addEventListener('click', R.openCheatsheetModal);
    document.getElementById('prof-rules-btn')?.addEventListener('click', function () { R.openInfoModal('rules'); });
    document.getElementById('prof-changelog-btn')?.addEventListener('click', function () { R.openInfoModal('changelog'); });

    root.querySelectorAll('[data-theme-opt]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.theme.apply(btn.dataset.themeOpt);
        R.renderProfile();
      });
    });

    root.querySelectorAll('[data-lang-opt]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.changeLanguage(btn.dataset.langOpt);
      });
    });

    root.querySelectorAll('[data-prof-goal]').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        const g = Number(btn.dataset.profGoal);
        const res = await R.api('/api/user/daily-goal', { method: 'POST', body: { daily_goal: g } });
        R.state.streak.daily_goal_questions = res.daily_goal_questions || g;
        R.showToast(R.t('daily_goal_label') + ': ' + g);
        R.renderProfile();
        R.syncShellUI();
      });
    });

    root.querySelectorAll('[data-review-sid]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.openSessionReviewModal(btn.dataset.reviewSid);
      });
    });
  };
})();
