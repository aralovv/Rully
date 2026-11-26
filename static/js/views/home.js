/**
 * RULLY 2.0 Home Dashboard View (Readiness Gauge, Daily Goal, Smart Next Action & Bento Grid)
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});

  function gradeMeta(grade, score) {
    if (grade === 'EXCELLENT' || score >= 85) {
      return {
        label: R.t('grade_excellent'),
        sub: R.t('readiness_subtext_ready'),
        stroke: '#10B981',
        badgeClass: 'badge-emerald'
      };
    }
    if (grade === 'EXAM_READY' || score >= 75) {
      return {
        label: R.t('grade_ready'),
        sub: R.t('readiness_subtext_ready'),
        stroke: '#10B981',
        badgeClass: 'badge-emerald'
      };
    }
    if (grade === 'IN_PROGRESS' || score >= 45) {
      return {
        label: R.t('grade_progress'),
        sub: R.t('readiness_subtext_progress'),
        stroke: '#F59E0B',
        badgeClass: 'badge-amber'
      };
    }
    return {
      label: R.t('grade_not_ready'),
      sub: R.t('readiness_subtext_start'),
      stroke: 'var(--color-primary)',
      badgeClass: 'badge-primary'
    };
  }

  R.openReadinessModal = function () {
    const stats = R.state.stats || {};
    const pillars = stats.readiness_pillars || {};
    const score = Number(stats.readiness_score || 0);
    const totalAns = Number(stats.total_questions_answered || 0);
    const meta = gradeMeta(stats.readiness_grade, score);

    const rows = [
      { title: R.t('pillar_exam_title'), desc: R.t('pillar_exam_desc'), val: pillars.exam_mastery || 0, weight: '30%' },
      { title: R.t('pillar_acc_title'), desc: R.t('pillar_acc_desc'), val: pillars.accuracy || 0, weight: '25%', warmup: totalAns < 35 ? R.t('pillar_acc_warmup_hint') : '' },
      { title: R.t('pillar_cov_title'), desc: R.t('pillar_cov_desc'), val: pillars.coverage || 0, weight: '25%' },
      { title: R.t('pillar_err_title'), desc: R.t('pillar_err_desc'), val: pillars.mistake_hygiene || 0, weight: '10%' },
      { title: R.t('pillar_streak_title'), desc: R.t('pillar_streak_desc'), val: pillars.pace_and_streak || 0, weight: '10%' }
    ];

    const body = document.getElementById('readiness-modal-body');
    if (!body) return;
    body.innerHTML =
      '<div class="surface-card" style="display:flex;align-items:center;justify-content:space-between;gap:12px;">' +
      '  <div>' +
      '    <span class="badge-pill ' + meta.badgeClass + '">' + R.escHtml(meta.label) + '</span>' +
      '    <p style="font-size:12.5px;color:var(--text-secondary);margin-top:6px;">' + R.escHtml(meta.sub) + '</p>' +
      '  </div>' +
      '  <div class="font-mono" style="font-size:28px;font-weight:800;">' + score.toFixed(1) + '%</div>' +
      '</div>' +
      '<div class="list-stack">' +
      rows.map(function (r) {
        const pct = Math.max(0, Math.min(100, Number(r.val || 0)));
        const barCls = pct >= 75 ? 'emerald' : (pct >= 45 ? 'amber' : '');
        return '<div class="surface-card" style="padding:12px 14px;">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:4px;">' +
          '  <strong style="font-size:13.5px;">' + R.escHtml(r.title) + '</strong>' +
          '  <span class="badge-pill badge-neutral font-mono">' + pct.toFixed(0) + '% • ' + r.weight + '</span>' +
          '</div>' +
          '<p style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;">' + R.escHtml(r.desc) + '</p>' +
          '<div class="progress-track"><div class="progress-fill ' + barCls + '" style="width:' + pct + '%"></div></div>' +
          (r.warmup ? '<p style="font-size:11.5px;color:var(--color-amber);margin-top:7px;font-weight:600;">' + R.icon('alertTriangle', 'xs') + ' ' + R.escHtml(r.warmup) + '</p>' : '') +
          '</div>';
      }).join('') +
      '</div>' +
      '<button type="button" class="btn btn-primary btn-block" id="btn-readiness-dismiss">' + R.escHtml(R.t('btn_modal_dismiss')) + '</button>';

    const disBtn = document.getElementById('btn-readiness-dismiss');
    if (disBtn) disBtn.addEventListener('click', function () { R.closeModal('readiness-diagnostic-modal'); });
    R.openModal('readiness-diagnostic-modal');
  };

  R.openDailyGoalModal = function () {
    const currentGoal = Number((R.state.streak && R.state.streak.daily_goal_questions) || 20);
    const body = document.getElementById('daily-goal-modal-body');
    if (!body) return;

    const presets = [10, 20, 30, 50];
    body.innerHTML =
      '<p style="font-size:13px;color:var(--text-secondary);">' + R.escHtml(R.t('daily_goal_customize')) + '</p>' +
      '<div class="seg-pills">' +
      presets.map(function (g) {
        return '<button type="button" class="seg-pill ' + (currentGoal === g ? 'active' : '') + '" data-goal-val="' + g + '">' + g + ' ' + R.escHtml(R.t('ticket_questions_badge', { n: '' }).trim()) + '</button>';
      }).join('') +
      '</div>';

    body.querySelectorAll('[data-goal-val]').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        const val = Number(btn.dataset.goalVal);
        try {
          R.haptic('light');
          const res = await R.api('/api/user/daily-goal', { method: 'POST', body: { daily_goal: val } });
          R.state.streak.daily_goal_questions = res.daily_goal_questions || val;
          R.closeModal('daily-goal-modal');
          R.showToast(R.t('daily_goal_label') + ': ' + R.state.streak.daily_goal_questions);
          R.renderHome();
          R.syncShellUI();
        } catch (err) {
          R.showToast(err.message || R.t('ai_generic_error'));
        }
      });
    });

    R.openModal('daily-goal-modal');
  };

  R.renderHome = function () {
    const root = document.getElementById('view-home');
    if (!root) return;

    if (R.state.authPending && !R.state.stats) {
      root.innerHTML =
        '<div class="home-bento-top">' +
        '  <div class="surface-card skeleton-block" style="height:210px;"></div>' +
        '  <div class="surface-card skeleton-block" style="height:210px;"></div>' +
        '</div>' +
        '<div class="kpi-strip">' +
        '  <div class="skeleton-block" style="height:76px;"></div>' +
        '  <div class="skeleton-block" style="height:76px;"></div>' +
        '  <div class="skeleton-block" style="height:76px;"></div>' +
        '  <div class="skeleton-block" style="height:76px;"></div>' +
        '</div>';
      return;
    }

    const stats = R.state.stats || {};
    const streak = R.state.streak || { current_streak: 1, daily_goal_questions: 20, today_questions_count: 0 };
    const sub = R.state.subscription || {};
    const ft = R.state.freeTier || {};
    const analytics = R.state.analytics || {};
    const score = Number(stats.readiness_score || 0);
    const pillars = stats.readiness_pillars || {};
    const meta = gradeMeta(stats.readiness_grade, score);

    // Semi-circle circumference r=54 -> pi * r ~= 169.6
    const arcLen = 169.65;
    const dashOffset = arcLen - (Math.max(0, Math.min(100, score)) / 100) * arcLen;

    const todayDone = Number(streak.today_questions_count || 0);
    const goalTarget = Math.max(5, Number(streak.daily_goal_questions || 20));
    const goalPct = Math.min(100, Math.round((todayDone / goalTarget) * 100));

    // Smart Next Action from /api/learning/analytics
    const rec = analytics.recommendation || { kind: 'adaptive_starter', target_type: 'ADAPTIVE' };
    let recTitle = R.t('rec_adaptive_title');
    let recDesc = R.t('rec_adaptive_desc', { n: analytics.overall_coverage_pct || 0 });
    if (rec.kind === 'mistake_drill') {
      recTitle = R.t('rec_mistake_drill_title');
      recDesc = R.t('rec_mistake_drill_desc', { n: rec.metric || stats.unresolved_mistakes || 0 });
    } else if (rec.kind === 'weak_topic') {
      recTitle = R.t('rec_weak_topic_title');
      recDesc = R.t('rec_weak_topic_desc', { topic: rec.topic_name || '', n: rec.metric || 0 });
    } else if (rec.kind === 'official_exam') {
      recTitle = R.t('rec_official_exam_title');
      recDesc = R.t('rec_official_exam_desc');
    }

    const freeExamsChip = sub.is_pro
      ? '<span class="badge-pill" style="background:rgba(255,255,255,0.2);color:#fff;">PRO</span>'
      : '<span class="badge-pill" style="background:rgba(255,255,255,0.2);color:#fff;">' + R.escHtml((ft.remaining_exams || 0) + ' / ' + (ft.allowed_exams || 2) + ' bepul') + '</span>';

    const mistakesBadge = (stats.unresolved_mistakes || 0) > 0
      ? '<span class="badge-pill badge-rose font-mono">' + stats.unresolved_mistakes + '</span>'
      : '<span class="badge-pill badge-emerald">0</span>';

    root.innerHTML =
      '<div class="home-bento-top">' +
      '  <section class="surface-card readiness-hero">' +
      '    <div class="readiness-top-row">' +
      '      <span class="badge-pill ' + meta.badgeClass + '">' + R.icon('gauge', 'xs') + ' ' + R.escHtml(R.t('cluster_heading')) + '</span>' +
      '      <button type="button" class="btn btn-sm btn-secondary" id="home-diag-btn">' + R.escHtml(R.t('readiness_diagnostic_btn')) + '</button>' +
      '    </div>' +
      '    <div class="readiness-gauge-row">' +
      '      <div class="gauge-box">' +
      '        <svg class="gauge-svg" viewBox="0 0 132 82" aria-hidden="true">' +
      '          <path class="gauge-track" d="M 12 72 A 54 54 0 0 1 120 72" />' +
      '          <path class="gauge-arc" d="M 12 72 A 54 54 0 0 1 120 72" style="stroke:' + meta.stroke + ';stroke-dasharray:' + arcLen + ';stroke-dashoffset:' + dashOffset.toFixed(1) + ';" />' +
      '        </svg>' +
      '        <div class="gauge-center-val">' +
      '          <div class="gauge-pct font-mono">' + Math.round(score) + '%</div>' +
      '          <div class="gauge-lbl">' + R.escHtml(R.t('speedometer_lbl')) + '</div>' +
      '        </div>' +
      '      </div>' +
      '      <div class="readiness-info-col">' +
      '        <div class="readiness-grade-title">' + R.escHtml(meta.label) + '</div>' +
      '        <p class="readiness-sub-copy">' + R.escHtml(meta.sub) + '</p>' +
      '      </div>' +
      '    </div>' +
      '    <div class="pillars-mini-grid">' +
      '      <div class="pillar-mini-cell"><div class="pillar-mini-val">' + Math.round(pillars.exam_mastery || 0) + '%</div><div class="pillar-mini-name">' + R.escHtml(R.t('pillar_exam')) + '</div></div>' +
      '      <div class="pillar-mini-cell"><div class="pillar-mini-val">' + Math.round(pillars.accuracy || 0) + '%</div><div class="pillar-mini-name">' + R.escHtml(R.t('pillar_acc')) + '</div></div>' +
      '      <div class="pillar-mini-cell"><div class="pillar-mini-val">' + Math.round(pillars.coverage || 0) + '%</div><div class="pillar-mini-name">' + R.escHtml(R.t('pillar_cov')) + '</div></div>' +
      '      <div class="pillar-mini-cell"><div class="pillar-mini-val">' + Math.round(pillars.mistake_hygiene || 0) + '%</div><div class="pillar-mini-name">' + R.escHtml(R.t('pillar_err')) + '</div></div>' +
      '      <div class="pillar-mini-cell"><div class="pillar-mini-val">' + Math.round(pillars.pace_and_streak || 0) + '%</div><div class="pillar-mini-name">' + R.escHtml(R.t('pillar_streak')) + '</div></div>' +
      '    </div>' +
      '  </section>' +

      '  <div class="home-right-stack">' +
      '    <section class="exam-launch-card">' +
      '      <div class="exam-launch-top">' +
      '        <div>' +
      '          <div class="exam-launch-title">' + R.escHtml(R.t('hero_title')) + '</div>' +
      '          <div class="exam-launch-desc">' + R.escHtml(R.t('hero_desc')) + '</div>' +
      '        </div>' +
      freeExamsChip +
      '      </div>' +
      '      <button type="button" class="btn btn-exam-light btn-block" id="home-start-exam-btn">' +
      R.icon('zap', 'sm') + '<span>' + R.escHtml(R.t('btn_start_exam')) + '</span>' +
      '      </button>' +
      '    </section>' +

      '    <div class="surface-card card-interactive daily-goal-card" id="home-daily-goal-card" role="button" tabindex="0">' +
      '      <div class="daily-goal-left">' +
      '        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">' +
      '          <strong style="font-size:13.5px;">' + R.escHtml(R.t('daily_goal_label')) + '</strong>' +
      '          <span class="font-mono" style="font-size:12.5px;font-weight:700;color:var(--color-primary);">' + R.escHtml(R.t('daily_goal_progress', { done: todayDone, goal: goalTarget })) + '</span>' +
      '        </div>' +
      '        <div class="progress-track"><div class="progress-fill ' + (goalPct >= 100 ? 'emerald' : '') + '" style="width:' + goalPct + '%"></div></div>' +
      '        <div style="display:flex;align-items:center;justify-content:space-between;font-size:11.5px;color:var(--text-muted);margin-top:2px;">' +
      '          <span>' + R.icon('flame', 'xs') + ' ' + R.escHtml(R.t('streak_badge', { days: streak.current_streak || 1 })) + '</span>' +
      '          <span>' + (goalPct >= 100 ? R.escHtml(R.t('daily_goal_done_badge')) : goalPct + '%') + '</span>' +
      '        </div>' +
      '      </div>' +
      '    </div>' +
      '  </div>' +
      '</div>' +

      '<div class="smart-rec-banner">' +
      '  <div class="smart-rec-left">' +
      '    <div class="smart-rec-icon">' + R.icon('target', 'lg') + '</div>' +
      '    <div style="min-width:0;">' +
      '      <div style="font-weight:700;font-size:14px;">' + R.escHtml(recTitle) + '</div>' +
      '      <div style="font-size:12px;color:var(--text-secondary);">' + R.escHtml(recDesc) + '</div>' +
      '    </div>' +
      '  </div>' +
      '  <button type="button" class="btn btn-primary btn-sm" id="home-smart-rec-btn">' + R.escHtml(R.t('btn_start_category')) + ' ' + R.icon('arrowRight', 'xs') + '</button>' +
      '</div>' +

      '<div class="kpi-strip">' +
      '  <div class="kpi-tile"><span class="kpi-value font-mono">' + Number(stats.pass_rate || 0).toFixed(0) + '%</span><span class="kpi-label">' + R.escHtml(R.t('stat_pass_rate')) + '</span></div>' +
      '  <div class="kpi-tile"><span class="kpi-value font-mono">' + Number(stats.total_exams || 0) + '</span><span class="kpi-label">' + R.escHtml(R.t('stat_tests_taken')) + '</span></div>' +
      '  <div class="kpi-tile"><span class="kpi-value font-mono">' + Number(stats.accuracy || 0).toFixed(0) + '%</span><span class="kpi-label">' + R.escHtml(R.t('stat_accuracy')) + '</span></div>' +
      '  <div class="kpi-tile"><span class="kpi-value font-mono">' + Number(R.state.bookmarksCount || 0) + '</span><span class="kpi-label">' + R.escHtml(R.t('stat_bookmarks')) + '</span></div>' +
      '</div>' +

      '<div class="section-heading"><span>' + R.escHtml(R.t('section_quick_start')) + '</span></div>' +
      '<div class="bento-action-grid">' +
      '  <button type="button" class="surface-card card-interactive action-tile" id="tile-tickets">' +
      '    <div class="tile-icon-box badge-primary">' + R.icon('grid', 'lg') + '</div>' +
      '    <div class="tile-body"><div class="tile-title">' + R.escHtml(R.t('tab_tickets')) + '</div><div class="tile-desc">' + R.escHtml(R.t('tickets_header_title')) + '</div></div>' +
      '  </button>' +
      '  <button type="button" class="surface-card card-interactive action-tile" id="tile-categories">' +
      '    <div class="tile-icon-box badge-emerald">' + R.icon('layers', 'lg') + '</div>' +
      '    <div class="tile-body"><div class="tile-title">' + R.escHtml(R.t('card_categories_title')) + '</div><div class="tile-desc">' + R.escHtml(R.t('card_categories_desc')) + '</div></div>' +
      '  </button>' +
      '  <button type="button" class="surface-card card-interactive action-tile" id="tile-mistakes">' +
      '    <div class="tile-icon-box badge-rose">' + R.icon('alertTriangle', 'lg') + '</div>' +
      '    <div class="tile-body"><div class="tile-title"><span>' + R.escHtml(R.t('card_mistakes_title')) + '</span> ' + mistakesBadge + '</div><div class="tile-desc">' + R.escHtml(R.t('card_mistakes_desc')) + '</div></div>' +
      '  </button>' +
      '  <button type="button" class="surface-card card-interactive action-tile" id="tile-adaptive">' +
      '    <div class="tile-icon-box" style="background:var(--color-indigo-soft);color:var(--color-indigo);">' + R.icon('sliders', 'lg') + '</div>' +
      '    <div class="tile-body"><div class="tile-title">' + R.escHtml(R.t('adaptive_title')) + '</div><div class="tile-desc">' + R.escHtml(R.t('custom_quiz_card_desc')) + '</div></div>' +
      '  </button>' +
      '  <button type="button" class="surface-card card-interactive action-tile" id="tile-amaliy">' +
      '    <div class="tile-icon-box badge-amber">' + R.icon('steeringWheel', 'lg') + '</div>' +
      '    <div class="tile-body"><div class="tile-title">' + R.escHtml(R.t('card_amaliy_title')) + '</div><div class="tile-desc">' + R.escHtml(R.t('card_amaliy_desc')) + '</div></div>' +
      '  </button>' +
      '  <button type="button" class="surface-card card-interactive action-tile" id="tile-cheatsheet">' +
      '    <div class="tile-icon-box badge-neutral">' + R.icon('lightbulb', 'lg') + '</div>' +
      '    <div class="tile-body"><div class="tile-title">' + R.escHtml(R.t('card_cheatsheet_title')) + (!sub.is_pro ? ' <span class="badge-pill badge-amber">PRO</span>' : '') + '</div><div class="tile-desc">' + R.escHtml(R.t('card_cheatsheet_desc')) + '</div></div>' +
      '  </button>' +
      '</div>';

    // Bind events
    const diagBtn = document.getElementById('home-diag-btn');
    if (diagBtn) diagBtn.addEventListener('click', R.openReadinessModal);

    const examBtn = document.getElementById('home-start-exam-btn');
    if (examBtn) examBtn.addEventListener('click', function () { R.startSession({ session_type: 'EXAM' }); });

    const goalCard = document.getElementById('home-daily-goal-card');
    if (goalCard) {
      goalCard.addEventListener('click', R.openDailyGoalModal);
      goalCard.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); R.openDailyGoalModal(); }
      });
    }

    const smartBtn = document.getElementById('home-smart-rec-btn');
    if (smartBtn) {
      smartBtn.addEventListener('click', function () {
        if (rec.target_type === 'MISTAKES') {
          R.startSession({ session_type: 'MISTAKES', total_questions: 30 });
        } else if (rec.target_type === 'CATEGORY' && rec.target_id !== undefined) {
          R.startSession({ session_type: 'CATEGORY', category_id: rec.target_id, total_questions: 20 });
        } else if (rec.target_type === 'EXAM') {
          R.startSession({ session_type: 'EXAM' });
        } else {
          R.startSession({ session_type: 'ADAPTIVE', total_questions: 20 });
        }
      });
    }

    document.getElementById('tile-tickets')?.addEventListener('click', function () {
      R.state.prepareSubtab = 'tickets';
      R.navigateTo('tests');
    });
    document.getElementById('tile-categories')?.addEventListener('click', function () {
      R.state.prepareSubtab = 'topics';
      R.navigateTo('tests');
    });
    document.getElementById('tile-mistakes')?.addEventListener('click', function () {
      if ((stats.unresolved_mistakes || 0) <= 0) {
        R.showToast(R.t('mistakes_zero_title'));
        return;
      }
      R.startSession({ session_type: 'MISTAKES', total_questions: 30 });
    });
    document.getElementById('tile-adaptive')?.addEventListener('click', function () {
      R.state.prepareSubtab = 'adaptive';
      R.navigateTo('tests');
    });
    document.getElementById('tile-amaliy')?.addEventListener('click', function () {
      R.navigateTo('amaliy');
    });
    document.getElementById('tile-cheatsheet')?.addEventListener('click', function () {
      R.openCheatsheetModal();
    });
  };
})();
