/**
 * RULLY 2.0 Phase 4 Reference Hub:
 * - Visual Uzbekistan Annex 1 Road Signs Explorer (SVG geometric vector glyphs + group drill launch)
 * - VMQ No. 172 (29 Chapters) & VMQ No. 408 Interactive Law Reader & Rules Norms
 * - Legal Provenance Verification Badge & Instant Law Reference Drawer
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});

  function parseChapterNum(refStr, chStr) {
    const src = String(chStr || '') + ' ' + String(refStr || '');
    const m = src.match(/(\d+)\s*[-–]?\s*(?:bob|боб|chapter|глав[аые]?)|\bглав[аые]?\s*(\d+)/i);
    if (!m) return null;
    return Number(m[1] || m[2]) || null;
  }

  R.renderProvenanceBadge = function (item, contextId) {
    if (!item) return '';
    const status = item.legal_verification_status || '';
    const refText = item.legal_reference || '';
    const chPart = item.legal_chapter || '';
    const clPart = item.legal_clause || '';
    const structuredRef = [chPart, clPart].filter(Boolean).join(', ');
    const displayRef = refText || structuredRef;
    const chapNum = parseChapterNum(refText, chPart);

    let badge = '';
    if (status === 'VERIFIED_PRIMARY_LAW') {
      badge = '<span class="badge-pill badge-emerald">' + R.icon('checkCircle', 'xs') + ' ' + R.escHtml(R.t('prov_verified_law')) + '</span>';
    } else if (status === 'VERIFIED_FIRST_AID_OR_TECH') {
      badge = '<span class="badge-pill badge-primary">' + R.icon('checkCircle', 'xs') + ' ' + R.escHtml(R.t('prov_verified_tech')) + '</span>';
    } else if (displayRef) {
      badge = '<span class="badge-pill badge-neutral">' + R.icon('bookOpen', 'xs') + ' ' + R.escHtml(R.t('prov_ref_law')) + '</span>';
    }

    const refChip = displayRef
      ? '<button type="button" class="badge-pill badge-neutral law-ref-trigger" data-open-law-ch="' + (chapNum || '') + '"' +
        (contextId ? ' data-law-ctx="' + R.escHtml(contextId) + '"' : '') + '>' +
        R.icon('bookOpen', 'xs') + ' <span>' + R.escHtml(displayRef) + '</span></button>'
      : '';

    if (!badge && !refChip) return '';
    return '<div class="provenance-row">' + badge + refChip + '</div>';
  };

  function signGlyphSvg(s) {
    const g = s.glyph || '';
    const lbl = R.escHtml(s.label || s.code || '');
    if (g === 'rail_barrier') {
      return '<path d="M22 46h28M26 42v8M32 42v8M38 42v8M44 42v8" stroke="#111827" stroke-width="2.2" stroke-linecap="round"/>';
    }
    if (g === 'train') {
      return '<rect x="30" y="34" width="12" height="14" rx="2" fill="#111827"/><circle cx="33" cy="50" r="1.8" fill="#111827"/><circle cx="39" cy="50" r="1.8" fill="#111827"/><path d="M32 32l4-4 4 4" stroke="#111827" stroke-width="2" fill="none"/>';
    }
    if (g === 'turn_right') {
      return '<path d="M30 50V40c0-4 3-7 7-7h4" fill="none" stroke="#111827" stroke-width="3" stroke-linecap="round"/><path d="M38 29l5 4-5 4" fill="#111827"/>';
    }
    if (g === 'slope_down') {
      return '<polygon points="22,38 50,51 22,51" fill="#111827"/><text x="38" y="42" font-size="8.5" font-weight="800" fill="#111827" text-anchor="middle">' + lbl + '</text>';
    }
    if (g === 'slope_up') {
      return '<polygon points="22,51 50,38 50,51" fill="#111827"/><text x="32" y="41" font-size="8.5" font-weight="800" fill="#111827" text-anchor="middle">' + lbl + '</text>';
    }
    if (g === 'slippery') {
      return '<rect x="31" y="31" width="10" height="8" rx="2" fill="#111827"/><path d="M29 42c-3 3 3 5-1 8M43 42c3 3-3 5 1 8" stroke="#111827" stroke-width="2" fill="none" stroke-linecap="round"/>';
    }
    if (g === 'pedestrian' || g === 'children') {
      return '<circle cx="36" cy="31" r="3" fill="#111827"/><path d="M36 35v8l-4 7M36 43l5 7M31 38l5-2 4 3" stroke="#111827" stroke-width="2.4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>';
    }
    if (g === 'roadworks') {
      return '<circle cx="35" cy="31" r="2.6" fill="#111827"/><path d="M34 34l-3 10M34 38l6 4v7" stroke="#111827" stroke-width="2.2" fill="none" stroke-linecap="round"/><polygon points="39,49 47,49 43,43" fill="#111827"/>';
    }
    if (g === 'priority_yield_opp') {
      return '<path d="M29 22v26" stroke="#111827" stroke-width="3.5" stroke-linecap="round"/><polygon points="29,51 24,44 34,44" fill="#111827"/><path d="M43 50V24" stroke="#DC2626" stroke-width="3.5" stroke-linecap="round"/><polygon points="43,20 38,27 48,27" fill="#DC2626"/>';
    }
    if (g === 'priority_me') {
      return '<path d="M29 24v24" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round"/><polygon points="29,20 24,27 34,27" fill="#FFFFFF"/><path d="M43 22v24" stroke="#EF4444" stroke-width="3.5" stroke-linecap="round"/><polygon points="43,51 38,44 48,44" fill="#EF4444"/>';
    }
    if (g === 'brick') {
      return '<rect x="18" y="31" width="36" height="10" rx="2" fill="#FFFFFF"/>';
    }
    if (g === 'car') {
      return '<rect x="22" y="32" width="28" height="11" rx="3" fill="#111827"/><circle cx="28" cy="44" r="3" fill="#111827"/><circle cx="44" cy="44" r="3" fill="#111827"/>';
    }
    if (g === 'truck') {
      return '<rect x="20" y="30" width="20" height="13" rx="2" fill="#111827"/><rect x="41" y="34" width="10" height="9" rx="1.5" fill="#111827"/><circle cx="27" cy="45" r="2.8" fill="#111827"/><circle cx="45" cy="45" r="2.8" fill="#111827"/>';
    }
    if (g === 'no_overtake') {
      return '<rect x="20" y="31" width="12" height="10" rx="2" fill="#DC2626"/><rect x="40" y="31" width="12" height="10" rx="2" fill="#111827"/><line x1="19" y1="53" x2="53" y2="19" stroke="#DC2626" stroke-width="4" stroke-linecap="round"/>';
    }
    if (g === 'no_right') {
      return '<path d="M29 48V35c0-3 2-5 5-5h7" fill="none" stroke="#111827" stroke-width="3.2"/><polygon points="46,30 39,25 39,35" fill="#111827"/><line x1="20" y1="52" x2="52" y2="20" stroke="#DC2626" stroke-width="4" stroke-linecap="round"/>';
    }
    if (g === 'no_left') {
      return '<path d="M43 48V35c0-3-2-5-5-5h-7" fill="none" stroke="#111827" stroke-width="3.2"/><polygon points="26,30 33,25 33,35" fill="#111827"/><line x1="20" y1="52" x2="52" y2="20" stroke="#DC2626" stroke-width="4" stroke-linecap="round"/>';
    }
    if (g === 'no_uturn') {
      return '<path d="M43 49V33a7 7 0 0 0-14 0v12" fill="none" stroke="#111827" stroke-width="3.2"/><polygon points="29,48 24,41 34,41" fill="#111827"/><line x1="20" y1="52" x2="52" y2="20" stroke="#DC2626" stroke-width="4" stroke-linecap="round"/>';
    }
    if (g === 'arrow_up') {
      return '<path d="M36 52V24" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round"/><polygon points="36,16 26,29 46,29" fill="#FFFFFF"/>';
    }
    if (g === 'arrow_right') {
      return '<path d="M20 36h28" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round"/><polygon points="56,36 43,26 43,46" fill="#FFFFFF"/>';
    }
    if (g === 'arrow_left') {
      return '<path d="M52 36H24" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round"/><polygon points="16,36 29,26 29,46" fill="#FFFFFF"/>';
    }
    if (g === 'roundabout') {
      return '<circle cx="36" cy="36" r="14" fill="none" stroke="#FFFFFF" stroke-width="3.8" stroke-dasharray="18 6"/><polygon points="36,18 42,24 31,25" fill="#FFFFFF"/>';
    }
    if (g === 'highway') {
      return '<path d="M28 52l4-32M44 52l-4-32" stroke="#FFFFFF" stroke-width="3.2"/><rect x="20" y="34" width="32" height="4" fill="#FFFFFF"/>';
    }
    if (g === 'one_way') {
      return '<path d="M36 53V24" stroke="#FFFFFF" stroke-width="5" stroke-linecap="round"/><polygon points="36,15 24,30 48,30" fill="#FFFFFF"/>';
    }
    if (g === 'ped_square') {
      return '<polygon points="36,14 57,54 15,54" fill="#FFFFFF"/><circle cx="36" cy="27" r="3" fill="#111827"/><path d="M36 31v9l-4 8M36 40l5 8" stroke="#111827" stroke-width="2.5" fill="none" stroke-linecap="round"/>';
    }
    if (g === 'cross_med') {
      return '<rect x="18" y="18" width="36" height="36" rx="3" fill="#FFFFFF"/><path d="M36 24v24M24 36h24" stroke="#059669" stroke-width="5.5" stroke-linecap="round"/>';
    }
    if (g === 'fuel') {
      return '<rect x="18" y="18" width="36" height="36" rx="3" fill="#FFFFFF"/><rect x="27" y="25" width="14" height="22" rx="2" fill="#111827"/><rect x="30" y="28" width="8" height="6" fill="#FFFFFF"/><path d="M41 30h4v12" stroke="#111827" stroke-width="2" fill="none"/>';
    }
    if (g === 'res_zone') {
      return '<polygon points="22,40 33,28 44,40" fill="#FFFFFF"/><rect x="25" y="40" width="16" height="12" fill="#FFFFFF"/><text x="50" y="32" font-size="11" font-weight="800" fill="#FFFFFF" text-anchor="middle">20</text>';
    }
    if (g === 'priority_turn') {
      return '<path d="M36 46V26h14" fill="none" stroke="#111827" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/><path d="M22 26h14V14" fill="none" stroke="#111827" stroke-width="2" stroke-linecap="round"/>';
    }
    if (g === 'plate_range') {
      return '<path d="M14 38V17" stroke="#111827" stroke-width="2.6" stroke-linecap="round"/><polygon points="14,12 10,19 18,19" fill="#111827"/>' +
        '<path d="M58 38V17" stroke="#111827" stroke-width="2.6" stroke-linecap="round"/><polygon points="58,12 54,19 62,19" fill="#111827"/>' +
        '<text x="36" y="31" font-size="12" font-weight="800" fill="#111827" text-anchor="middle" font-family="var(--font-mono)">100m</text>';
    }
    if (g === 'plate_down') {
      return '<path d="M56 15v21" stroke="#111827" stroke-width="2.6" stroke-linecap="round"/><polygon points="56,41 52,34 60,34" fill="#111827"/>' +
        '<text x="29" y="31" font-size="13" font-weight="800" fill="#111827" text-anchor="middle" font-family="var(--font-mono)">10 m</text>';
    }
    return '';
  }

  R.renderSignSvg = function (s) {
    const sh = s.shape || 'circle_red';
    const lbl = R.escHtml(s.label || '');
    const glyph = signGlyphSvg(s);

    if (sh === 'triangle' || sh === 'triangle_work') {
      const fill = sh === 'triangle_work' ? '#FACC15' : '#FFFFFF';
      return '<svg class="sign-svg" viewBox="0 0 72 68" aria-hidden="true">' +
        '<polygon points="36,6 67,60 5,60" fill="' + fill + '" stroke="#DC2626" stroke-width="6.5" stroke-linejoin="round"/>' +
        glyph +
        '</svg>';
    }
    if (sh === 'inv_triangle') {
      return '<svg class="sign-svg" viewBox="0 0 72 68" aria-hidden="true">' +
        '<polygon points="5,8 67,8 36,62" fill="#FFFFFF" stroke="#DC2626" stroke-width="6.5" stroke-linejoin="round"/>' +
        '</svg>';
    }
    if (sh === 'diamond' || sh === 'diamond_end') {
      return '<svg class="sign-svg" viewBox="0 0 72 72" aria-hidden="true">' +
        '<polygon points="36,4 68,36 36,68 4,36" fill="#FFFFFF" stroke="#111827" stroke-width="2"/>' +
        '<polygon points="36,13 59,36 36,59 13,36" fill="#FACC15" stroke="#111827" stroke-width="1.5"/>' +
        (sh === 'diamond_end' ? '<line x1="17" y1="55" x2="55" y2="17" stroke="#111827" stroke-width="4"/>' : '') +
        '</svg>';
    }
    if (sh === 'octagon') {
      return '<svg class="sign-svg" viewBox="0 0 72 72" aria-hidden="true">' +
        '<polygon points="24,6 48,6 66,24 66,48 48,66 24,66 6,48 6,24" fill="#DC2626" stroke="#FFFFFF" stroke-width="2.5"/>' +
        '<text x="36" y="42" font-size="16" font-weight="900" fill="#FFFFFF" text-anchor="middle" font-family="var(--font-display)">STOP</text>' +
        '</svg>';
    }
    if (sh === 'circle_no_entry') {
      return '<svg class="sign-svg" viewBox="0 0 72 72" aria-hidden="true">' +
        '<circle cx="36" cy="36" r="30" fill="#DC2626" stroke="#FFFFFF" stroke-width="2"/>' +
        glyph +
        '</svg>';
    }
    if (sh === 'circle_red_blue_x' || sh === 'circle_red_blue_slash') {
      return '<svg class="sign-svg" viewBox="0 0 72 72" aria-hidden="true">' +
        '<circle cx="36" cy="36" r="29" fill="#0057FF" stroke="#DC2626" stroke-width="7"/>' +
        '<line x1="16" y1="56" x2="56" y2="16" stroke="#DC2626" stroke-width="6"/>' +
        (sh === 'circle_red_blue_x' ? '<line x1="16" y1="16" x2="56" y2="56" stroke="#DC2626" stroke-width="6"/>' : '') +
        '</svg>';
    }
    if (sh === 'circle_blue') {
      return '<svg class="sign-svg" viewBox="0 0 72 72" aria-hidden="true">' +
        '<circle cx="36" cy="36" r="30" fill="#0057FF" stroke="#FFFFFF" stroke-width="2"/>' +
        (s.glyph === 'text' ? '<text x="36" y="44" font-size="22" font-weight="900" fill="#FFFFFF" text-anchor="middle">' + lbl + '</text>' : glyph) +
        '</svg>';
    }
    if (sh === 'square_blue' || sh === 'square_green' || sh === 'service_blue') {
      const bg = sh === 'square_green' ? '#059669' : '#0057FF';
      return '<svg class="sign-svg" viewBox="0 0 72 72" aria-hidden="true">' +
        '<rect x="7" y="7" width="58" height="58" rx="7" fill="' + bg + '" stroke="#FFFFFF" stroke-width="2"/>' +
        (s.glyph === 'text' ? '<text x="36" y="45" font-size="26" font-weight="900" fill="#FFFFFF" text-anchor="middle">' + lbl + '</text>' : glyph) +
        '</svg>';
    }
    if (sh === 'plate_white') {
      return '<svg class="sign-svg" viewBox="0 0 72 52" aria-hidden="true">' +
        '<rect x="4" y="8" width="64" height="36" rx="5" fill="#FFFFFF" stroke="#111827" stroke-width="2.5"/>' +
        ((s.glyph === 'priority_turn' || s.glyph === 'plate_range' || s.glyph === 'plate_down')
          ? glyph
          : '<text x="36" y="31" font-size="13" font-weight="800" fill="#111827" text-anchor="middle" font-family="var(--font-mono)">' + lbl + '</text>') +
        '</svg>';
    }
    if (sh === 'circle_slash') {
      return '<svg class="sign-svg" viewBox="0 0 72 72" aria-hidden="true">' +
        '<circle cx="36" cy="36" r="29" fill="#FFFFFF" stroke="#DC2626" stroke-width="7"/>' +
        glyph +
        '</svg>';
    }
    return '<svg class="sign-svg" viewBox="0 0 72 72" aria-hidden="true">' +
      '<circle cx="36" cy="36" r="29" fill="#FFFFFF" stroke="#DC2626" stroke-width="7"/>' +
      (s.glyph === 'text'
        ? '<text x="36" y="45" font-size="24" font-weight="900" fill="#111827" text-anchor="middle">' + lbl + '</text>'
        : glyph) +
      '</svg>';
  };

  R.loadReferenceSigns = async function (force) {
    const lang = R.state.lang || 'uz_latn';
    if (!force && R.state.refSigns && R.state.refSigns.language === lang) {
      return R.state.refSigns;
    }
    const data = await R.api('/api/reference/signs?lang=' + encodeURIComponent(lang));
    R.state.refSigns = data;
    return data;
  };

  R.loadReferenceLaw = async function (force) {
    const lang = R.state.lang || 'uz_latn';
    if (!force && R.state.refLaw && R.state.refLaw.language === lang) {
      return R.state.refLaw;
    }
    const data = await R.api('/api/reference/law?lang=' + encodeURIComponent(lang));
    R.state.refLaw = data;
    return data;
  };

  R.openSignDetailModal = function (signObj) {
    if (!signObj) return;
    const titleEl = document.getElementById('info-modal-title');
    const bodyEl = document.getElementById('info-modal-body');
    if (!bodyEl) return;

    const groups = (R.state.refSigns && R.state.refSigns.groups) || [];
    const grp = groups.find(function (g) { return g.id === signObj.group; });

    if (titleEl) titleEl.textContent = signObj.code + ' — ' + signObj.name;
    bodyEl.innerHTML =
      '<div class="surface-card" style="display:flex;align-items:center;gap:16px;">' +
      '  <div class="sign-visual-box lg">' + R.renderSignSvg(signObj) + '</div>' +
      '  <div style="min-width:0;">' +
      '    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px;">' +
      '      <span class="badge-pill badge-primary font-mono">' + R.escHtml(signObj.code) + '</span>' +
      (grp ? '<span class="badge-pill badge-neutral">' + R.escHtml(grp.name) + '</span>' : '') +
      '    </div>' +
      '    <strong style="font-size:15px;">' + R.escHtml(signObj.name) + '</strong>' +
      '  </div>' +
      '</div>' +
      '<div class="surface-card">' +
      '  <strong style="font-size:13px;display:block;margin-bottom:4px;">' + R.escHtml(R.t('ref_sign_rule_title')) + '</strong>' +
      '  <p style="font-size:13px;line-height:1.5;color:var(--text-secondary);">' + R.escHtml(signObj.rule) + '</p>' +
      (grp && grp.distance_rule ? '<p style="font-size:12px;color:var(--text-muted);margin-top:8px;">' + R.escHtml(grp.distance_rule) + '</p>' : '') +
      '</div>' +
      '<button type="button" class="btn btn-primary btn-block" id="btn-sign-practice-cat">' +
      R.icon('zap', 'sm') + '<span>' + R.escHtml(R.t('ref_practice_sign_group')) + '</span>' +
      '</button>';

    document.getElementById('btn-sign-practice-cat')?.addEventListener('click', function () {
      R.closeModal('info-modal');
      R.startSession({ session_type: 'CATEGORY', category_id: Number(signObj.category_id || 21), total_questions: 20 });
    });

    R.openModal('info-modal');
  };

  R.renderSignsExplorer = async function (container) {
    if (!container) return;
    if (!R.state.refSigns || R.state.refSigns.language !== R.state.lang) {
      container.innerHTML = '<div class="signs-grid"><div class="surface-card skeleton-block" style="height:132px;"></div><div class="surface-card skeleton-block" style="height:132px;"></div><div class="surface-card skeleton-block" style="height:132px;"></div><div class="surface-card skeleton-block" style="height:132px;"></div></div>';
      try {
        await R.loadReferenceSigns();
      } catch (err) {
        container.innerHTML = '<div class="surface-card"><p style="color:var(--color-rose);">' + R.escHtml(err.message || R.t('ai_generic_error')) + '</p></div>';
        return;
      }
    }

    const data = R.state.refSigns;
    const grpFilter = R.state.signsGroupFilter || 'all';
    const query = (R.state.signsSearch || '').trim().toLowerCase();

    const filtered = (data.signs || []).filter(function (s) {
      if (grpFilter !== 'all' && s.group !== grpFilter) return false;
      if (query) {
        const hay = (s.code + ' ' + s.name + ' ' + s.rule).toLowerCase();
        if (!hay.includes(query)) return false;
      }
      return true;
    });

    const activeGrp = (data.groups || []).find(function (g) { return g.id === grpFilter; });

    container.innerHTML =
      '<div class="surface-card" style="margin-bottom:12px;">' +
      '  <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:8px;">' +
      '    <div><strong style="font-size:15px;">' + R.escHtml(R.t('ref_signs_title')) + '</strong><p style="font-size:12px;color:var(--text-secondary);">' + R.escHtml(data.source_act || '') + '</p></div>' +
      '    <span class="badge-pill badge-primary font-mono">' + filtered.length + ' / ' + (data.total_signs || filtered.length) + '</span>' +
      '  </div>' +
      '  <div class="search-box" style="margin-bottom:10px;">' +
      '    <span class="search-icon">' + R.icon('search', 'sm') + '</span>' +
      '    <input type="search" class="search-input" id="signs-search-input" value="' + R.escHtml(R.state.signsSearch || '') + '" placeholder="' + R.escHtml(R.t('ref_signs_search_placeholder')) + '">' +
      '  </div>' +
      '  <div class="filter-chip-row">' +
      '    <button type="button" class="filter-chip ' + (grpFilter === 'all' ? 'active' : '') + '" data-sign-grp="all">' + R.escHtml(R.t('filter_all')) + '</button>' +
      (data.groups || []).map(function (g) {
        return '<button type="button" class="filter-chip ' + (grpFilter === g.id ? 'active' : '') + '" data-sign-grp="' + R.escHtml(g.id) + '">' + R.escHtml(g.code_prefix + '. ' + g.name.split(' ')[0]) + '</button>';
      }).join('') +
      '  </div>' +
      (activeGrp
        ? '<div class="law-group-callout"><span>' + R.escHtml(activeGrp.distance_rule) + '</span><button type="button" class="btn btn-sm btn-primary" data-drill-sign-cat="' + activeGrp.category_id + '">' + R.escHtml(R.t('btn_start_category')) + '</button></div>'
        : '') +
      '</div>' +
      (!filtered.length
        ? '<div class="surface-card empty-state-box"><strong>' + R.escHtml(R.t('empty_search_title')) + '</strong><p style="font-size:12.5px;color:var(--text-secondary);">' + R.escHtml(R.t('empty_search_desc')) + '</p></div>'
        : '<div class="signs-grid">' +
          filtered.map(function (s) {
            return '<button type="button" class="surface-card card-interactive sign-card" data-sign-code="' + R.escHtml(s.code) + '">' +
              '  <div class="sign-visual-box">' + R.renderSignSvg(s) + '</div>' +
              '  <span class="badge-pill badge-neutral font-mono" style="margin-top:4px;">' + R.escHtml(s.code) + '</span>' +
              '  <div class="sign-card-title">' + R.escHtml(s.name) + '</div>' +
              '</button>';
          }).join('') +
          '</div>');

    const sInput = document.getElementById('signs-search-input');
    if (sInput) {
      sInput.addEventListener('input', function () {
        R.state.signsSearch = sInput.value;
        R.renderSignsExplorer(container);
        const refocused = document.getElementById('signs-search-input');
        if (refocused) {
          refocused.focus();
          const len = refocused.value.length;
          refocused.setSelectionRange(len, len);
        }
      });
    }

    container.querySelectorAll('[data-sign-grp]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.state.signsGroupFilter = btn.dataset.signGrp;
        R.renderSignsExplorer(container);
      });
    });

    container.querySelectorAll('[data-drill-sign-cat]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.startSession({ session_type: 'CATEGORY', category_id: Number(btn.dataset.drillSignCat), total_questions: 20 });
      });
    });

    container.querySelectorAll('[data-sign-code]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const signObj = (data.signs || []).find(function (x) { return x.code === btn.dataset.signCode; });
        if (signObj) R.openSignDetailModal(signObj);
      });
    });
  };

  R.renderLawExplorer = async function (container, highlightChapter) {
    if (!container) return;
    if (!R.state.refLaw || R.state.refLaw.language !== R.state.lang) {
      container.innerHTML = '<div class="list-stack"><div class="surface-card skeleton-block" style="height:100px;"></div><div class="surface-card skeleton-block" style="height:100px;"></div></div>';
      try {
        await R.loadReferenceLaw();
      } catch (err) {
        container.innerHTML = '<div class="surface-card"><p style="color:var(--color-rose);">' + R.escHtml(err.message || R.t('ai_generic_error')) + '</p></div>';
        return;
      }
    }

    const data = R.state.refLaw;
    const subMode = R.state.lawSubMode || 'chapters';
    const query = (R.state.lawSearch || '').trim().toLowerCase();

    const normsHtml = '<div class="list-stack">' +
      (data.norms || []).map(function (n) {
        return '<div class="surface-card">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px;">' +
          '  <strong style="font-size:14px;">' + R.escHtml(n.title) + '</strong>' +
          '  <span class="badge-pill badge-' + R.escHtml(n.tone || 'primary') + ' font-mono">' + R.escHtml(n.badge) + '</span>' +
          '</div>' +
          '<p style="font-size:12.5px;color:var(--text-secondary);line-height:1.5;">' + R.escHtml(n.detail) + '</p>' +
          '</div>';
      }).join('') +
      '</div>';

    const chapters = (data.chapters || []).filter(function (ch) {
      if (!query) return true;
      return (String(ch.chapter) + ' ' + ch.title + ' ' + ch.summary).toLowerCase().includes(query);
    });

    const chaptersHtml =
      '<div class="search-box" style="margin-bottom:10px;">' +
      '  <span class="search-icon">' + R.icon('search', 'sm') + '</span>' +
      '  <input type="search" class="search-input" id="law-search-input" value="' + R.escHtml(R.state.lawSearch || '') + '" placeholder="' + R.escHtml(R.t('ref_law_search_placeholder')) + '">' +
      '</div>' +
      '<div class="list-stack">' +
      chapters.map(function (ch) {
        const isHi = highlightChapter && Number(highlightChapter) === Number(ch.chapter);
        const firstCat = (ch.category_ids && ch.category_ids.length) ? ch.category_ids[0] : null;
        return '<div class="surface-card law-chapter-card ' + (isHi ? 'highlighted' : '') + '" id="law-ch-' + ch.chapter + '">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px;">' +
          '  <div style="display:flex;align-items:center;gap:8px;min-width:0;flex:1 1 200px;">' +
          '    <span class="badge-pill badge-primary font-mono">' + ch.chapter + '</span>' +
          '    <strong style="font-size:13.5px;line-height:1.3;">' + R.escHtml(ch.title) + '</strong>' +
          '  </div>' +
          (firstCat !== null
            ? '<button type="button" class="btn btn-sm btn-secondary" data-law-cat="' + firstCat + '">' + R.icon('zap', 'xs') + ' ' + R.escHtml(R.t('btn_start_category')) + '</button>'
            : '') +
          '</div>' +
          '<p style="font-size:12.5px;color:var(--text-secondary);line-height:1.5;">' + R.escHtml(ch.summary) + '</p>' +
          '</div>';
      }).join('') +
      '</div>';

    container.innerHTML =
      '<div class="surface-card" style="margin-bottom:12px;">' +
      '  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap;margin-bottom:8px;">' +
      '    <div><strong style="font-size:15px;">' + R.escHtml(R.t('ref_law_title')) + '</strong><p style="font-size:12px;color:var(--text-secondary);">' + R.escHtml(data.resolution || '') + '</p></div>' +
      '    <a href="' + R.escHtml(data.source_url || 'https://lex.uz/docs/5963102') + '" target="_blank" rel="noopener" class="badge-pill badge-neutral">lex.uz ↗</a>' +
      '  </div>' +
      '  <div class="seg-pills" style="grid-template-columns:repeat(2,1fr);">' +
      '    <button type="button" class="seg-pill ' + (subMode === 'chapters' ? 'active' : '') + '" data-law-mode="chapters">' + R.escHtml(R.t('ref_law_tab_chapters')) + ' (' + (data.total_chapters || 29) + ')</button>' +
      '    <button type="button" class="seg-pill ' + (subMode === 'norms' ? 'active' : '') + '" data-law-mode="norms">' + R.escHtml(R.t('ref_law_tab_norms')) + '</button>' +
      '  </div>' +
      '</div>' +
      (subMode === 'norms' ? normsHtml : chaptersHtml);

    container.querySelectorAll('[data-law-mode]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.state.lawSubMode = btn.dataset.lawMode;
        R.renderLawExplorer(container, highlightChapter);
      });
    });

    const lInput = document.getElementById('law-search-input');
    if (lInput) {
      lInput.addEventListener('input', function () {
        R.state.lawSearch = lInput.value;
        R.renderLawExplorer(container, highlightChapter);
        const refocused = document.getElementById('law-search-input');
        if (refocused) {
          refocused.focus();
          const len = refocused.value.length;
          refocused.setSelectionRange(len, len);
        }
      });
    }

    container.querySelectorAll('[data-law-cat]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        R.closeModal('info-modal');
        R.startSession({ session_type: 'CATEGORY', category_id: Number(btn.dataset.lawCat), total_questions: 20 });
      });
    });

    if (highlightChapter) {
      const targetEl = document.getElementById('law-ch-' + highlightChapter);
      if (targetEl && typeof targetEl.scrollIntoView === 'function') {
        setTimeout(function () { targetEl.scrollIntoView({ block: 'center', behavior: 'smooth' }); }, 80);
      }
    }
  };

  R.openLawModal = async function (chapterNum) {
    const titleEl = document.getElementById('info-modal-title');
    const bodyEl = document.getElementById('info-modal-body');
    if (!bodyEl) return;
    if (titleEl) titleEl.textContent = R.t('ref_law_title');
    R.state.lawSubMode = 'chapters';
    R.openModal('info-modal');
    await R.renderLawExplorer(bodyEl, chapterNum);
  };
})();
