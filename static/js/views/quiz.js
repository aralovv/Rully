/**
 * RULLY 2.0 Focus Quiz / Exam Player, Results & Post-Session Review
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});

  let autoAdvanceTimer = null;

  function clearAutoAdvance() {
    if (autoAdvanceTimer) {
      clearTimeout(autoAdvanceTimer);
      autoAdvanceTimer = null;
    }
  }

  function clearQuizTimer() {
    clearAutoAdvance();
    if (R.state.quiz.timerInterval) {
      clearInterval(R.state.quiz.timerInterval);
      R.state.quiz.timerInterval = null;
    }
  }

  R.startSession = async function (opts) {
    const payload = {
      session_type: opts.session_type || 'EXAM',
      category_id: opts.category_id !== undefined ? opts.category_id : null,
      ticket_number: opts.ticket_number !== undefined ? opts.ticket_number : null,
      total_questions: opts.total_questions || 20,
      time_limit_seconds: opts.time_limit_seconds !== undefined ? opts.time_limit_seconds : (opts.session_type === 'EXAM' ? 25 * 60 : 0),
      show_answer: opts.show_answer !== undefined ? opts.show_answer : true,
      show_explanation: opts.show_explanation !== undefined ? opts.show_explanation : true,
      language: R.state.lang
    };

    try {
      R.haptic('light');
      const data = await R.api('/api/session/start', { method: 'POST', body: payload });
      clearQuizTimer();

      R.state.quiz = {
        active: true,
        sessionId: data.session_id,
        sessionType: data.session_type,
        ticketNumber: opts.ticket_number || null,
        questions: data.questions || [],
        currentIndex: 0,
        answers: {},
        timeRemaining: data.time_limit_seconds || 0,
        timerInterval: null,
        startTime: Date.now(),
        showAnswer: data.show_answer !== false,
        showExplanation: data.show_explanation !== false,
        isSubmitting: false
      };

      document.body.classList.add('focus-mode');
      R.showViewContainer('view-quiz');
      R.renderQuizQuestion();
      R.syncTelegramBackButton();

      if (R.state.quiz.timeRemaining > 0) {
        R.state.quiz.timerInterval = setInterval(function () {
          if (!R.state.quiz.active) { clearQuizTimer(); return; }
          R.state.quiz.timeRemaining -= 1;
          const clockEl = document.getElementById('quiz-clock-val');
          if (clockEl) clockEl.textContent = R.fmtClock(R.state.quiz.timeRemaining);
          if (R.state.quiz.timeRemaining <= 0) {
            clearQuizTimer();
            R.finishSession(true);
          }
        }, 1000);
      }
    } catch (err) {
      if (err.status === 403 && String(err.detail).includes('SUBSCRIPTION_REQUIRED')) {
        R.openPaywallModal();
      } else {
        R.showToast(err.detail || err.message || R.t('ai_generic_error'));
      }
    }
  };

  R.confirmAbortQuiz = async function () {
    const ok = await R.confirmDialog(R.t('confirm_finish_title'), R.t('confirm_finish_text'), R.t('btn_confirm'));
    if (ok) {
      await R.finishSession(true);
    }
  };

  R.renderQuizQuestion = function () {
    const root = document.getElementById('view-quiz');
    const qz = R.state.quiz;
    if (!root || !qz.active || !qz.questions.length) return;

    const q = qz.questions[qz.currentIndex];
    const ans = qz.answers[q.canonical_id];
    const mistakesUsed = Object.values(qz.answers).filter(function (a) { return a && !a.is_correct; }).length;
    const isExam = qz.sessionType === 'EXAM';

    let modeLabel = qz.sessionType;
    if (isExam) modeLabel = R.t('hero_title');
    else if (qz.sessionType === 'BILET') modeLabel = R.t('ticket_label', { n: qz.ticketNumber || '' });
    else if (qz.sessionType === 'ADAPTIVE') modeLabel = R.t('adaptive_title');
    else if (qz.sessionType === 'MISTAKES') modeLabel = R.t('card_mistakes_title');
    else if (q.category_name) modeLabel = q.category_name;

    const stepperHtml = qz.questions.map(function (item, idx) {
      const a = qz.answers[item.canonical_id];
      let cls = idx === qz.currentIndex ? 'current' : '';
      if (a) cls += (isExam && !qz.showAnswer) ? ' current' : (a.is_correct ? ' correct' : ' incorrect');
      return '<button type="button" class="q-step-dot ' + cls + '" data-q-jump="' + idx + '">' + (idx + 1) + '</button>';
    }).join('');

    const mistakeDotsHtml = isExam
      ? '<div class="mistake-dots" title="Max 2 mistakes">' +
        [0, 1, 2].map(function (i) { return '<span class="m-dot ' + (i < mistakesUsed ? 'used' : '') + '"></span>'; }).join('') +
        '</div>'
      : '';

    const optionsHtml = (q.options || []).map(function (opt) {
      let cls = '';
      if (ans) {
        if (ans.selected_key === opt.option_key) {
          cls = (isExam || !qz.showAnswer)
            ? (ans.is_correct ? 'is-correct' : 'is-wrong')
            : (ans.is_correct ? 'is-correct' : 'is-wrong');
        } else if (qz.showAnswer && ans.correct_key === opt.option_key) {
          cls = 'is-correct';
        }
      }
      return '<button type="button" class="option-btn ' + cls + '" data-opt-key="' + R.escHtml(opt.option_key) + '"' + (ans ? ' disabled' : '') + '>' +
        '<span class="option-key-badge">' + R.escHtml(opt.option_key) + '</span>' +
        '<span class="option-text">' + R.escHtml(opt.text) + '</span>' +
        '</button>';
    }).join('');

    let feedbackHtml = '';
    if (ans && (!isExam || qz.showExplanation)) {
      const cls = ans.is_correct ? 'correct' : 'wrong';
      const provHtml = typeof R.renderProvenanceBadge === 'function' ? R.renderProvenanceBadge(ans, q.canonical_id) : '';
      feedbackHtml =
        '<div class="feedback-panel ' + cls + '">' +
        '  <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">' +
        '    <span class="badge-pill ' + (ans.is_correct ? 'badge-emerald' : 'badge-rose') + '">' +
        R.icon(ans.is_correct ? 'checkCircle' : 'xCircle', 'xs') + ' ' +
        R.escHtml(ans.is_correct ? R.t('correct_badge') : R.t('wrong_badge')) +
        '    </span>' +
        '  </div>' +
        provHtml +
        (ans.explanation ? '<p style="font-size:13px;line-height:1.5;color:var(--text-primary);">' + R.escHtml(ans.explanation) + '</p>' : '') +
        '  <div>' +
        '    <button type="button" class="btn btn-sm btn-secondary" id="btn-quiz-ask-ai">' + R.icon('sparkles', 'xs') + ' ' + R.escHtml(R.t('btn_ask_ai_question')) + '</button>' +
        '  </div>' +
        '</div>';
    }

    const autoNextPill = (!isExam && qz.showAnswer)
      ? '<button type="button" class="filter-chip ' + (R.state.quizAutoAdvance ? 'active' : '') + '" id="quiz-autonext-btn" aria-pressed="' + Boolean(R.state.quizAutoAdvance) + '">' + R.icon('zap', 'xs') + ' <span>' + R.escHtml(R.t('quiz_auto_next')) + '</span></button>'
      : '';

    const isLast = qz.currentIndex >= qz.questions.length - 1;

    root.innerHTML =
      '<div class="quiz-topbar">' +
      '  <button type="button" class="btn btn-sm btn-secondary" id="quiz-exit-btn">' + R.icon('arrowLeft', 'sm') + '<span>' + R.escHtml(R.t('btn_finish_test')) + '</span></button>' +
      '  <div class="quiz-status-group">' +
      '    <span class="badge-pill badge-neutral font-mono">' + (qz.currentIndex + 1) + ' / ' + qz.questions.length + '</span>' +
      mistakeDotsHtml +
      autoNextPill +
      (qz.timeRemaining > 0 ? '<span class="badge-pill badge-primary font-mono" id="quiz-clock-val">' + R.fmtClock(qz.timeRemaining) + '</span>' : '') +
      '    <button type="button" class="icon-pill-btn" id="quiz-bm-btn" aria-label="Bookmark">' +
      R.icon(q.is_bookmarked ? 'bookmarkFill' : 'bookmark', 'sm') +
      '    </button>' +
      '  </div>' +
      '</div>' +
      '<div class="quiz-stepper">' + stepperHtml + '</div>' +
      '<article class="surface-card quiz-stage-card">' +
      '  <div style="font-size:11.5px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.03em;">' + R.escHtml(modeLabel) + '</div>' +
      (q.image_url
        ? '<div class="quiz-media-frame" id="quiz-media-zoom"><img src="' + R.escHtml(q.image_url) + '" alt="Traffic sign or intersection"><span class="media-zoom-btn">' + R.icon('zoomIn', 'sm') + '</span></div>'
        : '') +
      '  <h2 class="quiz-question-text">' + R.escHtml(q.question_text) + '</h2>' +
      '  <div class="options-stack">' + optionsHtml + '</div>' +
      feedbackHtml +
      '</article>' +
      '<div class="quiz-footer-nav">' +
      '  <button type="button" class="btn btn-secondary" id="quiz-prev-btn"' + (qz.currentIndex === 0 ? ' disabled' : '') + '>' + R.icon('chevronLeft', 'sm') + '<span>' + R.escHtml(R.t('btn_prev')) + '</span></button>' +
      (isLast
        ? '<button type="button" class="btn btn-emerald" id="quiz-finish-btn">' + R.escHtml(R.t('btn_finish_quiz')) + ' ' + R.icon('check', 'sm') + '</button>'
        : '<button type="button" class="btn btn-primary" id="quiz-next-btn"><span>' + R.escHtml(R.t('btn_next')) + '</span> ' + R.icon('chevronRight', 'sm') + '</button>') +
      '</div>';

    document.getElementById('quiz-exit-btn')?.addEventListener('click', R.confirmAbortQuiz);
    document.getElementById('quiz-prev-btn')?.addEventListener('click', function () {
      clearAutoAdvance();
      if (qz.currentIndex > 0) { qz.currentIndex -= 1; R.renderQuizQuestion(); }
    });
    document.getElementById('quiz-next-btn')?.addEventListener('click', function () {
      clearAutoAdvance();
      if (qz.currentIndex < qz.questions.length - 1) { qz.currentIndex += 1; R.renderQuizQuestion(); }
    });
    document.getElementById('quiz-autonext-btn')?.addEventListener('click', function () {
      R.state.quizAutoAdvance = !R.state.quizAutoAdvance;
      R.haptic('light');
      R.renderQuizQuestion();
    });
    root.querySelectorAll('[data-open-law-ch]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        clearAutoAdvance();
        if (typeof R.openLawModal === 'function') {
          const ch = Number(btn.dataset.openLawCh);
          R.openLawModal(ch || null);
        }
      });
    });
    document.getElementById('quiz-finish-btn')?.addEventListener('click', function () { R.finishSession(false); });
    document.getElementById('quiz-media-zoom')?.addEventListener('click', function () {
      R.openLightbox(q.image_url, q.question_text);
    });
    document.getElementById('btn-quiz-ask-ai')?.addEventListener('click', function () {
      clearQuizTimer();
      R.state.quiz.active = false;
      document.body.classList.remove('focus-mode');
      R.askAiAboutQuestion(q, ans.selected_key, ans.is_correct);
    });

    document.getElementById('quiz-bm-btn')?.addEventListener('click', async function () {
      try {
        const res = await R.api('/api/bookmarks/toggle', { method: 'POST', body: { canonical_id: q.canonical_id } });
        q.is_bookmarked = Boolean(res.is_bookmarked);
        R.haptic('light');
        R.renderQuizQuestion();
      } catch (e) {}
    });

    root.querySelectorAll('[data-q-jump]').forEach(function (dot) {
      dot.addEventListener('click', function () {
        qz.currentIndex = Number(dot.dataset.qJump);
        R.renderQuizQuestion();
      });
    });

    root.querySelectorAll('[data-opt-key]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.submitQuizAnswer(btn.dataset.optKey);
      });
    });
  };

  R.submitQuizAnswer = async function (selectedKey) {
    const qz = R.state.quiz;
    if (!qz.active || qz.isSubmitting) return;
    const q = qz.questions[qz.currentIndex];
    if (!q || qz.answers[q.canonical_id]) return;

    qz.isSubmitting = true;
    try {
      const res = await R.api('/api/session/answer', {
        method: 'POST',
        body: {
          session_id: qz.sessionId,
          canonical_id: q.canonical_id,
          selected_key: selectedKey,
          language: R.state.lang
        }
      });
      qz.answers[q.canonical_id] = res;
      if (res.streak) R.state.streak = Object.assign(R.state.streak || {}, res.streak);
      R.haptic(res.is_correct ? 'success' : 'error');

      if (res.is_exam_terminated) {
        R.showToast(R.t('res_exam_terminated_toast'), 3200);
        qz.isSubmitting = false;
        await R.finishSession(true);
        return;
      }
      qz.isSubmitting = false;
      R.renderQuizQuestion();

      if (res.is_correct && qz.sessionType !== 'EXAM' && qz.showAnswer && R.state.quizAutoAdvance && qz.currentIndex < qz.questions.length - 1) {
        clearAutoAdvance();
        autoAdvanceTimer = setTimeout(function () {
          if (R.state.quiz.active && R.state.quiz.currentIndex < R.state.quiz.questions.length - 1) {
            R.state.quiz.currentIndex += 1;
            R.renderQuizQuestion();
          }
        }, 900);
      }
    } catch (err) {
      qz.isSubmitting = false;
      R.showToast(err.detail || err.message || R.t('ai_generic_error'));
    }
  };

  R.finishSession = async function (skipConfirm) {
    const qz = R.state.quiz;
    if (!qz.sessionId) {
      document.body.classList.remove('focus-mode');
      R.navigateTo(R.state.activeTab || 'home');
      return;
    }

    if (!skipConfirm) {
      const answeredCount = Object.keys(qz.answers).length;
      if (answeredCount < qz.questions.length) {
        const ok = await R.confirmDialog(R.t('confirm_finish_title'), R.t('confirm_finish_text'), R.t('btn_confirm'));
        if (!ok) return;
      }
    }

    clearQuizTimer();
    const elapsed = Math.round((Date.now() - (qz.startTime || Date.now())) / 1000);
    qz.active = false;
    document.body.classList.remove('focus-mode');

    try {
      const fin = await R.api('/api/session/finish', {
        method: 'POST',
        body: { session_id: qz.sessionId, time_elapsed_seconds: elapsed }
      });
      R.state.tickets = []; // Force fresh ticket mastery badge next load
      R.state.analytics = null;
      await R.refreshProfileSnapshot();
      R.loadAnalyticsAsync();
      R.renderResults(fin, qz.ticketNumber);
    } catch (err) {
      R.showToast(err.message || R.t('ai_generic_error'));
      R.navigateTo('home');
    }
  };

  R.renderResults = function (fin, ticketNum) {
    const root = document.getElementById('view-results');
    if (!root) return;
    R.showViewContainer('view-results');
    R.syncTelegramBackButton();

    const passed = Boolean(fin.passed);
    const pct = Number(fin.percentage || 0);
    const elapsed = Number(fin.time_elapsed_seconds || 0);
    const mins = Math.floor(elapsed / 60);
    const secs = Math.floor(elapsed % 60);

    let title = passed ? R.t('res_passed_title') : R.t('res_failed_title');
    let subtitle = passed ? R.t('res_passed_subtitle') : R.t('res_failed_subtitle');
    if (fin.terminated_reason === 'MAX_MISTAKES_EXCEEDED') {
      subtitle = R.t('res_failed_mistakes_limit');
    } else if (fin.session_type !== 'EXAM') {
      title = pct >= 85 ? R.t('res_custom_great_title') : R.t('res_custom_complete_title');
      subtitle = passed ? R.t('res_practice_passed_subtitle') : R.t('res_practice_failed_subtitle');
    }

    const bd = fin.category_breakdown || {};
    const breakdownHtml = Object.keys(bd).map(function (cat) {
      const b = bd[cat];
      const catPct = b.total > 0 ? Math.round((b.correct / b.total) * 100) : 0;
      return '<div style="margin-bottom:8px;">' +
        '<div style="display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:4px;"><span>' + R.escHtml(cat) + '</span><span class="font-mono">' + b.correct + '/' + b.total + ' (' + catPct + '%)</span></div>' +
        '<div class="progress-track"><div class="progress-fill ' + (catPct >= 80 ? 'emerald' : 'amber') + '" style="width:' + catPct + '%"></div></div>' +
        '</div>';
    }).join('');

    root.innerHTML =
      '<section class="surface-card" style="text-align:center;margin-bottom:14px;">' +
      '  <div class="badge-pill ' + (passed ? 'badge-emerald' : 'badge-rose') + '" style="margin-bottom:10px;">' +
      R.icon(passed ? 'trophy' : 'xCircle', 'sm') + ' ' + R.escHtml(title) +
      '  </div>' +
      '  <div class="font-mono" style="font-size:38px;font-weight:800;line-height:1.1;margin-bottom:6px;">' + fin.correct_count + ' / ' + fin.total_questions + ' <span style="font-size:20px;color:var(--text-muted);">(' + pct.toFixed(0) + '%)</span></div>' +
      '  <p style="font-size:13.5px;color:var(--text-secondary);max-width:440px;margin:0 auto 14px;">' + R.escHtml(subtitle) + '</p>' +
      '  <div class="kpi-strip" style="margin-bottom:14px;">' +
      '    <div class="kpi-tile"><span class="kpi-value font-mono text-emerald">' + fin.correct_count + '</span><span class="kpi-label">' + R.escHtml(R.t('lbl_correct')) + '</span></div>' +
      '    <div class="kpi-tile"><span class="kpi-value font-mono text-rose">' + fin.incorrect_count + '</span><span class="kpi-label">' + R.escHtml(R.t('lbl_incorrect')) + '</span></div>' +
      '    <div class="kpi-tile"><span class="kpi-value font-mono">' + (fin.unanswered_count || 0) + '</span><span class="kpi-label">' + R.escHtml(R.t('lbl_unanswered')) + '</span></div>' +
      '    <div class="kpi-tile"><span class="kpi-value font-mono">' + mins + ':' + String(secs).padStart(2, '0') + '</span><span class="kpi-label">' + R.escHtml(R.t('lbl_time')) + '</span></div>' +
      '  </div>' +
      '  <div style="display:flex;gap:8px;flex-wrap:wrap;justify-content:center;">' +
      '    <button type="button" class="btn btn-primary" id="res-review-btn">' + R.icon('eye', 'sm') + '<span>' + R.escHtml(R.t('review_btn')) + '</span></button>' +
      '    <button type="button" class="btn btn-secondary" id="res-retake-btn">' + R.icon('rotateCcw', 'sm') + '<span>' + R.escHtml(R.t('btn_retake')) + '</span></button>' +
      '    <button type="button" class="btn btn-ghost" id="res-home-btn">' + R.escHtml(R.t('btn_back_home')) + '</button>' +
      '  </div>' +
      '</section>' +
      (breakdownHtml ? '<section class="surface-card"><h3 class="section-heading"><span>' + R.escHtml(R.t('res_category_breakdown')) + '</span></h3>' + breakdownHtml + '</section>' : '');

    document.getElementById('res-review-btn')?.addEventListener('click', function () {
      R.openSessionReviewModal(fin.session_id);
    });
    document.getElementById('res-retake-btn')?.addEventListener('click', function () {
      R.startSession({ session_type: fin.session_type, ticket_number: ticketNum });
    });
    document.getElementById('res-home-btn')?.addEventListener('click', function () {
      R.navigateTo('home');
    });
  };

  R.openSessionReviewModal = async function (sessionId) {
    const body = document.getElementById('session-review-body');
    if (!body) return;
    body.innerHTML = '<div class="skeleton-block" style="height:120px;"></div>';
    R.openModal('session-review-modal');

    try {
      const data = await R.api('/api/session/' + encodeURIComponent(sessionId) + '/review?lang=' + R.state.lang);
      const allItems = data.items || [];
      R.state.reviewFilter = 'all';

      function renderReviewList() {
        const filter = R.state.reviewFilter || 'all';
        const wrongCount = allItems.filter(function (x) { return x.is_correct === false; }).length;
        const shown = filter === 'mistakes' ? allItems.filter(function (x) { return x.is_correct === false; }) : allItems;

        const filterBar =
          '<div class="filter-chip-row" style="margin-bottom:4px;">' +
          '  <button type="button" class="filter-chip ' + (filter === 'all' ? 'active' : '') + '" data-rev-filter="all">' + R.escHtml(R.t('filter_all')) + ' (' + allItems.length + ')</button>' +
          '  <button type="button" class="filter-chip ' + (filter === 'mistakes' ? 'active' : '') + '" data-rev-filter="mistakes">' + R.escHtml(R.t('review_filter_mistakes')) + ' (' + wrongCount + ')</button>' +
          '</div>';

        const listHtml = !shown.length
          ? '<div class="surface-card empty-state-box"><strong>' + R.escHtml(R.t('mistakes_zero_title')) + '</strong></div>'
          : shown.map(function (it) {
              const tag = it.selected_key === null
                ? '<span class="badge-pill badge-neutral">' + R.escHtml(R.t('review_skipped_tag')) + '</span>'
                : (it.is_correct
                  ? '<span class="badge-pill badge-emerald">' + R.escHtml(R.t('review_correct_tag')) + '</span>'
                  : '<span class="badge-pill badge-rose">' + R.escHtml(R.t('review_wrong_tag')) + '</span>');
              const provHtml = typeof R.renderProvenanceBadge === 'function' ? R.renderProvenanceBadge(it, it.canonical_id) : '';

              return '<div class="surface-card">' +
                '<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:8px;">' +
                '  <span class="font-mono" style="font-weight:700;font-size:12.5px;">#' + it.index + ' • ' + R.escHtml(it.category_name || '') + '</span>' +
                tag +
                '</div>' +
                (it.image_url ? '<div class="quiz-media-frame" style="margin-bottom:8px;min-height:120px;max-height:190px;"><img src="' + R.escHtml(it.image_url) + '" alt="" loading="lazy"></div>' : '') +
                '<p style="font-weight:700;font-size:13.5px;margin-bottom:8px;">' + R.escHtml(it.question_text) + '</p>' +
                '<div style="font-size:12.5px;color:var(--text-secondary);margin-bottom:6px;">' +
                (it.selected_key ? R.escHtml(R.t('ticket_in_progress')) + ': <b>' + R.escHtml(it.selected_key) + '</b> • ' : '') +
                R.escHtml(R.t('saved_correct_answer_label')) + ' <b style="color:var(--color-emerald);">' + R.escHtml(it.correct_option_key) + ' — ' + R.escHtml(it.correct_answer_text || '') + '</b>' +
                '</div>' +
                provHtml +
                (it.explanation ? '<p style="font-size:12px;color:var(--text-muted);margin-bottom:8px;">' + R.escHtml(it.explanation) + '</p>' : '') +
                '<button type="button" class="btn btn-sm btn-secondary" data-rev-ai="' + it.index + '">' + R.icon('sparkles', 'xs') + ' ' + R.escHtml(R.t('btn_ask_ai_question')) + '</button>' +
                '</div>';
            }).join('');

        body.innerHTML = filterBar + listHtml;

        body.querySelectorAll('[data-rev-filter]').forEach(function (btn) {
          btn.addEventListener('click', function () {
            R.state.reviewFilter = btn.dataset.revFilter;
            renderReviewList();
          });
        });

        body.querySelectorAll('[data-open-law-ch]').forEach(function (btn) {
          btn.addEventListener('click', function () {
            R.closeModal('session-review-modal');
            if (typeof R.openLawModal === 'function') {
              R.openLawModal(Number(btn.dataset.openLawCh) || null);
            }
          });
        });

        body.querySelectorAll('[data-rev-ai]').forEach(function (btn) {
          btn.addEventListener('click', function () {
            const item = allItems.find(function (x) { return String(x.index) === btn.dataset.revAi; });
            if (item) {
              R.closeModal('session-review-modal');
              R.askAiAboutQuestion(item, item.selected_key, item.is_correct);
            }
          });
        });
      }

      renderReviewList();
    } catch (err) {
      body.innerHTML = '<p style="color:var(--color-rose);">' + R.escHtml(err.message) + '</p>';
    }
  };
})();
