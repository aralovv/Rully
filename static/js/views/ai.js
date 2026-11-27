/**
 * RULLY 2.0 Contextual AI Ustoz Studio + Non-Destructive Quiz AI Drawer (SSE Streaming + Free Teaser)
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});
  let drawerMessages = [];
  let drawerSending = false;
  let drawerCtx = null;

  function formatSafeMarkdown(rawText) {
    let safe = R.escHtml(rawText || '');
    safe = safe.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    safe = safe.replace(/\n/g, '<br>');
    return safe;
  }

  function renderCitationsHtml(m) {
    let html = '';
    if (Array.isArray(m.grounding) && m.grounding.length) {
      html += '<div class="ai-citations-row">' +
        m.grounding.map(function (g) {
          const label = typeof g === 'string' ? g : (g.ref || g.clause || g.title || g.source || 'YHQ');
          return '<span class="badge-pill badge-emerald font-mono" style="font-size:10.5px;">' + R.icon('bookOpen', 'xs') + ' ' + R.escHtml(label) + '</span>';
        }).join('') +
        '</div>';
    } else if (m.grounding && !Array.isArray(m.grounding)) {
      const g = m.grounding;
      const label = g.legal_reference || g.ref || g.clause || g.title || g.source || 'VMQ 172';
      const cls = g.verified ? 'badge-emerald' : 'badge-amber';
      html += '<div class="ai-citations-row">' +
        '<span class="badge-pill ' + cls + ' font-mono" style="font-size:10.5px;">' +
        R.icon('bookOpen', 'xs') + ' ' + R.escHtml(label) +
        '</span></div>';
    }
    if (Array.isArray(m.cards) && m.cards.length) {
      html += '<div class="list-stack" style="margin-top:8px;">' +
        m.cards.map(function (c) {
          return '<div class="surface-card" style="padding:10px;background:var(--bg-subtle);">' +
            '<div style="font-size:11px;font-weight:700;color:var(--color-primary);">' + R.escHtml(c.category_name || R.t('ai_rule_badge')) + '</div>' +
            '<div style="font-size:12.5px;font-weight:600;margin-top:2px;">' + R.escHtml(c.question || c.title || '') + '</div>' +
            '</div>';
        }).join('') +
        '</div>';
    }
    return html;
  }

  async function streamAiRequest(payload, handlers) {
    const headers = { 'Content-Type': 'application/json' };
    if (R.state.initData) headers['X-Telegram-Init-Data'] = R.state.initData;

    const resp = await fetch('/api/ai/chat/stream', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(payload)
    });

    const contentType = String(resp.headers.get('content-type') || '');
    if (!resp.ok || !resp.body || !contentType.includes('text/event-stream')) {
      const errJson = await resp.json().catch(function () { return {}; });
      if (resp.status === 404 || resp.status === 405) {
        const fbRes = await R.api('/api/ai/chat', { method: 'POST', body: payload });
        handlers.onDone(fbRes);
        return;
      }
      const err = new Error(errJson.detail || errJson.message || ('HTTP ' + resp.status));
      err.status = resp.status;
      throw err;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';
      parts.forEach(function (frame) {
        const line = frame.split('\n').find(function (l) { return l.startsWith('data:'); });
        if (!line) return;
        const raw = line.slice(5).trim();
        if (!raw || raw === '[DONE]') return;
        try {
          const evt = JSON.parse(raw);
          if (evt.type === 'delta' && evt.text && handlers.onDelta) {
            handlers.onDelta(evt.text);
          } else if (evt.type === 'status' && handlers.onStatus) {
            handlers.onStatus(evt.text || evt.status || '');
          } else if (evt.type === 'done' && handlers.onDone) {
            handlers.onDone(evt);
          } else if (evt.type === 'error' && handlers.onError) {
            handlers.onError(evt);
          }
        } catch (e) {}
      });
    }
  }

  R.loadAiStatusAndHistory = async function () {
    if (R.state.isGuest) {
      R.renderAiView();
      return;
    }
    try {
      const [stRes, histRes] = await Promise.all([
        R.api('/api/ai/status'),
        R.api('/api/ai/history?session_id=default')
      ]);
      if (stRes && stRes.usage) {
        R.state.ai.usage = stRes.usage;
      }
      if (histRes && Array.isArray(histRes.messages)) {
        R.state.ai.history = histRes.messages;
      }
      R.state.ai.loaded = true;
      R.renderAiView();
    } catch (e) {}
  };

  function renderQuizAiDrawerBody() {
    const body = document.getElementById('quiz-ai-drawer-body');
    if (!body) return;

    const ctxCard = drawerCtx
      ? '<div class="ai-context-banner" style="margin-bottom:8px;">' +
        '  <div style="display:flex;align-items:center;gap:10px;min-width:0;">' +
        (R.safeUrl(drawerCtx.image_url) ? '<img src="' + R.escHtml(R.safeUrl(drawerCtx.image_url)) + '" alt="" style="width:40px;height:40px;object-fit:cover;border-radius:8px;flex-shrink:0;">' : '') +
        '    <div style="min-width:0;"><div style="font-size:11px;font-weight:700;color:var(--color-primary);">' + R.escHtml(R.t('ai_context_attached')) + '</div><div style="font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">' + R.escHtml(drawerCtx.question_text || '') + '</div></div>' +
        '  </div>' +
        '</div>'
      : '';

    const bubbles = drawerMessages.map(function (m) {
      const displayText = m.text || m.statusText || (drawerSending && m.role === 'assistant' ? R.t('ai_drawer_streaming') : '');
      return '<div class="ai-bubble ' + (m.role === 'user' ? 'user' : 'assistant') + '">' +
        formatSafeMarkdown(displayText) +
        (m.role === 'assistant' ? renderCitationsHtml(m) : '') +
        '</div>';
    }).join('');

    body.innerHTML = ctxCard + (bubbles || '<div class="ai-bubble assistant">' + R.escHtml(R.t('ai_drawer_streaming')) + '</div>');
    body.scrollTop = body.scrollHeight;
  }

  async function sendDrawerMessage(promptText) {
    if (drawerSending || !promptText) return;
    if (R.state.isGuest) {
      R.openGuestSyncModal();
      return;
    }
    drawerMessages.push({ role: 'user', text: promptText });
    const assistantMsg = { role: 'assistant', text: '', statusText: '', cards: [], grounding: null };
    drawerMessages.push(assistantMsg);
    drawerSending = true;
    renderQuizAiDrawerBody();

    const ctx = drawerCtx;
    try {
      await streamAiRequest(
        {
          message: promptText,
          session_id: ctx && ctx.canonical_id ? ('quiz_' + ctx.canonical_id) : 'quiz_drawer',
          language: R.state.lang,
          image_url: ctx ? ctx.image_url : null,
          canonical_id: ctx ? ctx.canonical_id : null,
          question_context: ctx ? { selected_key: ctx.selected_key, is_correct: ctx.is_correct } : null
        },
        {
          onDelta: function (chunk) {
            assistantMsg.statusText = '';
            assistantMsg.text += chunk;
            requestAnimationFrame(function () { renderQuizAiDrawerBody(); });
          },
          onStatus: function (stTxt) {
            if (!assistantMsg.text && stTxt) {
              assistantMsg.statusText = stTxt;
              requestAnimationFrame(function () { renderQuizAiDrawerBody(); });
            }
          },
          onDone: function (res) {
            if (res.requires_pro) {
              drawerMessages.splice(-2, 2);
              R.closeQuizAiDrawer();
              R.openPaywallModal();
              return;
            }
            if (res.reply) assistantMsg.text = res.reply;
            assistantMsg.cards = res.cards || [];
            assistantMsg.grounding = res.grounding || [];
            if (res.usage) R.state.ai.usage = res.usage;
          },
          onError: function (evt) {
            assistantMsg.text = evt.detail || evt.message || R.t('ai_generic_error');
          }
        }
      );
    } catch (err) {
      if (err && err.status === 401) R.openGuestSyncModal();
      else assistantMsg.text = (err && (err.detail || err.message)) || R.t('ai_net_error');
    } finally {
      drawerSending = false;
      renderQuizAiDrawerBody();
    }
  }

  R.openQuizAiDrawer = function (q, selectedKey, isCorrect) {
    if (R.state.isGuest) {
      R.openGuestSyncModal();
      return;
    }
    drawerCtx = {
      canonical_id: q.canonical_id,
      question_text: q.question_text,
      image_url: q.image_url || null,
      selected_key: selectedKey || null,
      is_correct: isCorrect
    };
    drawerMessages = [];
    const drawer = document.getElementById('quiz-ai-drawer');
    if (!drawer) return;
    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');

    const prompt = R.t('ai_question_prefix') + ': ' + (q.question_text || '').slice(0, 140);
    sendDrawerMessage(prompt);
  };

  R.closeQuizAiDrawer = function () {
    const drawer = document.getElementById('quiz-ai-drawer');
    if (drawer) {
      drawer.classList.remove('open');
      drawer.setAttribute('aria-hidden', 'true');
    }
  };

  document.getElementById('btn-close-quiz-ai-drawer')?.addEventListener('click', R.closeQuizAiDrawer);
  document.getElementById('quiz-ai-drawer')?.addEventListener('click', function (e) {
    if (e.target && e.target.id === 'quiz-ai-drawer') R.closeQuizAiDrawer();
  });
  document.getElementById('quiz-ai-drawer-form')?.addEventListener('submit', function (e) {
    e.preventDefault();
    const inp = document.getElementById('quiz-ai-drawer-input');
    const txt = inp ? inp.value.trim() : '';
    if (!txt) return;
    if (inp) inp.value = '';
    sendDrawerMessage(txt);
  });

  R.askAiAboutQuestion = function (q, selectedKey, isCorrect) {
    if (R.state.quiz && R.state.quiz.active && document.getElementById('quiz-ai-drawer')) {
      R.openQuizAiDrawer(q, selectedKey, isCorrect);
      return;
    }
    R.state.ai.contextQuestion = {
      canonical_id: q.canonical_id,
      question_text: q.question_text,
      image_url: q.image_url || null,
      selected_key: selectedKey || null,
      is_correct: isCorrect
    };
    R.navigateTo('ai');
    setTimeout(function () {
      const inp = document.getElementById('ai-composer-input');
      if (inp && !inp.value) {
        inp.value = R.t('ai_question_prefix') + ': ' + (q.question_text || '').slice(0, 120);
        inp.focus();
      }
    }, 60);
  };

  R.sendAiMessage = async function (overrideText) {
    if (R.state.ai.sending) return;
    if (R.state.isGuest) {
      R.openGuestSyncModal();
      return;
    }
    const inp = document.getElementById('ai-composer-input');
    const msg = (overrideText !== undefined ? overrideText : (inp ? inp.value : '')).trim();
    if (!msg) return;

    const isPro = Boolean(R.state.subscription && R.state.subscription.is_pro);
    const usage = R.state.ai.usage || { current: 0, max: isPro ? 100 : 3 };
    if (!isPro && Number(usage.current || 0) >= Number(usage.max || 3)) {
      R.openPaywallModal();
      return;
    }

    if (inp && overrideText === undefined) inp.value = '';
    R.state.ai.history.push({ role: 'user', text: msg });
    const assistantMsg = { role: 'assistant', text: '', cards: [], grounding: null };
    R.state.ai.history.push(assistantMsg);
    R.state.ai.sending = true;
    const ctx = R.state.ai.contextQuestion;
    R.renderAiView();

    try {
      await streamAiRequest(
        {
          message: msg,
          session_id: 'default',
          language: R.state.lang,
          image_url: ctx ? ctx.image_url : null,
          canonical_id: ctx ? ctx.canonical_id : null,
          question_context: ctx ? { selected_key: ctx.selected_key, is_correct: ctx.is_correct } : null
        },
        {
          onDelta: function (chunk) {
            assistantMsg.text += chunk;
            requestAnimationFrame(function () {
              const activeEl = document.getElementById('ai-active-assistant-text');
              if (activeEl) {
                activeEl.innerHTML = formatSafeMarkdown(assistantMsg.text);
                const scrollBox = document.getElementById('ai-messages-scroll');
                if (scrollBox) scrollBox.scrollTop = scrollBox.scrollHeight;
              } else {
                R.renderAiView();
              }
            });
          },
          onDone: function (res) {
            if (res.requires_pro) {
              R.state.ai.history.splice(-2, 2);
              R.openPaywallModal();
              return;
            }
            if (res.reply) assistantMsg.text = res.reply;
            assistantMsg.cards = res.cards || [];
            assistantMsg.grounding = res.grounding || null;
            if (res.usage) R.state.ai.usage = res.usage;
          },
          onError: function (evt) {
            assistantMsg.text = evt.detail || evt.message || R.t('ai_generic_error');
          }
        }
      );
    } catch (err) {
      if (err && err.status === 403) R.openPaywallModal();
      else assistantMsg.text = (err && (err.detail || err.message)) || R.t('ai_net_error');
    } finally {
      R.state.ai.sending = false;
      R.renderAiView();
    }
  };

  R.renderAiView = function () {
    const root = document.getElementById('view-ai');
    if (!root) return;

    const isGuest = Boolean(R.state.isGuest);
    const isPro = Boolean(R.state.subscription && R.state.subscription.is_pro);
    const usage = R.state.ai.usage || { current: 0, max: isPro ? 100 : 3 };
    const maxFree = Number(usage.max || (isPro ? 100 : 3));
    const curUsed = Number(usage.current || 0);
    const teaserExhausted = !isPro && curUsed >= maxFree;
    const ctx = R.state.ai.contextQuestion;
    const history = R.state.ai.history || [];

    const chips = [
      { label: R.t('ai_chip_1_label'), prompt: R.t('ai_chip_1_prompt') },
      { label: R.t('ai_chip_2_label'), prompt: R.t('ai_chip_2_prompt') },
      { label: R.t('ai_chip_3_label'), prompt: R.t('ai_chip_3_prompt') },
      { label: R.t('ai_chip_4_label'), prompt: R.t('ai_chip_4_prompt') }
    ];

    let bodyHtml = '';
    if (isGuest || teaserExhausted) {
      bodyHtml =
        '<div class="surface-card" style="margin:auto 0;text-align:center;padding:24px 18px;">' +
        '  <div class="badge-pill badge-amber" style="margin-bottom:10px;">' + R.icon('sparkles', 'xs') + (isGuest ? ' TELEGRAM' : ' PRO') + '</div>' +
        '  <h3 style="font-family:var(--font-display);font-size:17px;margin-bottom:8px;">' + R.escHtml(isGuest ? R.t('guest_sync_tg') : R.t('ai_pro_locked_banner_title')) + '</h3>' +
        '  <p style="font-size:13px;color:var(--text-secondary);margin-bottom:14px;">' + R.escHtml(R.t('ai_pro_locked_banner_desc')) + '</p>' +
        '  <div class="list-stack" style="text-align:left;max-width:360px;margin:0 auto 16px;">' +
        '    <div style="font-size:12.5px;">' + R.icon('check', 'xs') + ' ' + R.escHtml(R.t('ai_perk_1')) + '</div>' +
        '    <div style="font-size:12.5px;">' + R.icon('check', 'xs') + ' ' + R.escHtml(R.t('ai_perk_2')) + '</div>' +
        '    <div style="font-size:12.5px;">' + R.icon('check', 'xs') + ' ' + R.escHtml(R.t('ai_perk_3')) + '</div>' +
        '  </div>' +
        '  <button type="button" class="btn btn-primary" id="ai-unlock-pro-btn">' + R.escHtml(isGuest ? R.t('web_gate_btn') : R.t('ai_pro_locked_btn')) + '</button>' +
        '</div>';
    } else {
      const bubbles = !history.length
        ? '<div class="ai-bubble assistant">' + R.safeRichHtml(R.t('ai_welcome_bubble')) + '</div>'
        : history.map(function (m, idx) {
            const isUser = m.role === 'user';
            const isStreamingLast = R.state.ai.sending && !isUser && idx === history.length - 1;
            const txtHtml = formatSafeMarkdown(m.text || (isStreamingLast ? R.t('ai_typing_text') : ''));
            const idAttr = isStreamingLast ? ' id="ai-active-assistant-text"' : '';
            return '<div class="ai-bubble ' + (isUser ? 'user' : 'assistant') + '"' + idAttr + '>' + txtHtml + (!isUser ? renderCitationsHtml(m) : '') + '</div>';
          }).join('');

      bodyHtml =
        '<div class="ai-messages-scroll" id="ai-messages-scroll">' +
        bubbles +
        '</div>';
    }

    const quotaBadge = isGuest
      ? ''
      : (isPro
        ? '<span class="badge-pill badge-neutral font-mono">' + R.escHtml(R.t('ai_quota_pill', { cur: curUsed, max: maxFree })) + '</span>'
        : '<span class="badge-pill badge-amber font-mono">' + R.escHtml(R.t('ai_teaser_badge', { left: Math.max(0, maxFree - curUsed), max: maxFree })) + '</span>');

    root.innerHTML =
      '<div class="ai-studio-shell">' +
      '  <div class="ai-header-bar">' +
      '    <div style="display:flex;align-items:center;gap:8px;">' +
      '      <span class="tile-icon-box badge-primary" style="width:36px;height:36px;">' + R.icon('bot', 'sm') + '</span>' +
      '      <div><strong style="font-size:15px;">' + R.escHtml(R.t('ai_header_title')) + '</strong><div style="font-size:11px;color:var(--text-muted);">YHQ & Vision AI • Streaming</div></div>' +
      '    </div>' +
      '    <div style="display:flex;align-items:center;gap:6px;">' +
      quotaBadge +
      (!isGuest ? '<button type="button" class="btn btn-sm btn-secondary" id="ai-clear-btn">' + R.icon('trash', 'xs') + '</button>' : '') +
      '    </div>' +
      '  </div>' +

      (ctx && R.safeUrl(ctx.image_url) !== undefined
        ? '<div class="ai-context-banner">' +
          '  <div style="display:flex;align-items:center;gap:10px;min-width:0;">' +
          (R.safeUrl(ctx.image_url) ? '<img src="' + R.escHtml(R.safeUrl(ctx.image_url)) + '" alt="" style="width:42px;height:42px;object-fit:cover;border-radius:8px;flex-shrink:0;">' : '') +
          '    <div style="min-width:0;"><div style="font-size:11px;font-weight:700;color:var(--color-primary);">' + R.escHtml(R.t('ai_context_attached')) + '</div><div style="font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + R.escHtml(ctx.question_text || '') + '</div></div>' +
          '  </div>' +
          '  <button type="button" class="btn btn-sm btn-ghost" id="ai-detach-ctx">' + R.icon('x', 'xs') + '</button>' +
          '</div>'
        : '') +

      bodyHtml +

      (!isGuest && !teaserExhausted
        ? '<div class="ai-chips-row">' +
          chips.map(function (c, idx) {
            return '<button type="button" class="ai-chip-btn" data-ai-chip="' + idx + '">' + R.escHtml(c.label) + '</button>';
          }).join('') +
          '</div>' +
          '<form class="ai-composer-form" id="ai-composer-form">' +
          '  <textarea rows="1" class="ai-input" id="ai-composer-input" placeholder="' + R.escHtml(R.t('ai_input_placeholder')) + '"></textarea>' +
          '  <button type="submit" class="btn btn-primary" aria-label="' + R.escHtml(R.t('ai_send_label')) + '"' + (R.state.ai.sending ? ' disabled' : '') + '>' + R.icon('send', 'sm') + '</button>' +
          '</form>'
        : '') +
      '</div>';

    const scrollBox = document.getElementById('ai-messages-scroll');
    if (scrollBox) scrollBox.scrollTop = scrollBox.scrollHeight;

    document.getElementById('ai-unlock-pro-btn')?.addEventListener('click', isGuest ? R.openGuestSyncModal : R.openPaywallModal);
    document.getElementById('ai-detach-ctx')?.addEventListener('click', function () {
      R.state.ai.contextQuestion = null;
      R.renderAiView();
    });
    document.getElementById('ai-clear-btn')?.addEventListener('click', async function () {
      const ok = await R.confirmDialog(R.t('ai_btn_clear'), R.t('ai_confirm_clear'), R.t('btn_confirm'));
      if (!ok) return;
      await R.api('/api/ai/clear', { method: 'POST', body: { session_id: 'default' } });
      R.state.ai.history = [];
      R.state.ai.contextQuestion = null;
      R.renderAiView();
    });

    root.querySelectorAll('[data-ai-chip]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const ch = chips[Number(btn.dataset.aiChip)];
        if (ch) R.sendAiMessage(ch.prompt);
      });
    });

    document.getElementById('ai-composer-form')?.addEventListener('submit', function (e) {
      e.preventDefault();
      R.sendAiMessage();
    });
  };
})();
