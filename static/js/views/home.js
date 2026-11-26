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
        stroke: 'var(--color-emerald-bright)',
        glow: 'rgba(16, 185, 129, 0.28)',
        badgeClass: 'badge-emerald'
      };
    }
    if (grade === 'EXAM_READY' || score >= 75) {
      return {
        label: R.t('grade_ready'),
        sub: R.t('readiness_subtext_ready'),
        stroke: 'var(--color-emerald-bright)',
        glow: 'rgba(16, 185, 129, 0.24)',
        badgeClass: 'badge-emerald'
      };
    }
    if (grade === 'IN_PROGRESS' || score >= 45) {
      return {
        label: R.t('grade_progress'),
        sub: R.t('readiness_subtext_progress'),
        stroke: 'var(--color-amber-bright)',
        glow: 'rgba(245, 158, 11, 0.24)',
        badgeClass: 'badge-amber'
      };
    }
    return {
      label: R.t('grade_not_ready'),
      sub: R.t('readiness_subtext_start'),
      stroke: 'var(--color-primary)',
      glow: 'rgba(0, 102, 255, 0.24)',
      badgeClass: 'badge-primary'
    };
  }

  function buildCockpitTicks(clampedScore) {
    const cx = 90;
    const cy = 90;
    let out = '';
    for (let i = 0; i <= 20; i++) {
      const pctStep = i * 5;
      const degScreen = -210 + (i / 20) * 240;
      const rad = (degScreen * Math.PI) / 180;
      const isMajor = i % 2 === 0;
      const rOuter = 60;
      const rInner = isMajor ? 52.5 : 55.5;
      const x1 = (cx + rInner * Math.cos(rad)).toFixed(2);
      const y1 = (cy + rInner * Math.sin(rad)).toFixed(2);
      const x2 = (cx + rOuter * Math.cos(rad)).toFixed(2);
      const y2 = (cy + rOuter * Math.sin(rad)).toFixed(2);
      const cls = 'cockpit-tick' + (isMajor ? ' major' : ' minor') + (clampedScore > 0 && pctStep <= clampedScore ? ' lit' : '');
      out += '<line class="' + cls + '" x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '" />';
    }
    return out;
  }

  R.openReadinessModal = function () {
    const stats = R.state.stats || {};
    const pillars = stats.readiness_pillars || {};
    const score = Number(stats.readiness_score || 0);
    const totalAns = Number(stats.total_questions_answered || 0);
    const meta = gradeMeta(stats.readiness_grade, score);
    const srs = stats.srs_summary || (R.state.analytics && R.state.analytics.srs_summary) || null;

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
      (srs && srs.tracked_count > 0
        ? '<div class="surface-card" style="padding:12px 14px;border-color:var(--color-primary-border);">' +
          '  <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px;">' +
          '    <strong style="font-size:13.5px;">' + R.escHtml(R.t('srs_mode_title')) + '</strong>' +
          '    <span class="badge-pill badge-primary font-mono">' + Number(srs.retention_rate || 100).toFixed(0) + '% • EF ' + Number(srs.avg_ease_factor || 2.5).toFixed(2) + '</span>' +
          '  </div>' +
          '  <div style="display:flex;gap:8px;flex-wrap:wrap;font-size:12px;color:var(--text-secondary);">' +
          '    <span>' + R.escHtml(R.t('srs_due_now_lbl')) + ': <b>' + (srs.due_now_count || 0) + '</b></span>' +
          '    <span>• ' + R.escHtml(R.t('srs_mastered_lbl')) + ': <b>' + (srs.mastered_count || 0) + '</b></span>' +
          '    <span>• ' + R.escHtml(R.t('srs_reviewing_lbl')) + ': <b>' + (srs.reviewing_count || 0) + '</b></span>' +
          '  </div>' +
          '</div>'
        : '') +
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

  R.openGuestSyncModal = function () {
    const titleEl = document.getElementById('info-modal-title');
    const bodyEl = document.getElementById('info-modal-body');
    if (!bodyEl) return;
    if (titleEl) titleEl.textContent = R.t('web_gate_title');
    bodyEl.innerHTML =
      '<div class="surface-card" style="text-align:center;">' +
      '  <div class="brand-mark" style="width:48px;height:48px;font-size:22px;margin:0 auto 12px;">R</div>' +
      '  <p style="font-size:13.5px;color:var(--text-secondary);margin-bottom:16px;">' + R.escHtml(R.t('web_gate_desc')) + '</p>' +
      '  <a href="https://t.me/rully_uz_bot" target="_blank" rel="noopener" class="btn btn-primary btn-block">' +
      R.icon('telegram', 'sm') + '<span>' + R.escHtml(R.t('web_gate_btn')) + '</span>' +
      '  </a>' +
      '</div>';
    R.openModal('info-modal');
  };

  R.maybeShowOnboarding = function () {
    try {
      if (localStorage.getItem('rully_onboarded') === '1') return;
    } catch (e) {}
    const stats = R.state.stats || {};
    if (Number(stats.total_questions_answered || 0) > 0) return;

    const body = document.getElementById('onboarding-modal-body');
    if (!body) return;

    function renderOnboardingBody() {
      const curGoal = Number((R.state.streak && R.state.streak.daily_goal_questions) || 20);
      body.innerHTML =
        '<p style="font-size:13px;color:var(--text-secondary);">' + R.escHtml(R.t('onboarding_desc')) + '</p>' +
        '<div>' +
        '  <div style="font-size:12.5px;font-weight:700;margin-bottom:6px;">1. ' + R.escHtml(R.t('language_select_title')) + '</div>' +
        '  <div class="seg-pills" style="grid-template-columns:repeat(3,1fr);">' +
        '    <button type="button" class="seg-pill ' + (R.state.lang === 'uz_latn' ? 'active' : '') + '" data-ob-lang="uz_latn">O‘zbekcha</button>' +
        '    <button type="button" class="seg-pill ' + (R.state.lang === 'uz_cyrl' ? 'active' : '') + '" data-ob-lang="uz_cyrl">Ўзбекча</button>' +
        '    <button type="button" class="seg-pill ' + (R.state.lang === 'ru' ? 'active' : '') + '" data-ob-lang="ru">Русский</button>' +
        '  </div>' +
        '</div>' +
        '<div>' +
        '  <div style="font-size:12.5px;font-weight:700;margin-bottom:6px;">2. ' + R.escHtml(R.t('daily_goal_label')) + '</div>' +
        '  <div class="seg-pills">' +
        [10, 20, 30, 50].map(function (g) {
          return '<button type="button" class="seg-pill ' + (curGoal === g ? 'active' : '') + '" data-ob-goal="' + g + '">' + g + '</button>';
        }).join('') +
        '  </div>' +
        '</div>' +
        '<button type="button" class="btn btn-primary btn-block" id="btn-ob-finish">' + R.escHtml(R.t('btn_start_exam')) + ' →</button>';

      body.querySelectorAll('[data-ob-lang]').forEach(function (btn) {
        btn.addEventListener('click', async function () {
          await R.changeLanguage(btn.dataset.obLang);
          renderOnboardingBody();
        });
      });
      body.querySelectorAll('[data-ob-goal]').forEach(function (btn) {
        btn.addEventListener('click', async function () {
          const g = Number(btn.dataset.obGoal);
          R.state.streak.daily_goal_questions = g;
          try { await R.api('/api/user/daily-goal', { method: 'POST', body: { daily_goal: g } }); } catch (e) {}
          R.syncShellUI();
          renderOnboardingBody();
        });
      });
      document.getElementById('btn-ob-finish')?.addEventListener('click', function () {
        try { localStorage.setItem('rully_onboarded', '1'); } catch (e) {}
        R.closeModal('onboarding-modal');
        R.renderHome();
      });
    }

    renderOnboardingBody();
    R.openModal('onboarding-modal');
  };

  function renderGuestHome(root) {
    const ov = R.state.publicOverview || {};
    const diag = R.state.guestDiag || { questions: [], index: 0, answers: {}, checked: null };
    const qs = diag.questions || [];
    const totalQ = ov.total_questions || 1327;
    let diagWidgetHtml = '';

    if (diag.checked) {
      const res = diag.checked;
      diagWidgetHtml =
        '<div class="surface-card diag-guest-card">' +
        '  <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px;">' +
        '    <strong>' + R.escHtml(R.t('guest_diag_done')) + '</strong>' +
        '    <span class="badge-pill ' + (res.percentage >= 80 ? 'badge-emerald' : 'badge-amber') + ' font-mono">' + res.correct_count + ' / ' + res.total + ' (' + res.percentage + '%)</span>' +
        '  </div>' +
        '  <div class="list-stack" style="margin-bottom:12px;">' +
        (res.items || []).map(function (it, idx) {
          return '<div class="surface-card" style="padding:10px;background:var(--bg-subtle);">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">' +
            '  <span class="font-mono" style="font-weight:700;font-size:12px;">#' + (idx + 1) + ' (' + R.escHtml(it.selected_key) + ' → ' + R.escHtml(it.correct_option_key) + ')</span>' +
            '  <span class="badge-pill ' + (it.is_correct ? 'badge-emerald' : 'badge-rose') + '">' + R.escHtml(it.is_correct ? R.t('correct_badge') : R.t('wrong_badge')) + '</span>' +
            '</div>' +
            (it.explanation ? '<p style="font-size:12px;color:var(--text-secondary);">' + R.escHtml(it.explanation) + '</p>' : '') +
            '</div>';
        }).join('') +
        '  </div>' +
        '  <div style="display:flex;gap:8px;flex-wrap:wrap;">' +
        '    <a href="https://t.me/rully_uz_bot" target="_blank" rel="noopener" class="btn btn-primary" style="flex:1;">' + R.icon('telegram', 'sm') + '<span>' + R.escHtml(R.t('guest_sync_tg')) + '</span></a>' +
        '    <button type="button" class="btn btn-secondary" id="guest-diag-restart">' + R.escHtml(R.t('btn_retake')) + '</button>' +
        '  </div>' +
        '</div>';
    } else if (qs.length && diag.active) {
      const q = qs[Math.min(diag.index, qs.length - 1)];
      const chosen = diag.answers[q.canonical_id];
      const imgUrl = R.safeUrl(q.image_url);
      diagWidgetHtml =
        '<div class="surface-card diag-guest-card">' +
        '  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">' +
        '    <span class="badge-pill badge-primary">' + R.escHtml(R.t('guest_diag_title')) + '</span>' +
        '    <span class="badge-pill badge-neutral font-mono">' + (diag.index + 1) + ' / ' + qs.length + '</span>' +
        '  </div>' +
        (imgUrl ? '<div class="quiz-media-frame" style="margin-bottom:10px;max-height:200px;"><img src="' + R.escHtml(imgUrl) + '" alt="Diagnostika"></div>' : '') +
        '  <p style="font-weight:700;font-size:14.5px;margin-bottom:10px;">' + R.escHtml(q.question_text) + '</p>' +
        '  <div class="options-stack">' +
        (q.options || []).map(function (o) {
          return '<button type="button" class="option-btn ' + (chosen === o.option_key ? 'is-correct' : '') + '" data-gdiag-opt="' + R.escHtml(o.option_key) + '">' +
            '<span class="option-key-badge">' + R.escHtml(o.option_key) + '</span>' +
            '<span class="option-text">' + R.escHtml(o.text) + '</span>' +
            '</button>';
        }).join('') +
        '  </div>' +
        '</div>';
    }

    root.innerHTML =
      '<div class="home-bento-top">' +
      '  <section class="surface-card" style="display:flex;flex-direction:column;justify-content:space-between;gap:12px;">' +
      '    <div>' +
      '      <span class="badge-pill badge-primary" style="margin-bottom:8px;">' + R.icon('sparkles', 'xs') + ' ' + R.escHtml(R.t('guest_hero_badge')) + '</span>' +
      '      <h1 style="font-family:var(--font-display);font-size:20px;font-weight:800;line-height:1.25;">' + R.escHtml(R.t('guest_hero_title')) + '</h1>' +
      '      <p style="font-size:13px;color:var(--text-secondary);margin-top:6px;">' + R.escHtml(R.t('guest_hero_desc')) + '</p>' +
      '    </div>' +
      '    <button type="button" class="btn btn-exam-ignition btn-block" id="guest-start-diag-btn">' + R.icon('zap', 'sm') + '<span>' + R.escHtml(R.t('guest_diag_btn')) + '</span></button>' +
      '  </section>' +
      '  <section class="exam-launch-card">' +
      '    <div class="exam-launch-top">' +
      '      <div>' +
      '        <div class="exam-launch-eyebrow"><span class="cockpit-pulse-dot" aria-hidden="true"></span><span>VMQ 408 / 172</span></div>' +
      '        <div class="exam-launch-title">' + totalQ.toLocaleString() + '+ ' + R.escHtml(R.t('nav_tests')) + '</div>' +
      '      </div>' +
      '      <span class="cockpit-quota-pill">TELEGRAM</span>' +
      '    </div>' +
      '    <p style="font-size:12.5px;color:rgba(255,255,255,0.85);margin-bottom:10px;">' + R.escHtml(R.t('web_gate_desc')) + '</p>' +
      '    <a href="https://t.me/rully_uz_bot" target="_blank" rel="noopener" class="btn btn-emerald btn-block">' + R.icon('telegram', 'sm') + '<span>' + R.escHtml(R.t('guest_sync_tg')) + '</span></a>' +
      '  </section>' +
      '</div>' +
      diagWidgetHtml +
      '<div class="section-heading"><span>' + R.escHtml(R.t('section_quick_start')) + '</span></div>' +
      '<div class="bento-action-grid">' +
      '  <button type="button" class="surface-card card-interactive action-tile" id="guest-tile-signs"><div class="tile-icon-box badge-primary">' + R.icon('compass', 'lg') + '</div><div class="tile-body"><div class="tile-title">' + R.escHtml(R.t('tab_signs')) + '</div><div class="tile-desc">' + R.escHtml(R.t('home_signs_desc')) + '</div></div></button>' +
      '  <button type="button" class="surface-card card-interactive action-tile" id="guest-tile-rules"><div class="tile-icon-box badge-emerald">' + R.icon('bookOpen', 'lg') + '</div><div class="tile-body"><div class="tile-title">' + R.escHtml(R.t('ref_law_title')) + '</div><div class="tile-desc">' + R.escHtml(R.t('home_rules_desc')) + '</div></div></button>' +
      '  <button type="button" class="surface-card card-interactive action-tile" id="guest-tile-amaliy"><div class="tile-icon-box badge-amber">' + R.icon('steeringWheel', 'lg') + '</div><div class="tile-body"><div class="tile-title">' + R.escHtml(R.t('amaliy_sim_tab')) + '</div><div class="tile-desc">' + R.escHtml(R.t('card_amaliy_desc')) + '</div></div></button>' +
      '  <button type="button" class="surface-card card-interactive action-tile" id="guest-tile-topics"><div class="tile-icon-box badge-neutral">' + R.icon('layers', 'lg') + '</div><div class="tile-body"><div class="tile-title">' + R.escHtml(R.t('card_categories_title')) + '</div><div class="tile-desc">' + R.escHtml(R.t('card_categories_desc')) + '</div></div></button>' +
      '</div>';

    document.getElementById('guest-start-diag-btn')?.addEventListener('click', function () {
      R.state.guestDiag = {
        questions: (R.state.publicOverview && R.state.publicOverview.diagnostic_questions) || [],
        index: 0,
        answers: {},
        checked: null,
        active: true
      };
      if (!R.state.guestDiag.questions.length) R.openGuestSyncModal();
      else R.renderHome();
    });

    document.getElementById('guest-diag-restart')?.addEventListener('click', function () {
      R.state.guestDiag = {
        questions: (R.state.publicOverview && R.state.publicOverview.diagnostic_questions) || [],
        index: 0,
        answers: {},
        checked: null,
        active: true
      };
      R.renderHome();
    });

    root.querySelectorAll('[data-gdiag-opt]').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        const q = qs[diag.index];
        if (!q) return;
        diag.answers[q.canonical_id] = btn.dataset.gdiagOpt;
        if (diag.index < qs.length - 1) {
          diag.index += 1;
          R.renderHome();
        } else {
          try {
            const list = Object.keys(diag.answers).map(function (cid) {
              return { canonical_id: cid, selected_key: diag.answers[cid] };
            });
            const checked = await R.api('/api/public/diagnostic/check', {
              method: 'POST',
              body: { language: R.state.lang, answers: list }
            });
            diag.checked = checked;
            diag.active = false;
            R.renderHome();
          } catch (e) { R.showToast(e.message || R.t('ai_net_error')); }
        }
      });
    });

    document.getElementById('guest-tile-signs')?.addEventListener('click', function () { R.state.prepareSubtab = 'signs'; R.navigateTo('tests'); });
    document.getElementById('guest-tile-rules')?.addEventListener('click', function () { R.state.prepareSubtab = 'rules'; R.navigateTo('tests'); });
    document.getElementById('guest-tile-amaliy')?.addEventListener('click', function () { R.state.amaliySubtab = 'simulator'; R.navigateTo('amaliy'); });
    document.getElementById('guest-tile-topics')?.addEventListener('click', function () { R.state.prepareSubtab = 'topics'; R.navigateTo('tests'); });
  }

  R.renderHome = function () {
    const root = document.getElementById('view-home');
    if (!root) return;

    if (R.state.isGuest) {
      renderGuestHome(root);
      return;
    }

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
    const streak = R.state.streak || { current_streak: 0, daily_goal_questions: 20, today_questions_count: 0 };
    const sub = R.state.subscription || {};
    const ft = R.state.freeTier || {};
    const analytics = R.state.analytics || {};
    const score = Number(stats.readiness_score || 0);
    const pillars = stats.readiness_pillars || {};
    const meta = gradeMeta(stats.readiness_grade, score);

    const clampedScore = Math.max(0, Math.min(100, score));
    // 240-degree precision cockpit arc: radius = 66 => (240/360) * 2 * pi * 66 = 276.46
    const arcLen = 276.46;
    const dashOffset = arcLen - (clampedScore / 100) * arcLen;
    const needleDeg = -120 + (clampedScore / 100) * 240;

    const todayDone = Number(streak.today_questions_count || 0);
    const goalTarget = Math.max(5, Number(streak.daily_goal_questions || 20));
    const goalPct = Math.min(100, Math.round((todayDone / goalTarget) * 100));

    // Smart Next Action from /api/learning/analytics
    const rec = analytics.recommendation || { kind: 'adaptive_starter', target_type: 'ADAPTIVE' };
    const srsSummary = analytics.srs_summary || stats.srs_summary || {};
    const srsDueNow = Number(srsSummary.due_now_count || 0);
    let recTitle = R.t('rec_adaptive_title');
    let recDesc = R.t('rec_adaptive_desc', { n: analytics.overall_coverage_pct || 0 });
    if (rec.kind === 'srs_review') {
      recTitle = R.t('rec_srs_review_title');
      recDesc = R.t('rec_srs_review_desc', { n: rec.metric || srsDueNow || 0 });
    } else if (rec.kind === 'mistake_drill') {
      recTitle = R.t('rec_mistake_drill_title');
      recDesc = R.t('rec_mistake_drill_desc', { n: rec.metric || stats.unresolved_mistakes || 0 });
    } else if (rec.kind === 'weak_topic') {
      recTitle = R.t('rec_weak_topic_title');
      recDesc = R.t('rec_weak_topic_desc', { topic: rec.topic_name || '', n: rec.metric || 0 });
    } else if (rec.kind === 'official_exam') {
      recTitle = R.t('rec_official_exam_title');
      recDesc = R.t('rec_official_exam_desc');
    }

    const srsBadgeHtml = srsDueNow > 0
      ? ' <span class="badge-pill badge-primary font-mono">' + R.escHtml(R.t('srs_due_badge', { n: srsDueNow })) + '</span>'
      : '';

    const freeExamsChip = sub.is_pro
      ? '<span class="cockpit-quota-pill pro">PRO</span>'
      : '<span class="cockpit-quota-pill">' + R.escHtml(R.t('cockpit_free_quota', { left: ft.remaining_exams || 0, total: ft.allowed_exams || 2 })) + '</span>';

    const mistakesBadge = (stats.unresolved_mistakes || 0) > 0
      ? '<span class="badge-pill badge-rose font-mono">' + stats.unresolved_mistakes + '</span>'
      : '<span class="badge-pill badge-emerald font-mono">0</span>';

    const pillarItems = [
      { key: 'pillar_exam', val: pillars.exam_mastery || 0 },
      { key: 'pillar_acc', val: pillars.accuracy || 0 },
      { key: 'pillar_cov', val: pillars.coverage || 0 },
      { key: 'pillar_err', val: pillars.mistake_hygiene || 0 },
      { key: 'pillar_streak', val: pillars.pace_and_streak || 0 }
    ];

    const draft = typeof R.getSavedQuizDraft === 'function' ? R.getSavedQuizDraft() : null;
    const resumeHtml = draft
      ? '<div class="surface-card resume-banner">' +
        '  <div><strong>' + R.escHtml(R.t('quiz_resume_title')) + '</strong><div style="font-size:12px;color:var(--text-secondary);">' + R.escHtml(draft.sessionType) + ' • ' + Object.keys(draft.answers || {}).length + ' / ' + (draft.questions || []).length + '</div></div>' +
        '  <div style="display:flex;gap:6px;">' +
        '    <button type="button" class="btn btn-primary btn-sm" id="home-resume-quiz-btn">' + R.escHtml(R.t('quiz_resume_btn')) + '</button>' +
        '    <button type="button" class="btn btn-ghost btn-sm" id="home-discard-quiz-btn">' + R.escHtml(R.t('quiz_resume_discard')) + '</button>' +
        '  </div>' +
        '</div>'
      : '';

    root.innerHTML =
      resumeHtml +
      '<div class="home-bento-top">' +
      '  <section class="surface-card readiness-hero" style="--gauge-accent:' + meta.stroke + ';--gauge-glow:' + meta.glow + ';">' +
      '    <div class="readiness-top-row">' +
      '      <span class="badge-pill ' + meta.badgeClass + '">' + R.icon('gauge', 'xs') + ' ' + R.escHtml(R.t('cluster_heading')) + '</span>' +
      '      <button type="button" class="btn btn-sm btn-secondary cockpit-diag-btn" id="home-diag-btn">' + R.escHtml(R.t('readiness_diagnostic_btn')) + '</button>' +
      '    </div>' +
      '    <div class="readiness-gauge-row">' +
      '      <div class="gauge-box cockpit-gauge-box">' +
      '        <svg class="gauge-svg" viewBox="0 0 180 156" aria-hidden="true">' +
      '          <circle class="cockpit-bezel-ring" cx="90" cy="90" r="76" />' +
      '          <path class="gauge-track" d="M 32.84 123 A 66 66 0 1 1 147.16 123" />' +
      buildCockpitTicks(clampedScore) +
      '          <path class="gauge-arc" d="M 32.84 123 A 66 66 0 1 1 147.16 123" style="stroke:' + meta.stroke + ';stroke-dasharray:' + arcLen + ';stroke-dashoffset:' + dashOffset.toFixed(2) + ';" />' +
      '          <g class="cockpit-needle" style="transform:rotate(' + needleDeg.toFixed(1) + 'deg);">' +
      '            <polygon class="cockpit-needle-blade" points="88.1,90 90,34 91.9,90" />' +
      '          </g>' +
      '          <circle class="cockpit-hub-outer" cx="90" cy="90" r="7.5" />' +
      '          <circle class="cockpit-hub-inner" cx="90" cy="90" r="3.4" />' +
      '        </svg>' +
      '        <div class="gauge-center-val">' +
      '          <div class="gauge-pct font-mono">' + Math.round(score) + '<span class="gauge-pct-sym">%</span></div>' +
      '          <div class="gauge-lbl">' + R.escHtml(R.t('speedometer_lbl')) + '</div>' +
      '        </div>' +
      '      </div>' +
      '      <div class="readiness-info-col">' +
      '        <div class="readiness-grade-title">' + R.escHtml(meta.label) + '</div>' +
      '        <p class="readiness-sub-copy">' + R.escHtml(meta.sub) + '</p>' +
      '      </div>' +
      '    </div>' +
      '    <div class="pillars-mini-grid">' +
      pillarItems.map(function (p) {
        const pv = Math.max(0, Math.min(100, Math.round(p.val)));
        const barTone = pv >= 75 ? 'emerald' : (pv >= 45 ? 'amber' : '');
        return '<div class="pillar-mini-cell">' +
          '  <div class="pillar-mini-val">' + pv + '%</div>' +
          '  <div class="pillar-mini-bar"><span class="' + barTone + '" style="width:' + pv + '%"></span></div>' +
          '  <div class="pillar-mini-name">' + R.escHtml(R.t(p.key)) + '</div>' +
          '</div>';
      }).join('') +
      '    </div>' +
      '  </section>' +

      '  <div class="home-right-stack">' +
      '    <section class="exam-launch-card">' +
      '      <div class="exam-launch-top">' +
      '        <div>' +
      '          <div class="exam-launch-eyebrow"><span class="cockpit-pulse-dot" aria-hidden="true"></span><span>' + R.escHtml(R.t('cockpit_live_badge')) + '</span></div>' +
      '          <div class="exam-launch-title">' + R.escHtml(R.t('hero_title')) + '</div>' +
      '        </div>' +
      freeExamsChip +
      '      </div>' +
      '      <div class="exam-spec-strip font-mono">' +
      '        <span class="exam-spec-pill">' + R.escHtml(R.t('cockpit_spec_questions')) + '</span>' +
      '        <span class="exam-spec-pill">' + R.escHtml(R.t('cockpit_spec_time')) + '</span>' +
      '        <span class="exam-spec-pill accent">' + R.escHtml(R.t('cockpit_spec_limit')) + '</span>' +
      '      </div>' +
      '      <button type="button" class="btn btn-exam-ignition btn-block" id="home-start-exam-btn">' +
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
      '          <span>' + R.icon('flame', 'xs') + ' ' + R.escHtml(R.t('streak_badge', { days: streak.current_streak || 0 })) + '</span>' +
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
      '    <div class="tile-body"><div class="tile-title"><span>' + R.escHtml(R.t('adaptive_title')) + '</span>' + srsBadgeHtml + '</div><div class="tile-desc">' + R.escHtml(R.t('custom_quiz_card_desc')) + '</div></div>' +
      '  </button>' +
      '  <button type="button" class="surface-card card-interactive action-tile" id="tile-amaliy">' +
      '    <div class="tile-icon-box badge-amber">' + R.icon('steeringWheel', 'lg') + '</div>' +
      '    <div class="tile-body"><div class="tile-title">' + R.escHtml(R.t('card_amaliy_title')) + '</div><div class="tile-desc">' + R.escHtml(R.t('card_amaliy_desc')) + '</div></div>' +
      '  </button>' +
      '  <button type="button" class="surface-card card-interactive action-tile" id="tile-signs">' +
      '    <div class="tile-icon-box badge-primary">' + R.icon('compass', 'lg') + '</div>' +
      '    <div class="tile-body"><div class="tile-title">' + R.escHtml(R.t('tab_signs')) + '</div><div class="tile-desc">' + R.escHtml(R.t('home_signs_desc')) + '</div></div>' +
      '  </button>' +
      '  <button type="button" class="surface-card card-interactive action-tile" id="tile-rules">' +
      '    <div class="tile-icon-box badge-emerald">' + R.icon('bookOpen', 'lg') + '</div>' +
      '    <div class="tile-body"><div class="tile-title">' + R.escHtml(R.t('ref_law_title')) + '</div><div class="tile-desc">' + R.escHtml(R.t('home_rules_desc')) + '</div></div>' +
      '  </button>' +
      '  <button type="button" class="surface-card card-interactive action-tile" id="tile-cheatsheet">' +
      '    <div class="tile-icon-box badge-neutral">' + R.icon('lightbulb', 'lg') + '</div>' +
      '    <div class="tile-body"><div class="tile-title">' + R.escHtml(R.t('card_cheatsheet_title')) + (!sub.is_pro ? ' <span class="badge-pill badge-amber">PRO</span>' : '') + '</div><div class="tile-desc">' + R.escHtml(R.t('card_cheatsheet_desc')) + '</div></div>' +
      '  </button>' +
      '</div>';

    // Bind events
    document.getElementById('home-resume-quiz-btn')?.addEventListener('click', function () { R.resumeSavedQuizSession(); });
    document.getElementById('home-discard-quiz-btn')?.addEventListener('click', function () { R.discardSavedQuizDraft(); });
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
        if (rec.target_type === 'SRS') {
          R.startSession({ session_type: 'SRS', total_questions: 20 });
        } else if (rec.target_type === 'MISTAKES') {
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
    document.getElementById('tile-signs')?.addEventListener('click', function () {
      R.state.prepareSubtab = 'signs';
      R.navigateTo('tests');
    });
    document.getElementById('tile-rules')?.addEventListener('click', function () {
      R.state.prepareSubtab = 'rules';
      R.navigateTo('tests');
    });
    document.getElementById('tile-cheatsheet')?.addEventListener('click', function () {
      R.openCheatsheetModal();
    });
  };
})();
