/**
 * RULLY 2.0 Contextual AI Ustoz Studio (Ground Truth + Student Snapshot + Tools)
 */
(function () {
  'use strict';

  const R = (window.RULLY = window.RULLY || {});

  function formatSafeMarkdown(rawText) {
    let safe = R.escHtml(rawText || '');
    safe = safe.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    safe = safe.replace(/\n/g, '<br>');
    return safe;
  }

  R.loadAiStatusAndHistory = async function () {
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

  R.askAiAboutQuestion = function (q, selectedKey, isCorrect) {
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
    const inp = document.getElementById('ai-composer-input');
    const msg = (overrideText !== undefined ? overrideText : (inp ? inp.value : '')).trim();
    if (!msg) return;

    const isPro = Boolean(R.state.subscription && R.state.subscription.is_pro);
    if (!isPro) {
      R.openPaywallModal();
      return;
    }

    if (inp && overrideText === undefined) inp.value = '';
    R.state.ai.history.push({ role: 'user', text: msg });
    R.state.ai.sending = true;
    const ctx = R.state.ai.contextQuestion;
    R.renderAiView();

    try {
      const res = await R.api('/api/ai/chat', {
        method: 'POST',
        body: {
          message: msg,
          session_id: 'default',
          language: R.state.lang,
          image_url: ctx ? ctx.image_url : null,
          canonical_id: ctx ? ctx.canonical_id : null,
          question_context: ctx ? { selected_key: ctx.selected_key, is_correct: ctx.is_correct } : null
        }
      });

      if (res.requires_pro) {
        R.openPaywallModal();
      } else {
        R.state.ai.history.push({
          role: 'assistant',
          text: res.reply || R.t('ai_generic_error'),
          cards: res.cards || []
        });
        if (res.usage) R.state.ai.usage = res.usage;
      }
      R.state.ai.contextQuestion = null;
    } catch (err) {
      R.state.ai.history.push({ role: 'assistant', text: err.detail || R.t('ai_net_error') });
    } finally {
      R.state.ai.sending = false;
      R.renderAiView();
    }
  };

  R.renderAiView = function () {
    const root = document.getElementById('view-ai');
    if (!root) return;

    const isPro = Boolean(R.state.subscription && R.state.subscription.is_pro);
    const usage = R.state.ai.usage || { current: 0, max: 100 };
    const ctx = R.state.ai.contextQuestion;
    const history = R.state.ai.history || [];

    const chips = [
      { label: R.t('ai_chip_1_label'), prompt: R.t('ai_chip_1_prompt') },
      { label: R.t('ai_chip_2_label'), prompt: R.t('ai_chip_2_prompt') },
      { label: R.t('ai_chip_3_label'), prompt: R.t('ai_chip_3_prompt') },
      { label: R.t('ai_chip_4_label'), prompt: R.t('ai_chip_4_prompt') }
    ];

    let bodyHtml = '';
    if (!isPro) {
      bodyHtml =
        '<div class="surface-card" style="margin:auto 0;text-align:center;padding:24px 18px;">' +
        '  <div class="badge-pill badge-amber" style="margin-bottom:10px;">' + R.icon('sparkles', 'xs') + ' PRO</div>' +
        '  <h3 style="font-family:var(--font-display);font-size:17px;margin-bottom:8px;">' + R.escHtml(R.t('ai_pro_locked_banner_title')) + '</h3>' +
        '  <p style="font-size:13px;color:var(--text-secondary);margin-bottom:14px;">' + R.escHtml(R.t('ai_pro_locked_banner_desc')) + '</p>' +
        '  <div class="list-stack" style="text-align:left;max-width:360px;margin:0 auto 16px;">' +
        '    <div style="font-size:12.5px;">' + R.icon('check', 'xs') + ' ' + R.escHtml(R.t('ai_perk_1')) + '</div>' +
        '    <div style="font-size:12.5px;">' + R.icon('check', 'xs') + ' ' + R.escHtml(R.t('ai_perk_2')) + '</div>' +
        '    <div style="font-size:12.5px;">' + R.icon('check', 'xs') + ' ' + R.escHtml(R.t('ai_perk_3')) + '</div>' +
        '  </div>' +
        '  <button type="button" class="btn btn-primary" id="ai-unlock-pro-btn">' + R.escHtml(R.t('ai_pro_locked_btn')) + '</button>' +
        '</div>';
    } else {
      const bubbles = !history.length
        ? '<div class="ai-bubble assistant">' + R.t('ai_welcome_bubble') + '</div>'
        : history.map(function (m) {
            const isUser = m.role === 'user';
            let cardsHtml = '';
            if (!isUser && Array.isArray(m.cards) && m.cards.length) {
              cardsHtml = '<div class="list-stack" style="margin-top:10px;">' +
                m.cards.map(function (c) {
                  return '<div class="surface-card" style="padding:10px;background:var(--bg-subtle);">' +
                    '<div style="font-size:11px;font-weight:700;color:var(--color-primary);">' + R.escHtml(c.category_name || R.t('ai_rule_badge')) + '</div>' +
                    '<div style="font-size:12.5px;font-weight:600;margin-top:2px;">' + R.escHtml(c.question || '') + '</div>' +
                    '</div>';
                }).join('') +
                '</div>';
            }
            return '<div class="ai-bubble ' + (isUser ? 'user' : 'assistant') + '">' + formatSafeMarkdown(m.text) + cardsHtml + '</div>';
          }).join('');

      bodyHtml =
        '<div class="ai-messages-scroll" id="ai-messages-scroll">' +
        bubbles +
        (R.state.ai.sending ? '<div class="ai-bubble assistant" style="color:var(--text-muted);">' + R.escHtml(R.t('ai_typing_text')) + '</div>' : '') +
        '</div>';
    }

    root.innerHTML =
      '<div class="ai-studio-shell">' +
      '  <div class="ai-header-bar">' +
      '    <div style="display:flex;align-items:center;gap:8px;">' +
      '      <span class="tile-icon-box badge-primary" style="width:36px;height:36px;">' + R.icon('bot', 'sm') + '</span>' +
      '      <div><strong style="font-size:15px;">' + R.escHtml(R.t('ai_header_title')) + '</strong><div style="font-size:11px;color:var(--text-muted);">YHQ & Vision AI</div></div>' +
      '    </div>' +
      '    <div style="display:flex;align-items:center;gap:6px;">' +
      (isPro ? '<span class="badge-pill badge-neutral font-mono">' + R.escHtml(R.t('ai_quota_pill', { cur: usage.current || 0, max: usage.max || 100 })) + '</span>' : '') +
      (isPro ? '<button type="button" class="btn btn-sm btn-secondary" id="ai-clear-btn">' + R.icon('trash', 'xs') + '</button>' : '') +
      '    </div>' +
      '  </div>' +

      (ctx
        ? '<div class="ai-context-banner">' +
          '  <div style="display:flex;align-items:center;gap:10px;min-width:0;">' +
          (ctx.image_url ? '<img src="' + R.escHtml(ctx.image_url) + '" alt="" style="width:42px;height:42px;object-fit:cover;border-radius:8px;flex-shrink:0;">' : '') +
          '    <div style="min-width:0;"><div style="font-size:11px;font-weight:700;color:var(--color-primary);">' + R.escHtml(R.t('ai_context_attached')) + '</div><div style="font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + R.escHtml(ctx.question_text || '') + '</div></div>' +
          '  </div>' +
          '  <button type="button" class="btn btn-sm btn-ghost" id="ai-detach-ctx">' + R.icon('x', 'xs') + '</button>' +
          '</div>'
        : '') +

      bodyHtml +

      (isPro
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

    document.getElementById('ai-unlock-pro-btn')?.addEventListener('click', R.openPaywallModal);
    document.getElementById('ai-detach-ctx')?.addEventListener('click', function () {
      R.state.ai.contextQuestion = null;
      R.renderAiView();
    });
    document.getElementById('ai-clear-btn')?.addEventListener('click', async function () {
      const ok = await R.confirmDialog(R.t('ai_btn_clear'), R.t('ai_confirm_clear'), R.t('btn_confirm'));
      if (!ok) return;
      await R.api('/api/ai/clear', { method: 'POST', body: { session_id: 'default' } });
      R.state.ai.history = [];
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
