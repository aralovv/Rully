/**
 * RULLY 2.0 Nazariya (Theory) View — 4-Subtab Clean IA:
 * 1. tickets   — Official VMQ 408 Tickets (01..67)
 * 2. topics    — 41 YHQ Categories with mastery tracking
 * 3. drill     — Official Exam + Active Mistakes + SM-2 SRS + Custom Drill + Bookmarks
 * 4. reference — Statutory Road Signs + VMQ 172 Law Reader + Cheatsheet
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});
  let topicFilter = 'all'; // 'all' | 'weak' | 'unstarted'
  let ticketFilter = 'all'; // 'all' | 'unpassed' | 'passed'

  function normalizeSubtab(raw) {
    const k = String(raw || '').toLowerCase();
    if (k === 'tickets' || k === 'bilet' || k === 'bilets') return 'tickets';
    if (k === 'topics' || k === 'categories' || k === 'mavzular') return 'topics';
    if (k === 'drill' || k === 'adaptive' || k === 'srs' || k === 'takrorlash' || k === 'saved' || k === 'mistakes' || k === 'custom') {
      return 'drill';
    }
    if (k === 'reference' || k === 'signs' || k === 'belgilar' || k === 'rules' || k === 'qoidalar' || k === 'law') {
      return 'reference';
    }
    return 'tickets';
  }

  R.loadPrepareData = async function () {
    const lang = R.state.lang || 'uz_latn';
    const sub = normalizeSubtab(R.state.prepareSubtab || 'tickets');
    R.state.prepareSubtab = sub;
    if (R.state.isGuest) {
      if (sub === 'reference') {
        if (R.state.refSubMode === 'rules' && typeof R.loadReferenceLaw === 'function') await R.loadReferenceLaw();
        else if (typeof R.loadReferenceSigns === 'function') await R.loadReferenceSigns();
      }
      R.renderPrepare();
      return;
    }

    const tasks = [];
    if (!R.state.categories || !R.state.categories.length) {
      tasks.push(R.api('/api/categories?lang=' + lang).then(function (d) { R.state.categories = d.categories || []; }));
    }
    if (sub === 'tickets' && (!R.state.tickets || !R.state.tickets.length)) {
      tasks.push(R.api('/api/tickets?lang=' + lang).then(function (d) { R.state.tickets = d.tickets || []; }));
    }
    if ((sub === 'topics' || sub === 'drill') && !R.state.analytics) {
      tasks.push(R.api('/api/learning/analytics?lang=' + lang).then(function (d) { R.state.analytics = d; }));
    }
    if (sub === 'drill') {
      tasks.push(R.api('/api/srs/queue?lang=' + lang + '&limit=10').then(function (d) { R.state.srsQueue = d; }));
      if (!R.state.bookmarksLoaded) {
        tasks.push(R.api('/api/bookmarks?lang=' + lang).then(function (d) {
          R.state.bookmarksList = d.questions || d.bookmarks || [];
          R.state.bookmarksCount = Number(d.count != null ? d.count : R.state.bookmarksList.length);
          R.state.bookmarksLoaded = true;
        }));
      }
    }
    if (sub === 'reference') {
      if (R.state.refSubMode === 'rules' && typeof R.loadReferenceLaw === 'function') tasks.push(R.loadReferenceLaw());
      else if (typeof R.loadReferenceSigns === 'function') tasks.push(R.loadReferenceSigns());
    }

    if (tasks.length) {
      try {
        await Promise.all(tasks);
      } catch (e) {}
    }
    R.renderPrepare();
  };

  function buildMasteryMap() {
    const map = {};
    const rows = (R.state.analytics && R.state.analytics.category_mastery) || [];
    rows.forEach(function (r) { map[Number(r.category_id)] = r; });
    return map;
  }

  function renderTicketsTab(container) {
    if (R.state.isGuest) {
      container.innerHTML =
        '<div class="surface-card" style="text-align:center;padding:24px 16px;">' +
        '  <strong style="display:block;font-size:15px;margin-bottom:6px;">' + R.escHtml(R.t('tab_tickets')) + '</strong>' +
        '  <p style="font-size:12.5px;color:var(--text-secondary);margin-bottom:14px;">' + R.escHtml(R.t('guest_sync_note')) + '</p>' +
        '  <button type="button" class="btn btn-primary btn-sm" id="prep-guest-ref-btn">' + R.escHtml(R.t('tab_reference')) + '</button>' +
        '</div>';
      document.getElementById('prep-guest-ref-btn')?.addEventListener('click', function () {
        R.state.prepareSubtab = 'reference';
        R.renderPrepare();
        R.loadPrepareData();
      });
      return;
    }

    const tickets = R.state.tickets || [];
    if (!tickets.length) {
      container.innerHTML = '<div class="tickets-grid">' +
        Array(6).fill('<div class="surface-card skeleton-block" style="height:82px;"></div>').join('') +
        '</div>';
      return;
    }

    const passedCount = tickets.filter(function (t) { return Boolean(t.is_passed); }).length;
    const pct = Math.round((passedCount / Math.max(1, tickets.length)) * 100);
    const searchVal = (R.state.ticketSearch || '').toLowerCase();

    const filtered = tickets.filter(function (t) {
      if (ticketFilter === 'passed' && !t.is_passed) return false;
      if (ticketFilter === 'unpassed' && t.is_passed) return false;
      if (!searchVal) return true;
      const topicTxt = String(t.primary_topic || t.topic_hint || '').toLowerCase();
      return String(t.ticket_number).includes(searchVal) || topicTxt.includes(searchVal);
    });

    container.innerHTML =
      '<div class="surface-card" style="margin-bottom:12px;">' +
      '  <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:8px;">' +
      '    <div><strong style="font-size:14.5px;">' + R.escHtml(R.t('tickets_header_title')) + '</strong><p style="font-size:12px;color:var(--text-secondary);">' + R.escHtml(R.t('tickets_header_sub')) + '</p></div>' +
      '    <span class="badge-pill badge-emerald font-mono">' + passedCount + ' / ' + tickets.length + ' (' + pct + '%)</span>' +
      '  </div>' +
      '  <div class="progress-track"><div class="progress-fill emerald" style="width:' + pct + '%"></div></div>' +
      '</div>' +
      '<div class="toolbar-row">' +
      '  <div class="search-box">' + R.icon('search', 'sm') +
      '    <input type="search" class="search-input" id="ticket-search-input" placeholder="' + R.escHtml(R.t('tickets_search_ph')) + '" value="' + R.escHtml(R.state.ticketSearch || '') + '">' +
      '  </div>' +
      '  <div class="filter-chip-row">' +
      '    <button type="button" class="filter-chip ' + (ticketFilter === 'all' ? 'active' : '') + '" data-tkt-filter="all">' + R.escHtml(R.t('filter_all')) + '</button>' +
      '    <button type="button" class="filter-chip ' + (ticketFilter === 'unpassed' ? 'active' : '') + '" data-tkt-filter="unpassed">' + R.escHtml(R.t('filter_unpassed')) + '</button>' +
      '    <button type="button" class="filter-chip ' + (ticketFilter === 'passed' ? 'active' : '') + '" data-tkt-filter="passed">' + R.escHtml(R.t('filter_passed')) + '</button>' +
      '  </div>' +
      '</div>' +
      '<div class="tickets-grid">' +
      filtered.map(function (t) {
        const qCount = Number(t.question_count != null ? t.question_count : (t.total_questions || 20));
        const badgeCls = t.is_passed ? 'badge-emerald' : (t.attempts_count > 0 ? 'badge-amber' : 'badge-neutral');
        const badgeTxt = t.is_passed
          ? R.escHtml(t.best_percentage + '% ✓')
          : (t.attempts_count > 0 ? R.escHtml(t.best_percentage + '%') : R.escHtml(R.t('questions_count', { n: qCount })));
        return '<button type="button" class="surface-card card-interactive ticket-card" data-ticket-num="' + t.ticket_number + '">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;">' +
          '  <span class="ticket-num">#' + String(t.ticket_number).padStart(2, '0') + '</span>' +
          '  <span class="badge-pill ' + badgeCls + ' font-mono">' + badgeTxt + '</span>' +
          '</div>' +
          '<div class="ticket-topic-hint">' + R.escHtml(t.primary_topic || t.topic_hint || R.t('ticket_official_label')) + '</div>' +
          '</button>';
      }).join('') +
      '</div>';

    document.getElementById('ticket-search-input')?.addEventListener('input', function (e) {
      R.state.ticketSearch = e.target.value;
      renderTicketsTab(container);
      const inp = document.getElementById('ticket-search-input');
      if (inp) { inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); }
    });

    container.querySelectorAll('[data-tkt-filter]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        ticketFilter = btn.dataset.tktFilter;
        renderTicketsTab(container);
      });
    });

    container.querySelectorAll('[data-ticket-num]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.startSession({ session_type: 'BILET', ticket_number: Number(btn.dataset.ticketNum) });
      });
    });
  }

  function renderTopicsTab(container) {
    if (R.state.isGuest) {
      container.innerHTML =
        '<div class="surface-card" style="text-align:center;padding:24px 16px;">' +
        '  <strong style="display:block;font-size:15px;margin-bottom:6px;">' + R.escHtml(R.t('tab_categories')) + '</strong>' +
        '  <p style="font-size:12.5px;color:var(--text-secondary);margin-bottom:14px;">' + R.escHtml(R.t('guest_sync_note')) + '</p>' +
        '  <button type="button" class="btn btn-primary btn-sm" id="prep-guest-ref-btn2">' + R.escHtml(R.t('tab_reference')) + '</button>' +
        '</div>';
      document.getElementById('prep-guest-ref-btn2')?.addEventListener('click', function () {
        R.state.prepareSubtab = 'reference';
        R.renderPrepare();
        R.loadPrepareData();
      });
      return;
    }

    const cats = R.state.categories || [];
    if (!cats.length) {
      container.innerHTML = '<div class="topics-grid">' +
        Array(6).fill('<div class="surface-card skeleton-block" style="height:98px;"></div>').join('') +
        '</div>';
      return;
    }

    const mMap = buildMasteryMap();
    const st = R.state.stats || {};
    const q = (R.state.topicSearch || '').toLowerCase();

    const filtered = cats.filter(function (c) {
      const m = mMap[Number(c.category_id)] || {};
      const mPct = Number(m.mastery_pct || 0);
      const ansCount = Number(m.unique_answered || 0);
      if (topicFilter === 'weak' && !(ansCount > 0 && mPct < 80)) return false;
      if (topicFilter === 'unstarted' && ansCount > 0) return false;
      if (!q) return true;
      return String(c.name || '').toLowerCase().includes(q) || String(c.category_id).includes(q);
    });

    const catCount = cats.length || 41;
    const catTested = Math.min(catCount, Number(st.categories_tested || 0));
    const covPct = Number(st.catalog_coverage_pct || 0).toFixed(0);

    container.innerHTML =
      '<div class="surface-card" style="margin-bottom:12px;">' +
      '  <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;">' +
      '    <div><strong style="font-size:14.5px;">' + R.escHtml(R.t('topics_overview_title', { total: catCount })) + '</strong><p style="font-size:12px;color:var(--text-secondary);">' + R.escHtml(R.t('topics_overview_desc', { tested: catTested, total: catCount, cov: covPct })) + '</p></div>' +
      '    <span class="badge-pill badge-primary font-mono">' + catTested + ' / ' + catCount + '</span>' +
      '  </div>' +
      '</div>' +
      '<div class="toolbar-row">' +
      '  <div class="search-box">' + R.icon('search', 'sm') +
      '    <input type="search" class="search-input" id="topic-search-input" placeholder="' + R.escHtml(R.t('search_topics_ph')) + '" value="' + R.escHtml(R.state.topicSearch || '') + '">' +
      '  </div>' +
      '  <div class="filter-chip-row">' +
      '    <button type="button" class="filter-chip ' + (topicFilter === 'all' ? 'active' : '') + '" data-top-filter="all">' + R.escHtml(R.t('filter_all')) + '</button>' +
      '    <button type="button" class="filter-chip ' + (topicFilter === 'weak' ? 'active' : '') + '" data-top-filter="weak">' + R.escHtml(R.t('filter_weak')) + '</button>' +
      '    <button type="button" class="filter-chip ' + (topicFilter === 'unstarted' ? 'active' : '') + '" data-top-filter="unstarted">' + R.escHtml(R.t('filter_unstarted')) + '</button>' +
      '  </div>' +
      '</div>' +
      (filtered.length
        ? '<div class="topics-grid">' +
          filtered.map(function (c) {
            const cid = Number(c.category_id);
            const m = mMap[cid] || {};
            const mPct = Math.round(Number(m.mastery_pct || 0));
            const activeErr = Number(m.unresolved_mistakes != null ? m.unresolved_mistakes : (m.active_mistakes || 0));
            const barCls = mPct >= 80 ? 'emerald' : (mPct > 0 ? 'amber' : '');
            return '<button type="button" class="surface-card card-interactive topic-card" data-cat-id="' + cid + '" data-cat-q="' + (c.question_count || 20) + '">' +
              '<div class="topic-card-head">' +
              '  <span class="badge-pill badge-neutral font-mono">#' + cid + ' • ' + (c.question_count || 0) + '</span>' +
              '  <div style="display:flex;gap:4px;">' +
              (activeErr > 0 ? '<span class="badge-pill badge-rose font-mono">' + activeErr + ' !</span>' : '') +
              '    <span class="badge-pill ' + (mPct >= 80 ? 'badge-emerald' : 'badge-neutral') + ' font-mono">' + mPct + '%</span>' +
              '  </div>' +
              '</div>' +
              '<div class="topic-name">' + R.escHtml(c.name) + '</div>' +
              '<div class="progress-track"><div class="progress-fill ' + barCls + '" style="width:' + Math.min(100, mPct) + '%"></div></div>' +
              '</button>';
          }).join('') +
          '</div>'
        : '<div class="surface-card empty-state-box">' + R.escHtml(R.t('no_topics_found')) + '</div>');

    document.getElementById('topic-search-input')?.addEventListener('input', function (e) {
      R.state.topicSearch = e.target.value;
      renderTopicsTab(container);
      const inp = document.getElementById('topic-search-input');
      if (inp) { inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); }
    });

    container.querySelectorAll('[data-top-filter]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        topicFilter = btn.dataset.topFilter;
        renderTopicsTab(container);
      });
    });

    container.querySelectorAll('[data-cat-id]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const cid = Number(btn.dataset.catId);
        const total = Math.min(20, Number(btn.dataset.catQ) || 20);
        R.startSession({ session_type: 'CATEGORY', category_id: cid, total_questions: total });
      });
    });
  }

  function renderDrillTab(container) {
    if (R.state.isGuest) {
      container.innerHTML =
        '<div class="surface-card" style="text-align:center;padding:24px 16px;">' +
        '  <strong style="display:block;font-size:15px;margin-bottom:6px;">' + R.escHtml(R.t('tab_drill')) + '</strong>' +
        '  <p style="font-size:12.5px;color:var(--text-secondary);margin-bottom:14px;">' + R.escHtml(R.t('guest_sync_note')) + '</p>' +
        '  <button type="button" class="btn btn-primary btn-sm" id="prep-guest-sign-btn">' + R.escHtml(R.t('tab_reference')) + '</button>' +
        '</div>';
      document.getElementById('prep-guest-sign-btn')?.addEventListener('click', function () {
        R.state.prepareSubtab = 'reference';
        R.renderPrepare();
        R.loadPrepareData();
      });
      return;
    }

    const st = R.state.stats || {};
    const cats = R.state.categories || [];
    const mistakesCnt = Number(st.unresolved_mistakes || 0);
    const srsObj = R.state.srsQueue || {};
    const srsSum = srsObj.summary || st.srs_summary || { tracked_count: 0, mastered_count: 0, due_now_count: 0, retention_rate: 0 };
    const srsQueue = srsObj.items || srsObj.queue || [];
    const trackedCount = Number(srsSum.tracked_count || 0);
    const dueNow = Number(srsSum.due_now_count || 0);
    const masteredCnt = Number(srsSum.mastered_count || 0);
    const retentionPct = trackedCount > 0 ? Math.round(Number(srsSum.retention_rate || 0)) : 0;
    const bookmarks = R.state.bookmarksList || [];
    const bmCount = Number(R.state.bookmarksCount != null ? R.state.bookmarksCount : bookmarks.length);

    container.innerHTML =
      '<div class="list-stack" style="gap:12px;">' +
      // 1. Official Exam + Active Mistakes pair
      '  <div class="builder-grid">' +
      '    <button type="button" class="surface-card card-interactive action-tile" id="btn-drill-official-exam">' +
      '      <div class="tile-icon-box badge-primary">' + R.icon('zap', 'lg') + '</div>' +
      '      <div class="tile-body">' +
      '        <div class="tile-title">' + R.escHtml(R.t('hero_title')) + '</div>' +
      '        <div class="tile-desc">' + R.escHtml(R.t('exam_spec_short')) + '</div>' +
      '      </div>' +
      '    </button>' +
      '    <button type="button" class="surface-card card-interactive action-tile" id="btn-drill-mistakes">' +
      '      <div class="tile-icon-box ' + (mistakesCnt > 0 ? 'badge-rose' : 'badge-emerald') + '">' + R.icon('alertTriangle', 'lg') + '</div>' +
      '      <div class="tile-body">' +
      '        <div class="tile-title">' + R.escHtml(R.t('card_mistakes_title')) + ' <span class="badge-pill ' + (mistakesCnt > 0 ? 'badge-rose' : 'badge-emerald') + ' font-mono">' + mistakesCnt + '</span></div>' +
      '        <div class="tile-desc">' + R.escHtml(mistakesCnt > 0 ? R.t('card_mistakes_has', { n: mistakesCnt }) : R.t('mistakes_zero_title')) + '</div>' +
      '      </div>' +
      '    </button>' +
      '  </div>' +

      // 2. SM-2 Aqlli Takrorlash + Adaptive Engine
      '  <div class="surface-card srs-hero-card">' +
      '    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap;margin-bottom:10px;">' +
      '      <div>' +
      '        <span class="badge-pill badge-primary">SM-2</span>' +
      '        <h3 style="font-size:15.5px;font-weight:700;margin-top:6px;">' + R.escHtml(R.t('srs_mode_title')) + '</h3>' +
      '        <p style="font-size:12.5px;color:var(--text-secondary);">' + R.escHtml(R.t('srs_subtitle')) + '</p>' +
      '      </div>' +
      '      <div style="display:flex;gap:8px;flex-wrap:wrap;">' +
      '        <button type="button" class="btn btn-primary btn-sm" id="btn-launch-srs">' + R.icon('zap', 'xs') + ' ' + R.escHtml(R.t('btn_start_srs')) + '</button>' +
      '        <button type="button" class="btn btn-secondary btn-sm" id="btn-launch-adaptive">' + R.icon('target', 'xs') + ' ' + R.escHtml(R.t('btn_start_adaptive')) + '</button>' +
      '      </div>' +
      '    </div>' +
      '    <div class="srs-stats-strip">' +
      '      <div class="srs-stat-box"><span class="srs-stat-val font-mono">' + dueNow + '</span><span class="srs-stat-lbl">' + R.escHtml(R.t('srs_due_now_lbl')) + '</span></div>' +
      '      <div class="srs-stat-box"><span class="srs-stat-val font-mono text-emerald">' + masteredCnt + '</span><span class="srs-stat-lbl">' + R.escHtml(R.t('srs_mastered_lbl')) + '</span></div>' +
      '      <div class="srs-stat-box"><span class="srs-stat-val font-mono">' + retentionPct + '%</span><span class="srs-stat-lbl">' + R.escHtml(R.t('srs_retention_lbl')) + '</span></div>' +
      '    </div>' +
      (srsQueue.length ? (
        '<div class="srs-queue-list" style="margin-top:10px;">' +
        srsQueue.slice(0, 4).map(function (it) {
          return '<div class="srs-queue-row">' +
            '<span style="font-size:12.5px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + R.escHtml(it.question_text || it.canonical_id) + '</span>' +
            '<span class="badge-pill badge-amber font-mono">' + R.escHtml(it.difficulty_label || (it.interval_days + 'd')) + '</span>' +
            '</div>';
        }).join('') +
        '</div>'
      ) : '') +
      '  </div>' +

      // 3. Custom Quiz Builder
      '  <div class="surface-card custom-builder-card">' +
      '    <h3 style="font-size:15px;font-weight:700;margin-bottom:4px;">' + R.escHtml(R.t('custom_builder_title')) + '</h3>' +
      '    <p style="font-size:12.5px;color:var(--text-secondary);margin-bottom:12px;">' + R.escHtml(R.t('custom_quiz_card_desc')) + '</p>' +
      '    <div class="builder-grid">' +
      '      <div>' +
      '        <label style="font-size:12px;font-weight:600;display:block;margin-bottom:4px;">' + R.escHtml(R.t('tab_categories')) + '</label>' +
      '        <select class="search-input" id="custom-cat-select" style="width:100%;border:1px solid var(--border-hairline);border-radius:var(--radius-sm);padding:8px 10px;">' +
      '          <option value="">' + R.escHtml(R.t('filter_all')) + '</option>' +
      cats.map(function (c) {
        return '<option value="' + c.category_id + '">' + R.escHtml(c.name) + ' (' + (c.question_count || 0) + ')</option>';
      }).join('') +
      '        </select>' +
      '      </div>' +
      '      <div>' +
      '        <label style="font-size:12px;font-weight:600;display:block;margin-bottom:4px;">' + R.escHtml(R.t('setting_q_count')) + '</label>' +
      '        <div class="seg-pills" id="custom-count-pills">' +
      '          <button type="button" class="seg-pill" data-qcnt="10">10</button>' +
      '          <button type="button" class="seg-pill active" data-qcnt="20">20</button>' +
      '          <button type="button" class="seg-pill" data-qcnt="30">30</button>' +
      '        </div>' +
      '      </div>' +
      '    </div>' +
      '    <div class="toggle-row" style="margin-top:12px;">' +
      '      <label style="display:flex;align-items:center;gap:8px;font-size:13px;cursor:pointer;">' +
      '        <input type="checkbox" id="custom-show-ans" checked> ' + R.escHtml(R.t('setting_show_answer')) +
      '      </label>' +
      '      <button type="button" class="btn btn-primary btn-sm" id="btn-launch-custom">' + R.escHtml(R.t('btn_start_custom_quiz')) + '</button>' +
      '    </div>' +
      '  </div>' +

      // 4. Saved Bookmarks (integrated cleanly, zero extra tab needed)
      '  <div class="surface-card">' +
      '    <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:10px;">' +
      '      <div style="display:flex;align-items:center;gap:8px;">' +
      '        <strong style="font-size:14.5px;">' + R.escHtml(R.t('tab_saved')) + '</strong>' +
      '        <span class="badge-pill badge-neutral font-mono">' + bmCount + '</span>' +
      '      </div>' +
      '    </div>' +
      (bookmarks.length ? (
        '<div class="list-stack">' +
        bookmarks.slice(0, 12).map(function (b) {
          return '<div class="data-row-card">' +
            '<div style="flex:1;min-width:0;">' +
            '  <div style="font-size:13px;font-weight:600;margin-bottom:2px;">' + R.escHtml(b.question_text || '') + '</div>' +
            '  <div style="font-size:11.5px;color:var(--text-muted);">' + R.escHtml(b.category_name || '') + '</div>' +
            '</div>' +
            '<div style="display:flex;gap:6px;flex-shrink:0;">' +
            (b.image_url ? '<button type="button" class="icon-pill-btn" data-zoom-src="' + R.escHtml(R.safeUrl(b.image_url)) + '" aria-label="Zoom">' + R.icon('eye', 'xs') + '</button>' : '') +
            '  <button type="button" class="icon-pill-btn" data-rm-bookmark="' + R.escHtml(b.canonical_id) + '" aria-label="Remove">' + R.icon('bookmark', 'xs') + '</button>' +
            '</div>' +
            '</div>';
        }).join('') +
        '</div>'
      ) : '<div class="empty-state-box" style="padding:14px;">' + R.escHtml(R.t('saved_empty_title')) + '</div>') +
      '  </div>' +
      '</div>';

    document.getElementById('btn-drill-official-exam')?.addEventListener('click', function () {
      R.startSession({ session_type: 'EXAM' });
    });
    document.getElementById('btn-drill-mistakes')?.addEventListener('click', function () {
      R.startSession({ session_type: 'MISTAKES', total_questions: 30 });
    });
    document.getElementById('btn-launch-srs')?.addEventListener('click', function () {
      R.startSession({ session_type: 'SRS', total_questions: 20 });
    });
    document.getElementById('btn-launch-adaptive')?.addEventListener('click', function () {
      R.startSession({ session_type: 'ADAPTIVE', total_questions: 20 });
    });

    let customCount = 20;
    container.querySelectorAll('#custom-count-pills [data-qcnt]').forEach(function (pill) {
      pill.addEventListener('click', function () {
        customCount = Number(pill.dataset.qcnt) || 20;
        container.querySelectorAll('#custom-count-pills [data-qcnt]').forEach(function (x) {
          x.classList.toggle('active', x === pill);
        });
      });
    });

    document.getElementById('btn-launch-custom')?.addEventListener('click', function () {
      const catSel = document.getElementById('custom-cat-select');
      const showAns = Boolean(document.getElementById('custom-show-ans')?.checked);
      const cidVal = catSel && catSel.value ? Number(catSel.value) : null;
      R.startSession({
        session_type: 'CUSTOM',
        category_id: cidVal,
        total_questions: customCount,
        show_answer: showAns,
        show_explanation: showAns
      });
    });

    container.querySelectorAll('[data-zoom-src]').forEach(function (el) {
      el.addEventListener('click', function () { R.openLightbox(el.dataset.zoomSrc); });
    });
    container.querySelectorAll('[data-rm-bookmark]').forEach(function (el) {
      el.addEventListener('click', async function () {
        const cid = el.dataset.rmBookmark;
        try {
          await R.api('/api/bookmarks/toggle', { method: 'POST', body: { canonical_id: cid } });
          R.state.bookmarksList = (R.state.bookmarksList || []).filter(function (x) { return x.canonical_id !== cid; });
          R.state.bookmarksCount = R.state.bookmarksList.length;
          R.state.bookmarksLoaded = false;
          renderDrillTab(container);
        } catch (e) {}
      });
    });
  }

  function renderReferenceTab(container) {
    const mode = R.state.refSubMode === 'rules' ? 'rules' : 'signs';
    R.state.refSubMode = mode;

    container.innerHTML =
      '<div class="toolbar-row" style="justify-content:space-between;align-items:center;margin-bottom:12px;">' +
      '  <div class="seg-pills">' +
      '    <button type="button" class="seg-pill ' + (mode === 'signs' ? 'active' : '') + '" data-ref-mode="signs">' + R.icon('compass', 'xs') + ' ' + R.escHtml(R.t('tab_signs')) + '</button>' +
      '    <button type="button" class="seg-pill ' + (mode === 'rules' ? 'active' : '') + '" data-ref-mode="rules">' + R.icon('bookOpen', 'xs') + ' ' + R.escHtml(R.t('tab_rules')) + '</button>' +
      '  </div>' +
      '  <button type="button" class="btn btn-sm btn-secondary" id="btn-prep-cheatsheet">' + R.icon('sparkles', 'xs') + ' ' + R.escHtml(R.t('card_cheatsheet_title')) + '</button>' +
      '</div>' +
      '<div id="ref-sub-container"></div>';

    container.querySelectorAll('[data-ref-mode]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.state.refSubMode = btn.dataset.refMode;
        if (R.state.activeTab === 'tests' && window.history && window.history.replaceState) {
          window.history.replaceState(null, '', '#tests/reference/' + R.state.refSubMode);
        }
        R.renderPrepare();
        R.loadPrepareData();
      });
    });

    document.getElementById('btn-prep-cheatsheet')?.addEventListener('click', function () {
      if (typeof R.openCheatsheetModal === 'function') R.openCheatsheetModal();
    });

    const bodyEl = document.getElementById('ref-sub-container');
    if (mode === 'rules') {
      if (typeof R.renderLawExplorer === 'function') R.renderLawExplorer(bodyEl, R.state.lawHighlightChapter || null);
    } else {
      if (typeof R.renderSignsExplorer === 'function') R.renderSignsExplorer(bodyEl);
    }
  }

  R.renderPrepare = function () {
    const root = document.getElementById('view-tests');
    if (!root) return;

    const sub = normalizeSubtab(R.state.prepareSubtab || 'tickets');
    R.state.prepareSubtab = sub;

    root.innerHTML =
      '<div style="margin-bottom:10px;">' +
      '  <h2 style="font-family:var(--font-display);font-size:18px;font-weight:800;">' + R.escHtml(R.t('nav_tests')) + '</h2>' +
      '</div>' +
      '<div class="subtab-bar" role="tablist">' +
      '  <button type="button" class="subtab-btn ' + (sub === 'tickets' ? 'active' : '') + '" data-prep-tab="tickets">' + R.escHtml(R.t('tab_tickets')) + '</button>' +
      '  <button type="button" class="subtab-btn ' + (sub === 'topics' ? 'active' : '') + '" data-prep-tab="topics">' + R.escHtml(R.t('tab_categories')) + '</button>' +
      '  <button type="button" class="subtab-btn ' + (sub === 'drill' ? 'active' : '') + '" data-prep-tab="drill">' + R.escHtml(R.t('tab_drill')) + '</button>' +
      '  <button type="button" class="subtab-btn ' + (sub === 'reference' ? 'active' : '') + '" data-prep-tab="reference">' + R.escHtml(R.t('tab_reference')) + '</button>' +
      '</div>' +
      '<div id="prepare-subtab-body"></div>';

    root.querySelectorAll('[data-prep-tab]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const nextSub = normalizeSubtab(btn.dataset.prepTab);
        R.state.prepareSubtab = nextSub;
        if (R.state.activeTab === 'tests' && window.history && window.history.replaceState) {
          const refSuffix = nextSub === 'reference' ? '/' + (R.state.refSubMode === 'rules' ? 'rules' : 'signs') : '';
          window.history.replaceState(null, '', '#tests/' + nextSub + refSuffix);
        }
        R.renderPrepare();
        R.loadPrepareData();
      });
    });

    const body = document.getElementById('prepare-subtab-body');
    if (sub === 'topics') renderTopicsTab(body);
    else if (sub === 'drill') renderDrillTab(body);
    else if (sub === 'reference') renderReferenceTab(body);
    else renderTicketsTab(body);
  };
})();
