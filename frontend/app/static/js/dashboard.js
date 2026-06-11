/* BioPay Dashboard */
document.addEventListener('DOMContentLoaded', async () => {

  const GREEN  = '#00c896';
  const RED    = '#ff4d6d';
  const BLUE   = '#4da6ff';
  const ORANGE = '#ffa843';
  const GRID   = 'rgba(255,255,255,0.05)';
  const TEXT   = '#8b93a0';

  Chart.defaults.color = TEXT;
  Chart.defaults.borderColor = GRID;
  Chart.defaults.font.family = "'Inter', sans-serif";

  let txnChart = null;
  let typeChart = null;

  /* ── Load wallet ──────────────────────────────────────── */
  async function loadWallet() {
    const { ok, data } = await BioPay.get('/dashboard/api/wallet');
    if (!ok) return;

    const balVal = BioPay.el('balanceValue');
    if (balVal) {
      balVal.textContent = parseFloat(data.balance).toLocaleString('en-US', {
        minimumFractionDigits: 2, maximumFractionDigits: 2
      });
    }
    const addrEl = BioPay.el('walletAddressText');
    if (addrEl) addrEl.textContent = data.wallet_address;

    // Set avatar color from user
    const user = window.BIOPAY_USER || {};
    const avatarEl = document.getElementById('userAvatar');
    const profileAvatar = document.getElementById('profileAvatarLarge');
    [avatarEl, profileAvatar].forEach(el => {
      if (el && user.avatar_color) el.style.background = user.avatar_color + '22';
    });
  }

  /* ── Load analytics ───────────────────────────────────── */
  async function loadAnalytics() {
    const { ok, data } = await BioPay.get('/dashboard/api/analytics');
    if (!ok) return;

    const sentEl  = BioPay.el('totalSent');
    const rcvEl   = BioPay.el('totalReceived');
    const txnEl   = BioPay.el('txnCount');

    if (sentEl) sentEl.textContent = BioPay.formatCurrency(data.total_sent || 0);
    if (rcvEl)  rcvEl.textContent  = BioPay.formatCurrency(data.total_received || 0);
    if (txnEl)  txnEl.textContent  = data.transaction_count || 0;

    renderTxnChart(data.monthly_data || []);
    renderTypeChart(data.spending_by_type || []);
  }

  function renderTxnChart(monthly) {
    const ctx = document.getElementById('txnChart');
    if (!ctx) return;
    if (txnChart) txnChart.destroy();

    const labels = monthly.map(m => {
      const [y, mo] = m.month.split('-');
      return new Date(y, mo - 1).toLocaleString('default', { month: 'short', year: '2-digit' });
    });

    txnChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Sent',
            data: monthly.map(m => m.sent || 0),
            backgroundColor: RED + '88',
            borderColor: RED,
            borderWidth: 1.5,
            borderRadius: 4,
          },
          {
            label: 'Received',
            data: monthly.map(m => m.received || 0),
            backgroundColor: GREEN + '88',
            borderColor: GREEN,
            borderWidth: 1.5,
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#1a1e26',
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1,
            callbacks: {
              label: ctx => ` ${BioPay.formatCurrency(ctx.raw)}`,
            },
          },
        },
        scales: {
          x: { grid: { color: GRID }, ticks: { color: TEXT } },
          y: {
            grid: { color: GRID },
            ticks: {
              color: TEXT,
              callback: v => '$' + (v >= 1000 ? (v / 1000).toFixed(1) + 'k' : v),
            },
          },
        },
      },
    });
  }

  function renderTypeChart(types) {
    const ctx = document.getElementById('typeChart');
    if (!ctx) return;
    if (typeChart) typeChart.destroy();

    if (!types.length) {
      types = [{ type: 'No data', count: 1 }];
    }

    const palette = [GREEN, RED, BLUE, ORANGE, '#b34dff'];

    typeChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: types.map(t => t.type.replace(/_/g, ' ')),
        datasets: [{
          data: types.map(t => t.count),
          backgroundColor: palette.slice(0, types.length).map(c => c + 'cc'),
          borderColor: palette.slice(0, types.length),
          borderWidth: 2,
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        cutout: '68%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: TEXT, boxWidth: 12, padding: 14, font: { size: 11 } },
          },
          tooltip: {
            backgroundColor: '#1a1e26',
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1,
          },
        },
      },
    });
  }

  /* ── Load transactions ────────────────────────────────── */
  async function loadTransactions() {
    BioPay.show('txnLoading');
    BioPay.hide('txnEmpty');

    const { ok, data } = await BioPay.get('/dashboard/api/transactions?page=1&page_size=20');

    BioPay.hide('txnLoading');

    if (!ok || !data.transactions?.length) {
      BioPay.show('txnEmpty');
      return;
    }

    const list = BioPay.el('txnList');
    if (!list) return;

    const walletResp = await BioPay.get('/dashboard/api/wallet');
    const myWalletId = walletResp.ok ? walletResp.data.id : null;

    list.innerHTML = data.transactions.map(tx => {
      const isSent     = tx.sender_wallet_id === myWalletId;
      const iconClass  = isSent ? 'txn-icon-sent' : 'txn-icon-received';
      const icon       = isSent ? 'bi-arrow-up-right-circle' : 'bi-arrow-down-left-circle';
      const amtClass   = isSent ? 'sent' : 'received';
      const sign       = isSent ? '-' : '+';
      const statusBadge = tx.status === 'completed'
        ? `<span class="badge" style="background:rgba(0,200,150,0.15);color:#00c896;font-size:.68rem">${tx.status}</span>`
        : `<span class="badge" style="background:rgba(255,168,67,0.15);color:#ffa843;font-size:.68rem">${tx.status}</span>`;

      return `
        <div class="txn-item">
          <div class="txn-icon ${iconClass}"><i class="bi ${icon}"></i></div>
          <div class="txn-details">
            <div class="txn-label">${escHtml(tx.description || tx.transaction_type.replace(/_/g, ' '))}</div>
            <div class="txn-meta">${BioPay.timeAgo(tx.created_at)} · ${statusBadge}</div>
            <div class="txn-ref">${tx.reference_id}</div>
          </div>
          <div class="txn-amount ${amtClass}">${sign}${BioPay.formatCurrency(tx.amount)}</div>
        </div>`;
    }).join('');
  }

  function escHtml(str) {
    return String(str).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  /* ── Refresh button ───────────────────────────────────── */
  const refreshBtn = BioPay.el('refreshTxnBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', async () => {
      BioPay.setLoading(refreshBtn, true);
      await Promise.all([loadTransactions(), loadWallet()]);
      BioPay.setLoading(refreshBtn, false);
    });
  }

  /* ── Init ─────────────────────────────────────────────── */
  await Promise.all([loadWallet(), loadAnalytics(), loadTransactions()]);
});
