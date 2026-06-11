/* BioPay Core JS — shared utilities */

const BioPay = {
  /* ── API helpers ──────────────────────────────────────── */
  async api(method, path, body = null) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  },

  get(path)         { return this.api('GET', path); },
  post(path, body)  { return this.api('POST', path, body); },
  put(path, body)   { return this.api('PUT', path, body); },
  del(path)         { return this.api('DELETE', path); },

  /* ── Formatting ───────────────────────────────────────── */
  formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
      style: 'currency', currency,
      minimumFractionDigits: 2,
    }).format(amount);
  },

  formatDate(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  },

  formatDateTime(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  },

  timeAgo(dateStr) {
    const diff = (Date.now() - new Date(dateStr)) / 1000;
    if (diff < 60)     return `${Math.floor(diff)}s ago`;
    if (diff < 3600)   return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400)  return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  },

  /* ── Toast notifications ──────────────────────────────── */
  toast(message, type = 'success') {
    const container = document.getElementById('toastContainer') || (() => {
      const el = document.createElement('div');
      el.id = 'toastContainer';
      el.className = 'position-fixed bottom-0 end-0 p-3';
      el.style.zIndex = '9999';
      document.body.appendChild(el);
      return el;
    })();

    const icon = type === 'success' ? 'check-circle-fill' : type === 'error' ? 'x-circle-fill' : 'info-circle-fill';
    const color = type === 'success' ? '#00c896' : type === 'error' ? '#ff4d6d' : '#4da6ff';

    const toast = document.createElement('div');
    toast.className = 'toast show align-items-center border-0';
    toast.style.cssText = `background:#1a1e26;color:#eef0f3;border:1px solid rgba(255,255,255,0.1)!important;min-width:280px;margin-top:8px`;
    toast.innerHTML = `
      <div class="d-flex">
        <div class="toast-body d-flex align-items-center gap-2">
          <i class="bi bi-${icon}" style="color:${color}"></i>
          <span>${message}</span>
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.closest('.toast').remove()"></button>
      </div>`;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  },

  /* ── Element helpers ──────────────────────────────────── */
  el(id) { return document.getElementById(id); },

  show(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove('d-none');
  },

  hide(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('d-none');
  },

  showError(id, msg) {
    const el = document.getElementById(id);
    if (el) { el.textContent = msg; el.classList.remove('d-none'); }
  },

  hideError(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('d-none');
  },

  setLoading(btn, loading) {
    if (!btn) return;
    if (loading) {
      btn.dataset.originalText = btn.innerHTML;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Please wait...';
      btn.disabled = true;
    } else {
      btn.innerHTML = btn.dataset.originalText || btn.innerHTML;
      btn.disabled = false;
    }
  },

  /* ── Copy to clipboard ────────────────────────────────── */
  async copyToClipboard(text, btnEl) {
    try {
      await navigator.clipboard.writeText(text);
      if (btnEl) {
        const orig = btnEl.innerHTML;
        btnEl.innerHTML = '<i class="bi bi-check-lg"></i>';
        btnEl.style.color = '#00c896';
        setTimeout(() => { btnEl.innerHTML = orig; btnEl.style.color = ''; }, 1500);
      }
      BioPay.toast('Copied to clipboard');
    } catch {
      BioPay.toast('Copy failed', 'error');
    }
  },
};

/* Sidebar toggle */
document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  if (toggle && sidebar) {
    toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
    document.addEventListener('click', (e) => {
      if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  }
});
