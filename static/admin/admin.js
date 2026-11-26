(function () {
  'use strict';

  // ================= STATE & HELPERS =================
  const state = {
    currentAdmin: null,
    activeView: 'overview',
    currentPaymentTab: 'ALL',
    otpChallengeId: null,
    otpTimerInterval: null,
    searchDebounce: null,
    ordersCache: [],
    reviewCasesCache: [],
    unmatchedCache: [],
    transactionsCache: [],
    usersCache: [],
    stagedCache: [],
    selectedEditorialIds: new Set(),
    editorial: {
      status: 'PENDING_EDITORIAL_REVIEW',
      page: 1,
      limit: 20,
      total: 0,
      items: []
    }
  };

  function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function safeUrl(url) {
    const raw = String(url || '').trim();
    if (!raw) return '';
    if (raw.startsWith('/') && !raw.startsWith('//')) return raw;
    if (/^https?:\/\//i.test(raw) || /^tg:\/\//i.test(raw)) return raw;
    return '';
  }

  function sanitizeTelegramPreviewHtml(raw) {
    if (!raw || !raw.trim()) return '<i>Xabar matni kiritilmagan...</i>';
    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(raw, 'text/html');
      const allowed = new Set(['B', 'STRONG', 'I', 'EM', 'CODE', 'PRE', 'S', 'DEL', 'U', 'A', 'BR']);

      function walk(node) {
        if (node.nodeType === Node.TEXT_NODE) {
          return escapeHtml(node.textContent || '');
        }
        if (node.nodeType !== Node.ELEMENT_NODE) return '';
        const tag = node.tagName.toUpperCase();
        const childrenHtml = Array.from(node.childNodes).map(walk).join('');
        if (!allowed.has(tag)) return childrenHtml;
        if (tag === 'BR') return '<br>';
        if (tag === 'A') {
          const href = safeUrl(node.getAttribute('href') || '');
          if (!href) return childrenHtml;
          return `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:underline;">${childrenHtml}</a>`;
        }
        const lower = tag.toLowerCase();
        return `<${lower}>${childrenHtml}</${lower}>`;
      }

      return Array.from(doc.body.childNodes).map(walk).join('') || escapeHtml(raw);
    } catch {
      return escapeHtml(raw);
    }
  }

  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : '';
  }

  async function apiFetch(endpoint, options = {}) {
    options.headers = options.headers || {};
    if (!options.headers['Content-Type'] && !(options.body instanceof FormData)) {
      options.headers['Content-Type'] = 'application/json';
    }
    const method = String(options.method || 'GET').toUpperCase();
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
      const csrf = getCookie('rully_csrf');
      if (csrf && !options.headers['X-CSRF-Token']) {
        options.headers['X-CSRF-Token'] = csrf;
      }
    }
    options.credentials = 'same-origin';

    const res = await fetch(endpoint, options);
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      const err = new Error(data.detail || data.message || `Xatolik yuz berdi (${res.status})`);
      err.status = res.status;
      throw err;
    }
    return data;
  }

  function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  function formatMoney(amount) {
    if (amount == null || isNaN(Number(amount))) return '0 UZS';
    return Number(amount).toLocaleString('ru-RU') + ' UZS';
  }

  function formatDate(isoStr) {
    if (!isoStr) return '-';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return String(isoStr).slice(0, 16);
      return d.toLocaleDateString('uz-UZ', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return String(isoStr);
    }
  }

  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function hasRole(required) {
    const role = String(state.currentAdmin?.role || '').toUpperCase();
    if (!role || role === 'SUPERADMIN') return true;
    return role === String(required || '').toUpperCase();
  }

  function openModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.style.display = 'flex';
  }

  function closeModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.style.display = 'none';
  }

  function toggleAccordion(accId) {
    const el = document.getElementById(accId);
    if (el) el.classList.toggle('open');
  }

  // ================= VIEW SWITCHER =================
  function switchView(viewName) {
    if (!viewName) return;
    state.activeView = viewName;

    document.querySelectorAll('.sidebar-nav .nav-item').forEach(el => {
      el.classList.toggle('active', el.getAttribute('data-view') === viewName);
    });
    document.querySelectorAll('.mobile-bottom-nav .m-nav-item').forEach(el => {
      el.classList.toggle('active', el.getAttribute('data-view') === viewName);
    });
    document.querySelectorAll('.view-panel').forEach(el => el.classList.remove('active'));
    const targetPane = document.getElementById(`view-${viewName}`);
    if (targetPane) targetPane.classList.add('active');

    const titles = {
      overview: 'Asosiy Panel',
      payments: 'To‘lovlar & Yarashuv',
      users: 'Foydalanuvchilar',
      broadcast: 'Xabarnoma (Broadcast)',
      settings: 'Tizim & Tahririyat'
    };
    setText('topbar-view-title', titles[viewName] || 'Boshqaruv');
    window.scrollTo({ top: 0, behavior: 'smooth' });

    switch (viewName) {
      case 'overview': loadOverview(); break;
      case 'payments': loadPaymentsHub(); break;
      case 'users': loadUsers(); break;
      case 'broadcast': loadBroadcastView(); break;
      case 'settings': loadSettings(); break;
    }
  }

  // ================= 1. OVERVIEW & BI ANALYTICS =================
  async function loadBiAnalytics() {
    const card = document.getElementById('ov-analytics-card');
    if (!card) return;
    if (!hasRole('FINANCE')) {
      card.style.display = 'none';
      return;
    }
    card.style.display = 'block';
    const range = document.getElementById('ov-sales-range')?.value || '30d';

    const [actRes, retRes, salesRes] = await Promise.allSettled([
      apiFetch('/api/admin/analytics/activity'),
      apiFetch('/api/admin/analytics/retention'),
      apiFetch(`/api/admin/dashboard/sales-analytics?range_filter=${encodeURIComponent(range)}`)
    ]);

    if (actRes.status === 'fulfilled') {
      const a = actRes.value.analytics || {};
      setText('bi-dau-wau-mau', `${a.dau ?? 0} / ${a.wau ?? 0} / ${a.mau ?? 0}`);
      const feat = Object.entries(a.feature_distribution || {}).sort((x, y) => y[1] - x[1])[0];
      setText('bi-top-feature', feat ? `${feat[0]} (${feat[1]})` : 'Ma’lumot yo‘q');
    }

    if (retRes.status === 'fulfilled') {
      const r = retRes.value.retention || {};
      setText('bi-retention', `${r.d1_pct ?? 0}% / ${r.d7_pct ?? 0}% / ${r.d30_pct ?? 0}%`);
    }

    if (salesRes.status === 'fulfilled') {
      const s = salesRes.value.summary || {};
      setText('bi-conversion', `${s.conversion_rate_pct ?? 0}% • ${formatMoney(s.average_transaction_uzs || 0)}`);
      const chartEl = document.getElementById('ov-sales-chart');
      if (chartEl) {
        const pts = (salesRes.value.daily_chart || []).slice(-14);
        if (!pts.length) {
          chartEl.innerHTML = '<div class="text-[11px] text-muted self-center m-auto">Tanlangan davrda savdo grafik ma’lumoti yo‘q</div>';
        } else {
          const maxVal = Math.max(1, ...pts.map(p => Number(p.revenue_uzs || p.amount_uzs || 0)));
          chartEl.innerHTML = pts.map(p => {
            const val = Number(p.revenue_uzs || p.amount_uzs || 0);
            const pct = Math.max(6, Math.round((val / maxVal) * 100));
            const label = escapeHtml(`${p.date || ''}: ${formatMoney(val)}`);
            return `<div class="bi-bar-col" title="${label}"><div class="bi-bar-fill" style="height:${pct}%"></div></div>`;
          }).join('');
        }
      }
    }
  }

  async function loadOverview() {
    try {
      const [kpiRes, mtRes, ordRes] = await Promise.allSettled([
        apiFetch('/api/admin/dashboard/kpi'),
        apiFetch('/api/admin/mtproto/status'),
        apiFetch('/api/admin/orders?limit=5')
      ]);

      if (kpiRes.status === 'fulfilled') {
        const k = kpiRes.value.kpis || {};
        setText('kpi-total-users', Number(k.total_users || 0).toLocaleString());
        setText('kpi-new-today', `${k.new_users_today || 0} yangi`);
        setText('kpi-active-subs', Number(k.active_subscribers || 0).toLocaleString());
        setText('kpi-subs-today', String(k.subscriptions_today || 0));
        setText('kpi-today-rev', formatMoney(k.today_revenue_uzs || 0));
        setText('kpi-total-rev', formatMoney(k.total_revenue_uzs || 0));
        setText('kpi-month-rev', formatMoney(k.month_revenue_uzs || 0));
        setText('kpi-unmatched-badge', `${k.pending_orders || 0} / ${k.unmatched_payments || 0}`);
      }

      if (mtRes.status === 'fulfilled') {
        const st = mtRes.value.status || {};
        const isConn = st.connection_status === 'CONNECTED';
        const badge = document.getElementById('overview-mtproto-badge');
        const desc = document.getElementById('ov-mtproto-desc');
        const icon = document.getElementById('ov-mtproto-icon');
        if (badge) {
          badge.className = `badge ${isConn ? 'badge-emerald' : 'badge-amber'}`;
          badge.textContent = isConn ? 'FAOL — TINGLAMOQDA' : escapeHtml(st.connection_status || 'NOFAOL');
        }
        if (desc) {
          desc.textContent = isConn
            ? `Ulangan hisob: ${st.account_info?.first_name || ''} (${st.account_info?.phone || ''}). Humocardbot tinglanmoqda.`
            : 'Humocardbot to‘lov xabarnomalarini avtomatik ushlash holati.';
        }
        setText('ov-mtproto-btn-txt', isConn ? 'Holatni Ko‘rish' : 'Akkauntni Ulash');
        if (icon) {
          icon.style.background = isConn ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)';
          icon.style.color = isConn ? '#10b981' : '#f59e0b';
        }
      }

      const container = document.getElementById('overview-orders-container');
      if (container && ordRes.status === 'fulfilled') {
        const orders = ordRes.value.orders || [];
        if (!orders.length) {
          container.innerHTML = '<div class="text-center text-muted text-xs py-8">Hozircha buyurtmalar yo‘q</div>';
        } else {
          container.innerHTML = orders.map(o => `
            <div class="mobile-card-row">
              <div class="m-card-top">
                <span class="font-mono font-bold text-xs text-slate-200">#${escapeHtml(o.order_id)}</span>
                ${renderStatusBadge(o.status)}
              </div>
              <div class="m-card-body">
                <div>
                  <div class="font-bold text-slate-100 text-sm">${o.username ? '@' + escapeHtml(o.username) : 'ID: ' + escapeHtml(o.user_id)}</div>
                  <div class="text-[11px] text-muted">${escapeHtml(formatDate(o.created_at))}</div>
                </div>
                <div class="text-right">
                  <div class="font-mono font-bold text-emerald text-sm">${escapeHtml(formatMoney(o.final_amount_uzs))}</div>
                  <div class="text-[10px] text-muted"><span class="badge badge-blue text-[10px] py-0">${escapeHtml(o.plan_name || o.plan_id)}</span></div>
                </div>
              </div>
            </div>
          `).join('');
        }
      }

      await loadBiAnalytics();
    } catch (e) {
      console.error('Overview load error:', e);
    }
  }

  function renderStatusBadge(status) {
    switch (status) {
      case 'PAID': return '<span class="badge badge-emerald">Muvaffaqiyatli</span>';
      case 'PENDING': return '<span class="badge badge-amber">Kutilmoqda</span>';
      case 'EXPIRED': return '<span class="badge badge-gray">Muddati o‘tgan</span>';
      case 'PAYMENT_REVIEW_REQUIRED': return '<span class="badge badge-red">Ko‘rib chiqish</span>';
      default: return `<span class="badge badge-gray">${escapeHtml(status)}</span>`;
    }
  }

  // ================= 2. PAYMENTS & RECONCILIATION HUB =================
  function setPaymentTab(tab) {
    state.currentPaymentTab = tab;
    document.querySelectorAll('#payments-subtabs .subtab-btn').forEach(b => {
      b.classList.toggle('active', b.getAttribute('data-ptab') === tab);
    });
    renderPaymentsHub();
  }

  async function loadPaymentsHub() {
    const container = document.getElementById('payments-list-container');
    if (!hasRole('FINANCE')) {
      if (container) container.innerHTML = '<div class="text-center text-muted text-xs py-8">Bu bo‘lim uchun FINANCE huquqi talab etiladi.</div>';
      return;
    }

    try {
      const [ordRes, revRes, unmRes, txRes] = await Promise.allSettled([
        apiFetch('/api/admin/orders?limit=100'),
        apiFetch('/api/admin/payments/review-cases?status=PENDING'),
        apiFetch('/api/admin/payments/unmatched?status=UNRESOLVED&limit=50'),
        apiFetch('/api/admin/payments/transactions?limit=50')
      ]);

      state.ordersCache = ordRes.status === 'fulfilled' ? (ordRes.value.orders || []) : [];
      state.reviewCasesCache = revRes.status === 'fulfilled' ? (revRes.value.cases || []) : [];
      state.unmatchedCache = unmRes.status === 'fulfilled' ? (unmRes.value.unmatched || []) : [];
      state.transactionsCache = txRes.status === 'fulfilled' ? (txRes.value.transactions || []) : [];

      setText('ptab-badge-review', String(state.reviewCasesCache.length));
      setText('ptab-badge-unmatched', String(state.unmatchedCache.length));

      await renderPaymentsHub();
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  async function renderPaymentsHub() {
    const container = document.getElementById('payments-list-container');
    const summaryBox = document.getElementById('payments-reconcile-summary');
    if (!container) return;

    const tab = state.currentPaymentTab;
    const query = (document.getElementById('payments-search-input')?.value || '').toLowerCase().trim();
    if (summaryBox) summaryBox.style.display = tab === 'RECONCILE' ? 'block' : 'none';

    if (tab === 'RECONCILE') {
      try {
        const rep = await apiFetch('/api/admin/payments/reconciliation');
        const ev = rep.events_summary || {};
        const ld = rep.ledger_summary || {};
        const sub = rep.subscription_summary || {};
        if (summaryBox) {
          summaryBox.innerHTML = `
            <div class="card p-4 space-y-3">
              <div class="flex items-center justify-between">
                <h4 class="font-bold text-sm text-slate-100">Moliyaviy Yarashuv Hisoboti</h4>
                <span class="badge ${rep.is_balanced ? 'badge-emerald' : 'badge-red'}">${rep.is_balanced ? 'BALANS MOS (0 FARQ)' : 'TAFOVUT: ' + escapeHtml(rep.discrepancy_count)}</span>
              </div>
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div class="bg-slate-900/80 border border-slate-800 rounded p-2.5">
                  <div class="text-[11px] text-muted">Bank Kirim Events</div>
                  <div class="font-bold text-sm font-mono">${escapeHtml(ev.incoming_events || 0)} (${escapeHtml(formatMoney(ev.total_incoming_uzs || 0))})</div>
                </div>
                <div class="bg-slate-900/80 border border-slate-800 rounded p-2.5">
                  <div class="text-[11px] text-muted">Tasdiqlangan Ledger</div>
                  <div class="font-bold text-sm font-mono text-emerald">${escapeHtml(ld.total_ledger_tx || 0)} (${escapeHtml(formatMoney(ld.total_ledger_uzs || 0))})</div>
                </div>
                <div class="bg-slate-900/80 border border-slate-800 rounded p-2.5">
                  <div class="text-[11px] text-muted">Noma’lum / Kechiktirilgan</div>
                  <div class="font-bold text-sm font-mono text-amber-300">${escapeHtml(ev.unmatched_events || 0)} / ${escapeHtml(ev.late_review_events || 0)}</div>
                </div>
                <div class="bg-slate-900/80 border border-slate-800 rounded p-2.5">
                  <div class="text-[11px] text-muted">Obunalar (Faol / Grant / Bekor)</div>
                  <div class="font-bold text-sm font-mono">${escapeHtml(sub.active_subs || 0)} / ${escapeHtml(sub.manual_grants || 0)} / ${escapeHtml(sub.revoked_subs || 0)}</div>
                </div>
              </div>
            </div>
          `;
        }
        container.innerHTML = '';
      } catch (e) {
        container.innerHTML = `<div class="text-xs text-rose p-4">${escapeHtml(e.message)}</div>`;
      }
      return;
    }

    if (tab === 'REVIEW') {
      let cases = state.reviewCasesCache;
      if (query) {
        cases = cases.filter(c =>
          String(c.order_id || '').toLowerCase().includes(query) ||
          String(c.user_id || '').includes(query) ||
          String(c.username || '').toLowerCase().includes(query)
        );
      }
      if (!cases.length) {
        container.innerHTML = '<div class="text-center text-muted text-xs py-8">Kechiktirilgan yoki tekshiruvdagi to‘lovlar yo‘q.</div>';
        return;
      }
      container.innerHTML = cases.map(c => `
        <div class="mobile-card-row">
          <div class="m-card-top">
            <span class="font-mono font-bold text-xs text-slate-200">Case #${escapeHtml(c.case_id)} • Order #${escapeHtml(c.order_id)}</span>
            <span class="badge badge-red">${escapeHtml(c.status)}</span>
          </div>
          <div class="m-card-body">
            <div>
              <div class="font-bold text-sm text-slate-100">${c.username ? '@' + escapeHtml(c.username) : 'ID: ' + escapeHtml(c.user_id)}</div>
              <div class="text-[11px] text-muted">${escapeHtml(c.reason || '')} • ${escapeHtml(formatDate(c.created_at))}</div>
            </div>
            <div class="text-right">
              <div class="font-mono font-bold text-emerald text-sm">${escapeHtml(formatMoney(c.incoming_amount_uzs || c.expected_amount_uzs))}</div>
              <div class="text-[10px] text-muted">${escapeHtml(c.plan_name || c.plan_id || '')}</div>
            </div>
          </div>
          <div class="m-card-footer">
            <span class="text-xs text-muted font-mono">User ID: ${escapeHtml(c.user_id)}</span>
            <div class="flex gap-2">
              <button type="button" class="btn btn-primary btn-sm" data-action="approve-review" data-case-id="${escapeHtml(c.case_id)}" data-order-id="${escapeHtml(c.order_id)}">✅ Tasdiqlash</button>
              <button type="button" class="btn btn-danger btn-sm" data-action="reject-review" data-case-id="${escapeHtml(c.case_id)}">❌ Rad etish</button>
            </div>
          </div>
        </div>
      `).join('');
      return;
    }

    if (tab === 'UNMATCHED') {
      let unm = state.unmatchedCache;
      if (query) {
        unm = unm.filter(u =>
          String(u.incoming_amount_uzs || '').includes(query) ||
          String(u.raw_message || '').toLowerCase().includes(query) ||
          String(u.candidate_order_id || '').toLowerCase().includes(query)
        );
      }
      if (!unm.length) {
        container.innerHTML = '<div class="text-center text-muted text-xs py-8">Bog‘lanmagan to‘lovlar mavjud emas.</div>';
        return;
      }
      container.innerHTML = unm.map(u => `
        <div class="mobile-card-row">
          <div class="m-card-top">
            <span class="font-mono font-bold text-xs text-amber-300">Unmatched #${escapeHtml(u.id)} • ${escapeHtml(formatMoney(u.incoming_amount_uzs))}</span>
            <span class="badge badge-amber">${escapeHtml(u.status || 'UNRESOLVED')}</span>
          </div>
          <div class="text-xs text-slate-300 mt-1">${escapeHtml(u.raw_message || u.reason || 'Bank xabari')}</div>
          <div class="text-[11px] text-muted mt-1">
            Karta: •••• ${escapeHtml(u.card_suffix || '—')} | Vaqt: ${escapeHtml(formatDate(u.created_at))}
            ${u.candidate_order_id ? ` | Tavsiya: <b class="font-mono text-slate-200">${escapeHtml(u.candidate_order_id)}</b>` : ''}
          </div>
          <div class="m-card-footer mt-2">
            <button type="button" class="btn btn-primary btn-sm" data-action="link-unmatched" data-unmatched-id="${escapeHtml(u.id)}" data-candidate-order="${escapeHtml(u.candidate_order_id || '')}">🔗 Buyurtmaga bog‘lash</button>
            <button type="button" class="btn btn-ghost btn-sm text-xs" data-action="resolve-unmatched" data-unmatched-id="${escapeHtml(u.id)}">Ignor / Qaytarildi</button>
          </div>
        </div>
      `).join('');
      return;
    }

    if (tab === 'TRANSACTIONS') {
      let txs = state.transactionsCache;
      if (query) {
        txs = txs.filter(t =>
          String(t.order_id || '').toLowerCase().includes(query) ||
          String(t.user_id || '').includes(query) ||
          String(t.username || '').toLowerCase().includes(query)
        );
      }
      if (!txs.length) {
        container.innerHTML = '<div class="text-center text-muted text-xs py-8">Tasdiqlangan tranzaksiyalar topilmadi.</div>';
        return;
      }
      container.innerHTML = txs.map(t => `
        <div class="mobile-card-row">
          <div class="m-card-top">
            <span class="font-mono font-bold text-xs text-slate-200">TX #${escapeHtml(t.id)} • Order #${escapeHtml(t.order_id)}</span>
            <span class="badge badge-emerald">${escapeHtml(t.source || 'HUMO')}</span>
          </div>
          <div class="m-card-body">
            <div>
              <div class="font-bold text-sm text-slate-100">${t.username ? '@' + escapeHtml(t.username) : 'ID: ' + escapeHtml(t.user_id)}</div>
              <div class="text-[11px] text-muted">${escapeHtml(formatDate(t.created_at))}</div>
            </div>
            <div class="text-right">
              <div class="font-mono font-bold text-emerald text-sm">${escapeHtml(formatMoney(t.amount_uzs))}</div>
              <div class="text-[10px] text-muted">${escapeHtml(t.plan_id || '')}</div>
            </div>
          </div>
        </div>
      `).join('');
      return;
    }

    // Default Orders view (ALL, PAID, PENDING)
    let list = state.ordersCache;
    if (tab === 'PAID') list = list.filter(o => o.status === 'PAID');
    else if (tab === 'PENDING') list = list.filter(o => o.status === 'PENDING');

    if (query) {
      list = list.filter(o =>
        String(o.order_id).toLowerCase().includes(query) ||
        String(o.user_id).includes(query) ||
        String(o.username || '').toLowerCase().includes(query)
      );
    }

    if (!list.length) {
      container.innerHTML = '<div class="text-center text-muted text-xs py-8">Mos keluvchi buyurtmalar topilmadi</div>';
      return;
    }

    container.innerHTML = list.map(o => `
      <div class="mobile-card-row">
        <div class="m-card-top">
          <div class="flex items-center gap-2">
            <span class="font-mono font-bold text-xs text-slate-200">#${escapeHtml(o.order_id)}</span>
            <span class="text-muted text-[11px] font-mono">ID: ${escapeHtml(o.user_id)}</span>
          </div>
          ${renderStatusBadge(o.status)}
        </div>
        <div class="m-card-body">
          <div>
            <div class="font-bold text-slate-100 text-sm">${o.username ? '@' + escapeHtml(o.username) : 'Foydalanuvchi'}</div>
            <div class="text-[11px] text-muted">${escapeHtml(formatDate(o.created_at))}</div>
          </div>
          <div class="text-right">
            <div class="font-mono font-bold text-emerald text-base">${escapeHtml(formatMoney(o.final_amount_uzs))}</div>
            <div class="text-[10px] text-muted font-mono">Asosiy: ${escapeHtml(formatMoney(o.base_price_uzs))} (${o.suffix_uzs > 0 ? '+' + escapeHtml(o.suffix_uzs) : '0'})</div>
          </div>
        </div>
        <div class="m-card-footer">
          <span class="badge badge-blue text-[10px]">${escapeHtml(o.plan_name || o.plan_id)}</span>
          ${o.status === 'PAYMENT_REVIEW_REQUIRED'
            ? `<button type="button" class="btn btn-primary btn-sm" data-action="approve-order-review" data-order-id="${escapeHtml(o.order_id)}">Tasdiqlash</button>`
            : '<span class="text-muted text-xs font-mono">—</span>'
          }
        </div>
      </div>
    `).join('');
  }

  async function approveReviewCase(caseId, orderId) {
    if (!confirm(`Kechiktirilgan to‘lovni (Case #${caseId} / Order ${orderId || ''}) tasdiqlamoqchimisiz? PRO obuna darhol faollashadi.`)) return;
    try {
      await apiFetch(`/api/admin/payments/review/${encodeURIComponent(caseId)}/approve`, {
        method: 'POST',
        body: JSON.stringify({ notes: 'Admin qo‘lda tasdiqladi' })
      });
      showToast('Buyurtma muvaffaqiyatli tasdiqlandi!');
      await loadPaymentsHub();
      loadOverview();
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  async function rejectReviewCase(caseId) {
    const notes = prompt(`Case #${caseId} rad etish sababini kiriting:`, 'To‘lov topilmadi');
    if (notes === null) return;
    try {
      await apiFetch(`/api/admin/payments/review/${encodeURIComponent(caseId)}/reject`, {
        method: 'POST',
        body: JSON.stringify({ notes: notes.trim() || 'Admin rad etdi' })
      });
      showToast('Kechiktirilgan holat rad etildi', 'info');
      await loadPaymentsHub();
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  async function approveOrderReview(orderId) {
    if (!confirm(`Buyurtmani (${orderId}) qo‘lda tasdiqlamoqchimisiz? PRO obuna darhol faollashadi.`)) return;
    try {
      const res = await apiFetch('/api/admin/payments/review-cases?status=PENDING');
      const c = (res.cases || []).find(x => x.order_id === orderId);
      if (!c) {
        showToast('Ushbu buyurtma uchun ochiq review case topilmadi.', 'error');
        return;
      }
      await apiFetch(`/api/admin/payments/review/${encodeURIComponent(c.case_id)}/approve`, {
        method: 'POST',
        body: JSON.stringify({ notes: 'Admin qo‘lda tasdiqladi' })
      });
      showToast('Buyurtma muvaffaqiyatli tasdiqlandi!');
      await loadPaymentsHub();
      loadOverview();
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  async function linkUnmatchedToOrder(unmatchedId, suggestedOrderId) {
    const orderId = prompt('Qaysi buyurtma ID siga bog‘lansin?', suggestedOrderId || '');
    if (!orderId || !orderId.trim()) return;
    const notes = prompt('Izoh (audit uchun):', 'Admin unmatched payment bog‘ladi') || '';
    try {
      const res = await apiFetch(`/api/admin/payments/unmatched/${encodeURIComponent(unmatchedId)}/link-order`, {
        method: 'POST',
        body: JSON.stringify({ order_id: orderId.trim(), notes: notes.trim() })
      });
      showToast(res.message || 'To‘lov buyurtmaga bog‘landi!');
      await loadPaymentsHub();
      loadOverview();
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  async function resolveUnmatched(unmatchedId) {
    const statusChoice = prompt('Holat (RESOLVED_REFUNDED yoki IGNORED):', 'RESOLVED_REFUNDED');
    if (!statusChoice) return;
    const notes = prompt('Sabab / Izoh:', 'Pul qaytarildi yoki xatolik');
    if (!notes) return;
    try {
      const res = await apiFetch(`/api/admin/payments/unmatched/${encodeURIComponent(unmatchedId)}/resolve`, {
        method: 'POST',
        body: JSON.stringify({ status: statusChoice.trim(), notes: notes.trim() })
      });
      showToast(res.message || 'Holat hal qilindi.');
      await loadPaymentsHub();
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  // ================= 3. FOYDALANUVCHILAR & USER DOSSIER =================
  async function loadUsers() {
    const query = document.getElementById('users-search-input')?.value || '';
    const filter = document.getElementById('users-filter-sub')?.value || 'all';
    const sortBy = document.getElementById('users-sort-by')?.value || 'created_at';
    const container = document.getElementById('users-list-container');

    try {
      const params = new URLSearchParams({ q: query, filter_status: filter, sort_by: sortBy, limit: '50' });
      const res = await apiFetch(`/api/admin/users?${params.toString()}`);
      state.usersCache = res.users || [];

      if (!container) return;
      if (!state.usersCache.length) {
        container.innerHTML = '<div class="text-center text-muted text-xs py-8">Foydalanuvchilar topilmadi</div>';
        return;
      }

      container.innerHTML = state.usersCache.map(u => {
        const displayName = u.username ? '@' + escapeHtml(u.username) : escapeHtml(u.first_name || ('ID: ' + u.user_id));
        const rawLabel = u.username || u.first_name || String(u.user_id);
        const seg = u.activity_classification?.segment || '';

        return `
          <div class="mobile-card-row">
            <div class="m-card-top">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-bold text-slate-100 text-sm">${displayName}</span>
                <span class="text-muted text-[11px] font-mono">ID: ${escapeHtml(u.user_id)}</span>
                ${seg ? `<span class="badge badge-indigo text-[10px]">${escapeHtml(seg)}</span>` : ''}
              </div>
              <div>
                ${u.is_pro ? '<span class="badge badge-emerald">PRO FAOL</span>' : '<span class="badge badge-gray">BEPUL</span>'}
              </div>
            </div>

            <div class="m-card-body">
              <div class="text-xs">
                ${u.is_pro
                  ? `<span class="text-emerald font-semibold">Tugash vaqti:</span> <span class="font-mono text-slate-300">${escapeHtml(formatDate(u.subscription_expires_at))}</span>`
                  : '<span class="text-muted">Faol obuna mavjud emas</span>'
                }
                <div class="text-[10px] text-muted mt-0.5">Ro‘yxatdan: ${escapeHtml(formatDate(u.created_at))}</div>
              </div>
              <div class="text-right">
                ${u.is_blocked ? '<span class="badge badge-red text-[10px]">BLOKLANGAN</span>' : ''}
              </div>
            </div>

            <div class="m-card-footer">
              <div class="flex items-center gap-1.5 flex-wrap">
                <button type="button" class="btn btn-secondary btn-sm" data-action="user-dossier" data-user-id="${escapeHtml(u.user_id)}">📋 Profil</button>
                ${u.is_pro
                  ? `
                    <button type="button" class="btn btn-danger btn-sm" data-action="revoke-sub" data-user-id="${escapeHtml(u.user_id)}" data-user-label="${escapeHtml(rawLabel)}">Obunani Olish</button>
                    <button type="button" class="btn btn-secondary btn-sm" data-action="open-grant-sub" data-user-id="${escapeHtml(u.user_id)}" data-user-label="${escapeHtml(rawLabel)}" data-extend="1">+ Uzaytirish</button>
                  `
                  : `<button type="button" class="btn btn-primary btn-sm" data-action="open-grant-sub" data-user-id="${escapeHtml(u.user_id)}" data-user-label="${escapeHtml(rawLabel)}" data-extend="0">+ PRO Berish</button>`
                }
              </div>
              <div>
                ${u.is_blocked
                  ? `<button type="button" class="btn btn-ghost btn-sm text-emerald text-xs" data-action="toggle-block" data-user-id="${escapeHtml(u.user_id)}" data-block="0">Blokdan chiqarish</button>`
                  : `<button type="button" class="btn btn-ghost btn-sm text-rose text-xs" data-action="toggle-block" data-user-id="${escapeHtml(u.user_id)}" data-block="1">Bloklash</button>`
                }
              </div>
            </div>
          </div>
        `;
      }).join('');
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  async function openUserDossier(userId) {
    const body = document.getElementById('dossier-modal-body');
    setText('dossier-modal-title', `Foydalanuvchi Dossier — ID: ${userId}`);
    if (body) body.innerHTML = '<div class="text-muted py-4 text-center">Ma’lumotlar yuklanmoqda...</div>';
    openModal('modal-user-dossier');

    try {
      const res = await apiFetch(`/api/admin/users/${encodeURIComponent(userId)}`);
      const u = res.user || {};
      const ex = res.exam_stats || {};
      const subs = res.subscriptions || [];
      const txs = res.payments || [];
      const acts = res.activity_events || [];

      if (body) {
        body.innerHTML = `
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
            <div class="bg-slate-900/80 border border-slate-800 rounded p-2.5">
              <div class="text-[11px] text-muted">Ism / Username</div>
              <div class="font-bold text-slate-100">${escapeHtml(u.first_name || '')} ${u.username ? '(@' + escapeHtml(u.username) + ')' : ''}</div>
            </div>
            <div class="bg-slate-900/80 border border-slate-800 rounded p-2.5">
              <div class="text-[11px] text-muted">Segment / Faollik</div>
              <div class="font-bold text-indigo-200">${escapeHtml(u.activity_classification?.segment || 'UNKNOWN')}</div>
            </div>
            <div class="bg-slate-900/80 border border-slate-800 rounded p-2.5">
              <div class="text-[11px] text-muted">Imtihonlar (O‘tgan / Jami)</div>
              <div class="font-bold text-emerald font-mono">${escapeHtml(ex.passed_exams || 0)} / ${escapeHtml(ex.total_exams || 0)} (${Math.round(Number(ex.avg_score || 0))}%)</div>
            </div>
          </div>

          <div class="bg-slate-900/60 border border-slate-800 rounded p-2.5">
            <div class="font-bold text-slate-200 mb-1">Obunalar tarixi (${subs.length})</div>
            ${subs.length ? subs.slice(0, 5).map(s => `<div class="text-[11px] text-slate-300 font-mono">${escapeHtml(s.status)} • ${escapeHtml(s.plan_id || '')} • ${escapeHtml(formatDate(s.starts_at))} → ${escapeHtml(formatDate(s.expires_at))}</div>`).join('') : '<div class="text-muted">Obuna tarixi yo‘q</div>'}
          </div>

          <div class="bg-slate-900/60 border border-slate-800 rounded p-2.5">
            <div class="font-bold text-slate-200 mb-1">To‘lovlar (${txs.length})</div>
            ${txs.length ? txs.slice(0, 5).map(t => `<div class="text-[11px] text-emerald font-mono">${escapeHtml(formatMoney(t.amount_uzs))} • #${escapeHtml(t.order_id)} • ${escapeHtml(formatDate(t.created_at))}</div>`).join('') : '<div class="text-muted">To‘lovlar yo‘q</div>'}
          </div>

          <div class="bg-slate-900/60 border border-slate-800 rounded p-2.5">
            <div class="font-bold text-slate-200 mb-1">So‘nggi harakatlar (${acts.length})</div>
            ${acts.length ? acts.slice(0, 8).map(ev => `<div class="text-[11px] text-slate-400 font-mono">${escapeHtml(ev.event_name)} (${escapeHtml(ev.feature_area || '')}) • ${escapeHtml(formatDate(ev.created_at))}</div>`).join('') : '<div class="text-muted">Telemetriya yo‘q</div>'}
          </div>
        `;
      }
    } catch (e) {
      if (body) body.innerHTML = `<div class="text-rose p-3">${escapeHtml(e.message)}</div>`;
    }
  }

  async function revokeUserSubscription(userId, name) {
    const reason = prompt(`${name} (ID: ${userId}) ning PRO obunasini bekor qilish sababini yozing:`, 'Admin qarori bilan bekor qilindi');
    if (reason === null) return;
    try {
      const res = await apiFetch(`/api/admin/users/${encodeURIComponent(userId)}/revoke-subscription`, {
        method: 'POST',
        body: JSON.stringify({ reason: reason.trim() || 'Admin qarori bilan bekor qilindi' })
      });
      showToast(res.message || 'PRO obuna bekor qilindi!');
      loadUsers();
      loadOverview();
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  function openGrantSubModal(userId, name, isExtend) {
    document.getElementById('grant-user-id').value = userId;
    setText('grant-user-display', `${name} (ID: ${userId})`);
    setText('grant-modal-title', isExtend ? 'PRO Obunani Uzaytirish' : 'Foydalanuvchiga PRO Obuna Berish');
    document.getElementById('grant-reason').value = '';
    openModal('modal-grant-sub');
  }

  async function toggleUserBlock(userId, shouldBlock) {
    const actionText = shouldBlock ? 'bloklamoqchimisiz' : 'blokdan chiqarmoqchimisiz';
    if (!confirm(`Foydalanuvchini (${userId}) ${actionText}?`)) return;
    try {
      if (shouldBlock) {
        await apiFetch(`/api/admin/users/${encodeURIComponent(userId)}/block`, {
          method: 'POST',
          body: JSON.stringify({ reason: 'Admin qarori bilan bloklandi' })
        });
        showToast('Foydalanuvchi bloklandi');
      } else {
        await apiFetch(`/api/admin/users/${encodeURIComponent(userId)}/unblock`, { method: 'POST' });
        showToast('Foydalanuvchi blokdan chiqarildi');
      }
      loadUsers();
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  // ================= 4. SETTINGS, SYNC, EDITORIAL & OBSERVABILITY =================
  async function loadSettings() {
    const loaders = [];

    // MTProto
    loaders.push((async () => {
      try {
        const mtRes = await apiFetch('/api/admin/mtproto/status');
        const st = mtRes.status || {};
        const isConn = st.connection_status === 'CONNECTED';
        const badge = document.getElementById('mtproto-status-badge');
        if (badge) {
          badge.className = `badge ${isConn ? 'badge-emerald' : 'badge-amber'}`;
          badge.textContent = isConn ? 'ULANGAN (FAOL)' : (st.connection_status || 'ULANMAGAN');
        }
        const disBox = document.getElementById('mtproto-disconnected-box');
        const connBox = document.getElementById('mtproto-connected-box');
        if (disBox) disBox.style.display = isConn ? 'none' : 'block';
        if (connBox) connBox.style.display = isConn ? 'block' : 'none';
        if (isConn) {
          setText('mtproto-account-title', st.account_info?.first_name || 'Telegram Akkaunt Ulangan');
          setText('mtproto-account-phone', st.account_info?.phone || '—');
        }
      } catch {}
    })());

    // Cards & Plans (FINANCE)
    if (hasRole('FINANCE')) {
      document.getElementById('acc-card')?.style.removeProperty('display');
      document.getElementById('acc-pricing')?.style.removeProperty('display');
      loaders.push((async () => {
        try {
          const cardRes = await apiFetch('/api/admin/cards');
          const cards = cardRes.cards || [];
          if (cards.length) {
            const c = cards[0];
            const editId = document.getElementById('edit-card-id');
            if (editId) editId.value = c.id;
            setText('disp-card-number', c.card_number_masked || '•••• •••• •••• ••••');
            setText('disp-card-holder', c.cardholder_name || 'KARTA EGASI');
            setText('disp-card-type', (c.card_type || 'HUMO') + ' CARD');
            setText('acc-card-summary', `${c.card_type || 'HUMO'} •••• ${c.card_suffix || c.suffix_digits || '****'}`);
            const inpHolder = document.getElementById('inp-card-holder');
            const inpType = document.getElementById('inp-card-type');
            if (inpHolder) inpHolder.value = c.cardholder_name || '';
            if (inpType) inpType.value = c.card_type || 'HUMO';
          }
        } catch {}
      })());

      loaders.push((async () => {
        try {
          const planRes = await apiFetch('/api/admin/plans');
          const plans = planRes.plans || [];
          const planContainer = document.getElementById('plans-pricing-container');
          if (planContainer) {
            planContainer.innerHTML = plans.map(p => `
              <div class="mobile-card-row">
                <div class="flex items-center justify-between">
                  <div>
                    <div class="font-bold text-slate-100 text-sm">${escapeHtml(p.name)}</div>
                    <div class="text-xs text-muted font-mono">${escapeHtml(p.duration_days)} kunlik muddat</div>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="font-mono text-emerald font-bold text-sm">${escapeHtml(formatMoney(p.base_price_uzs))}</span>
                    <button type="button" class="btn btn-secondary btn-sm" data-action="edit-plan-price" data-plan-id="${escapeHtml(p.id)}" data-plan-name="${escapeHtml(p.name)}" data-plan-price="${escapeHtml(p.base_price_uzs)}">O‘zgartirish</button>
                  </div>
                </div>
              </div>
            `).join('');
          }
        } catch {}
      })());
    } else {
      const accCard = document.getElementById('acc-card');
      const accPrice = document.getElementById('acc-pricing');
      if (accCard) accCard.style.display = 'none';
      if (accPrice) accPrice.style.display = 'none';
    }

    // Question Sync & Editorial (MODERATOR)
    if (hasRole('MODERATOR')) {
      document.getElementById('acc-sync')?.style.removeProperty('display');
      document.getElementById('acc-editorial')?.style.removeProperty('display');
      loaders.push(loadQuestionSyncStatus(), loadEditorialQueue(state.editorial.page));
    } else {
      const accSync = document.getElementById('acc-sync');
      const accEd = document.getElementById('acc-editorial');
      if (accSync) accSync.style.display = 'none';
      if (accEd) accEd.style.display = 'none';
    }

    // Observability (SUPERADMIN)
    if (hasRole('SUPERADMIN')) {
      document.getElementById('acc-observability')?.style.removeProperty('display');
      loaders.push(loadSystemObservability());
    } else {
      const accObs = document.getElementById('acc-observability');
      if (accObs) accObs.style.display = 'none';
    }

    await Promise.allSettled(loaders);
  }

  async function loadQuestionSyncStatus() {
    try {
      const res = await apiFetch('/api/admin/questions/sync/status');
      if (!res.success) return;
      const db = res.database || {};
      setText('sync-kpi-cq', Number(db.canonical_questions || 0).toLocaleString());
      setText('sync-kpi-ct', Number(db.canonical_translations || 0).toLocaleString());
      setText('sync-kpi-img', Number(db.total_images || 0).toLocaleString());
      setText('sync-kpi-pending', Number(db.pending_staged_reviews || 0).toLocaleString());
      setText('sync-overall-badge', `${Number(db.canonical_questions || 0).toLocaleString()} ta savol`);
      const pendingCount = db.pending_staged_reviews || 0;
      setText('staged-count-badge', `${pendingCount} kutilmoqda`);
      const approveAllBtn = document.getElementById('btn-approve-all-sync');
      if (approveAllBtn) approveAllBtn.style.display = pendingCount > 0 ? 'inline-flex' : 'none';

      (res.sources || []).forEach(s => {
        const badge = document.getElementById(`sync-badge-${s.source_code}`);
        const meta = document.getElementById(`sync-meta-${s.source_code}`);
        if (badge) {
          badge.className = `badge ${s.is_online ? 'badge-emerald' : 'badge-red'}`;
          badge.textContent = s.is_online ? `Onlayn (${s.tickets_count} bilet)` : 'Oflayn';
        }
        if (meta) {
          meta.textContent = s.is_online ? `Tezlik: ${s.response_time_ms}ms | ~${s.estimated_questions} ta savol` : (s.error || 'Xatolik');
        }
      });

      await loadStagedQuestions();
    } catch (e) {
      console.warn('Question sync status error:', e);
    }
  }

  async function loadStagedQuestions() {
    const listEl = document.getElementById('staged-questions-list');
    if (!listEl) return;

    try {
      const res = await apiFetch('/api/admin/questions/staging?status=PENDING_REVIEW');
      state.stagedCache = res.questions || [];
      const count = state.stagedCache.length;
      setText('staged-count-badge', `${count} kutilmoqda`);
      setText('sync-kpi-pending', String(count));
      const approveAllBtn = document.getElementById('btn-approve-all-sync');
      if (approveAllBtn) approveAllBtn.style.display = count > 0 ? 'inline-flex' : 'none';

      if (!count) {
        listEl.innerHTML = '<div class="text-xs text-muted text-center py-4 bg-slate-900/40 rounded border border-slate-800">✅ Kutilayotgan savollar yo‘q.</div>';
        return;
      }

      listEl.innerHTML = state.stagedCache.map(q => {
        const optHtml = (q.options || []).map(opt => `
          <div class="staged-opt-item ${opt.is_correct ? 'correct' : ''}">
            <span class="staged-opt-key">${escapeHtml(opt.key)})</span>
            <span>${escapeHtml(opt.text_uz_latn || '')}</span>
            ${opt.is_correct ? '<span class="ml-auto text-emerald-400 font-bold text-xs">✓ To‘g‘ri</span>' : ''}
          </div>
        `).join('');
        const imgUrl = safeUrl(q.image_src);
        const imgHtml = imgUrl ? `<img src="${escapeHtml(imgUrl)}" class="staged-image-preview ed-thumb-img" alt="Savol rasmi" data-action="open-image" data-url="${escapeHtml(imgUrl)}">` : '';
        const changeBadge = q.change_type === 'AMENDMENT'
          ? '<span class="badge badge-amber text-[10px]">JAVOB TUZATISH</span>'
          : '<span class="badge badge-emerald text-[10px]">YANGI SAVOL</span>';

        return `
          <div class="staged-card" id="staged-card-${escapeHtml(q.id)}">
            <div class="staged-card-top">
              <div class="staged-source-meta">
                <span class="font-bold text-slate-200">${escapeHtml((q.source_code || '').toUpperCase())}</span>
                <span>•</span>
                <span>Bilet ${escapeHtml(q.source_ticket || '?')}, №${escapeHtml(q.source_position || '?')}</span>
                <span>•</span>
                ${changeBadge}
              </div>
              <div class="text-[11px] text-muted">${escapeHtml((q.created_at || '').substring(0, 16))}</div>
            </div>
            <div class="staged-content-grid">
              ${imgHtml}
              <div class="staged-text-box">
                <div class="staged-text-lang">🇺🇿 Lotincha:</div>
                <div>${escapeHtml(q.text_uz_latn || '')}</div>
              </div>
              ${q.text_ru && q.text_ru !== q.text_uz_latn ? `
                <div class="staged-text-box">
                  <div class="staged-text-lang" style="color:#a5b4fc;">🇷🇺 Ruscha:</div>
                  <div class="text-xs text-slate-300">${escapeHtml(q.text_ru)}</div>
                </div>
              ` : ''}
              <div class="staged-options-list">${optHtml}</div>
            </div>
            <div class="staged-actions-row">
              <button type="button" class="btn btn-emerald btn-sm" data-action="approve-staged" data-staged-id="${escapeHtml(q.id)}">✅ Tasdiqlash</button>
              <button type="button" class="btn btn-secondary btn-sm" data-action="edit-staged" data-staged-id="${escapeHtml(q.id)}">✏️ Tahrirlash</button>
              <button type="button" class="btn btn-danger btn-sm" data-action="reject-staged" data-staged-id="${escapeHtml(q.id)}">❌ Rad etish</button>
            </div>
          </div>
        `;
      }).join('');
    } catch (e) {
      listEl.innerHTML = `<div class="text-xs text-red-400 p-3">Xatolik: ${escapeHtml(e.message)}</div>`;
    }
  }

  async function approveStagedQuestion(stagedId) {
    try {
      const card = document.getElementById(`staged-card-${stagedId}`);
      if (card) card.style.opacity = '0.5';
      const res = await apiFetch(`/api/admin/questions/staging/${encodeURIComponent(stagedId)}/approve`, { method: 'POST' });
      showToast(res.message || 'Savol tasdiqlandi!', 'success');
      await loadQuestionSyncStatus();
    } catch (err) {
      showToast(err.message, 'error');
      const card = document.getElementById(`staged-card-${stagedId}`);
      if (card) card.style.opacity = '1';
    }
  }

  async function rejectStagedQuestion(stagedId) {
    const reason = prompt('Rad etish sababini kiriting:', 'Noto‘g‘ri yoki dublikat savol');
    if (!reason) return;
    try {
      const res = await apiFetch(`/api/admin/questions/staging/${encodeURIComponent(stagedId)}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason })
      });
      showToast(res.message || 'Savol rad etildi', 'info');
      await loadQuestionSyncStatus();
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  function openEditStagedModal(stagedId) {
    const q = state.stagedCache.find(item => String(item.id) === String(stagedId));
    if (!q) return;
    document.getElementById('inp-edit-staged-id').value = q.id;
    document.getElementById('inp-edit-staged-latn').value = q.text_uz_latn || '';
    document.getElementById('inp-edit-staged-cyrl').value = q.text_uz_cyrl || '';
    document.getElementById('inp-edit-staged-ru').value = q.text_ru || '';
    document.getElementById('inp-edit-staged-correct-key').value = q.correct_option_key || 'A';
    document.getElementById('inp-edit-staged-explanation').value = q.explanation || '';
    setText('edit-staged-title', `Savol #${q.id} ni Tahrirlash (${(q.source_code || '').toUpperCase()})`);
    openModal('modal-edit-staged');
  }

  // ================= 4.2 EDITORIAL PROVENANCE & BULK APPROVAL =================
  function updateEditorialSelectionUi() {
    const count = state.selectedEditorialIds.size;
    setText('ed-selected-count', String(count));
    const bulkBtn = document.getElementById('btn-ed-bulk-approve');
    if (bulkBtn) bulkBtn.disabled = count === 0;
    const selectAll = document.getElementById('ed-select-all');
    if (selectAll && state.editorial.items.length) {
      selectAll.checked = state.editorial.items.every(i => state.selectedEditorialIds.has(Number(i.id)));
    }
  }

  async function loadEditorialQueue(page = 1) {
    const listEl = document.getElementById('editorial-queue-list');
    if (!listEl) return;
    state.editorial.page = page;
    state.selectedEditorialIds.clear();
    const selectAll = document.getElementById('ed-select-all');
    if (selectAll) selectAll.checked = false;

    const offset = (page - 1) * state.editorial.limit;
    const qVal = (document.getElementById('ed-filter-q')?.value || '').trim();
    const flagVal = (document.getElementById('ed-filter-flag')?.value || '').trim();

    const params = new URLSearchParams({
      status: state.editorial.status,
      limit: String(state.editorial.limit),
      offset: String(offset)
    });
    if (qVal) params.set('q', qVal);
    if (flagVal) params.set('issue_flag', flagVal);

    try {
      const res = await apiFetch(`/api/admin/questions/editorial?${params.toString()}`);
      state.editorial.items = res.items || [];
      state.editorial.total = Number(res.total || 0);

      const sc = res.status_counts || {};
      const pendingCount = Number(sc.PENDING_EDITORIAL_REVIEW || 0);
      const aiCount = Number(sc.AI_DRAFT_PENDING_REVIEW || 0);
      setText('ed-count-pending', pendingCount.toLocaleString());
      setText('ed-count-ai', aiCount.toLocaleString());
      setText('ed-count-approved', Number(sc.APPROVED || 0).toLocaleString());
      setText('ed-count-rejected', Number(sc.REJECTED || 0).toLocaleString());
      setText('editorial-overall-badge', `${(pendingCount + aiCount).toLocaleString()} ta ko‘rib chiqilmagan`);

      const maxPage = Math.max(1, Math.ceil(state.editorial.total / state.editorial.limit));
      setText('ed-pagination-summary', `Jami: ${state.editorial.total.toLocaleString()} ta savol (${page}/${maxPage}-sahifa)`);
      setText('ed-page-label', `${page} / ${maxPage}`);
      const prevBtn = document.getElementById('ed-btn-prev');
      const nextBtn = document.getElementById('ed-btn-next');
      if (prevBtn) prevBtn.disabled = page <= 1;
      if (nextBtn) nextBtn.disabled = page >= maxPage;
      updateEditorialSelectionUi();

      if (!state.editorial.items.length) {
        listEl.innerHTML = '<div class="text-xs text-muted text-center py-4 bg-slate-900/40 rounded border border-slate-800">Tanlangan filtr bo‘yicha elementlar topilmadi.</div>';
        return;
      }

      listEl.innerHTML = state.editorial.items.map(item => {
        const flagsHtml = (item.issue_flags || []).map(f => {
          const isBleed = f.includes('BLEED') || f.includes('MISMATCH');
          return `<span class="editorial-flag-pill ${isBleed ? 'bleed' : ''}">${escapeHtml(f)}</span>`;
        }).join('');
        const legalBadgeClass = item.current_legal_status === 'VERIFIED_PRIMARY_LAW'
          ? 'badge-emerald'
          : (item.current_legal_status === 'VERIFIED_FIRST_AID_OR_TECH' ? 'badge-blue' : 'badge-amber');
        const tr = item.translations || {};
        const uzLatnQ = (tr.uz_latn && tr.uz_latn.question_text) || item.preview_text_uz_latn || '';
        const imgUrl = safeUrl(item.image_url);
        const optionsHtml = (item.options || []).map(opt => {
          const isCorr = Boolean(opt.is_correct) || (opt.key && opt.key === item.correct_option_key);
          return `<div class="text-[11px] px-2 py-0.5 rounded ${isCorr ? 'bg-slate-900 text-emerald font-bold' : 'text-slate-400'}">${escapeHtml(opt.key)}) ${escapeHtml(opt.text_uz_latn || '')} ${isCorr ? '✓' : ''}</div>`;
        }).join('');

        return `
          <div class="staged-card" id="editorial-card-${escapeHtml(item.id)}">
            <div class="staged-card-top">
              <div class="staged-source-meta">
                <input type="checkbox" class="ed-row-checkbox" data-queue-id="${escapeHtml(item.id)}">
                <span class="font-bold text-slate-200 font-mono">${escapeHtml(item.canonical_id)}</span>
                <span>•</span>
                <span>${escapeHtml(item.category_name || 'Kategoriyasiz')}</span>
                <span class="badge ${legalBadgeClass} text-[10px]">${escapeHtml(item.current_legal_status || 'UNRESOLVED_LEGAL_REVIEW')}</span>
              </div>
              <div class="text-[11px] text-muted">${escapeHtml(item.source_type || 'AUDIT_FLAG')} • #${escapeHtml(item.id)}</div>
            </div>

            ${imgUrl ? `<div><img src="${escapeHtml(imgUrl)}" class="ed-thumb-img" alt="Savol rasmi" data-action="open-image" data-url="${escapeHtml(imgUrl)}"></div>` : ''}

            <div class="text-xs text-slate-200 leading-relaxed">${escapeHtml(uzLatnQ)}</div>

            ${optionsHtml ? `<div class="space-y-1 bg-slate-900/40 p-2 rounded border border-slate-800">${optionsHtml}</div>` : ''}

            ${item.current_legal_hint ? `<div class="text-[11px] text-slate-400"><b>Joriy havola:</b> ${escapeHtml(item.current_legal_hint)}</div>` : ''}

            ${item.draft_explanation ? `<div class="text-[11px] p-2 rounded bg-indigo-950/40 border border-indigo-500/30 text-indigo-200"><b>🤖 Qoralama (${escapeHtml(item.language)}):</b> ${escapeHtml(item.draft_explanation)}</div>` : ''}

            ${flagsHtml ? `<div class="flex flex-wrap gap-1">${flagsHtml}</div>` : ''}

            <div class="staged-actions-row">
              <button type="button" class="btn btn-primary btn-sm" data-action="ed-open-modal" data-queue-id="${escapeHtml(item.id)}">✏️ Tahrir &amp; Tasdiqlash</button>
              <button type="button" class="btn btn-secondary btn-sm" data-action="ed-ai-draft" data-queue-id="${escapeHtml(item.id)}">✨ AI Qoralama</button>
              ${item.review_status !== 'REJECTED' ? `<button type="button" class="btn btn-danger btn-sm" data-action="ed-reject" data-queue-id="${escapeHtml(item.id)}">❌ Rad etish</button>` : ''}
            </div>
          </div>
        `;
      }).join('');
    } catch (e) {
      listEl.innerHTML = `<div class="text-xs text-red-400 p-3">Tahririyat navbati xatoligi: ${escapeHtml(e.message)}</div>`;
    }
  }

  function openEditEditorialModal(queueId) {
    const item = state.editorial.items.find(x => String(x.id) === String(queueId));
    if (!item) return;

    const tr = item.translations || {};
    document.getElementById('ed-modal-queue-id').value = item.id;
    setText('ed-modal-title', `${item.canonical_id} — Huquqiy Asos & Izoh`);

    const flagsText = (item.issue_flags || []).join(', ') || 'Yo‘q';
    document.getElementById('ed-modal-meta-box').innerHTML = `
      <div><b>Kategoriya:</b> ${escapeHtml(item.category_name || '')} &nbsp;|&nbsp; <b>Til:</b> ${escapeHtml(item.language)} &nbsp;|&nbsp; <b>To‘g‘ri kalit:</b> ${escapeHtml(item.correct_option_key || '—')}</div>
      <div><b>Joriy havola izi:</b> ${escapeHtml(item.current_legal_hint || 'Mavjud emas')}</div>
      <div><b>Aniqlangan belgilar:</b> ${escapeHtml(flagsText)}</div>
    `;

    const visBox = document.getElementById('ed-modal-visual-box');
    const imgUrl = safeUrl(item.image_url);
    const opts = item.options || [];
    if (visBox && (imgUrl || opts.length)) {
      visBox.style.display = 'block';
      visBox.innerHTML = `
        ${imgUrl ? `<img src="${escapeHtml(imgUrl)}" class="ed-thumb-img" alt="Savol rasmi">` : ''}
        ${opts.map(o => `<div class="text-[11px] ${o.is_correct ? 'text-emerald font-bold' : 'text-slate-400'}">${escapeHtml(o.key)}) ${escapeHtml(o.text_uz_latn || '')} ${o.is_correct ? '✓' : ''}</div>`).join('')}
      `;
    } else if (visBox) {
      visBox.style.display = 'none';
      visBox.innerHTML = '';
    }

    document.getElementById('ed-modal-q-latn').value = (tr.uz_latn && tr.uz_latn.question_text) || '';
    document.getElementById('ed-modal-q-cyrl').value = (tr.uz_cyrl && tr.uz_cyrl.question_text) || '';
    document.getElementById('ed-modal-q-ru').value = (tr.ru && tr.ru.question_text) || '';

    document.getElementById('ed-modal-expl-latn').value =
      (item.language === 'uz_latn' && item.draft_explanation) || (tr.uz_latn && tr.uz_latn.explanation) || '';
    document.getElementById('ed-modal-expl-cyrl').value =
      (item.language === 'uz_cyrl' && item.draft_explanation) || (tr.uz_cyrl && tr.uz_cyrl.explanation) || '';
    document.getElementById('ed-modal-expl-ru').value =
      (item.language === 'ru' && item.draft_explanation) || (tr.ru && tr.ru.explanation) || '';

    const defaultStatus = item.current_legal_status === 'VERIFIED_FIRST_AID_OR_TECH'
      ? 'VERIFIED_FIRST_AID_OR_TECH'
      : 'VERIFIED_PRIMARY_LAW';
    document.getElementById('ed-modal-legal-status').value = defaultStatus;
    document.getElementById('ed-modal-legal-doc-title').value = item.current_legal_doc_title || item.draft_legal_doc_title || '';
    document.getElementById('ed-modal-legal-doc-url').value = item.current_legal_doc_url || item.draft_legal_doc_url || '';
    document.getElementById('ed-modal-legal-chapter').value = item.current_legal_chapter || item.draft_legal_chapter || '';
    document.getElementById('ed-modal-legal-clause').value = item.current_legal_clause || item.draft_legal_clause || '';
    document.getElementById('ed-modal-legal-effective-date').value = item.current_legal_effective_date || '';
    document.getElementById('ed-modal-reviewer-notes').value = 'Human verified';

    openModal('modal-edit-editorial');
  }

  async function requestAiDraft(queueId, populateModal = false) {
    try {
      showToast('AI qoralama yaratilmoqda...', 'info');
      const res = await apiFetch(`/api/admin/questions/editorial/${encodeURIComponent(queueId)}/ai-draft`, { method: 'POST' });
      const drafts = res.drafts || {};
      if (populateModal) {
        if (drafts.uz_latn) document.getElementById('ed-modal-expl-latn').value = drafts.uz_latn;
        if (drafts.uz_cyrl) document.getElementById('ed-modal-expl-cyrl').value = drafts.uz_cyrl;
        if (drafts.ru) document.getElementById('ed-modal-expl-ru').value = drafts.ru;
      } else {
        await loadEditorialQueue(state.editorial.page);
      }
      showToast('AI qoralama karantinga saqlandi (tasdiqlashdan oldin tekshiring).', 'success');
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  async function bulkApproveSelectedEditorial() {
    const ids = Array.from(state.selectedEditorialIds);
    if (!ids.length) return;
    const legalStatus = document.getElementById('ed-bulk-legal-status')?.value || 'VERIFIED_PRIMARY_LAW';
    const clause = (document.getElementById('ed-bulk-clause')?.value || '').trim();
    if (!confirm(`${ids.length} ta tanlangan tahririyat yozuvini tasdiqlamoqchimisiz?`)) return;

    try {
      const res = await apiFetch('/api/admin/questions/editorial/bulk-approve', {
        method: 'POST',
        body: JSON.stringify({
          queue_ids: ids,
          legal_verification_status: legalStatus,
          legal_doc_title: 'Vazirlar Mahkamasining 2022-yil 12-apreldagi 172-son qarori (YHQ)',
          legal_clause: clause || null,
          reviewer_notes: 'Bulk admin approved'
        })
      });
      showToast(`Tasdiqlandi: ${(res.approved || []).length} ta, Xato: ${(res.failed || []).length} ta`, 'success');
      await loadEditorialQueue(state.editorial.page);
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  async function rejectEditorialQueueItem(queueId) {
    const reason = prompt('Rad etish sababini kiriting:', 'Qo‘shimcha tekshiruv uchun rad etildi');
    if (!reason) return;
    try {
      await apiFetch(`/api/admin/questions/editorial/${encodeURIComponent(queueId)}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason })
      });
      showToast(`Tahririyat yozuvi #${queueId} rad etildi.`, 'info');
      await loadEditorialQueue(state.editorial.page);
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  // ================= 5. BROADCAST SYSTEM =================
  let selectedBroadcastTarget = 'all';

  function selectBroadcastTarget(target) {
    selectedBroadcastTarget = target;
    document.querySelectorAll('.broadcast-target-opt').forEach(el => el.classList.remove('active'));
    document.getElementById(`target-opt-${target}`)?.classList.add('active');
  }

  function insertBroadcastTag(tag) {
    const textarea = document.getElementById('broadcast-message-text');
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const selected = text.substring(start, end);
    const replacement = `<${tag}>${selected || 'matn'}</${tag}>`;
    textarea.value = text.substring(0, start) + replacement + text.substring(end);
    textarea.focus();
    updateBroadcastPreview();
  }

  function insertBroadcastLink() {
    const textarea = document.getElementById('broadcast-message-text');
    if (!textarea) return;
    const url = prompt('Havola manzilini kiriting (URL):', 'https://t.me/');
    if (!url || !safeUrl(url)) return;
    const linkText = prompt('Havola matni:', 'Bu yerni bosing') || url;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    textarea.value = text.substring(0, start) + `<a href="${url}">${linkText}</a>` + text.substring(end);
    textarea.focus();
    updateBroadcastPreview();
  }

  function updateBroadcastPreview() {
    const textarea = document.getElementById('broadcast-message-text');
    const preview = document.getElementById('broadcast-live-preview');
    const counter = document.getElementById('broadcast-char-count');
    if (!textarea) return;
    const val = textarea.value;
    if (counter) counter.textContent = `${val.length} / 4000`;
    if (preview) preview.innerHTML = sanitizeTelegramPreviewHtml(val);
  }

  async function loadBroadcastAudience() {
    try {
      const res = await apiFetch('/api/admin/broadcast/audience');
      if (res?.counts) {
        setText('bc-count-all', `${res.counts.all} ta`);
        setText('bc-count-free', `${res.counts.free} ta`);
        setText('bc-count-pro', `${res.counts.pro} ta`);
      }
    } catch {}
  }

  async function loadBroadcastHistory() {
    const container = document.getElementById('broadcast-history-list');
    if (!container) return;
    try {
      const res = await apiFetch('/api/admin/broadcast/history');
      const list = res.history || [];
      if (!list.length) {
        container.innerHTML = '<div class="text-xs text-muted py-2">Yuborilgan xabarnomalar mavjud emas.</div>';
        return;
      }
      container.innerHTML = list.map(item => {
        const meta = item.meta || {};
        const targetMap = { all: '👥 Barchaga', pro: '⭐ PRO larga', free: '🆓 Bepullarga' };
        return `
          <div class="p-3 bg-slate-900 border border-slate-800 rounded-lg text-xs space-y-1">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-200">${escapeHtml(targetMap[meta.target_group] || meta.target_group || 'Barchaga')}</span>
              <span class="text-muted font-mono">${escapeHtml((item.performed_at || '').replace('T', ' ').substring(0, 16))}</span>
            </div>
            <div class="text-slate-300 font-sans italic bg-slate-950 p-2 rounded border border-slate-800 mt-1">"${escapeHtml(meta.message_snippet || '')}"</div>
            <div class="flex items-center gap-3 text-xs pt-1 text-slate-400">
              <span class="text-emerald">✓ Yetkazildi: <b>${escapeHtml(meta.sent || 0)}</b></span>
              <span class="text-rose">✕ Xatolik: <b>${escapeHtml(meta.failed || 0)}</b></span>
              <span class="text-muted">Jami: <b>${escapeHtml(meta.total_targets || 0)}</b></span>
            </div>
          </div>
        `;
      }).join('');
    } catch {
      container.innerHTML = '<div class="text-xs text-rose py-2">Tarixni yuklashda xatolik.</div>';
    }
  }

  function loadBroadcastView() {
    loadBroadcastAudience();
    loadBroadcastHistory();
    updateBroadcastPreview();
  }

  async function sendBroadcast() {
    const textarea = document.getElementById('broadcast-message-text');
    const msg = textarea ? textarea.value.trim() : '';
    if (!msg) {
      showToast('Iltimos, xabar matnini kiriting!', 'error');
      return;
    }
    if (!confirm(`Ushbu xabarni (${selectedBroadcastTarget}) auditoriyasiga yuborishni tasdiqlaysizmi?`)) return;

    const btn = document.getElementById('btn-send-broadcast');
    if (btn) btn.disabled = true;
    try {
      const res = await apiFetch('/api/admin/broadcast/send', {
        method: 'POST',
        body: JSON.stringify({ target_group: selectedBroadcastTarget, message: msg })
      });
      showToast(res.message || 'Xabarnoma yuborildi!');
      if (textarea) textarea.value = '';
      updateBroadcastPreview();
      loadBroadcastHistory();
    } catch (e) {
      showToast(e.message, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  // ================= 6. SYSTEM OBSERVABILITY =================
  async function loadSystemObservability() {
    try {
      const [healthRes, logsRes] = await Promise.all([
        apiFetch('/api/admin/system/health'),
        apiFetch('/api/admin/system/audit-logs?limit=10')
      ]);

      const badge = document.getElementById('obs-overall-badge');
      const routesEl = document.getElementById('obs-routes-summary');
      const logsEl = document.getElementById('obs-audit-logs-list');

      const obs = healthRes.observability || {};
      const db = healthRes.database || {};
      const rl = healthRes.rate_limiter || {};
      const rt = healthRes.runtime || {};

      if (badge) {
        const statusText = healthRes.status || 'HEALTHY';
        badge.className = `badge ${statusText === 'HEALTHY' ? 'badge-emerald' : 'badge-amber'}`;
        badge.textContent = statusText;
      }
      setText('obs-db-val', `${db.integrity_check || 'ok'} • ${db.latency_ms ?? 0}ms`);
      setText('obs-latency-val', `p50 ${obs.latency_p50_ms ?? 0}ms / p95 ${obs.latency_p95_ms ?? 0}ms`);
      setText('obs-req-val', `${obs.total_requests ?? 0} req • 5xx:${obs.errors_5xx ?? 0} • RL:${rl.rejected_requests ?? 0}`);
      const upMin = Math.floor((obs.uptime_seconds || 0) / 60);
      setText('obs-runtime-val', `${upMin}m • ${rt.rss_mb ?? 'n/a'}MB • ${rt.router_mode || 'full'}`);

      if (routesEl) {
        const top = (obs.top_routes || []).slice(0, 4).map(r => `${r.route} (${r.count}x, p95 ${r.p95_ms}ms)`);
        routesEl.textContent = top.length ? `Top yo‘llar: ${top.join(' | ')}` : 'Hozircha marshrutlar statistikasi yig‘ilmoqda.';
      }

      if (logsEl) {
        const items = logsRes.logs || [];
        logsEl.innerHTML = items.length
          ? items.map(l => `
              <div class="bg-slate-900/60 border border-slate-800 rounded p-2 flex items-center justify-between gap-2">
                <div class="min-w-0">
                  <span class="font-bold text-slate-200">${escapeHtml(l.action)}</span>
                  <span class="text-muted"> — ${escapeHtml(l.username || 'system')}</span>
                  <div class="text-[11px] text-slate-400 truncate">${escapeHtml(l.details || '')}</div>
                </div>
                <span class="text-[11px] text-muted font-mono shrink-0">${escapeHtml((l.performed_at || '').slice(0, 19))}</span>
              </div>
            `).join('')
          : '<div class="text-muted py-2">Audit yozuvlari topilmadi.</div>';
      }
    } catch (e) {
      console.error('Observability load error:', e);
    }
  }

  // ================= AUTH & POLLERS =================
  function startOtpCountdown(seconds) {
    clearInterval(state.otpTimerInterval);
    const display = document.getElementById('otp-countdown');
    let left = seconds;
    const render = s => {
      const m = Math.floor(s / 60);
      const rem = s % 60;
      if (display) display.textContent = `${String(m).padStart(2, '0')}:${String(rem).padStart(2, '0')}`;
    };
    render(left);
    state.otpTimerInterval = setInterval(() => {
      left--;
      if (left <= 0) {
        clearInterval(state.otpTimerInterval);
        if (display) display.textContent = '00:00 (Muddati tugadi)';
      } else {
        render(left);
      }
    }, 1000);
  }

  async function handleLogout() {
    if (!confirm('Admin paneldan chiqmoqchimisiz?')) return;
    try { await apiFetch('/api/admin/auth/logout', { method: 'POST' }); } catch {}
    location.reload();
  }

  async function loadTopbarIndicators() {
    try {
      const res = await apiFetch('/api/admin/mtproto/status');
      const st = res.status || {};
      const isConn = st.connection_status === 'CONNECTED';
      const dot = document.getElementById('topbar-mtproto-dot');
      const deskDot = document.getElementById('mtproto-status-dot-desktop');
      const mobDot = document.getElementById('m-dot-mtproto');
      if (dot) dot.className = `indicator-dot ${isConn ? 'connected' : ''}`;
      setText('topbar-mtproto-text', isConn ? 'MTProto: Faol' : 'MTProto: Nofaol');
      if (deskDot) deskDot.className = `status-dot-mini ${isConn ? 'connected' : ''}`;
      if (mobDot) mobDot.className = `m-status-dot ${isConn ? 'connected' : ''}`;

      const activeOrd = st.active_orders_count || 0;
      const bNav = document.getElementById('badge-nav-orders');
      const bMob = document.getElementById('m-badge-orders');
      if (bNav) { bNav.textContent = activeOrd; bNav.style.display = activeOrd > 0 ? 'inline-block' : 'none'; }
      if (bMob) { bMob.textContent = activeOrd; bMob.style.display = activeOrd > 0 ? 'block' : 'none'; }
    } catch {}
  }

  function applyAdminProfileUi(admin) {
    state.currentAdmin = admin;
    const uname = admin?.username || 'Admin';
    const role = String(admin?.role || 'SUPERADMIN').toUpperCase();
    setText('topbar-admin-name', uname);
    setText('topbar-admin-avatar', uname.charAt(0).toUpperCase());
    setText('topbar-admin-role', role);
    setText('topbar-role-badge', role);
  }

  function showAppCockpit() {
    document.getElementById('auth-container').style.display = 'none';
    document.getElementById('app-container').style.display = 'flex';
    switchView('overview');
    loadTopbarIndicators();
    setInterval(() => {
      if (!document.hidden) loadTopbarIndicators();
    }, 20000);
  }

  // ================= CENTRALIZED EVENT DELEGATION (ZERO INLINE JS) =================
  function setupEventListeners() {
    document.querySelectorAll('.sidebar-nav .nav-item, .mobile-bottom-nav .m-nav-item').forEach(el => {
      el.addEventListener('click', e => {
        e.preventDefault();
        switchView(el.getAttribute('data-view'));
      });
    });

    document.addEventListener('click', e => {
      const closeBtn = e.target.closest('[data-close-modal]');
      if (closeBtn) {
        closeModal(closeBtn.getAttribute('data-close-modal'));
        return;
      }

      const accHeader = e.target.closest('.accordion-header[data-acc-target]');
      if (accHeader) {
        toggleAccordion(accHeader.getAttribute('data-acc-target'));
        return;
      }

      const actionEl = e.target.closest('[data-action]');
      if (actionEl) {
        const action = actionEl.getAttribute('data-action');
        if (action === 'switch-view') switchView(actionEl.getAttribute('data-view'));
        else if (action === 'logout') handleLogout();
        else if (action === 'reload-bi') loadBiAnalytics();
        else if (action === 'open-image') {
          const u = safeUrl(actionEl.getAttribute('data-url'));
          if (u) window.open(u, '_blank', 'noopener,noreferrer');
        }
        else if (action === 'approve-order-review') approveOrderReview(actionEl.getAttribute('data-order-id'));
        else if (action === 'approve-review') approveReviewCase(actionEl.getAttribute('data-case-id'), actionEl.getAttribute('data-order-id'));
        else if (action === 'reject-review') rejectReviewCase(actionEl.getAttribute('data-case-id'));
        else if (action === 'link-unmatched') linkUnmatchedToOrder(actionEl.getAttribute('data-unmatched-id'), actionEl.getAttribute('data-candidate-order'));
        else if (action === 'resolve-unmatched') resolveUnmatched(actionEl.getAttribute('data-unmatched-id'));
        else if (action === 'user-dossier') openUserDossier(actionEl.getAttribute('data-user-id'));
        else if (action === 'open-grant-sub') openGrantSubModal(actionEl.getAttribute('data-user-id'), actionEl.getAttribute('data-user-label'), actionEl.getAttribute('data-extend') === '1');
        else if (action === 'revoke-sub') revokeUserSubscription(actionEl.getAttribute('data-user-id'), actionEl.getAttribute('data-user-label'));
        else if (action === 'toggle-block') toggleUserBlock(actionEl.getAttribute('data-user-id'), actionEl.getAttribute('data-block') === '1');
        else if (action === 'edit-plan-price') {
          document.getElementById('edit-plan-id').value = actionEl.getAttribute('data-plan-id');
          setText('edit-plan-name', actionEl.getAttribute('data-plan-name'));
          document.getElementById('edit-plan-price').value = actionEl.getAttribute('data-plan-price');
          document.getElementById('edit-plan-reason').value = '';
          openModal('modal-edit-price');
        }
        else if (action === 'approve-staged') approveStagedQuestion(actionEl.getAttribute('data-staged-id'));
        else if (action === 'edit-staged') openEditStagedModal(actionEl.getAttribute('data-staged-id'));
        else if (action === 'reject-staged') rejectStagedQuestion(actionEl.getAttribute('data-staged-id'));
        else if (action === 'ed-open-modal') openEditEditorialModal(actionEl.getAttribute('data-queue-id'));
        else if (action === 'ed-ai-draft') requestAiDraft(actionEl.getAttribute('data-queue-id'), false);
        else if (action === 'ed-reject') rejectEditorialQueueItem(actionEl.getAttribute('data-queue-id'));
        return;
      }
    });

    // Payment Subtabs & Search
    document.getElementById('payments-subtabs')?.addEventListener('click', e => {
      const btn = e.target.closest('.subtab-btn[data-ptab]');
      if (btn) setPaymentTab(btn.getAttribute('data-ptab'));
    });
    document.getElementById('payments-search-input')?.addEventListener('input', () => renderPaymentsHub());
    document.getElementById('btn-refresh-payments')?.addEventListener('click', () => loadPaymentsHub());

    // Overview BI range
    document.getElementById('ov-sales-range')?.addEventListener('change', () => loadBiAnalytics());

    // Users Search / Filter / Sort
    document.getElementById('users-search-input')?.addEventListener('input', () => {
      clearTimeout(state.searchDebounce);
      state.searchDebounce = setTimeout(loadUsers, 300);
    });
    document.getElementById('users-filter-sub')?.addEventListener('change', () => loadUsers());
    document.getElementById('users-sort-by')?.addEventListener('change', () => loadUsers());

    // Broadcast Controls
    document.getElementById('btn-refresh-bc-audience')?.addEventListener('click', loadBroadcastAudience);
    document.getElementById('broadcast-targets-grid')?.addEventListener('click', e => {
      const opt = e.target.closest('[data-bc-target]');
      if (opt) selectBroadcastTarget(opt.getAttribute('data-bc-target'));
    });
    document.getElementById('broadcast-format-bar')?.addEventListener('click', e => {
      const tagBtn = e.target.closest('[data-bc-tag]');
      if (tagBtn) insertBroadcastTag(tagBtn.getAttribute('data-bc-tag'));
    });
    document.getElementById('btn-bc-insert-link')?.addEventListener('click', insertBroadcastLink);
    document.getElementById('broadcast-message-text')?.addEventListener('input', updateBroadcastPreview);
    document.getElementById('btn-send-broadcast')?.addEventListener('click', sendBroadcast);

    // Editorial Queue Filters, Bulk Checkboxes & Pagination
    document.getElementById('ed-status-pills')?.addEventListener('click', e => {
      const btn = e.target.closest('.subtab-btn[data-ed-status]');
      if (!btn) return;
      state.editorial.status = btn.getAttribute('data-ed-status');
      document.querySelectorAll('#ed-status-pills .subtab-btn').forEach(b => b.classList.toggle('active', b === btn));
      loadEditorialQueue(1);
    });
    document.getElementById('ed-filter-flag')?.addEventListener('change', () => loadEditorialQueue(1));
    document.getElementById('btn-ed-search')?.addEventListener('click', () => loadEditorialQueue(1));
    document.getElementById('btn-editorial-audit-seed')?.addEventListener('click', async () => {
      const btn = document.getElementById('btn-editorial-audit-seed');
      if (btn) btn.disabled = true;
      try {
        const res = await apiFetch('/api/admin/questions/editorial/audit-seed', { method: 'POST' });
        showToast(`Audit yakunlandi: ${res.queued_new_items || 0} ta yangi element.`, 'success');
        await loadEditorialQueue(1);
      } catch (e) { showToast(e.message, 'error'); }
      finally { if (btn) btn.disabled = false; }
    });

    document.getElementById('ed-select-all')?.addEventListener('change', e => {
      const checked = e.target.checked;
      document.querySelectorAll('.ed-row-checkbox').forEach(cb => {
        cb.checked = checked;
        const qid = Number(cb.getAttribute('data-queue-id'));
        if (checked) state.selectedEditorialIds.add(qid);
        else state.selectedEditorialIds.delete(qid);
      });
      updateEditorialSelectionUi();
    });

    document.getElementById('editorial-queue-list')?.addEventListener('change', e => {
      if (!e.target.classList.contains('ed-row-checkbox')) return;
      const qid = Number(e.target.getAttribute('data-queue-id'));
      if (e.target.checked) state.selectedEditorialIds.add(qid);
      else state.selectedEditorialIds.delete(qid);
      updateEditorialSelectionUi();
    });

    document.getElementById('btn-ed-bulk-approve')?.addEventListener('click', bulkApproveSelectedEditorial);
    document.getElementById('btn-ed-modal-ai-draft')?.addEventListener('click', () => {
      const qid = document.getElementById('ed-modal-queue-id')?.value;
      if (qid) requestAiDraft(qid, true);
    });

    document.getElementById('ed-btn-prev')?.addEventListener('click', () => {
      if (state.editorial.page > 1) loadEditorialQueue(state.editorial.page - 1);
    });
    document.getElementById('ed-btn-next')?.addEventListener('click', () => {
      const maxPage = Math.max(1, Math.ceil(state.editorial.total / state.editorial.limit));
      if (state.editorial.page < maxPage) loadEditorialQueue(state.editorial.page + 1);
    });

    // Observability refresh
    document.getElementById('btn-refresh-obs')?.addEventListener('click', loadSystemObservability);

    // Sync controls
    document.getElementById('btn-reload-staged')?.addEventListener('click', loadStagedQuestions);
    document.getElementById('btn-check-sync-updates')?.addEventListener('click', async () => {
      const btn = document.getElementById('btn-check-sync-updates');
      const consoleEl = document.getElementById('sync-console-output');
      if (btn) btn.disabled = true;
      if (consoleEl) consoleEl.textContent = '🔍 Manbalar tekshirilmoqda...';
      try {
        const res = await apiFetch('/api/admin/questions/sync/check?auto_stage=true', { method: 'POST' });
        if (consoleEl) consoleEl.textContent = JSON.stringify(res.source_reports || res, null, 2);
        await loadQuestionSyncStatus();
      } catch (e) { showToast(e.message, 'error'); }
      finally { if (btn) btn.disabled = false; }
    });
    document.getElementById('btn-approve-all-sync')?.addEventListener('click', async () => {
      if (!confirm('Barcha kutilayotgan savollarni tasdiqlaysizmi?')) return;
      try {
        const res = await apiFetch('/api/admin/questions/staging/approve-all', { method: 'POST' });
        showToast(res.message || 'Tasdiqlandi!', 'success');
        await loadQuestionSyncStatus();
      } catch (e) { showToast(e.message, 'error'); }
    });

    // Auth & Modal Forms
    document.getElementById('form-login')?.addEventListener('submit', async e => {
      e.preventDefault();
      const u = document.getElementById('login-username').value;
      const p = document.getElementById('login-password').value;
      const btn = document.getElementById('btn-login-submit');
      btn.disabled = true;
      btn.textContent = 'Tekshirilmoqda...';
      try {
        const res = await apiFetch('/api/admin/auth/login', {
          method: 'POST',
          body: JSON.stringify({ username: u, password: p })
        });
        state.otpChallengeId = res.data.challenge_id;
        setText('otp-tg-masked', res.data.telegram_id_masked || '***');
        document.getElementById('form-login').style.display = 'none';
        document.getElementById('form-otp').style.display = 'block';
        startOtpCountdown(res.data.expires_in_seconds || 300);
        document.getElementById('otp-input').focus();
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = 'Kirish';
      }
    });

    document.getElementById('form-otp')?.addEventListener('submit', async e => {
      e.preventDefault();
      const code = document.getElementById('otp-input').value.trim();
      const btn = document.getElementById('btn-otp-submit');
      btn.disabled = true;
      btn.textContent = 'Tasdiqlanmoqda...';
      try {
        const verifyRes = await apiFetch('/api/admin/auth/otp/verify', {
          method: 'POST',
          body: JSON.stringify({ challenge_id: state.otpChallengeId, otp_code: code })
        });
        applyAdminProfileUi(verifyRes.data?.admin || {});
        showToast('Xush kelibsiz!');
        clearInterval(state.otpTimerInterval);
        showAppCockpit();
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = 'Tasdiqlash & Kirish';
      }
    });

    document.getElementById('btn-otp-back')?.addEventListener('click', () => {
      clearInterval(state.otpTimerInterval);
      document.getElementById('form-otp').style.display = 'none';
      document.getElementById('form-login').style.display = 'block';
    });

    document.getElementById('btn-logout')?.addEventListener('click', handleLogout);

    document.getElementById('form-grant-sub')?.addEventListener('submit', async e => {
      e.preventDefault();
      const userId = document.getElementById('grant-user-id').value;
      const duration = parseInt(document.querySelector('input[name="grant-duration"]:checked')?.value || '14', 10);
      const reason = document.getElementById('grant-reason').value;
      try {
        await apiFetch(`/api/admin/users/${encodeURIComponent(userId)}/grant-subscription`, {
          method: 'POST',
          body: JSON.stringify({ duration_days: duration, reason })
        });
        showToast('PRO obuna faollashtirildi!');
        closeModal('modal-grant-sub');
        loadUsers();
        loadOverview();
      } catch (err) { showToast(err.message, 'error'); }
    });

    document.getElementById('form-edit-price')?.addEventListener('submit', async e => {
      e.preventDefault();
      const planId = document.getElementById('edit-plan-id').value;
      const newPrice = parseInt(document.getElementById('edit-plan-price').value, 10);
      const reason = document.getElementById('edit-plan-reason').value;
      try {
        await apiFetch(`/api/admin/plans/${encodeURIComponent(planId)}/price`, {
          method: 'POST',
          body: JSON.stringify({ new_price_uzs: newPrice, reason })
        });
        showToast('Tarif narxi yangilandi!');
        closeModal('modal-edit-price');
        loadSettings();
      } catch (err) { showToast(err.message, 'error'); }
    });

    document.getElementById('inp-card-number')?.addEventListener('input', e => {
      let val = e.target.value.replace(/\D/g, '').substring(0, 16);
      e.target.value = val.replace(/(.{4})/g, '$1 ').trim();
    });

    document.getElementById('form-edit-card')?.addEventListener('submit', async e => {
      e.preventDefault();
      let cardId = parseInt(document.getElementById('edit-card-id')?.value, 10);
      if (isNaN(cardId) || cardId <= 0) cardId = 1;
      const rawNum = (document.getElementById('inp-card-number')?.value || '').replace(/\s+/g, '');
      const cardHolder = (document.getElementById('inp-card-holder')?.value || '').trim();
      const cardType = document.getElementById('inp-card-type')?.value || 'HUMO';
      if (rawNum && !/^\d{16}$/.test(rawNum)) {
        showToast('Karta raqami aniq 16 xonali bo‘lishi shart!', 'error');
        return;
      }
      const body = { cardholder_name: cardHolder, card_type: cardType };
      if (rawNum) body.card_number = rawNum;
      try {
        const res = await apiFetch(`/api/admin/cards/${cardId}`, { method: 'PUT', body: JSON.stringify(body) });
        showToast(res.message || 'Karta yangilandi!');
        document.getElementById('inp-card-number').value = '';
        await loadSettings();
      } catch (err) { showToast(err.message, 'error'); }
    });

    // MTProto Forms
    document.getElementById('form-mtproto-connect')?.addEventListener('submit', async e => {
      e.preventDefault();
      const body = { phone_number: document.getElementById('inp-mtproto-phone').value };
      const apiId = document.getElementById('inp-mtproto-api-id')?.value;
      const apiHash = document.getElementById('inp-mtproto-api-hash')?.value;
      if (apiId) body.api_id = parseInt(apiId, 10);
      if (apiHash) body.api_hash = apiHash.trim();
      try {
        const res = await apiFetch('/api/admin/mtproto/send-code', { method: 'POST', body: JSON.stringify(body) });
        showToast(res.message);
        document.getElementById('form-mtproto-connect').style.display = 'none';
        document.getElementById('form-mtproto-code-step').style.display = 'block';
      } catch (err) { showToast(err.message, 'error'); }
    });

    document.getElementById('form-mtproto-code-step')?.addEventListener('submit', async e => {
      e.preventDefault();
      try {
        const res = await apiFetch('/api/admin/mtproto/sign-in', {
          method: 'POST',
          body: JSON.stringify({ code: document.getElementById('inp-mtproto-code-val').value })
        });
        if (res.requires_2fa) {
          document.getElementById('form-mtproto-code-step').style.display = 'none';
          document.getElementById('form-mtproto-2fa-step').style.display = 'block';
        } else {
          showToast(res.message);
          loadSettings();
          loadTopbarIndicators();
        }
      } catch (err) { showToast(err.message, 'error'); }
    });

    document.getElementById('form-mtproto-2fa-step')?.addEventListener('submit', async e => {
      e.preventDefault();
      try {
        const res = await apiFetch('/api/admin/mtproto/sign-in-2fa', {
          method: 'POST',
          body: JSON.stringify({ password: document.getElementById('inp-mtproto-2fa-val').value })
        });
        showToast(res.message);
        loadSettings();
      } catch (err) { showToast(err.message, 'error'); }
    });

    document.getElementById('btn-mtproto-reset')?.addEventListener('click', () => {
      document.getElementById('form-mtproto-connect').style.display = 'block';
      document.getElementById('form-mtproto-code-step').style.display = 'none';
      document.getElementById('form-mtproto-2fa-step').style.display = 'none';
    });

    document.getElementById('btn-mtproto-disconnect')?.addEventListener('click', async () => {
      if (!confirm('MTProto sessiyasini uzmoqchimisiz?')) return;
      try {
        const res = await apiFetch('/api/admin/mtproto/disconnect', { method: 'POST' });
        showToast(res.message);
        loadSettings();
        loadTopbarIndicators();
      } catch (e) { showToast(e.message, 'error'); }
    });

    document.getElementById('form-edit-staged')?.addEventListener('submit', async e => {
      e.preventDefault();
      const stagedId = document.getElementById('inp-edit-staged-id')?.value;
      if (!stagedId) return;
      const legalStatus = document.getElementById('inp-edit-staged-legal-status')?.value || 'UNRESOLVED_LEGAL_REVIEW';
      const payload = {
        text_uz_latn: document.getElementById('inp-edit-staged-latn')?.value.trim(),
        text_uz_cyrl: document.getElementById('inp-edit-staged-cyrl')?.value.trim(),
        text_ru: document.getElementById('inp-edit-staged-ru')?.value.trim(),
        correct_option_key: document.getElementById('inp-edit-staged-correct-key')?.value,
        explanation: document.getElementById('inp-edit-staged-explanation')?.value.trim(),
        explanation_uz_cyrl: document.getElementById('inp-edit-staged-expl-cyrl')?.value.trim() || null,
        explanation_ru: document.getElementById('inp-edit-staged-expl-ru')?.value.trim() || null,
        legal_verification_status: legalStatus,
        legal_doc_title: document.getElementById('inp-edit-staged-legal-doc-title')?.value.trim() || null,
        legal_chapter: document.getElementById('inp-edit-staged-legal-chapter')?.value.trim() || null,
        legal_clause: document.getElementById('inp-edit-staged-legal-clause')?.value.trim() || null,
        legal_doc_url: document.getElementById('inp-edit-staged-legal-doc-url')?.value.trim() || null
      };
      try {
        const res = await apiFetch(`/api/admin/questions/staging/${encodeURIComponent(stagedId)}/edit`, {
          method: 'POST',
          body: JSON.stringify(payload)
        });
        showToast(res.message || 'Savol tasdiqlandi!', 'success');
        closeModal('modal-edit-staged');
        await loadQuestionSyncStatus();
      } catch (err) { showToast(err.message, 'error'); }
    });

    document.getElementById('form-edit-editorial')?.addEventListener('submit', async e => {
      e.preventDefault();
      const queueId = document.getElementById('ed-modal-queue-id')?.value;
      if (!queueId) return;
      const legalStatus = document.getElementById('ed-modal-legal-status')?.value || 'VERIFIED_PRIMARY_LAW';
      const docTitle = document.getElementById('ed-modal-legal-doc-title')?.value.trim() || null;
      const chapter = document.getElementById('ed-modal-legal-chapter')?.value.trim() || null;
      const clause = document.getElementById('ed-modal-legal-clause')?.value.trim() || null;

      if (legalStatus === 'VERIFIED_PRIMARY_LAW' && (!docTitle || (!chapter && !clause))) {
        showToast('VERIFIED_PRIMARY_LAW uchun hujjat nomi va bob yoki band shart!', 'error');
        return;
      }

      const explanationsByLang = {};
      const explLatn = document.getElementById('ed-modal-expl-latn')?.value.trim();
      const explCyrl = document.getElementById('ed-modal-expl-cyrl')?.value.trim();
      const explRu = document.getElementById('ed-modal-expl-ru')?.value.trim();
      if (explLatn) explanationsByLang.uz_latn = explLatn;
      if (explCyrl) explanationsByLang.uz_cyrl = explCyrl;
      if (explRu) explanationsByLang.ru = explRu;

      const questionTextsByLang = {};
      const qLatn = document.getElementById('ed-modal-q-latn')?.value.trim();
      const qCyrl = document.getElementById('ed-modal-q-cyrl')?.value.trim();
      const qRu = document.getElementById('ed-modal-q-ru')?.value.trim();
      if (qLatn) questionTextsByLang.uz_latn = qLatn;
      if (qCyrl) questionTextsByLang.uz_cyrl = qCyrl;
      if (qRu) questionTextsByLang.ru = qRu;

      try {
        const res = await apiFetch(`/api/admin/questions/editorial/${encodeURIComponent(queueId)}/approve`, {
          method: 'POST',
          body: JSON.stringify({
            legal_verification_status: legalStatus,
            legal_doc_title: docTitle,
            legal_doc_url: document.getElementById('ed-modal-legal-doc-url')?.value.trim() || null,
            legal_chapter: chapter,
            legal_clause: clause,
            legal_effective_date: document.getElementById('ed-modal-legal-effective-date')?.value.trim() || null,
            explanations_by_lang: Object.keys(explanationsByLang).length ? explanationsByLang : null,
            question_texts_by_lang: Object.keys(questionTextsByLang).length ? questionTextsByLang : null,
            reviewer_notes: document.getElementById('ed-modal-reviewer-notes')?.value.trim() || 'Human verified'
          })
        });
        showToast(`${res.canonical_id} tasdiqlandi!`, 'success');
        closeModal('modal-edit-editorial');
        await loadEditorialQueue(state.editorial.page);
      } catch (err) { showToast(err.message, 'error'); }
    });
  }

  async function init() {
    setupEventListeners();
    try {
      const me = await apiFetch('/api/admin/auth/me');
      if (me && me.admin) {
        applyAdminProfileUi(me.admin);
        showAppCockpit();
        return;
      }
    } catch {}
    document.getElementById('auth-container').style.display = 'flex';
    document.getElementById('app-container').style.display = 'none';
  }

  window.addEventListener('DOMContentLoaded', init);
})();
