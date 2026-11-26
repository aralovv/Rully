/**
 * RULLY 2.0 Practical Driving (Amaliy Avtodrom): 10 Modules | Checklist | Scenarios
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});
  let scenIndex = 0;
  let scenAnswers = {};

  R.loadAmaliyData = async function () {
    const lang = R.state.lang;
    try {
      const [mRes, cRes, sRes] = await Promise.all([
        R.api('/api/amaliy/modules?lang=' + lang),
        R.api('/api/amaliy/checklist?lang=' + lang),
        R.api('/api/amaliy/scenarios?lang=' + lang)
      ]);
      R.state.modules = mRes.modules || [];
      R.state.amaliyModulesMeta = {
        completed: mRes.completed_count || 0,
        total: mRes.total || 10,
        pct: mRes.completion_percentage || 0
      };
      R.state.checklist = cRes.items || [];
      R.state.checklistMeta = {
        completed: cRes.completed_count || 0,
        total: cRes.total || 0,
        pct: cRes.readiness_percentage || 0
      };
      R.state.scenarios = sRes.scenarios || [];
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

  function renderChecklistTab(container) {
    const items = R.state.checklist || [];
    const meta = R.state.checklistMeta || { completed: 0, total: 0, pct: 0 };

    const catLabels = {
      tayyorgarlik: R.t('checklist_cat_tayyorgarlik'),
      avtodrom: R.t('checklist_cat_avtodrom'),
      shahar: R.t('checklist_cat_shahar'),
      yakunlash: R.t('checklist_cat_yakunlash')
    };

    const grouped = {};
    items.forEach(function (it) {
      const cat = it.category || 'tayyorgarlik';
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(it);
    });

    let html =
      '<div class="surface-card" style="margin-bottom:12px;">' +
      '  <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;">' +
      '    <strong style="font-size:14px;">' + R.escHtml(R.t('checklist_readiness')) + '</strong>' +
      '    <div style="display:flex;gap:8px;align-items:center;">' +
      '      <span class="badge-pill badge-emerald font-mono">' + meta.completed + ' / ' + meta.total + '</span>' +
      '      <button type="button" class="btn btn-sm btn-secondary" id="btn-chk-reset">' + R.icon('rotateCcw', 'xs') + ' ' + R.escHtml(R.t('checklist_btn_reset')) + '</button>' +
      '    </div>' +
      '  </div>' +
      '  <div class="progress-track"><div class="progress-fill emerald" style="width:' + Math.min(100, meta.pct) + '%"></div></div>' +
      '</div>';

    Object.keys(grouped).forEach(function (cat) {
      html += '<div class="section-heading" style="margin-top:12px;font-size:14px;"><span>' + R.escHtml(catLabels[cat] || cat) + '</span></div>' +
        '<div class="list-stack">' +
        grouped[cat].map(function (it) {
          return '<button type="button" class="data-row-card card-interactive" style="width:100%;text-align:left;" data-chk-id="' + R.escHtml(it.id) + '">' +
            '<span style="font-size:13.5px;font-weight:500;' + (it.is_completed ? 'text-decoration:line-through;color:var(--text-muted);' : '') + '">' + R.escHtml(it.title) + '</span>' +
            '<span class="badge-pill ' + (it.is_completed ? 'badge-emerald' : 'badge-neutral') + '">' + R.icon(it.is_completed ? 'check' : 'x', 'xs') + '</span>' +
            '</button>';
        }).join('') +
        '</div>';
    });

    container.innerHTML = html;

    document.getElementById('btn-chk-reset')?.addEventListener('click', async function () {
      await R.api('/api/amaliy/checklist/reset', { method: 'POST' });
      R.haptic('light');
      await R.loadAmaliyData();
    });

    container.querySelectorAll('[data-chk-id]').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        await R.api('/api/amaliy/checklist/toggle', { method: 'POST', body: { item_id: btn.dataset.chkId } });
        R.haptic('light');
        await R.loadAmaliyData();
      });
    });
  }

  function renderScenariosTab(container) {
    const scens = R.state.scenarios || [];
    if (!scens.length) {
      container.innerHTML = '<div class="surface-card skeleton-block" style="height:140px;"></div>';
      return;
    }

    if (scenIndex >= scens.length) scenIndex = 0;
    const sc = scens[scenIndex];
    const ans = scenAnswers[sc.id];

    container.innerHTML =
      '<div class="surface-card">' +
      '  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">' +
      '    <span class="badge-pill badge-amber">' + R.escHtml(R.t('scenario_question', { cur: scenIndex + 1, total: scens.length })) + '</span>' +
      '    <strong style="font-size:13px;">' + R.escHtml(sc.title) + '</strong>' +
      '  </div>' +
      '  <p style="font-size:14.5px;font-weight:600;line-height:1.45;margin-bottom:12px;">' + R.escHtml(sc.situation) + '</p>' +
      '  <div class="options-stack">' +
      (sc.options || []).map(function (opt) {
        let cls = '';
        if (ans) {
          if (opt.id === ans.correct_option) cls = 'is-correct';
          else if (opt.id === ans.selected_option && !ans.is_correct) cls = 'is-wrong';
        }
        return '<button type="button" class="option-btn ' + cls + '" data-scen-opt="' + opt.id + '"' + (ans ? ' disabled' : '') + '>' +
          '<span class="option-key-badge">' + opt.id + '</span>' +
          '<span class="option-text">' + R.escHtml(opt.text) + '</span>' +
          '</button>';
      }).join('') +
      '  </div>' +
      (ans ? '<div class="feedback-panel ' + (ans.is_correct ? 'correct' : 'wrong') + '" style="margin-top:12px;"><strong style="font-size:13px;">' + R.escHtml(ans.is_correct ? R.t('correct_badge') : R.t('wrong_badge')) + '</strong><p style="font-size:12.5px;">' + R.escHtml(ans.explanation) + '</p></div>' : '') +
      '  <div style="display:flex;justify-content:space-between;gap:8px;margin-top:14px;">' +
      '    <button type="button" class="btn btn-sm btn-secondary" id="scen-prev-btn"' + (scenIndex === 0 ? ' disabled' : '') + '>' + R.escHtml(R.t('scenario_btn_prev')) + '</button>' +
      (scenIndex < scens.length - 1
        ? '<button type="button" class="btn btn-sm btn-primary" id="scen-next-btn">' + R.escHtml(R.t('scenario_btn_next')) + '</button>'
        : '<button type="button" class="btn btn-sm btn-emerald" id="scen-restart-btn">' + R.escHtml(R.t('scenario_btn_restart')) + '</button>') +
      '  </div>' +
      '</div>';

    container.querySelectorAll('[data-scen-opt]').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        const chosen = Number(btn.dataset.scenOpt);
        const res = await R.api('/api/amaliy/scenarios/answer', {
          method: 'POST',
          body: { scenario_id: sc.id, selected_option: chosen, language: R.state.lang }
        });
        scenAnswers[sc.id] = res;
        R.haptic(res.is_correct ? 'success' : 'error');
        renderScenariosTab(container);
      });
    });

    document.getElementById('scen-prev-btn')?.addEventListener('click', function () {
      if (scenIndex > 0) { scenIndex -= 1; renderScenariosTab(container); }
    });
    document.getElementById('scen-next-btn')?.addEventListener('click', function () {
      if (scenIndex < scens.length - 1) { scenIndex += 1; renderScenariosTab(container); }
    });
    document.getElementById('scen-restart-btn')?.addEventListener('click', function () {
      scenAnswers = {};
      scenIndex = 0;
      renderScenariosTab(container);
    });
  }

  R.renderAmaliy = function () {
    const root = document.getElementById('view-amaliy');
    if (!root) return;
    const sub = R.state.amaliySubtab || 'modules';

    root.innerHTML =
      '<div style="margin-bottom:12px;">' +
      '  <h2 style="font-family:var(--font-display);font-size:18px;font-weight:800;">' + R.escHtml(R.t('amaliy_title')) + '</h2>' +
      '  <p style="font-size:12.5px;color:var(--text-secondary);">' + R.escHtml(R.t('amaliy_subtitle')) + '</p>' +
      '</div>' +
      '<div class="subtab-bar" style="grid-template-columns:repeat(3,1fr);">' +
      '  <button type="button" class="subtab-btn ' + (sub === 'modules' ? 'active' : '') + '" data-am-tab="modules">' + R.escHtml(R.t('tab_modules')) + '</button>' +
      '  <button type="button" class="subtab-btn ' + (sub === 'checklist' ? 'active' : '') + '" data-am-tab="checklist">' + R.escHtml(R.t('tab_checklist')) + '</button>' +
      '  <button type="button" class="subtab-btn ' + (sub === 'scenarios' ? 'active' : '') + '" data-am-tab="scenarios">' + R.escHtml(R.t('tab_scenarios')) + '</button>' +
      '</div>' +
      '<div id="amaliy-subtab-body"></div>';

    root.querySelectorAll('[data-am-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.state.amaliySubtab = btn.dataset.amTab;
        R.renderAmaliy();
      });
    });

    const body = document.getElementById('amaliy-subtab-body');
    if (sub === 'modules') renderModulesTab(body);
    else if (sub === 'checklist') renderChecklistTab(body);
    else renderScenariosTab(body);
  };
})();
