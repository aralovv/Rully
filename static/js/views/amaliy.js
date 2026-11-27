/**
 * RULLY 2.0 Practical Driving (Amaliy): 10 Core Modules | YIM Penalty Calculator
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});
  let checkedPenalties = {};

  const PENALTY_ITEMS = [
    { id: 'belt', pts: 100, title: 'Xavfsizlik kamarisiz harakatlanish / Svetofor qizil', note: 'Avtomatik chetlatish (-100)' },
    { id: 'ped', pts: 100, title: 'Piyodaga yo‘l bermaslik', note: 'Qo‘pol xato (-100)' },
    { id: 'rollback', pts: 100, title: 'Estakadada 30 sm dan ko‘p orqaga siljish', note: 'Avtomatik chetlatish (-100)' },
    { id: 'turn_signal', pts: 15, title: 'Burilish chirog‘ini (pavorotnik) yoqmaslik', note: '-15 ball' },
    { id: 'stall', pts: 10, title: 'Dvigatelni o‘chirib qo‘yish (gloxnut)', note: '-10 ball' },
    { id: 'line_touch', pts: 20, title: 'Yo‘l chizig‘i va chegaralarni kesib o‘tish', note: '-20 ball' },
    { id: 'mirror', pts: 10, title: 'Ko‘zgularni tekshirmasdan harakatlanish', note: '-10 ball' }
  ];

  R.loadAmaliyData = async function () {
    if (R.state.isGuest) return;
    const lang = R.state.lang;
    try {
      const mRes = await R.api('/api/amaliy/modules?lang=' + lang);
      R.state.modules = mRes.modules || [];
      R.state.amaliyModulesMeta = {
        completed: mRes.completed_count || 0,
        total: mRes.total || 10,
        pct: mRes.completion_percentage || 0
      };
      R.renderAmaliy();
    } catch (e) {}
  };

  R.openModuleDetailModal = async function (modId) {
    const body = document.getElementById('module-detail-body');
    const titleEl = document.getElementById('module-detail-title');
    if (!body) return;
    body.innerHTML = '<div class="skeleton-block" style="height:140px;"></div>';
    R.openModal('module-detail-modal');

    try {
      const mod = await R.api('/api/amaliy/modules/' + encodeURIComponent(modId) + '?lang=' + R.state.lang);
      if (titleEl) titleEl.textContent = mod.title;

      const stepsHtml = (mod.steps || []).map(function (s) {
        return '<div class="step-timeline-item">' +
          '<div class="step-num-dot">' + s.step + '</div>' +
          '<div><strong style="font-size:13.5px;">' + R.escHtml(s.title) + '</strong><p style="font-size:12.5px;color:var(--text-secondary);margin-top:2px;">' + R.escHtml(s.instruction) + '</p></div>' +
          '</div>';
      }).join('');

      const mistakesHtml = (mod.common_mistakes || []).map(function (m) {
        return '<li style="margin-bottom:4px;font-size:12.5px;color:var(--text-secondary);">' + R.escHtml(m) + '</li>';
      }).join('');

      body.innerHTML =
        '<div style="display:flex;gap:8px;flex-wrap:wrap;">' +
        '  <span class="badge-pill badge-primary">' + R.escHtml(mod.badge || '') + '</span>' +
        '  <span class="badge-pill badge-neutral">' + R.escHtml(R.t('duration_mins', { n: mod.duration_min || 15 })) + '</span>' +
        '</div>' +
        '<p style="font-size:13.5px;color:var(--text-secondary);">' + R.escHtml(mod.description || '') + '</p>' +
        '<div><strong style="font-size:13.5px;display:block;margin-bottom:8px;">' + R.escHtml(R.t('step_by_step_guide')) + '</strong><div class="list-stack">' + stepsHtml + '</div></div>' +
        (mistakesHtml ? '<div class="surface-card"><strong style="font-size:13px;display:block;margin-bottom:6px;">' + R.escHtml(R.t('common_mistakes_title')) + '</strong><ul style="padding-left:18px;">' + mistakesHtml + '</ul></div>' : '') +
        (mod.disqualification_trap
          ? '<div class="surface-card" style="background:var(--color-rose-soft);border-color:rgba(239,68,68,0.35);">' +
            '  <strong style="font-size:13px;color:var(--color-rose);display:flex;align-items:center;gap:6px;">' + R.icon('alertTriangle', 'sm') + ' ' + R.escHtml(R.t('disqualification_warning')) + '</strong>' +
            '  <p style="font-size:12.5px;margin-top:4px;">' + R.escHtml(mod.disqualification_trap) + '</p>' +
            '</div>'
          : '') +
        '<button type="button" class="btn ' + (mod.is_completed ? 'btn-secondary' : 'btn-emerald') + ' btn-block" id="btn-toggle-mod-done">' +
        R.icon(mod.is_completed ? 'rotateCcw' : 'checkCircle', 'sm') + '<span>' + R.escHtml(mod.is_completed ? R.t('module_btn_unmaster') : R.t('module_btn_mastered')) + '</span>' +
        '</button>';

      document.getElementById('btn-toggle-mod-done')?.addEventListener('click', async function () {
        const res = await R.api('/api/amaliy/modules/toggle', { method: 'POST', body: { module_id: mod.id } });
        R.haptic(res.is_completed ? 'success' : 'light');
        R.closeModal('module-detail-modal');
        await R.loadAmaliyData();
      });
    } catch (err) {
      body.innerHTML = '<p style="color:var(--color-rose);">' + R.escHtml(err.message) + '</p>';
    }
  };

  function renderModulesTab(container) {
    if (R.state.isGuest) {
      container.innerHTML =
        '<div class="surface-card" style="text-align:center;padding:24px 16px;">' +
        '  <strong style="display:block;font-size:15px;margin-bottom:6px;">' + R.escHtml(R.t('tab_modules')) + '</strong>' +
        '  <p style="font-size:12.5px;color:var(--text-secondary);margin-bottom:14px;">' + R.escHtml(R.t('amaliy_guest_modules_hint')) + '</p>' +
        '  <button type="button" class="btn btn-primary btn-sm" id="btn-amaliy-guest-penalty">' + R.escHtml(R.t('amaliy_penalty_tab')) + '</button>' +
        '</div>';
      document.getElementById('btn-amaliy-guest-penalty')?.addEventListener('click', function () {
        R.state.amaliySubtab = 'penalty';
        R.renderAmaliy();
      });
      return;
    }

    const mods = R.state.modules || [];
    const meta = R.state.amaliyModulesMeta || { completed: 0, total: 10, pct: 0 };

    if (!mods.length) {
      container.innerHTML = '<div class="list-stack"><div class="surface-card skeleton-block" style="height:82px;"></div><div class="surface-card skeleton-block" style="height:82px;"></div></div>';
      return;
    }

    container.innerHTML =
      '<div class="surface-card" style="margin-bottom:12px;">' +
      '  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">' +
      '    <strong style="font-size:14px;">' + R.escHtml(R.t('modules_readiness')) + '</strong>' +
      '    <span class="badge-pill badge-amber font-mono">' + meta.completed + ' / ' + meta.total + ' (' + Math.round(meta.pct) + '%)</span>' +
      '  </div>' +
      '  <div class="progress-track"><div class="progress-fill amber" style="width:' + Math.min(100, meta.pct) + '%"></div></div>' +
      '</div>' +
      '<div class="topics-grid">' +
      mods.map(function (m) {
        return '<button type="button" class="surface-card card-interactive topic-card" data-mod-id="' + R.escHtml(m.id) + '">' +
          '<div class="topic-card-head">' +
          '  <span class="badge-pill badge-neutral">' + R.escHtml(m.badge) + '</span>' +
          (m.is_completed
            ? '<span class="badge-pill badge-emerald">' + R.icon('check', 'xs') + ' ' + R.escHtml(R.t('badge_completed')) + '</span>'
            : '<span class="badge-pill badge-neutral font-mono">' + R.escHtml(R.t('module_steps', { n: m.steps_count })) + '</span>') +
          '</div>' +
          '<div class="topic-name">' + m.order + '. ' + R.escHtml(m.title) + '</div>' +
          '<p style="font-size:12px;color:var(--text-secondary);">' + R.escHtml(m.description) + '</p>' +
          '</button>';
      }).join('') +
      '</div>';

    container.querySelectorAll('[data-mod-id]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.openModuleDetailModal(btn.dataset.modId);
      });
    });
  }

  function renderPenaltyTab(container) {
    let deducted = 0;
    Object.keys(checkedPenalties).forEach(function (pid) {
      if (checkedPenalties[pid]) {
        const item = PENALTY_ITEMS.find(function (x) { return x.id === pid; });
        if (item) deducted += item.pts;
      }
    });
    const score = Math.max(0, 100 - deducted);
    const passed = score >= 80;

    container.innerHTML =
      '<div class="surface-card" style="margin-bottom:12px;">' +
      '  <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">' +
      '    <div><strong style="font-size:15px;">' + R.escHtml(R.t('amaliy_penalty_tab')) + '</strong><p style="font-size:12px;color:var(--text-secondary);">VMQ 408: Kamida 80 / 100 ball talab etiladi</p></div>' +
      '    <span class="badge-pill ' + (passed ? 'badge-emerald' : 'badge-rose') + ' font-mono" style="font-size:15px;">' + score + ' / 100</span>' +
      '  </div>' +
      '  <div class="progress-track" style="margin-top:8px;"><div class="progress-fill ' + (passed ? 'emerald' : 'amber') + '" style="width:' + score + '%"></div></div>' +
      '</div>' +
      '<div class="list-stack">' +
      PENALTY_ITEMS.map(function (it) {
        const active = Boolean(checkedPenalties[it.id]);
        return '<button type="button" class="data-row-card card-interactive penalty-row ' + (active ? 'is-penalized' : '') + '" data-pen-id="' + it.id + '" style="width:100%;text-align:left;">' +
          '  <div><div style="font-weight:600;font-size:13px;">' + R.escHtml(it.title) + '</div><div style="font-size:11.5px;color:var(--text-muted);">' + R.escHtml(it.note) + '</div></div>' +
          '  <span class="badge-pill ' + (active ? 'badge-rose' : 'badge-neutral') + ' font-mono">' + (active ? '-' + it.pts : '0') + '</span>' +
          '</button>';
      }).join('') +
      '</div>';

    container.querySelectorAll('[data-pen-id]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const id = btn.dataset.penId;
        checkedPenalties[id] = !checkedPenalties[id];
        renderPenaltyTab(container);
      });
    });
  }

  R.renderAmaliy = function () {
    const root = document.getElementById('view-amaliy');
    if (!root) return;
    const defaultTab = R.state.isGuest ? 'penalty' : 'modules';
    let sub = R.state.amaliySubtab || defaultTab;
    if (sub !== 'modules' && sub !== 'penalty') {
      sub = defaultTab;
      R.state.amaliySubtab = sub;
    }

    root.innerHTML =
      '<div style="margin-bottom:12px;">' +
      '  <h2 style="font-family:var(--font-display);font-size:18px;font-weight:800;">' + R.escHtml(R.t('amaliy_title')) + '</h2>' +
      '  <p style="font-size:12.5px;color:var(--text-secondary);">' + R.escHtml(R.t('amaliy_subtitle')) + '</p>' +
      '</div>' +
      '<div class="subtab-bar">' +
      '  <button type="button" class="subtab-btn ' + (sub === 'modules' ? 'active' : '') + '" data-am-tab="modules">' + R.escHtml(R.t('tab_modules')) + '</button>' +
      '  <button type="button" class="subtab-btn ' + (sub === 'penalty' ? 'active' : '') + '" data-am-tab="penalty">' + R.escHtml(R.t('amaliy_penalty_tab')) + '</button>' +
      '</div>' +
      '<div id="amaliy-subtab-body"></div>';

    root.querySelectorAll('[data-am-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.state.amaliySubtab = btn.dataset.amTab;
        R.renderAmaliy();
      });
    });

    const body = document.getElementById('amaliy-subtab-body');
    if (sub === 'penalty') renderPenaltyTab(body);
    else renderModulesTab(body);
  };
})();
