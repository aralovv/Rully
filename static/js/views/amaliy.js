/**
 * RULLY 2.0 Practical Driving (Amaliy Avtodrom): 10 Modules | Checklist | Scenarios
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});
  let scenIndex = 0;
  let scenAnswers = {};
  let simKey = 'parallel';
  let simStep = 0;
  let checkedPenalties = {};

  const SIM_MANEUVERS = {
    parallel: {
      title: { uz_latn: 'Parallel parkovka', uz_cyrl: 'Параллел парковка', ru: 'Параллельная парковка' },
      rule: {
        uz_latn: 'VMQ 408: Yon chiziqlarga tegmasdan, 2 ta manevr (orqa + to‘g‘ri) bilan belgilangan zonaga kiring.',
        uz_cyrl: 'VMQ 408: Ён чизиқларга тегмасдан, 2 та маневр билан зонага киринг.',
        ru: 'ПКМ 408: Заехать в зону парковки не задевая конусы и разметку.'
      },
      steps: [
        { x: 185, y: 26, rot: 0, wheel: '0°', mirror: 'O‘ng ko‘zgu', txt: 'Oldingi chiziq bilan tenglashing (50 sm yon masofa).' },
        { x: 162, y: 58, rot: 35, wheel: '+360° →', mirror: 'O‘ng orqa ustun', txt: 'Rulni o‘ngga to‘liq burib orqaga sekin yuring (45°).' },
        { x: 132, y: 82, rot: 0, wheel: '0° to‘g‘ri', mirror: 'Chap ko‘zgu', txt: 'Chiziq ko‘ringach rulni tekislang va chuqurroq kiring.' },
        { x: 120, y: 92, rot: 0, wheel: '-360° ←', mirror: 'Old bamper', txt: 'Rulni chapga burib old qismni to‘g‘rilab to‘xtang.' }
      ]
    },
    garage: {
      title: { uz_latn: 'Garaj (Boksga orqaga kirish)', uz_cyrl: 'Гараж (Боксга орқага кириш)', ru: 'Гараж (Заезд задним ходом)' },
      rule: {
        uz_latn: '90° burchak ostida boks chegarasini bosmasdan markazga joylashing.',
        uz_cyrl: '90° бурчак остида бокс чегарасини босмасдан жойлашинг.',
        ru: 'Заезд под углом 90° задним ходом строго по центру бокса.'
      },
      steps: [
        { x: 64, y: 28, rot: 0, wheel: '0°', mirror: 'Chap va O‘ng', txt: 'Boks oldidan 1.2 m chaproqda to‘xtang.' },
        { x: 108, y: 42, rot: -48, wheel: '-360° ←', mirror: 'O‘ng burchak', txt: 'Rulni burib boks kirish qismiga yo‘naltiring.' },
        { x: 130, y: 74, rot: -86, wheel: '0° to‘g‘ri', mirror: 'Ikkala ko‘zgu', txt: 'Ikkala yonda parallel bo‘lgach g‘ildirakni tekislang.' },
        { x: 130, y: 104, rot: -90, wheel: 'N / P', mirror: 'Orqa oyna', txt: 'Old g‘ildiraklar chiziqdan o‘tgach to‘liq to‘xtang.' }
      ]
    },
    hill: {
      title: { uz_latn: 'Estakada (Balandlik qoidasi)', uz_cyrl: 'Эстакада (Баландлик қоидаси)', ru: 'Эстакада (Подъём в гору)' },
      rule: {
        uz_latn: 'DIQQAT: Ko‘tarilishda to‘xtagandan keyin qayta qo‘zg‘alishda orqaga 30 sm dan ortiq siljish — darhol yiqilish!',
        uz_cyrl: 'ДИҚҚАТ: Қўзғалишда орқага 30 см дан ортиқ силжиш — ЙИҚИЛИШ!',
        ru: 'Откат назад более чем на 30 см на подъёме — немедленный незачет!'
      },
      steps: [
        { x: 45, y: 80, rot: 0, wheel: '1-uzatma', mirror: 'Old to‘xtash chizig‘i', txt: 'Nishablikka chiqib to‘xtash chizig‘ida to‘xtang.' },
        { x: 115, y: 80, rot: -8, wheel: 'Ruchnik ↑', mirror: 'Stopline', txt: 'Qo‘l tormozini torting va oyog‘ingizni tormozdan oling.' },
        { x: 155, y: 80, rot: -8, wheel: 'Ilashma nuqtasi', mirror: 'Taxometr 2000', txt: 'Gazni 2000 ob/min berib muftani tutish nuqtasida ushlang.' },
        { x: 215, y: 80, rot: 0, wheel: 'Ruchnik ↓', mirror: 'Orqaga siljimaslik', txt: 'Kaput ko‘tarilgach ruchnikni tushiring — 0 sm siljish!' }
      ]
    },
    snake: {
      title: { uz_latn: 'Ilon izi (Zmeyka)', uz_cyrl: 'Илон изи (Змейка)', ru: 'Змейка' },
      rule: {
        uz_latn: 'Belgilangan koridor chizig‘ini kesmasdan silliq chap-o‘ng manevr bajaring.',
        uz_cyrl: 'Коридор чизиғини кесмасдан силлиқ маневр бажаринг.',
        ru: 'Плавное прохождение S-образного коридора без наезда на разметку.'
      },
      steps: [
        { x: 35, y: 82, rot: 0, wheel: '0°', mirror: 'Chap chet', txt: 'Koridorga o‘rta-o‘ngdan silliq kiring.' },
        { x: 96, y: 42, rot: -24, wheel: '-270° ←', mirror: 'Old chap', txt: 'Birinchi burilishdan oldin rulni chapga silliq buring.' },
        { x: 168, y: 102, rot: 28, wheel: '+300° →', mirror: 'O‘ng g‘ildirak', txt: 'Markazda tekislab, ikkinchi yoyda o‘ngga yo‘naltiring.' },
        { x: 235, y: 74, rot: 0, wheel: '0°', mirror: 'Chiqish chizig‘i', txt: 'Chiqishda avtomobilni to‘g‘rilab yakunlang.' }
      ]
    }
  };

  const PENALTY_ITEMS = [
    { id: 'belt', pts: 100, title: 'Xavfsizlik kamarisiz harakatlanish / Svetofor qizil', note: 'Avtomatik chetlatish (-100)' },
    { id: 'ped', pts: 100, title: 'Piyodaga yo‘l bermaslik', note: 'Qo‘pol xato (-100)' },
    { id: 'rollback', pts: 100, title: 'Estakadada 30 sm dan ko‘p orqaga siljish', note: 'Avtomatik chetlatish (-100)' },
    { id: 'turn_signal', pts: 15, title: 'Burilish chirog‘ini (pavorotnik) yoqmaslik', note: '-15 ball' },
    { id: 'stall', pts: 10, title: 'Dvigatelni o‘chirib qo‘yish (gloxnut)', note: '-10 ball' },
    { id: 'line_touch', pts: 20, title: 'Avtodrom cheklov chizig‘iga tegish', note: '-20 ball' },
    { id: 'mirror', pts: 10, title: 'Ko‘zgularni tekshirmasdan harakatlanish', note: '-10 ball' }
  ];

  R.loadAmaliyData = async function () {
    if (R.state.isGuest) return;
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

  function renderSimulatorTab(container) {
    const m = SIM_MANEUVERS[simKey] || SIM_MANEUVERS.parallel;
    const st = m.steps[Math.min(simStep, m.steps.length - 1)];
    const lang = R.state.lang || 'uz_latn';
    const mTitle = (m.title && (m.title[lang] || m.title.uz_latn)) || simKey;
    const mRule = (m.rule && (m.rule[lang] || m.rule.uz_latn)) || '';

    let trackExtras = '';
    if (simKey === 'parallel') {
      trackExtras = '<rect x="96" y="70" width="90" height="44" rx="6" fill="rgba(16,185,129,0.14)" stroke="#10B981" stroke-dasharray="5 3" stroke-width="2"/>' +
        '<rect x="30" y="76" width="54" height="28" rx="5" fill="#475569" opacity="0.6"/><rect x="198" y="76" width="54" height="28" rx="5" fill="#475569" opacity="0.6"/>';
    } else if (simKey === 'garage') {
      trackExtras = '<rect x="104" y="62" width="52" height="68" rx="6" fill="rgba(16,185,129,0.14)" stroke="#10B981" stroke-dasharray="5 3" stroke-width="2"/>';
    } else if (simKey === 'hill') {
      trackExtras = '<path d="M20 112 L100 112 L175 68 L260 68" fill="none" stroke="#F59E01" stroke-width="5"/><line x1="145" y1="54" x2="145" y2="96" stroke="#EF4444" stroke-width="3" stroke-dasharray="4 3"/>';
    } else {
      trackExtras = '<path d="M25 90 Q85 15 140 80 T250 72" fill="none" stroke="rgba(59,130,246,0.45)" stroke-width="32" stroke-linecap="round"/>';
    }

    container.innerHTML =
      '<div class="filter-chip-row" style="margin-bottom:10px;">' +
      Object.keys(SIM_MANEUVERS).map(function (k) {
        const it = SIM_MANEUVERS[k];
        const lbl = (it.title && (it.title[lang] || it.title.uz_latn)) || k;
        return '<button type="button" class="filter-chip ' + (simKey === k ? 'active' : '') + '" data-sim-key="' + k + '">' + R.escHtml(lbl) + '</button>';
      }).join('') +
      '</div>' +
      '<div class="surface-card">' +
      '  <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">' +
      '    <strong>' + R.escHtml(mTitle) + '</strong>' +
      '    <span class="badge-pill badge-primary font-mono">' + R.escHtml(R.t('amaliy_sim_step', { cur: simStep + 1, total: m.steps.length })) + '</span>' +
      '  </div>' +
      '  <div class="avtodrom-stage">' +
      '    <svg viewBox="0 0 280 140" class="avtodrom-svg" role="img" aria-label="Avtodrom maneuver diagram">' +
      '      <rect x="0" y="0" width="280" height="140" rx="12" fill="#0F172A"/>' +
      '      <line x1="12" y1="50" x2="268" y2="50" stroke="rgba(255,255,255,0.16)" stroke-dasharray="6 6" stroke-width="1.5"/>' +
      trackExtras +
      '      <g transform="translate(' + st.x + ',' + st.y + ') rotate(' + st.rot + ')" style="transition:transform 0.35s ease;">' +
      '        <rect x="-22" y="-12" width="44" height="24" rx="5" fill="#3B82F6" stroke="#FFFFFF" stroke-width="1.8"/>' +
      '        <rect x="6" y="-9" width="10" height="18" rx="2" fill="#BAE6FD"/>' +
      '        <circle cx="-13" cy="-12" r="2.5" fill="#FACC15"/><circle cx="-13" cy="12" r="2.5" fill="#FACC15"/>' +
      '      </g>' +
      '    </svg>' +
      '  </div>' +
      '  <div style="display:flex;gap:8px;flex-wrap:wrap;margin:10px 0;">' +
      '    <span class="badge-pill badge-emerald font-mono">Rul: ' + R.escHtml(st.wheel) + '</span>' +
      '    <span class="badge-pill badge-amber">' + R.escHtml(st.mirror) + '</span>' +
      '  </div>' +
      '  <p style="font-size:13.5px;font-weight:600;margin-bottom:6px;">' + R.escHtml(st.txt) + '</p>' +
      '  <p style="font-size:12px;color:var(--text-secondary);margin-bottom:12px;">' + R.escHtml(mRule) + '</p>' +
      '  <div style="display:flex;justify-content:space-between;gap:8px;">' +
      '    <button type="button" class="btn btn-sm btn-secondary" id="sim-prev-btn"' + (simStep <= 0 ? ' disabled' : '') + '>' + R.escHtml(R.t('btn_prev')) + '</button>' +
      '    <button type="button" class="btn btn-sm btn-ghost" id="sim-reset-btn">' + R.escHtml(R.t('amaliy_sim_reset')) + '</button>' +
      '    <button type="button" class="btn btn-sm btn-primary" id="sim-next-btn"' + (simStep >= m.steps.length - 1 ? ' disabled' : '') + '>' + R.escHtml(R.t('btn_next')) + '</button>' +
      '  </div>' +
      '</div>';

    container.querySelectorAll('[data-sim-key]').forEach(function (btn) {
      btn.addEventListener('click', function () { simKey = btn.dataset.simKey; simStep = 0; renderSimulatorTab(container); });
    });
    document.getElementById('sim-prev-btn')?.addEventListener('click', function () { if (simStep > 0) { simStep -= 1; renderSimulatorTab(container); } });
    document.getElementById('sim-next-btn')?.addEventListener('click', function () { if (simStep < m.steps.length - 1) { simStep += 1; renderSimulatorTab(container); } });
    document.getElementById('sim-reset-btn')?.addEventListener('click', function () { simStep = 0; renderSimulatorTab(container); });
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
    const defaultTab = R.state.isGuest ? 'simulator' : 'modules';
    const sub = R.state.amaliySubtab || defaultTab;

    root.innerHTML =
      '<div style="margin-bottom:12px;">' +
      '  <h2 style="font-family:var(--font-display);font-size:18px;font-weight:800;">' + R.escHtml(R.t('amaliy_title')) + '</h2>' +
      '  <p style="font-size:12.5px;color:var(--text-secondary);">' + R.escHtml(R.t('amaliy_subtitle')) + '</p>' +
      '</div>' +
      '<div class="subtab-bar subtab-bar-scroll">' +
      '  <button type="button" class="subtab-btn ' + (sub === 'modules' ? 'active' : '') + '" data-am-tab="modules">' + R.escHtml(R.t('tab_modules')) + '</button>' +
      '  <button type="button" class="subtab-btn ' + (sub === 'simulator' ? 'active' : '') + '" data-am-tab="simulator">' + R.escHtml(R.t('amaliy_sim_tab')) + '</button>' +
      '  <button type="button" class="subtab-btn ' + (sub === 'penalty' ? 'active' : '') + '" data-am-tab="penalty">' + R.escHtml(R.t('amaliy_penalty_tab')) + '</button>' +
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
    if (sub === 'simulator') renderSimulatorTab(body);
    else if (sub === 'penalty') renderPenaltyTab(body);
    else if (R.state.isGuest) renderSimulatorTab(body);
    else if (sub === 'modules') renderModulesTab(body);
    else if (sub === 'checklist') renderChecklistTab(body);
    else renderScenariosTab(body);
  };
})();
