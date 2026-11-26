/**
 * RULLY 2.0 Tayyorlov (Prepare) View: Topics (43) | Tickets (67) | Adaptive & Custom | Saved
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});

  R.loadPrepareData = async function () {
    const lang = R.state.lang;
    try {
      const promises = [];
      if (!R.state.categories.length) {
        promises.push(R.api('/api/categories?lang=' + lang).then(function (d) { R.state.categories = d.categories || []; }));
      }
      if (!R.state.tickets.length) {
        promises.push(R.api('/api/tickets?lang=' + lang).then(function (d) {
          R.state.tickets = d.tickets || [];
          R.state.ticketsMeta = {
            total_tickets: d.total_tickets || 67,
            passed_tickets: d.passed_tickets || 0,
            attempted_tickets: d.attempted_tickets || 0
          };
        }));
      }
      if (!R.state.analytics) {
        promises.push(R.api('/api/learning/analytics?lang=' + lang).then(function (d) { R.state.analytics = d; }));
      }
      if (R.state.prepareSubtab === 'saved') {
        promises.push(R.api('/api/bookmarks?lang=' + lang).then(function (d) {
          R.state.bookmarksList = d.questions || [];
          R.state.bookmarksCount = R.state.bookmarksList.length;
        }));
      }
      if (R.state.prepareSubtab === 'adaptive' && !R.state.srsQueue) {
        promises.push(R.api('/api/srs/queue?lang=' + lang + '&limit=10').then(function (d) {
          R.state.srsQueue = d;
        }));
      }
      if (promises.length) {
        await Promise.all(promises);
        R.renderPrepare();
      }
    } catch (e) {
      // Non-fatal; view stays interactive
    }
  };

  function renderTopicsTab(container) {
    const masteryMap = {};
    ((R.state.analytics && R.state.analytics.category_mastery) || []).forEach(function (m) {
      masteryMap[m.category_id] = m;
    });

    const query = (R.state.topicSearch || '').trim().toLowerCase();
    const filter = R.state.topicFilter || 'all';

    const list = (R.state.categories || []).filter(function (c) {
      if (query && !(c.name || '').toLowerCase().includes(query)) return false;
      if (filter === 'unmastered') {
        const m = masteryMap[c.category_id];
        return !m || m.mastery_pct < 80;
      }
      return true;
    });

    let html =
      '<div class="toolbar-row">' +
      '  <div class="search-box">' +
      '    <span class="search-icon">' + R.icon('search', 'sm') + '</span>' +
      '    <input type="search" class="search-input" id="prepare-topic-search" value="' + R.escHtml(R.state.topicSearch || '') + '" placeholder="' + R.escHtml(R.t('search_category')) + '">' +
      '  </div>' +
      '  <div class="filter-chip-row">' +
      '    <button type="button" class="filter-chip ' + (filter === 'all' ? 'active' : '') + '" data-topic-filter="all">' + R.escHtml(R.t('filter_all')) + '</button>' +
      '    <button type="button" class="filter-chip ' + (filter === 'unmastered' ? 'active' : '') + '" data-topic-filter="unmastered">' + R.escHtml(R.t('analytics_weak_title')) + '</button>' +
      '  </div>' +
      '</div>';

    if (!R.state.categories.length) {
      html += '<div class="topics-grid"><div class="surface-card skeleton-block" style="height:96px;"></div><div class="surface-card skeleton-block" style="height:96px;"></div><div class="surface-card skeleton-block" style="height:96px;"></div></div>';
      container.innerHTML = html;
      return;
    }

    if (!list.length) {
      html +=
        '<div class="surface-card empty-state-box">' +
        '  <div class="r-icon lg">' + R.icon('search', 'lg') + '</div>' +
        '  <strong>' + R.escHtml(R.t('empty_search_title')) + '</strong>' +
        '  <p style="font-size:12.5px;color:var(--text-secondary);">' + R.escHtml(R.t('empty_search_desc')) + '</p>' +
        '  <button type="button" class="btn btn-secondary btn-sm" id="btn-reset-topic-filter">' + R.escHtml(R.t('filter_all')) + '</button>' +
        '</div>';
    } else {
      html += '<div class="topics-grid">' +
        list.map(function (c) {
          const m = masteryMap[c.category_id] || { mastery_pct: 0, accuracy_pct: null, unique_correct: 0 };
          const pct = Math.min(100, Math.round(m.mastery_pct || 0));
          const accBadge = m.accuracy_pct !== null
            ? '<span class="badge-pill ' + (m.accuracy_pct >= 80 ? 'badge-emerald' : 'badge-amber') + ' font-mono">' + Math.round(m.accuracy_pct) + '%</span>'
            : '<span class="badge-pill badge-neutral font-mono">' + R.escHtml(R.t('questions_count', { n: c.question_count })) + '</span>';

          return '<button type="button" class="surface-card card-interactive topic-card" data-start-cat="' + c.category_id + '">' +
            '<div class="topic-card-head">' +
            '  <span class="topic-name">' + R.escHtml(c.name) + '</span>' +
            accBadge +
            '</div>' +
            '<div class="progress-track"><div class="progress-fill ' + (pct >= 80 ? 'emerald' : '') + '" style="width:' + pct + '%"></div></div>' +
            '<div class="topic-meta-row">' +
            '  <span>' + R.escHtml(R.t('questions_count', { n: c.question_count })) + '</span>' +
            '  <span class="font-mono">' + (m.unique_correct || 0) + ' / ' + c.question_count + '</span>' +
            '</div>' +
            '</button>';
        }).join('') +
        '</div>';
    }

    container.innerHTML = html;

    const searchInput = document.getElementById('prepare-topic-search');
    if (searchInput) {
      searchInput.addEventListener('input', function () {
        R.state.topicSearch = searchInput.value;
        renderTopicsTab(container);
        const refocused = document.getElementById('prepare-topic-search');
        if (refocused) {
          refocused.focus();
          const len = refocused.value.length;
          refocused.setSelectionRange(len, len);
        }
      });
    }

    container.querySelectorAll('[data-topic-filter]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.state.topicFilter = btn.dataset.topicFilter;
        renderTopicsTab(container);
      });
    });

    const resetBtn = document.getElementById('btn-reset-topic-filter');
    if (resetBtn) {
      resetBtn.addEventListener('click', function () {
        R.state.topicSearch = '';
        R.state.topicFilter = 'all';
        renderTopicsTab(container);
      });
    }

    container.querySelectorAll('[data-start-cat]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.startSession({ session_type: 'CATEGORY', category_id: Number(btn.dataset.startCat), total_questions: 30 });
      });
    });
  }

  function renderTicketsTab(container) {
    const meta = R.state.ticketsMeta || { total_tickets: 67, passed_tickets: 0 };
    const filter = R.state.ticketFilter || 'all';
    const tickets = (R.state.tickets || []).filter(function (tk) {
      if (filter === 'passed') return tk.is_passed;
      if (filter === 'unpassed') return !tk.is_passed;
      return true;
    });

    const passPct = Math.round(((meta.passed_tickets || 0) / Math.max(1, meta.total_tickets || 67)) * 100);

    let html =
      '<div class="surface-card" style="margin-bottom:12px;">' +
      '  <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px;">' +
      '    <div><strong style="font-size:15px;">' + R.escHtml(R.t('tickets_header_title')) + '</strong><p style="font-size:12px;color:var(--text-secondary);">' + R.escHtml(R.t('tickets_header_sub')) + '</p></div>' +
      '    <span class="badge-pill badge-emerald font-mono">' + (meta.passed_tickets || 0) + ' / ' + (meta.total_tickets || 67) + '</span>' +
      '  </div>' +
      '  <div class="progress-track" style="margin-bottom:10px;"><div class="progress-fill emerald" style="width:' + passPct + '%"></div></div>' +
      '  <div class="filter-chip-row">' +
      '    <button type="button" class="filter-chip ' + (filter === 'all' ? 'active' : '') + '" data-tk-filter="all">' + R.escHtml(R.t('filter_all')) + '</button>' +
      '    <button type="button" class="filter-chip ' + (filter === 'unpassed' ? 'active' : '') + '" data-tk-filter="unpassed">' + R.escHtml(R.t('filter_unpassed')) + '</button>' +
      '    <button type="button" class="filter-chip ' + (filter === 'passed' ? 'active' : '') + '" data-tk-filter="passed">' + R.escHtml(R.t('filter_passed')) + '</button>' +
      '  </div>' +
      '</div>';

    if (!R.state.tickets.length) {
      html += '<div class="tickets-grid"><div class="surface-card skeleton-block" style="height:86px;"></div><div class="surface-card skeleton-block" style="height:86px;"></div></div>';
      container.innerHTML = html;
      return;
    }

    html += '<div class="tickets-grid">' +
      tickets.map(function (tk) {
        let badge = '<span class="badge-pill badge-neutral">' + R.escHtml(R.t('ticket_new')) + '</span>';
        if (tk.is_passed) {
          badge = '<span class="badge-pill badge-emerald font-mono">' + R.icon('check', 'xs') + ' ' + tk.best_correct + '/' + tk.question_count + '</span>';
        } else if (tk.attempts_count > 0) {
          badge = '<span class="badge-pill badge-amber font-mono">' + tk.best_correct + '/' + tk.question_count + '</span>';
        }
        return '<button type="button" class="surface-card card-interactive ticket-card ' + (tk.is_passed ? 'passed' : '') + '" data-ticket-num="' + tk.ticket_number + '">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:4px;">' +
          '  <span class="ticket-num font-mono">#' + String(tk.ticket_number).padStart(2, '0') + '</span>' +
          badge +
          '</div>' +
          '<div class="ticket-topic-hint">' + R.escHtml(tk.primary_topic || '') + '</div>' +
          '<div style="font-size:11px;color:var(--text-muted);">' + R.escHtml(R.t('ticket_questions_badge', { n: tk.question_count })) + '</div>' +
          '</button>';
      }).join('') +
      '</div>';

    container.innerHTML = html;

    container.querySelectorAll('[data-tk-filter]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.state.ticketFilter = btn.dataset.tkFilter;
        renderTicketsTab(container);
      });
    });

    container.querySelectorAll('[data-ticket-num]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.startSession({ session_type: 'BILET', ticket_number: Number(btn.dataset.ticketNum) });
      });
    });
  }

  function renderAdaptiveTab(container) {
    const cfg = R.state.customQuiz;
    const isPro = Boolean(R.state.subscription && R.state.subscription.is_pro);
    const srsQ = R.state.srsQueue || {};
    const analyticsSrs = (R.state.analytics && R.state.analytics.srs_summary) || {};
    const statsSrs = (R.state.stats && R.state.stats.srs_summary) || {};
    const sum = Object.assign({ due_now_count: 0, learning_count: 0, reviewing_count: 0, mastered_count: 0, tracked_count: 0, retention_rate: 100, avg_ease_factor: 2.5 }, statsSrs, analyticsSrs, srsQ.summary || {});
    const queueItems = (srsQ.items || []).slice(0, 5);
    const retentionPct = Math.max(0, Math.min(100, Math.round(Number(sum.retention_rate || 100))));

    const queuePreviewHtml = queueItems.length
      ? '<div class="srs-queue-list">' +
        queueItems.map(function (it) {
          const ivLabel = it.is_due
            ? R.t('srs_due_now_lbl')
            : R.t('srs_next_days', { d: it.interval_days || 1 });
          const badgeCls = it.is_due ? 'badge-rose' : (it.mastery_level === 'MASTERED' ? 'badge-emerald' : 'badge-primary');
          return '<div class="srs-queue-row">' +
            '  <div style="min-width:0;flex:1;">' +
            '    <div style="font-size:12.5px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + R.escHtml(it.question_text || it.canonical_id) + '</div>' +
            '    <div style="font-size:11px;color:var(--text-muted);">' + R.escHtml(it.category_name || '') + ' • EF ' + Number(it.ease_factor || 2.5).toFixed(2) + '</div>' +
            '  </div>' +
            '  <span class="badge-pill ' + badgeCls + ' font-mono" style="flex-shrink:0;">' + R.escHtml(ivLabel) + '</span>' +
            '</div>';
        }).join('') +
        '</div>'
      : '<p style="font-size:12px;color:var(--text-secondary);">' + R.escHtml(R.t('srs_queue_empty')) + '</p>';

    container.innerHTML =
      '<section class="surface-card srs-hero-card" style="margin-bottom:14px;">' +
      '  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap;">' +
      '    <div>' +
      '      <span class="badge-pill badge-primary" style="margin-bottom:6px;">' + R.icon('flame', 'xs') + ' SM-2</span>' +
      '      <h3 style="font-family:var(--font-display);font-size:18px;font-weight:800;">' + R.escHtml(R.t('srs_mode_title')) + '</h3>' +
      '      <p style="font-size:12.5px;color:var(--text-secondary);margin-top:2px;">' + R.escHtml(R.t('srs_subtitle')) + '</p>' +
      '    </div>' +
      '    <button type="button" class="btn btn-primary" id="btn-launch-srs">' + R.icon('zap', 'sm') + '<span>' + R.escHtml(R.t('btn_start_srs')) + (sum.due_now_count > 0 ? ' (' + sum.due_now_count + ')' : ' (20)') + '</span></button>' +
      '  </div>' +
      '  <div class="srs-stats-strip">' +
      '    <div class="srs-stat-box"><span class="srs-stat-val text-rose">' + (sum.due_now_count || 0) + '</span><span class="srs-stat-lbl">' + R.escHtml(R.t('srs_due_now_lbl')) + '</span></div>' +
      '    <div class="srs-stat-box"><span class="srs-stat-val" style="color:var(--color-amber);">' + (sum.learning_count || 0) + '</span><span class="srs-stat-lbl">' + R.escHtml(R.t('srs_learning_lbl')) + '</span></div>' +
      '    <div class="srs-stat-box"><span class="srs-stat-val" style="color:var(--color-primary);">' + (sum.reviewing_count || 0) + '</span><span class="srs-stat-lbl">' + R.escHtml(R.t('srs_reviewing_lbl')) + '</span></div>' +
      '    <div class="srs-stat-box"><span class="srs-stat-val text-emerald">' + (sum.mastered_count || 0) + '</span><span class="srs-stat-lbl">' + R.escHtml(R.t('srs_mastered_lbl')) + '</span></div>' +
      '  </div>' +
      '  <div>' +
      '    <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px;"><span>' + R.escHtml(R.t('srs_retention_lbl')) + '</span><span class="font-mono" style="font-weight:700;">' + retentionPct + '% • EF ' + Number(sum.avg_ease_factor || 2.5).toFixed(2) + '</span></div>' +
      '    <div class="progress-track"><div class="progress-fill ' + (retentionPct >= 75 ? 'emerald' : 'amber') + '" style="width:' + retentionPct + '%"></div></div>' +
      '  </div>' +
      '  <div>' +
      '    <div style="font-size:12px;font-weight:700;color:var(--text-muted);margin-bottom:6px;">' + R.escHtml(R.t('srs_queue_preview_title')) + '</div>' +
      queuePreviewHtml +
      '  </div>' +
      '</section>' +
      '<div class="builder-grid">' +
      '  <section class="surface-card" style="display:flex;flex-direction:column;justify-content:space-between;gap:14px;">' +
      '    <div>' +
      '      <span class="badge-pill badge-primary" style="margin-bottom:8px;">' + R.icon('zap', 'xs') + ' Smart AI Mix</span>' +
      '      <h3 style="font-family:var(--font-display);font-size:17px;margin-bottom:6px;">' + R.escHtml(R.t('adaptive_title')) + '</h3>' +
      '      <p style="font-size:13px;color:var(--text-secondary);">' + R.escHtml(R.t('adaptive_desc')) + '</p>' +
      '    </div>' +
      '    <button type="button" class="btn btn-primary btn-block" id="btn-launch-adaptive">' + R.icon('sliders', 'sm') + '<span>' + R.escHtml(R.t('btn_start_adaptive')) + ' (20)</span></button>' +
      '  </section>' +

      '  <section class="surface-card" style="display:flex;flex-direction:column;gap:12px;">' +
      '    <h3 style="font-family:var(--font-display);font-size:16px;">' + R.escHtml(R.t('custom_builder_title')) + '</h3>' +
      '    <div>' +
      '      <div style="font-size:12.5px;font-weight:600;margin-bottom:6px;">' + R.escHtml(R.t('setting_q_count')) + '</div>' +
      '      <div class="seg-pills">' +
      [10, 20, 30, 50].map(function (cnt) {
        const locked = cnt > 20 && !isPro;
        return '<button type="button" class="seg-pill ' + (cfg.total_questions === cnt ? 'active' : '') + '" data-cq-count="' + cnt + '">' + cnt + (locked ? ' 🔒' : '') + '</button>';
      }).join('') +
      '      </div>' +
      '    </div>' +
      '    <div>' +
      '      <div style="font-size:12.5px;font-weight:600;margin-bottom:6px;">' + R.escHtml(R.t('setting_time_limit')) + '</div>' +
      '      <div class="seg-pills" style="grid-template-columns:repeat(3,1fr);">' +
      [0, 15, 25].map(function (m) {
        const lbl = m === 0 ? R.t('opt_unlimited') : R.t('opt_minutes', { m: m });
        return '<button type="button" class="seg-pill ' + (cfg.time_limit_minutes === m ? 'active' : '') + '" data-cq-time="' + m + '">' + R.escHtml(lbl) + '</button>';
      }).join('') +
      '      </div>' +
      '    </div>' +
      '    <div class="toggle-row">' +
      '      <div><div style="font-size:13px;font-weight:600;">' + R.escHtml(R.t('setting_show_answer')) + '</div><div style="font-size:11.5px;color:var(--text-muted);">' + R.escHtml(R.t('setting_show_answer_desc')) + '</div></div>' +
      '      <button type="button" class="switch-btn ' + (cfg.show_answer ? 'active' : '') + '" id="cq-toggle-answer" aria-pressed="' + cfg.show_answer + '"></button>' +
      '    </div>' +
      '    <div class="toggle-row">' +
      '      <div><div style="font-size:13px;font-weight:600;">' + R.escHtml(R.t('setting_show_explanation')) + '</div><div style="font-size:11.5px;color:var(--text-muted);">' + R.escHtml(R.t('setting_show_explanation_desc')) + '</div></div>' +
      '      <button type="button" class="switch-btn ' + (cfg.show_explanation ? 'active' : '') + '" id="cq-toggle-exp" aria-pressed="' + cfg.show_explanation + '"></button>' +
      '    </div>' +
      '    <button type="button" class="btn btn-secondary btn-block" id="btn-launch-custom">' + R.escHtml(R.t('btn_start_custom_quiz')) + '</button>' +
      '  </section>' +
      '</div>';

    document.getElementById('btn-launch-srs')?.addEventListener('click', function () {
      R.startSession({ session_type: 'SRS', total_questions: 20 });
    });

    document.getElementById('btn-launch-adaptive')?.addEventListener('click', function () {
      R.startSession({ session_type: 'ADAPTIVE', total_questions: 20 });
    });

    container.querySelectorAll('[data-cq-count]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const cnt = Number(btn.dataset.cqCount);
        if (cnt > 20 && !isPro) {
          R.openPaywallModal();
          return;
        }
        cfg.total_questions = cnt;
        renderAdaptiveTab(container);
      });
    });

    container.querySelectorAll('[data-cq-time]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        cfg.time_limit_minutes = Number(btn.dataset.cqTime);
        renderAdaptiveTab(container);
      });
    });

    document.getElementById('cq-toggle-answer')?.addEventListener('click', function () {
      cfg.show_answer = !cfg.show_answer;
      renderAdaptiveTab(container);
    });
    document.getElementById('cq-toggle-exp')?.addEventListener('click', function () {
      cfg.show_explanation = !cfg.show_explanation;
      renderAdaptiveTab(container);
    });
    document.getElementById('btn-launch-custom')?.addEventListener('click', function () {
      R.startSession({
        session_type: 'CUSTOM',
        total_questions: cfg.total_questions,
        time_limit_seconds: cfg.time_limit_minutes * 60,
        show_answer: cfg.show_answer,
        show_explanation: cfg.show_explanation
      });
    });
  }

  function renderSavedTab(container) {
    const list = R.state.bookmarksList || [];
    if (!list.length) {
      container.innerHTML =
        '<div class="surface-card empty-state-box">' +
        '  <div class="r-icon lg">' + R.icon('bookmark', 'lg') + '</div>' +
        '  <strong>' + R.escHtml(R.t('saved_empty_title')) + '</strong>' +
        '  <p style="font-size:12.5px;color:var(--text-secondary);max-width:340px;">' + R.escHtml(R.t('saved_empty_desc')) + '</p>' +
        '</div>';
      return;
    }

    container.innerHTML =
      '<div class="surface-card" style="margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;">' +
      '  <div><strong>' + R.escHtml(R.t('saved_modal_title')) + '</strong><p style="font-size:12px;color:var(--text-secondary);">' + R.escHtml(R.t('saved_questions_count_caption', { n: list.length })) + '</p></div>' +
      '</div>' +
      '<div class="list-stack">' +
      list.map(function (q, i) {
        return '<article class="surface-card">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px;">' +
          '  <span class="badge-pill badge-neutral">' + R.escHtml(q.category_name || '') + '</span>' +
          '  <button type="button" class="btn btn-sm btn-ghost" data-unbookmark="' + R.escHtml(q.canonical_id) + '">' + R.icon('trash', 'xs') + ' ' + R.escHtml(R.t('btn_remove_saved')) + '</button>' +
          '</div>' +
          (q.image_url ? '<div class="quiz-media-frame" style="margin-bottom:10px;" data-zoom-src="' + R.escHtml(q.image_url) + '"><img src="' + R.escHtml(q.image_url) + '" alt="" loading="lazy"></div>' : '') +
          '<p style="font-weight:700;font-size:14px;margin-bottom:8px;">' + (i + 1) + '. ' + R.escHtml(q.question_text) + '</p>' +
          '<div class="badge-pill badge-emerald" style="margin-bottom:8px;">' + R.escHtml(R.t('saved_correct_answer_label')) + ' ' + R.escHtml(q.correct_option_key || '') + ' — ' + R.escHtml(q.correct_answer_text || '') + '</div>' +
          (q.explanation ? '<p style="font-size:12.5px;color:var(--text-secondary);margin-bottom:10px;">' + R.escHtml(q.explanation) + '</p>' : '') +
          '<button type="button" class="btn btn-sm btn-secondary" data-saved-ask-ai="' + i + '">' + R.icon('sparkles', 'xs') + ' ' + R.escHtml(R.t('btn_ask_ai_saved')) + '</button>' +
          '</article>';
      }).join('') +
      '</div>';

    container.querySelectorAll('[data-zoom-src]').forEach(function (el) {
      el.addEventListener('click', function () { R.openLightbox(el.dataset.zoomSrc); });
    });

    container.querySelectorAll('[data-unbookmark]').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        const cid = btn.dataset.unbookmark;
        await R.api('/api/bookmarks/toggle', { method: 'POST', body: { canonical_id: cid } });
        R.state.bookmarksList = R.state.bookmarksList.filter(function (x) { return x.canonical_id !== cid; });
        R.state.bookmarksCount = R.state.bookmarksList.length;
        R.showToast(R.t('saved_removed_toast'));
        renderSavedTab(container);
      });
    });

    container.querySelectorAll('[data-saved-ask-ai]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const q = R.state.bookmarksList[Number(btn.dataset.savedAskAi)];
        if (q) R.askAiAboutQuestion(q, q.correct_option_key, true);
      });
    });
  }

  R.renderPrepare = function () {
    const root = document.getElementById('view-tests');
    if (!root) return;

    const sub = R.state.prepareSubtab || 'topics';
    root.innerHTML =
      '<div class="subtab-bar subtab-bar-scroll" role="tablist">' +
      '  <button type="button" class="subtab-btn ' + (sub === 'topics' ? 'active' : '') + '" data-prep-tab="topics">' + R.escHtml(R.t('tab_categories')) + '</button>' +
      '  <button type="button" class="subtab-btn ' + (sub === 'tickets' ? 'active' : '') + '" data-prep-tab="tickets">' + R.escHtml(R.t('tab_tickets')) + '</button>' +
      '  <button type="button" class="subtab-btn ' + (sub === 'signs' ? 'active' : '') + '" data-prep-tab="signs">' + R.escHtml(R.t('tab_signs')) + '</button>' +
      '  <button type="button" class="subtab-btn ' + (sub === 'rules' ? 'active' : '') + '" data-prep-tab="rules">' + R.escHtml(R.t('tab_rules')) + '</button>' +
      '  <button type="button" class="subtab-btn ' + (sub === 'adaptive' ? 'active' : '') + '" data-prep-tab="adaptive">' + R.escHtml(R.t('tab_adaptive')) + '</button>' +
      '  <button type="button" class="subtab-btn ' + (sub === 'saved' ? 'active' : '') + '" data-prep-tab="saved">' + R.escHtml(R.t('tab_saved')) + '</button>' +
      '</div>' +
      '<div id="prepare-subtab-body"></div>';

    root.querySelectorAll('[data-prep-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.state.prepareSubtab = btn.dataset.prepTab;
        R.renderPrepare();
        R.loadPrepareData();
      });
    });

    const body = document.getElementById('prepare-subtab-body');
    if (sub === 'topics') renderTopicsTab(body);
    else if (sub === 'tickets') renderTicketsTab(body);
    else if (sub === 'signs') { if (typeof R.renderSignsExplorer === 'function') R.renderSignsExplorer(body); }
    else if (sub === 'rules') { if (typeof R.renderLawExplorer === 'function') R.renderLawExplorer(body); }
    else if (sub === 'adaptive') renderAdaptiveTab(body);
    else if (sub === 'saved') renderSavedTab(body);
  };
})();
