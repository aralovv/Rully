/**
 * RULLY Admin Control Panel (v2.3.0)
 * Mobile-First, Clean UX Single Page Application Controller
 */

(function () {
  'use strict';

  // Global App State
  const state = {
    currentAdmin: null,
    activeView: 'overview',
    otpChallengeId: null,
    otpTimerInterval: null,
    currentPaymentTab: 'ALL',
    searchDebounce: null,
    ordersCache: [],
    usersCache: []
  };

  // Helper: Escape HTML to avoid XSS in dynamically rendered strings
  function escapeHtml(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Helper: API Fetch with JSON and Credentials
  async function apiFetch(endpoint, options = {}) {
    options.headers = options.headers || {};
    if (!options.headers['Content-Type'] && !(options.body instanceof FormData)) {
      options.headers['Content-Type'] = 'application/json';
    }
    options.credentials = 'same-origin';

    const res = await fetch(endpoint, options);
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      throw new Error(data.detail || data.message || `Xatolik yuz berdi (${res.status})`);
    }
    return data;
  }

  // Toast Notifications
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
    if (amount == null) return '0 UZS';
    return Number(amount).toLocaleString('ru-RU') + ' UZS';
  }

  function formatDate(isoStr) {
    if (!isoStr) return '-';
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('uz-UZ', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoStr;
    }
  }

  // ================= ACCORDION CONTROLLER =================
  window.toggleAccordion = function (accId) {
    const el = document.getElementById(accId);
    if (!el) return;
    el.classList.toggle('open');
  };

  // ================= VIEW SWITCHER =================
  window.switchView = function (viewName) {
    state.activeView = viewName;

    // 1. Update Desktop Sidebar Nav
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(el => {
      el.classList.toggle('active', el.getAttribute('data-view') === viewName);
    });

    // 2. Update Mobile Bottom Nav
    document.querySelectorAll('.mobile-bottom-nav .m-nav-item').forEach(el => {
      el.classList.toggle('active', el.getAttribute('data-view') === viewName);
    });

    // 3. Update Panels
    document.querySelectorAll('.view-panel').forEach(el => el.classList.remove('active'));
    const targetPane = document.getElementById(`view-${viewName}`);
    if (targetPane) targetPane.classList.add('active');

    // 4. Update Header Title
    const titles = {
      overview: 'Asosiy Panel',
      payments: 'To‘lovlar & Buyurtmalar',
      users: 'Foydalanuvchilar',
      broadcast: 'Xabarnoma (Broadcast)',
      settings: 'MTProto & Sozlamalar'
    };
    const titleEl = document.getElementById('topbar-view-title');
    if (titleEl) titleEl.textContent = titles[viewName] || 'Boshqaruv';

    // 5. Scroll main container to top
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // 6. Load data for active view
    switch (viewName) {
      case 'overview': loadOverview(); break;
      case 'payments': loadPaymentsHub(); break;
      case 'users': loadUsers(); break;
      case 'broadcast': loadBroadcastView(); break;
      case 'settings': loadSettings(); break;
    }
  };

  // ================= 1. ASOSIY PANEL (OVERVIEW) =================
  async function loadOverview() {
    try {
      // 1. Load Real Financial KPIs
      const res = await apiFetch('/api/admin/dashboard/kpi');
      const kpis = res.kpis || {};

      const elUsers = document.getElementById('kpi-total-users');
      const elNewToday = document.getElementById('kpi-new-today');
      const elActiveSubs = document.getElementById('kpi-active-subs');
      const elSubsToday = document.getElementById('kpi-subs-today');
      const elTodayRev = document.getElementById('kpi-today-rev');
      const elTotalRev = document.getElementById('kpi-total-rev');
      const elMonthRev = document.getElementById('kpi-month-rev');

      if (elUsers) elUsers.textContent = kpis.total_users || 0;
      if (elNewToday) elNewToday.textContent = `${kpis.new_users_today || 0} yangi`;
      if (elActiveSubs) elActiveSubs.textContent = kpis.active_subscribers || 0;
      if (elSubsToday) elSubsToday.textContent = kpis.subscriptions_today || 0;
      if (elTodayRev) elTodayRev.textContent = formatMoney(kpis.today_revenue_uzs || 0);
      if (elTotalRev) elTotalRev.textContent = formatMoney(kpis.total_revenue_uzs || 0);
      if (elMonthRev) elMonthRev.textContent = formatMoney(kpis.month_revenue_uzs || 0);

      // 2. Load MTProto Status Banner
      const mtRes = await apiFetch('/api/admin/mtproto/status');
      const st = mtRes.status || {};
      const isConn = st.connection_status === 'CONNECTED';

      const badge = document.getElementById('overview-mtproto-badge');
      const desc = document.getElementById('ov-mtproto-desc');
      const icon = document.getElementById('ov-mtproto-icon');
      const btnTxt = document.getElementById('ov-mtproto-btn-txt');

      if (badge) {
        badge.className = `badge ${isConn ? 'badge-emerald' : 'badge-amber'}`;
        badge.textContent = isConn ? 'FAOL — TINGLAMOQDA' : 'NOFAOL (ULANMAGAN)';
      }
      if (desc) {
        desc.textContent = isConn
          ? `Ulangan hisob: ${st.account_info?.first_name || ''} (${st.account_info?.phone || ''}). Humocardbot real-vaqtda tinglanmoqda.`
          : 'Humocardbot to‘lov xabarnomalarini avtomat ushlash uchun Telegram akkauntingizni ulang.';
      }
      if (btnTxt) {
        btnTxt.textContent = isConn ? 'Holatni Ko‘rish' : 'Akkauntni Ulash';
      }
      if (icon) {
        icon.style.background = isConn ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)';
        icon.style.color = isConn ? '#10b981' : '#f59e0b';
      }

      // 3. Load Recent Orders (Cards for Mobile)
      const ordRes = await apiFetch('/api/admin/orders?limit=5');
      const orders = ordRes.orders || [];
      const container = document.getElementById('overview-orders-container');

      if (container) {
        if (!orders.length) {
          container.innerHTML = '<div class="text-center text-muted text-xs py-8">Hozircha buyurtmalar yo‘q</div>';
        } else {
          container.innerHTML = orders.map(o => `
            <div class="mobile-card-row">
              <div class="m-card-top">
                <span class="font-mono font-bold text-xs text-slate-200">#${o.order_id}</span>
                ${renderStatusBadge(o.status)}
              </div>
              <div class="m-card-body">
                <div>
                  <div class="font-bold text-slate-100 text-sm">${o.username ? '@' + escapeHtml(o.username) : 'ID: ' + o.user_id}</div>
                  <div class="text-[11px] text-muted">${formatDate(o.created_at)}</div>
                </div>
                <div class="text-right">
                  <div class="font-mono font-bold text-emerald text-sm">${formatMoney(o.final_amount_uzs)}</div>
                  <div class="text-[10px] text-muted"><span class="badge badge-blue text-[10px] py-0">${escapeHtml(o.plan_name || o.plan_id)}</span></div>
                </div>
              </div>
            </div>
          `).join('');
        }
      }

    } catch (e) {
      console.error("Dashboard yuklashda xatolik:", e);
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

  // ================= 2. TO‘LOVLAR & BUYURTMALAR (PAYMENTS HUB) =================
  window.setPaymentTab = function (tab) {
    state.currentPaymentTab = tab;
    document.querySelectorAll('.subtab-btn').forEach(b => {
      b.classList.toggle('active', b.getAttribute('data-ptab') === tab);
    });
    renderPaymentsCards();
  };

  async function loadPaymentsHub() {
    try {
      const res = await apiFetch('/api/admin/orders?limit=100');
      state.ordersCache = res.orders || [];
      renderPaymentsCards();
    } catch (e) {
      showToast(e.message, 'error');
    }
  }

  window.filterPaymentsList = function () {
    renderPaymentsCards();
  };

  function renderPaymentsCards() {
    const container = document.getElementById('payments-list-container');
    if (!container) return;

    const query = (document.getElementById('payments-search-input')?.value || '').toLowerCase().trim();
    let list = state.ordersCache;

    // Filter by Tab
    if (state.currentPaymentTab === 'PAID') list = list.filter(o => o.status === 'PAID');
    else if (state.currentPaymentTab === 'PENDING') list = list.filter(o => o.status === 'PENDING');
    else if (state.currentPaymentTab === 'REVIEW') list = list.filter(o => o.status === 'PAYMENT_REVIEW_REQUIRED');

    // Filter by Search
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
            <span class="font-mono font-bold text-xs text-slate-200">#${o.order_id}</span>
            <span class="text-muted text-[11px] font-mono">ID: ${o.user_id}</span>
          </div>
          ${renderStatusBadge(o.status)}
        </div>
        <div class="m-card-body">
          <div>
            <div class="font-bold text-slate-100 text-sm">${o.username ? '@' + escapeHtml(o.username) : 'Foydalanuvchi'}</div>
            <div class="text-[11px] text-muted">${formatDate(o.created_at)}</div>
          </div>
          <div class="text-right">
            <div class="font-mono font-bold text-emerald text-base">${formatMoney(o.final_amount_uzs)}</div>
            <div class="text-[10px] text-muted font-mono">Asosiy: ${formatMoney(o.base_price_uzs)} (${o.suffix_uzs > 0 ? '+' + o.suffix_uzs : '0'})</div>
          </div>
        </div>
        <div class="m-card-footer">
          <span class="badge badge-blue text-[10px]">${escapeHtml(o.plan_name || o.plan_id)}</span>
          ${o.status === 'PAYMENT_REVIEW_REQUIRED'
            ? `<button class="btn btn-primary btn-sm" onclick="approveOrderReview('${o.order_id}')">Tasdiqlash</button>`
            : `<span class="text-muted text-xs font-mono">—</span>`
          }
        </div>
      </div>
    `).join('');
  }

  window.approveOrderReview = async function (orderId) {
    if (!confirm(`Buyurtmani (${orderId}) qo‘lda tasdiqlamoqchimisiz? PRO obuna darhol faollashadi.`)) return;
    try {
      const res = await apiFetch(`/api/admin/payments/review-cases`);
      const c = (res.cases || []).find(x => x.order_id === orderId);
      if (c) {
        await apiFetch(`/api/admin/payments/review/${c.case_id}/approve`, {
          method: 'POST',
          body: JSON.stringify({ note: 'Admin qo‘lda tasdiqladi' })
        });
      }
      showToast("Buyurtma muvaffaqiyatli tasdiqlandi!");
      loadPaymentsHub();
      loadOverview();
    } catch (e) {
      showToast(e.message, 'error');
    }
  };

  // ================= 3. FOYDALANUVCHILAR (USERS) =================
  window.debounceUserSearch = function () {
    clearTimeout(state.searchDebounce);
    state.searchDebounce = setTimeout(loadUsers, 300);
  };

  async function loadUsers() {
    const query = document.getElementById('users-search-input')?.value || '';
    const filter = document.getElementById('users-filter-sub')?.value || 'all';
    const container = document.getElementById('users-list-container');

    try {
      const res = await apiFetch(`/api/admin/users?query=${encodeURIComponent(query)}&filter_status=${filter}`);
      state.usersCache = res.users || [];

      if (!container) return;

      if (!state.usersCache.length) {
        container.innerHTML = '<div class="text-center text-muted text-xs py-8">Foydalanuvchilar topilmadi</div>';
        return;
      }

      container.innerHTML = state.usersCache.map(u => {
        const displayName = u.username ? '@' + escapeHtml(u.username) : escapeHtml(u.first_name || ('ID: ' + u.user_id));
        const jsName = escapeHtml(u.username || u.first_name || u.user_id);

        return `
          <div class="mobile-card-row">
            <div class="m-card-top">
              <div class="flex items-center gap-2">
                <span class="font-bold text-slate-100 text-sm">${displayName}</span>
                <span class="text-muted text-[11px] font-mono">ID: ${u.user_id}</span>
              </div>
              <div>
                ${u.is_pro
                  ? '<span class="badge badge-emerald">PRO FAOL</span>'
                  : '<span class="badge badge-gray">BEPUL</span>'
                }
              </div>
            </div>

            <div class="m-card-body">
              <div class="text-xs">
                ${u.is_pro
                  ? `<span class="text-emerald font-semibold">Tugash vaqti:</span> <span class="font-mono text-slate-300">${formatDate(u.subscription_expires_at)}</span>`
                  : `<span class="text-muted">Faol obuna mavjud emas</span>`
                }
                <div class="text-[10px] text-muted mt-0.5">Ro‘yxatdan: ${formatDate(u.created_at)}</div>
              </div>
              <div class="text-right">
                ${u.is_blocked ? '<span class="badge badge-red text-[10px]">BLOKLANGAN</span>' : ''}
              </div>
            </div>

            <!-- SMART ACTION BUTTONS: OBUNANI OLISH vs PRO BERISH -->
            <div class="m-card-footer">
              <div class="flex items-center gap-1.5 flex-wrap">
                ${u.is_pro
                  ? `
                    <button class="btn btn-danger btn-sm" onclick="revokeUserSubscription(${u.user_id}, '${jsName}')">
                      Obunani Olish
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="openGrantSubModal(${u.user_id}, '${jsName}', true)">
                      + Uzaytirish
                    </button>
                  `
                  : `
                    <button class="btn btn-primary btn-sm" onclick="openGrantSubModal(${u.user_id}, '${jsName}', false)">
                      + PRO Berish
                    </button>
                  `
                }
              </div>

              <div>
                ${u.is_blocked
                  ? `<button class="btn btn-ghost btn-sm text-emerald text-xs" onclick="toggleUserBlock(${u.user_id}, false)">Blokdan chiqarish</button>`
                  : `<button class="btn btn-ghost btn-sm text-rose text-xs" onclick="toggleUserBlock(${u.user_id}, true)">Bloklash</button>`
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

  // Revoke Subscription Immediately with Reason
  window.revokeUserSubscription = async function (userId, name) {
    const reason = prompt(`${name} (ID: ${userId}) ning PRO obunasini bekor qilish sababini yozing:`, "Admin qarori bilan bekor qilindi");
    if (reason === null) return;
    const cleanReason = reason.trim() || "Admin qarori bilan bekor qilindi";

    try {
      const res = await apiFetch(`/api/admin/users/${userId}/revoke-subscription`, {
        method: 'POST',
        body: JSON.stringify({ reason: cleanReason })
      });
      showToast(res.message || "PRO obuna darhol bekor qilindi!");
      loadUsers();
      loadOverview();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  window.openGrantSubModal = function (userId, name, isExtend = false) {
    document.getElementById('grant-user-id').value = userId;
    document.getElementById('grant-user-display').textContent = `${name} (ID: ${userId})`;
    document.getElementById('grant-modal-title').textContent = isExtend
      ? "PRO Obunani Uzaytirish"
      : "Foydalanuvchiga PRO Obuna Berish";
    document.getElementById('grant-reason').value = '';
    document.getElementById('modal-grant-sub').style.display = 'flex';
  };

  window.toggleUserBlock = async function (userId, shouldBlock) {
    const actionText = shouldBlock ? "bloklamoqchimisiz" : "blokdan chiqarmoqchimisiz";
    if (!confirm(`Foydalanuvchini (${userId}) ${actionText}?`)) return;

    try {
      if (shouldBlock) {
        await apiFetch(`/api/admin/users/${userId}/block`, {
          method: 'POST',
          body: JSON.stringify({ reason: "Admin qarori" })
        });
        showToast("Foydalanuvchi bloklandi");
      } else {
        await apiFetch(`/api/admin/users/${userId}/unblock`, { method: 'POST' });
        showToast("Foydalanuvchi blokdan chiqarildi");
      }
      loadUsers();
    } catch (e) {
      showToast(e.message, 'error');
    }
  };

  // ================= 4. MTProto & SOZLAMALAR =================
  async function loadSettings() {
    try {
      // 1. MTProto Status
      const mtRes = await apiFetch('/api/admin/mtproto/status');
      const st = mtRes.status || {};
      const isConn = st.connection_status === 'CONNECTED';

      const badge = document.getElementById('mtproto-status-badge');
      if (badge) {
        badge.className = `badge ${isConn ? 'badge-emerald' : 'badge-amber'}`;
        badge.textContent = isConn ? 'ULANGAN (FAOL)' : 'ULANMAGAN';
      }

      const disBox = document.getElementById('mtproto-disconnected-box');
      const connBox = document.getElementById('mtproto-connected-box');
      if (disBox) disBox.style.display = isConn ? 'none' : 'block';
      if (connBox) connBox.style.display = isConn ? 'block' : 'none';

      if (isConn) {
        const titleEl = document.getElementById('mtproto-account-title');
        const phoneEl = document.getElementById('mtproto-account-phone');
        if (titleEl) titleEl.textContent = st.account_info?.first_name || 'Telegram Akkaunt Ulangan';
        if (phoneEl) phoneEl.textContent = st.account_info?.phone || '';
      }

      // 2. Receiving Bank Card Details & Form Pre-fill
      const cardRes = await apiFetch('/api/admin/cards');
      const cards = cardRes.cards || [];
      if (cards.length) {
        const c = cards[0];
        const editId = document.getElementById('edit-card-id');
        const dispNum = document.getElementById('disp-card-number');
        const dispHolder = document.getElementById('disp-card-holder');
        const dispType = document.getElementById('disp-card-type');
        const accSummary = document.getElementById('acc-card-summary');
        const inpHolder = document.getElementById('inp-card-holder');
        const inpType = document.getElementById('inp-card-type');

        const activeCardId = c.id || c.card_id || 1;
        if (editId) editId.value = activeCardId;
        if (dispNum) dispNum.textContent = c.card_number_masked;
        if (dispHolder) dispHolder.textContent = c.cardholder_name;
        if (dispType) dispType.textContent = (c.card_type || 'HUMO') + ' CARD';
        if (accSummary) accSummary.textContent = `${c.card_type || 'HUMO'} •••• ${c.card_suffix || c.suffix_digits || '5370'}`;
        if (inpHolder) inpHolder.value = c.cardholder_name;
        if (inpType) inpType.value = c.card_type || 'HUMO';
      }

      // 3. Subscription Plans Pricing
      const planRes = await apiFetch('/api/admin/plans');
      const plans = planRes.plans || [];
      const planContainer = document.getElementById('plans-pricing-container');

      if (planContainer) {
        planContainer.innerHTML = plans.map(p => `
          <div class="mobile-card-row">
            <div class="flex items-center justify-between">
              <div>
                <div class="font-bold text-slate-100 text-sm">${escapeHtml(p.name)}</div>
                <div class="text-xs text-muted font-mono">${p.duration_days} kunlik muddat</div>
              </div>
              <div class="flex items-center gap-3">
                <span class="font-mono text-emerald font-bold text-sm">${formatMoney(p.base_price_uzs)}</span>
                <button class="btn btn-secondary btn-sm" onclick="openPriceModal('${p.id}', '${escapeHtml(p.name)}', ${p.base_price_uzs})">O‘zgartirish</button>
              </div>
            </div>
          </div>
        `).join('');
      }

      // 4. Load Question Sync & Source Monitoring + Editorial Legal Queue
      await loadQuestionSyncStatus();
      await loadEditorialQueue(1);

    } catch (e) {
      console.error("Sozlamalar yuklashda xatolik:", e);
    }
  }

  // ================= 4.1 QUESTION SYNC & HUMAN-IN-THE-LOOP REVIEW CONTROLLER =================
  let cachedStagedQuestions = [];

  async function loadQuestionSyncStatus() {
    try {
      const res = await apiFetch('/api/admin/questions/sync/status');
      if (!res.success) return;

      const db = res.database || {};
      const cqEl = document.getElementById('sync-kpi-cq');
      const ctEl = document.getElementById('sync-kpi-ct');
      const imgEl = document.getElementById('sync-kpi-img');
      const pendingEl = document.getElementById('sync-kpi-pending');
      const overallBadge = document.getElementById('sync-overall-badge');
      const stagedBadge = document.getElementById('staged-count-badge');
      const approveAllBtn = document.getElementById('btn-approve-all-sync');

      if (cqEl) cqEl.textContent = Number(db.canonical_questions || 0).toLocaleString();
      if (ctEl) ctEl.textContent = Number(db.canonical_translations || 0).toLocaleString();
      if (imgEl) imgEl.textContent = Number(db.total_images || 0).toLocaleString();
      if (pendingEl) pendingEl.textContent = Number(db.pending_staged_reviews || 0).toLocaleString();
      if (overallBadge) overallBadge.textContent = `${Number(db.canonical_questions || 0).toLocaleString()} ta savol`;

      const pendingCount = db.pending_staged_reviews || 0;
      if (stagedBadge) stagedBadge.textContent = `${pendingCount} kutilmoqda`;
      if (approveAllBtn) approveAllBtn.style.display = pendingCount > 0 ? 'inline-flex' : 'none';

      const sources = res.sources || [];
      sources.forEach(s => {
        const badge = document.getElementById(`sync-badge-${s.source_code}`);
        const meta = document.getElementById(`sync-meta-${s.source_code}`);
        if (badge) {
          badge.className = `badge ${s.is_online ? 'badge-emerald' : 'badge-red'}`;
          badge.textContent = s.is_online ? `Onlayn (${s.tickets_count} bilet)` : 'Oflayn';
        }
        if (meta) {
          meta.textContent = s.is_online 
            ? `Tezlik: ${s.response_time_ms}ms | ~${s.estimated_questions} ta savol`
            : (s.error || 'Ulanishda xatolik');
        }
      });

      await loadStagedQuestions();
    } catch (e) {
      console.warn("Question sync status fetch error:", e);
    }
  }

  window.loadStagedQuestions = async function () {
    const listEl = document.getElementById('staged-questions-list');
    if (!listEl) return;

    try {
      const res = await apiFetch('/api/admin/questions/staging?status=PENDING_REVIEW');
      cachedStagedQuestions = res.questions || [];
      const count = cachedStagedQuestions.length;

      const badge = document.getElementById('staged-count-badge');
      const pendingKpi = document.getElementById('sync-kpi-pending');
      const approveAllBtn = document.getElementById('btn-approve-all-sync');

      if (badge) badge.textContent = `${count} kutilmoqda`;
      if (pendingKpi) pendingKpi.textContent = count;
      if (approveAllBtn) approveAllBtn.style.display = count > 0 ? 'inline-flex' : 'none';

      if (!cachedStagedQuestions.length) {
        listEl.innerHTML = `
          <div class="text-xs text-muted text-center py-4 bg-slate-900/40 rounded border border-slate-800">
            ✅ Kutilayotgan savollar yo‘q. Hamma savollar ko‘rib chiqilgan va asosiy bazada tasdiqlangan.
          </div>
        `;
        return;
      }

      listEl.innerHTML = cachedStagedQuestions.map(q => {
        const options = q.options || [];
        const optHtml = options.map(opt => `
          <div class="staged-opt-item ${opt.is_correct ? 'correct' : ''}">
            <span class="staged-opt-key">${opt.key})</span>
            <span>${escapeHtml(opt.text_uz_latn || '')}</span>
            ${opt.is_correct ? '<span class="ml-auto text-emerald-400 font-bold text-xs">✓ To‘g‘ri</span>' : ''}
          </div>
        `).join('');

        const imgHtml = q.image_src ? `
          <img src="${q.image_src}" class="staged-image-preview" alt="Savol rasmi" onclick="window.open('${q.image_src}', '_blank')">
        ` : '';

        const changeBadge = q.change_type === 'AMENDMENT' 
          ? '<span class="badge badge-amber text-[10px]">JAVOB TUZATISH</span>' 
          : '<span class="badge badge-emerald text-[10px]">YANGI SAVOL</span>';

        return `
          <div class="staged-card" id="staged-card-${q.id}">
            <div class="staged-card-top">
              <div class="staged-source-meta">
                <span class="font-bold text-slate-200">${q.source_code.toUpperCase()}</span>
                <span>•</span>
                <span>Bilet ${q.source_ticket || '?'}, №${q.source_position || '?'}</span>
                <span>•</span>
                ${changeBadge}
              </div>
              <div class="text-[11px] text-muted">${q.created_at ? q.created_at.substring(0, 16) : ''}</div>
            </div>

            <div class="staged-content-grid">
              ${imgHtml}

              <div class="staged-text-box">
                <div class="staged-text-lang">🇺🇿 Lotincha:</div>
                <div>${escapeHtml(q.text_uz_latn || '')}</div>
              </div>

              ${q.text_ru && q.text_ru !== q.text_uz_latn ? `
                <div class="staged-text-box">
                  <div class="staged-text-lang" style="color: #a5b4fc;">🇷🇺 Ruscha:</div>
                  <div class="text-xs text-slate-300">${escapeHtml(q.text_ru)}</div>
                </div>
              ` : ''}

              <div class="staged-options-list">
                ${optHtml}
              </div>

              ${q.explanation ? `
                <div class="text-[11px] text-slate-400 p-2 bg-slate-900/60 rounded border border-slate-800">
                  <span class="font-bold text-slate-300">💡 Izoh:</span> ${escapeHtml(q.explanation)}
                </div>
              ` : ''}
            </div>

            <div class="staged-actions-row">
              <button type="button" class="btn btn-emerald btn-sm" onclick="approveStagedQuestion(${q.id})">
                ✅ Tasdiqlash & Bazaga Qo‘shish
              </button>
              <button type="button" class="btn btn-secondary btn-sm" onclick="openEditStagedModal(${q.id})">
                ✏️ Tahrirlash
              </button>
              <button type="button" class="btn btn-danger btn-sm" onclick="rejectStagedQuestion(${q.id})">
                ❌ Rad etish
              </button>
            </div>
          </div>
        `;
      }).join('');

    } catch (e) {
      console.error("Staged questions fetch error:", e);
      listEl.innerHTML = `<div class="text-xs text-red-400 p-3">Kutilayotgan savollarni yuklashda xatolik: ${e.message}</div>`;
    }
  };

  window.approveStagedQuestion = async function (stagedId) {
    try {
      const card = document.getElementById(`staged-card-${stagedId}`);
      if (card) card.style.opacity = '0.5';

      const res = await apiFetch(`/api/admin/questions/staging/${stagedId}/approve`, { method: 'POST' });
      showToast(res.message || "Savol tasdiqlandi va bazaga qo‘shildi!", "success");
      await loadQuestionSyncStatus();
    } catch (err) {
      showToast(err.message, "error");
      const card = document.getElementById(`staged-card-${stagedId}`);
      if (card) card.style.opacity = '1';
    }
  };

  window.rejectStagedQuestion = async function (stagedId) {
    const reason = prompt("Ushbu savolni rad etish sababini kiriting:", "Noto‘g‘ri yoki dublikat savol");
    if (!reason) return;

    try {
      const res = await apiFetch(`/api/admin/questions/staging/${stagedId}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason })
      });
      showToast(res.message || "Savol rad etildi", "info");
      await loadQuestionSyncStatus();
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  window.openEditStagedModal = function (stagedId) {
    const q = cachedStagedQuestions.find(item => item.id === stagedId);
    if (!q) return;

    document.getElementById('inp-edit-staged-id').value = q.id;
    document.getElementById('inp-edit-staged-latn').value = q.text_uz_latn || '';
    document.getElementById('inp-edit-staged-cyrl').value = q.text_uz_cyrl || '';
    document.getElementById('inp-edit-staged-ru').value = q.text_ru || '';
    document.getElementById('inp-edit-staged-correct-key').value = q.correct_option_key || 'A';
    document.getElementById('inp-edit-staged-explanation').value = q.explanation || '';
    if (document.getElementById('inp-edit-staged-expl-cyrl')) {
      document.getElementById('inp-edit-staged-expl-cyrl').value = '';
    }
    if (document.getElementById('inp-edit-staged-expl-ru')) {
      document.getElementById('inp-edit-staged-expl-ru').value = '';
    }
    if (document.getElementById('inp-edit-staged-legal-status')) {
      document.getElementById('inp-edit-staged-legal-status').value = 'UNRESOLVED_LEGAL_REVIEW';
      document.getElementById('inp-edit-staged-legal-doc-title').value = '';
      document.getElementById('inp-edit-staged-legal-chapter').value = '';
      document.getElementById('inp-edit-staged-legal-clause').value = '';
      document.getElementById('inp-edit-staged-legal-doc-url').value = '';
    }

    const titleEl = document.getElementById('edit-staged-title');
    if (titleEl) titleEl.textContent = `Savol #${q.id} ni Tahrirlash & Tasdiqlash (${q.source_code.toUpperCase()})`;

    openModal('modal-edit-staged');
  };

  // ================= 4.2 EDITORIAL PROVENANCE & LEGAL QUALITY CONTROLLER =================
  const editorialState = {
    status: 'PENDING_EDITORIAL_REVIEW',
    page: 1,
    limit: 20,
    total: 0,
    items: []
  };

  window.setEditorialStatusFilter = function (newStatus) {
    editorialState.status = newStatus;
    document.querySelectorAll('#ed-status-pills .subtab-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.edStatus === newStatus);
    });
    loadEditorialQueue(1);
  };

  window.changeEditorialPage = function (delta) {
    const maxPage = Math.max(1, Math.ceil((editorialState.total || 0) / editorialState.limit));
    const target = Math.min(maxPage, Math.max(1, editorialState.page + delta));
    if (target !== editorialState.page) {
      loadEditorialQueue(target);
    }
  };

  window.loadEditorialQueue = async function (page = 1) {
    const listEl = document.getElementById('editorial-queue-list');
    if (!listEl) return;

    editorialState.page = page;
    const offset = (page - 1) * editorialState.limit;
    const qVal = (document.getElementById('ed-filter-q')?.value || '').trim();
    const flagVal = (document.getElementById('ed-filter-flag')?.value || '').trim();

    const params = new URLSearchParams({
      status: editorialState.status,
      limit: String(editorialState.limit),
      offset: String(offset)
    });
    if (qVal) params.set('q', qVal);
    if (flagVal) params.set('issue_flag', flagVal);

    try {
      const res = await apiFetch(`/api/admin/questions/editorial?${params.toString()}`);
      editorialState.items = res.items || [];
      editorialState.total = Number(res.total || 0);

      const sc = res.status_counts || {};
      const pendingCount = Number(sc.PENDING_EDITORIAL_REVIEW || 0);
      const aiCount = Number(sc.AI_DRAFT_PENDING_REVIEW || 0);
      const approvedCount = Number(sc.APPROVED || 0);
      const rejectedCount = Number(sc.REJECTED || 0);

      const setTxt = (id, v) => {
        const el = document.getElementById(id);
        if (el) el.textContent = v;
      };
      setTxt('ed-count-pending', pendingCount.toLocaleString());
      setTxt('ed-count-ai', aiCount.toLocaleString());
      setTxt('ed-count-approved', approvedCount.toLocaleString());
      setTxt('ed-count-rejected', rejectedCount.toLocaleString());
      setTxt('editorial-overall-badge', `${(pendingCount + aiCount).toLocaleString()} ta ko‘rib chiqilmagan`);

      const maxPage = Math.max(1, Math.ceil(editorialState.total / editorialState.limit));
      setTxt('ed-pagination-summary', `Jami: ${editorialState.total.toLocaleString()} ta savol (${page}/${maxPage}-sahifa)`);
      setTxt('ed-page-label', `${page} / ${maxPage}`);
      const prevBtn = document.getElementById('ed-btn-prev');
      const nextBtn = document.getElementById('ed-btn-next');
      if (prevBtn) prevBtn.disabled = page <= 1;
      if (nextBtn) nextBtn.disabled = page >= maxPage;

      if (!editorialState.items.length) {
        listEl.innerHTML = `
          <div class="text-xs text-muted text-center py-4 bg-slate-900/40 rounded border border-slate-800">
            Tanlangan filtr bo‘yicha tahririyat elementlari topilmadi.
          </div>
        `;
        return;
      }

      listEl.innerHTML = editorialState.items.map(item => {
        const flags = item.issue_flags || [];
        const flagsHtml = flags.map(f => {
          const isBleed = f.includes('BLEED') || f.includes('MISMATCH');
          return `<span class="editorial-flag-pill ${isBleed ? 'bleed' : ''}">${escapeHtml(f)}</span>`;
        }).join('');

        const legalBadgeClass = item.current_legal_status === 'VERIFIED_PRIMARY_LAW'
          ? 'badge-emerald'
          : (item.current_legal_status === 'VERIFIED_FIRST_AID_OR_TECH' ? 'badge-blue' : 'badge-amber');

        const tr = item.translations || {};
        const uzLatnQ = (tr.uz_latn && tr.uz_latn.question_text) || item.preview_text_uz_latn || '';
        const draftBanner = item.draft_explanation ? `
          <div class="text-[11px] p-2 rounded bg-indigo-950/40 border border-indigo-500/30 text-indigo-200">
            <b>🤖 Qoralama (${escapeHtml(item.language)}):</b> ${escapeHtml(item.draft_explanation)}
          </div>
        ` : '';

        return `
          <div class="staged-card" id="editorial-card-${item.id}">
            <div class="staged-card-top">
              <div class="staged-source-meta">
                <span class="font-bold text-slate-200 font-mono">${escapeHtml(item.canonical_id)}</span>
                <span>•</span>
                <span>${escapeHtml(item.category_name || 'Kategoriyasiz')}</span>
                <span>•</span>
                <span class="badge ${legalBadgeClass} text-[10px]">${escapeHtml(item.current_legal_status || 'UNRESOLVED_LEGAL_REVIEW')}</span>
              </div>
              <div class="text-[11px] text-muted">${escapeHtml(item.source_type || 'AUDIT_FLAG')} • #${item.id}</div>
            </div>

            <div class="text-xs text-slate-200 leading-relaxed">${escapeHtml(uzLatnQ)}</div>

            ${item.current_legal_hint ? `
              <div class="text-[11px] text-slate-400">
                <b>Joriy havola izi:</b> ${escapeHtml(item.current_legal_hint)}
              </div>
            ` : ''}

            ${draftBanner}

            ${flagsHtml ? `<div class="flex flex-wrap gap-1">${flagsHtml}</div>` : ''}

            <div class="staged-actions-row">
              <button type="button" class="btn btn-primary btn-sm" onclick="openEditEditorialModal(${item.id})">
                ✏️ Huquqiy Asos & 3 Tilli Izoh
              </button>
              ${item.review_status !== 'REJECTED' ? `
                <button type="button" class="btn btn-danger btn-sm" onclick="rejectEditorialQueueItem(${item.id})">
                  ❌ Rad etish
                </button>
              ` : ''}
            </div>
          </div>
        `;
      }).join('');
    } catch (e) {
      console.error("Editorial queue load error:", e);
      listEl.innerHTML = `<div class="text-xs text-red-400 p-3">Tahririyat navbatini yuklashda xatolik: ${escapeHtml(e.message)}</div>`;
    }
  };

  window.runEditorialAuditSeed = async function () {
    const btn = document.getElementById('btn-editorial-audit-seed');
    if (btn) btn.disabled = true;
    try {
      const res = await apiFetch('/api/admin/questions/editorial/audit-seed', { method: 'POST' });
      showToast(`Audit yakunlandi: ${res.queued_new_items || 0} ta yangi element qo‘shildi.`, 'success');
      await loadEditorialQueue(1);
    } catch (e) {
      showToast(e.message, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  };

  window.openEditEditorialModal = function (queueId) {
    const item = editorialState.items.find(x => x.id === queueId);
    if (!item) return;

    const tr = item.translations || {};
    document.getElementById('ed-modal-queue-id').value = item.id;
    document.getElementById('ed-modal-title').textContent = `${item.canonical_id} — Huquqiy Asos & Izoh`;

    const flagsText = (item.issue_flags || []).join(', ') || 'Yo‘q';
    document.getElementById('ed-modal-meta-box').innerHTML = `
      <div><b>Kategoriya:</b> ${escapeHtml(item.category_name || '')} &nbsp;|&nbsp; <b>Til doirasi:</b> ${escapeHtml(item.language)}</div>
      <div><b>Joriy havola izi:</b> ${escapeHtml(item.current_legal_hint || 'Mavjud emas')}</div>
      <div><b>Aniqlangan belgilar:</b> ${escapeHtml(flagsText)}</div>
    `;

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
      : (item.current_legal_status === 'UNRESOLVED_LEGAL_REVIEW' ? 'VERIFIED_PRIMARY_LAW' : (item.current_legal_status || 'VERIFIED_PRIMARY_LAW'));
    document.getElementById('ed-modal-legal-status').value = defaultStatus;
    document.getElementById('ed-modal-legal-doc-title').value = item.current_legal_doc_title || item.draft_legal_doc_title || '';
    document.getElementById('ed-modal-legal-doc-url').value = item.current_legal_doc_url || item.draft_legal_doc_url || '';
    document.getElementById('ed-modal-legal-chapter').value = item.current_legal_chapter || item.draft_legal_chapter || '';
    document.getElementById('ed-modal-legal-clause').value = item.current_legal_clause || item.draft_legal_clause || '';
    document.getElementById('ed-modal-legal-effective-date').value = item.current_legal_effective_date || '';
    document.getElementById('ed-modal-reviewer-notes').value = 'Human verified';

    openModal('modal-edit-editorial');
  };

  window.rejectEditorialQueueItem = async function (queueId) {
    const reason = prompt("Ushbu tahririyat yozuvini rad etish sababini kiriting:", "Qo‘shimcha tekshiruv uchun rad etildi");
    if (!reason) return;
    try {
      await apiFetch(`/api/admin/questions/editorial/${queueId}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason })
      });
      showToast(`Tahririyat yozuvi #${queueId} rad etildi.`, 'info');
      await loadEditorialQueue(editorialState.page);
    } catch (e) {
      showToast(e.message, 'error');
    }
  };

  window.approveAllStagedQuestions = async function () {
    if (!confirm("Barcha kutilayotgan savollarni birdaniga tasdiqlab, asosiy kanonik bazaga kiritishni tasdiqlaysizmi?")) return;

    const btn = document.getElementById('btn-approve-all-sync');
    if (btn) btn.disabled = true;

    try {
      const res = await apiFetch('/api/admin/questions/staging/approve-all', { method: 'POST' });
      showToast(res.message || "Barcha savollar tasdiqlandi!", "success");
      await loadQuestionSyncStatus();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  };

  async function checkQuestionSyncUpdates() {
    const btn = document.getElementById('btn-check-sync-updates');
    const consoleEl = document.getElementById('sync-console-output');
    if (btn) btn.disabled = true;
    if (consoleEl) consoleEl.textContent = "🔍 Manbalar tekshirilmoqda (YesPrava, ProPDD)...\nYangi savollar aniqlansa, moderatsiya navbatiga kiritiladi...";

    try {
      const res = await apiFetch('/api/admin/questions/sync/check?auto_stage=true', { method: 'POST' });
      if (consoleEl) {
        let out = `Tekshiruv vaqti: ${new Date().toLocaleTimeString()}\n`;
        out += `Yangilanishlar holati: ${res.has_updates ? '⚠️ YANGI O‘ZGARISHLAR TOPILDI!' : '✅ Baza to‘liq yangilangan'}\n\n`;
        (res.source_reports || []).forEach(r => {
          out += `[${r.source_name}]: ${r.has_changes ? 'O‘zgarishlar bor' : 'Yangilik yo‘q'}\n`;
          out += `  • Onlayn biletlar: ${r.total_tickets_online} ta\n`;
          out += `  • Yangi biletlar: ${r.new_tickets?.length ? r.new_tickets.join(', ') : 'Yo‘q'}\n`;
          out += `  • Yangi savollar: ${r.new_questions_count} ta\n`;
          out += `  • Kiritilgan tuzatishlar: ${r.amended_questions_count} ta\n\n`;
        });
        if (res.has_updates) {
          out += `📋 Jami ${res.newly_staged_count || 0} ta yangi savol Moderatsiya navbatiga kiritildi!\n`;
          out += `Quyidagi ro‘yxatda har birini ko‘rib chiqib, "Tasdiqlash" tugmasini bosing.`;
        } else {
          out += `Barcha savollar va rasmlar 100% eng so‘nggi holatda turibdi.`;
        }
        consoleEl.textContent = out;
      }
      showToast(res.has_updates ? "Yangi savollar moderatsiya navbatiga olindi!" : "Baza to‘liq dolzarb holatda", res.has_updates ? "warning" : "success");
      await loadQuestionSyncStatus();
    } catch (err) {
      if (consoleEl) consoleEl.textContent = `Xatolik yuz berdi: ${err.message}`;
      showToast(err.message, "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  window.resetMtprotoForm = function () {
    const fConnect = document.getElementById('form-mtproto-connect');
    const fCode = document.getElementById('form-mtproto-code-step');
    const f2fa = document.getElementById('form-mtproto-2fa-step');
    if (fConnect) fConnect.style.display = 'block';
    if (fCode) fCode.style.display = 'none';
    if (f2fa) f2fa.style.display = 'none';
  };

  window.disconnectMTProto = async function () {
    if (!confirm("MTProto sessiyasini uzmoqchimisiz? Humocardbot tinglash to‘xtaydi.")) return;
    try {
      const res = await apiFetch('/api/admin/mtproto/disconnect', { method: 'POST' });
      showToast(res.message);
      resetMtprotoForm();
      loadSettings();
      loadTopbarIndicators();
      loadOverview();
    } catch (e) {
      showToast(e.message, 'error');
    }
  };

  window.openPriceModal = function (id, name, price) {
    document.getElementById('edit-plan-id').value = id;
    document.getElementById('edit-plan-name').textContent = name;
    document.getElementById('edit-plan-price').value = price;
    document.getElementById('edit-plan-reason').value = '';
    document.getElementById('modal-edit-price').style.display = 'flex';
  };

  window.openModal = function (modalId) {
    const el = document.getElementById(modalId);
    if (el) el.style.display = 'flex';
  };

  window.closeModal = function (modalId) {
    const el = document.getElementById(modalId);
    if (el) el.style.display = 'none';
  };

  window.handleLogout = async function () {
    if (!confirm("Admin paneldan chiqmoqchimisiz?")) return;
    try {
      await apiFetch('/api/admin/auth/logout', { method: 'POST' });
    } catch {}
    location.reload();
  };

  // ================= TOPBAR STATUS POLLER =================
  async function loadTopbarIndicators() {
    try {
      const res = await apiFetch('/api/admin/mtproto/status');
      const st = res.status || {};
      const isConn = st.connection_status === 'CONNECTED';

      // Desktop & Mobile Status Dots
      const dot = document.getElementById('topbar-mtproto-dot');
      const text = document.getElementById('topbar-mtproto-text');
      const deskDot = document.getElementById('mtproto-status-dot-desktop');
      const mobDot = document.getElementById('m-dot-mtproto');

      if (dot) dot.className = `indicator-dot ${isConn ? 'connected' : ''}`;
      if (text) text.textContent = isConn ? 'MTProto: Faol' : 'MTProto: Ulanmagan';
      if (deskDot) deskDot.className = `status-dot-mini ${isConn ? 'connected' : ''}`;
      if (mobDot) mobDot.className = `m-status-dot ${isConn ? 'connected' : ''}`;

      // Active Orders Badge
      const activeOrd = st.active_orders_count || 0;
      const bNav = document.getElementById('badge-nav-orders');
      const bMob = document.getElementById('m-badge-orders');

      if (bNav) {
        bNav.textContent = activeOrd;
        bNav.style.display = activeOrd > 0 ? 'inline-block' : 'none';
      }
      if (bMob) {
        bMob.textContent = activeOrd;
        bMob.style.display = activeOrd > 0 ? 'block' : 'none';
      }
    } catch (e) {}
  }

  // ================= EVENT LISTENERS SETUP =================
  function setupEventListeners() {
    // 1. Navigation items (Desktop)
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(el => {
      el.addEventListener('click', (e) => {
        e.preventDefault();
        const view = el.getAttribute('data-view');
        switchView(view);
      });
    });

    // 2. Login Form
    document.getElementById('form-login')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const u = document.getElementById('login-username').value;
      const p = document.getElementById('login-password').value;
      const btn = document.getElementById('btn-login-submit');
      btn.disabled = true;
      btn.textContent = "Tekshirilmoqda...";

      try {
        const res = await apiFetch('/api/admin/auth/login', {
          method: 'POST',
          body: JSON.stringify({ username: u, password: p })
        });

        state.otpChallengeId = res.data.challenge_id;
        const tgMasked = document.getElementById('otp-tg-masked');
        if (tgMasked) tgMasked.textContent = res.data.telegram_id_masked || '***9701';

        document.getElementById('form-login').style.display = 'none';
        document.getElementById('form-otp').style.display = 'block';
        startOtpCountdown(res.data.expires_in_seconds || 300);
        document.getElementById('otp-input').focus();
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>Kirish</span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="sm-icon"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`;
      }
    });

    // 3. OTP Form
    document.getElementById('form-otp')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const code = document.getElementById('otp-input').value.trim();
      const btn = document.getElementById('btn-otp-submit');
      btn.disabled = true;
      btn.textContent = "Tasdiqlanmoqda...";

      try {
        await apiFetch('/api/admin/auth/otp/verify', {
          method: 'POST',
          body: JSON.stringify({
            challenge_id: state.otpChallengeId,
            otp_code: code
          })
        });

        showToast("Xush kelibsiz!");
        clearInterval(state.otpTimerInterval);
        showAppCockpit();
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = "Tasdiqlash & Kirish";
      }
    });

    document.getElementById('btn-otp-back')?.addEventListener('click', () => {
      clearInterval(state.otpTimerInterval);
      document.getElementById('form-otp').style.display = 'none';
      document.getElementById('form-login').style.display = 'block';
    });

    // 4. Logout (Desktop)
    document.getElementById('btn-logout')?.addEventListener('click', handleLogout);

    // 5. Grant Sub Modal Form
    document.getElementById('form-grant-sub')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const userId = document.getElementById('grant-user-id').value;
      const duration = parseInt(document.querySelector('input[name="grant-duration"]:checked')?.value || '14', 10);
      const reason = document.getElementById('grant-reason').value;

      try {
        await apiFetch(`/api/admin/users/${userId}/grant-subscription`, {
          method: 'POST',
          body: JSON.stringify({ duration_days: duration, reason: reason })
        });
        showToast("PRO obuna muvaffaqiyatli saqlandi!");
        closeModal('modal-grant-sub');
        loadUsers();
        loadOverview();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });

    // 6. Edit Price Form
    document.getElementById('form-edit-price')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const planId = document.getElementById('edit-plan-id').value;
      const newPrice = parseInt(document.getElementById('edit-plan-price').value, 10);
      const reason = document.getElementById('edit-plan-reason').value;

      try {
        await apiFetch(`/api/admin/plans/${planId}/price`, {
          method: 'POST',
          body: JSON.stringify({ new_price_uzs: newPrice, reason: reason })
        });
        showToast("Tarif narxi muvaffaqiyatli yangilandi!");
        closeModal('modal-edit-price');
        loadSettings();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });

    // 7. Edit Recipient Card Form
    const cardInput = document.getElementById('inp-card-number');
    if (cardInput) {
      cardInput.addEventListener('input', (e) => {
        let val = e.target.value.replace(/\D/g, '').substring(0, 16);
        val = val.replace(/(.{4})/g, '$1 ').trim();
        e.target.value = val;
      });
    }

    document.getElementById('form-edit-card')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      let cardId = parseInt(document.getElementById('edit-card-id')?.value, 10);
      if (isNaN(cardId) || cardId <= 0) cardId = 1;

      const rawNum = (document.getElementById('inp-card-number')?.value || '').replace(/\s+/g, '');
      const cardHolder = (document.getElementById('inp-card-holder')?.value || '').trim();
      const cardType = document.getElementById('inp-card-type')?.value || 'HUMO';
      const btn = document.getElementById('btn-save-card');

      if (rawNum && (rawNum.length !== 16 || !/^\d{16}$/.test(rawNum))) {
        showToast("Karta raqami aniq 16 xonali bo‘lishi shart!", 'error');
        return;
      }

      btn.disabled = true;
      btn.textContent = "Saqlanmoqda...";

      const body = {
        cardholder_name: cardHolder,
        card_type: cardType
      };
      if (rawNum) {
        body.card_number = rawNum;
      }

      try {
        const res = await apiFetch(`/api/admin/cards/${cardId}`, {
          method: 'PUT',
          body: JSON.stringify(body)
        });
        showToast(res.message || "Karta ma’lumotlari muvaffaqiyatli yangilandi!");
        if (document.getElementById('inp-card-number')) {
          document.getElementById('inp-card-number').value = '';
        }
        await loadSettings();
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = "Karta Ma’lumotlarini Saqlash";
      }
    });

    // 8. MTProto Connect Form
    document.getElementById('form-mtproto-connect')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const phone = document.getElementById('inp-mtproto-phone').value;
      const apiIdVal = document.getElementById('inp-mtproto-api-id')?.value;
      const apiHashVal = document.getElementById('inp-mtproto-api-hash')?.value;
      const btn = document.getElementById('btn-mtproto-send-code');

      btn.disabled = true;
      btn.textContent = "Kod so‘ralmoqda...";

      try {
        const body = { phone_number: phone };
        if (apiIdVal) body.api_id = parseInt(apiIdVal, 10);
        if (apiHashVal) body.api_hash = apiHashVal.trim();

        const res = await apiFetch('/api/admin/mtproto/send-code', {
          method: 'POST',
          body: JSON.stringify(body)
        });

        showToast(res.message);
        document.getElementById('form-mtproto-connect').style.display = 'none';
        document.getElementById('form-mtproto-code-step').style.display = 'block';
        document.getElementById('inp-mtproto-code-val').focus();
      } catch (err) {
        showToast(err.message, 'error');
      } finally {
        btn.disabled = false;
        btn.textContent = "Tasdiqlash Kodini Olish";
      }
    });

    // 9. MTProto Code Submit Form
    document.getElementById('form-mtproto-code-step')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const code = document.getElementById('inp-mtproto-code-val').value;

      try {
        const res = await apiFetch('/api/admin/mtproto/sign-in', {
          method: 'POST',
          body: JSON.stringify({ code: code })
        });

        if (res.requires_2fa) {
          showToast(res.message, 'error');
          document.getElementById('form-mtproto-code-step').style.display = 'none';
          document.getElementById('form-mtproto-2fa-step').style.display = 'block';
          document.getElementById('inp-mtproto-2fa-val').focus();
        } else {
          showToast(res.message);
          loadSettings();
          loadTopbarIndicators();
          loadOverview();
        }
      } catch (err) {
        showToast(err.message, 'error');
      }
    });

    // 10. MTProto 2FA Submit Form
    document.getElementById('form-mtproto-2fa-step')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const pw = document.getElementById('inp-mtproto-2fa-val').value;

      try {
        const res = await apiFetch('/api/admin/mtproto/sign-in-2fa', {
          method: 'POST',
          body: JSON.stringify({ password: pw })
        });
        showToast(res.message);
        loadSettings();
        loadTopbarIndicators();
        loadOverview();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });

    // 10. Question Synchronization Buttons & Staging Actions
    const btnCheckSync = document.getElementById('btn-check-sync-updates');
    if (btnCheckSync) btnCheckSync.onclick = checkQuestionSyncUpdates;

    const btnRunSync = document.getElementById('btn-run-sync-now');
    if (btnRunSync) btnRunSync.onclick = runQuestionSyncNow;

    const btnApproveAll = document.getElementById('btn-approve-all-sync');
    if (btnApproveAll) btnApproveAll.onclick = approveAllStagedQuestions;

    // 11. Edit Staged Question Form Submission (with 3-language explanations & legal provenance)
    document.getElementById('form-edit-staged')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const stagedId = document.getElementById('inp-edit-staged-id')?.value;
      if (!stagedId) return;

      const legalStatus = document.getElementById('inp-edit-staged-legal-status')?.value || 'UNRESOLVED_LEGAL_REVIEW';
      const legalDocTitle = document.getElementById('inp-edit-staged-legal-doc-title')?.value.trim() || null;
      const legalChapter = document.getElementById('inp-edit-staged-legal-chapter')?.value.trim() || null;
      const legalClause = document.getElementById('inp-edit-staged-legal-clause')?.value.trim() || null;
      const legalDocUrl = document.getElementById('inp-edit-staged-legal-doc-url')?.value.trim() || null;

      if (legalStatus === 'VERIFIED_PRIMARY_LAW' && (!legalDocTitle || (!legalChapter && !legalClause))) {
        showToast("VERIFIED_PRIMARY_LAW uchun hujjat nomi va bob/band majburiy!", "error");
        return;
      }

      const payload = {
        text_uz_latn: document.getElementById('inp-edit-staged-latn')?.value.trim(),
        text_uz_cyrl: document.getElementById('inp-edit-staged-cyrl')?.value.trim(),
        text_ru: document.getElementById('inp-edit-staged-ru')?.value.trim(),
        correct_option_key: document.getElementById('inp-edit-staged-correct-key')?.value,
        explanation: document.getElementById('inp-edit-staged-explanation')?.value.trim(),
        explanation_uz_cyrl: document.getElementById('inp-edit-staged-expl-cyrl')?.value.trim() || null,
        explanation_ru: document.getElementById('inp-edit-staged-expl-ru')?.value.trim() || null,
        legal_verification_status: legalStatus,
        legal_doc_title: legalDocTitle,
        legal_chapter: legalChapter,
        legal_clause: legalClause,
        legal_doc_url: legalDocUrl
      };

      try {
        const res = await apiFetch(`/api/admin/questions/staging/${stagedId}/edit`, {
          method: 'POST',
          body: JSON.stringify(payload)
        });
        showToast(res.message || "Savol tahrirlandi va tasdiqlandi!", "success");
        closeModal('modal-edit-staged');
        await loadQuestionSyncStatus();
      } catch (err) {
        showToast(err.message, "error");
      }
    });

    // 12. Editorial Legal Provenance & Translation Moderation Form
    document.getElementById('form-edit-editorial')?.addEventListener('submit', async (e) => {
      e.preventDefault();
      const queueId = document.getElementById('ed-modal-queue-id')?.value;
      if (!queueId) return;

      const legalStatus = document.getElementById('ed-modal-legal-status')?.value || 'VERIFIED_PRIMARY_LAW';
      const docTitle = document.getElementById('ed-modal-legal-doc-title')?.value.trim() || null;
      const chapter = document.getElementById('ed-modal-legal-chapter')?.value.trim() || null;
      const clause = document.getElementById('ed-modal-legal-clause')?.value.trim() || null;

      if (legalStatus === 'VERIFIED_PRIMARY_LAW' && (!docTitle || (!chapter && !clause))) {
        showToast("VERIFIED_PRIMARY_LAW uchun normativ hujjat nomi va bob yoki band kiritilishi shart!", "error");
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

      const payload = {
        legal_verification_status: legalStatus,
        legal_doc_title: docTitle,
        legal_doc_url: document.getElementById('ed-modal-legal-doc-url')?.value.trim() || null,
        legal_chapter: chapter,
        legal_clause: clause,
        legal_effective_date: document.getElementById('ed-modal-legal-effective-date')?.value.trim() || null,
        explanations_by_lang: Object.keys(explanationsByLang).length ? explanationsByLang : null,
        question_texts_by_lang: Object.keys(questionTextsByLang).length ? questionTextsByLang : null,
        reviewer_notes: document.getElementById('ed-modal-reviewer-notes')?.value.trim() || 'Human verified'
      };

      try {
        const res = await apiFetch(`/api/admin/questions/editorial/${queueId}/approve`, {
          method: 'POST',
          body: JSON.stringify(payload)
        });
        showToast(`${res.canonical_id} huquqiy asosi va izohlari tasdiqlandi!`, 'success');
        closeModal('modal-edit-editorial');
        await loadEditorialQueue(editorialState.page);
      } catch (err) {
        showToast(err.message, 'error');
      }
    });
  }

  function startOtpCountdown(seconds) {
    clearInterval(state.otpTimerInterval);
    const display = document.getElementById('otp-countdown');
    let left = seconds;

    function render(s) {
      const m = Math.floor(s / 60);
      const rem = s % 60;
      if (display) display.textContent = `${String(m).padStart(2, '0')}:${String(rem).padStart(2, '0')}`;
    }

    render(left);
    state.otpTimerInterval = setInterval(() => {
      left--;
      if (left <= 0) {
        clearInterval(state.otpTimerInterval);
        if (display) display.textContent = "00:00 (Muddati tugadi)";
      } else {
        render(left);
      }
    }, 1000);
  }

  // ================= 5. BROADCAST SYSTEM =================
  let selectedBroadcastTarget = 'all';

  window.selectBroadcastTarget = function (target) {
    selectedBroadcastTarget = target;
    document.querySelectorAll('.broadcast-target-opt').forEach(el => {
      el.classList.remove('active');
    });
    const activeEl = document.getElementById(`target-opt-${target}`);
    if (activeEl) activeEl.classList.add('active');
  };

  window.insertTag = function (tag) {
    const textarea = document.getElementById('broadcast-message-text');
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const selected = text.substring(start, end);

    const replacement = `<${tag}>${selected || 'matn'}</${tag}>`;
    textarea.value = text.substring(0, start) + replacement + text.substring(end);
    textarea.focus();
    textarea.setSelectionRange(start + tag.length + 2, start + replacement.length - tag.length - 3);
    window.updateBroadcastPreview();
  };

  window.insertLinkPrompt = function () {
    const textarea = document.getElementById('broadcast-message-text');
    if (!textarea) return;
    const url = prompt("Havola manzilini kiriting (URL):", "https://t.me/...");
    if (!url) return;
    const linkText = prompt("Havola matnini kiriting:", "Bu yerni bosing") || url;
    
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    const replacement = `<a href="${url}">${linkText}</a>`;
    textarea.value = text.substring(0, start) + replacement + text.substring(end);
    textarea.focus();
    window.updateBroadcastPreview();
  };

  window.updateBroadcastPreview = function () {
    const textarea = document.getElementById('broadcast-message-text');
    const preview = document.getElementById('broadcast-live-preview');
    const counter = document.getElementById('broadcast-char-count');
    if (!textarea) return;

    const val = textarea.value;
    if (counter) counter.textContent = `${val.length} / 4000`;

    if (!val.trim()) {
      if (preview) preview.innerHTML = '<i>Xabar matni kiritilmagan...</i>';
      return;
    }

    if (preview) {
      preview.innerHTML = val;
    }
  };

  window.loadBroadcastAudience = async function () {
    try {
      const res = await apiFetch('/api/admin/broadcast/audience');
      if (res && res.counts) {
        const elAll = document.getElementById('bc-count-all');
        const elFree = document.getElementById('bc-count-free');
        const elPro = document.getElementById('bc-count-pro');
        if (elAll) elAll.textContent = `${res.counts.all} ta`;
        if (elFree) elFree.textContent = `${res.counts.free} ta`;
        if (elPro) elPro.textContent = `${res.counts.pro} ta`;
      }
    } catch (err) {
      console.warn("Broadcast audience fetch error:", err);
    }
  };

  window.loadBroadcastHistory = async function () {
    const container = document.getElementById('broadcast-history-list');
    if (!container) return;

    try {
      const res = await apiFetch('/api/admin/broadcast/history');
      const list = res.history || [];
      if (!list.length) {
        container.innerHTML = '<div class="text-xs text-muted py-2">Hozircha yuborilgan xabarnomalar mavjud emas.</div>';
        return;
      }

      container.innerHTML = list.map(item => {
        const meta = item.meta || {};
        const targetMap = { all: '👥 Barchaga', pro: '⭐ PRO larga', free: '🆓 Bepullarga' };
        const targetBadge = targetMap[meta.target_group] || meta.target_group || 'Barchaga';
        const dateStr = item.performed_at ? item.performed_at.replace('T', ' ').substring(0, 16) : '';
        return `
          <div class="p-3 bg-slate-900 border border-slate-800 rounded-lg text-xs space-y-1">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-200">${targetBadge}</span>
              <span class="text-muted font-mono">${dateStr}</span>
            </div>
            <div class="text-slate-300 font-sans italic bg-slate-950 p-2 rounded border border-slate-800/60 mt-1">
              "${escapeHtml(meta.message_snippet || '')}"
            </div>
            <div class="flex items-center gap-3 text-xs pt-1 text-slate-400">
              <span class="text-emerald">✓ Yetkazildi: <b>${meta.sent || 0}</b></span>
              <span class="text-rose">✕ Xatolik: <b>${meta.failed || 0}</b></span>
              <span class="text-muted">Jami: <b>${meta.total_targets || 0}</b></span>
            </div>
          </div>
        `;
      }).join('');
    } catch (err) {
      container.innerHTML = '<div class="text-xs text-rose py-2">Tarixni yuklashda xatolik yuz berdi.</div>';
    }
  };

  window.loadBroadcastView = function () {
    loadBroadcastAudience();
    loadBroadcastHistory();
    updateBroadcastPreview();
  };

  window.confirmAndSendBroadcast = async function () {
    const textarea = document.getElementById('broadcast-message-text');
    const msg = textarea ? textarea.value.trim() : '';
    if (!msg) {
      showToast("Iltimos, xabar matnini kiriting!", "error");
      if (textarea) textarea.focus();
      return;
    }

    const targetNames = {
      all: 'Barcha foydalanuvchilar',
      free: 'Faqat bepul tarifdagilar',
      pro: 'Faqat PRO obunachilar'
    };
    const targetLabel = targetNames[selectedBroadcastTarget] || 'Tanlangan foydalanuvchilar';

    const confirmed = confirm(`Haqiqatan ham "${targetLabel}" guruhiga ushbu xabarni yubormoqchimisiz?\n\nBu xabar Telegram bot orqali barchaga yetkaziladi.`);
    if (!confirmed) return;

    const btn = document.getElementById('btn-send-broadcast');
    const label = document.getElementById('btn-broadcast-label');
    if (btn) btn.disabled = true;
    if (label) label.textContent = 'Yuborilmoqda...';

    try {
      const res = await apiFetch('/api/admin/broadcast', {
        method: 'POST',
        body: JSON.stringify({
          message_text: msg,
          target_group: selectedBroadcastTarget
        })
      });

      showToast(res.message || "Xabarnoma muvaffaqiyatli yuborildi!");
      if (textarea) textarea.value = '';
      updateBroadcastPreview();
      loadBroadcastAudience();
      loadBroadcastHistory();
    } catch (err) {
      showToast(err.message || "Xabarnoma yuborishda xatolik yuz berdi", "error");
    } finally {
      if (btn) btn.disabled = false;
      if (label) label.textContent = 'Xabarni Yuborish';
    }
  };

  function showAppCockpit() {
    document.getElementById('auth-container').style.display = 'none';
    document.getElementById('app-container').style.display = 'flex';
    switchView('overview');
    loadTopbarIndicators();
    setInterval(() => {
      if (!document.hidden) {
        loadTopbarIndicators();
      }
    }, 20000);
  }

  // ================= APP INITIALIZATION =================
  async function init() {
    setupEventListeners();

    // Check existing session
    try {
      const me = await apiFetch('/api/admin/auth/me');
      if (me && me.admin) {
        state.currentAdmin = me.admin;
        const nameEl = document.getElementById('topbar-admin-name');
        if (nameEl) nameEl.textContent = me.admin.username || 'Anvarjon';
        showAppCockpit();
        return;
      }
    } catch {}

    // Not authenticated -> show login form
    document.getElementById('auth-container').style.display = 'flex';
    document.getElementById('app-container').style.display = 'none';
  }

  window.addEventListener('DOMContentLoaded', init);

})();
