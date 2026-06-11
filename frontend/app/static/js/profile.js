/* BioPay Profile & Security Page */
document.addEventListener('DOMContentLoaded', async () => {

  /* ── Load credentials ─────────────────────────────────── */
  async function loadCredentials() {
    const list = document.getElementById('credentialsList');
    if (!list) return;

    const { ok, data } = await BioPay.get('/profile/api/credentials');
    if (!ok || !data.length) {
      list.innerHTML = '<div class="device-loading" style="color:var(--text-muted);font-size:.83rem;padding:20px">No biometric devices registered.</div>';
      return;
    }

    list.innerHTML = data.map(cred => `
      <div class="device-item" id="cred-${cred.id}">
        <div class="device-icon"><i class="bi bi-fingerprint"></i></div>
        <div class="device-info">
          <div class="device-name">${escHtml(cred.device_name)}</div>
          <div class="device-meta">
            Registered ${BioPay.formatDate(cred.created_at)}
            ${cred.last_used ? ' · Last used ' + BioPay.timeAgo(cred.last_used) : ''}
          </div>
        </div>
        <button class="btn-device-remove" onclick="removeCred('${cred.id}')">
          <i class="bi bi-trash"></i> Remove
        </button>
      </div>`).join('');
  }

  window.removeCred = async (id) => {
    if (!confirm('Remove this biometric device? You will need at least one device to log in.')) return;
    const { ok } = await BioPay.del(`/profile/api/credentials/${id}`);
    if (ok) { BioPay.toast('Device removed'); loadCredentials(); }
    else    BioPay.toast('Failed to remove device', 'error');
  };

  /* ── Add biometric ────────────────────────────────────── */
  document.getElementById('addBiometricBtn')?.addEventListener('click', async () => {
    const btn = document.getElementById('addBiometricBtn');
    BioPay.setLoading(btn, true);

    try {
      const { ok: optOk, data: optData } = await BioPay.post('/profile/api/webauthn/add/begin', {});
      if (!optOk) throw new Error(optData.detail || 'Could not begin enrollment.');

      const credential = await WebAuthnHelper.register(optData);
      const deviceName = prompt('Name this device:', WebAuthnHelper.getDeviceName()) || 'New Device';

      const { ok, data } = await BioPay.post('/profile/api/webauthn/add/complete', {
        credential,
        device_name: deviceName,
      });
      if (!ok) throw new Error(data.detail || 'Enrollment failed.');

      BioPay.toast('New biometric device added!');
      loadCredentials();

    } catch (err) {
      let msg = err.message || 'Enrollment failed.';
      if (err.name === 'NotAllowedError') msg = 'Biometric prompt was dismissed.';
      BioPay.toast(msg, 'error');
    } finally {
      BioPay.setLoading(btn, false);
    }
  });

  /* ── Load trusted devices ─────────────────────────────── */
  async function loadDevices() {
    const list = document.getElementById('devicesList');
    if (!list) return;

    const { ok, data } = await BioPay.get('/profile/api/devices');
    if (!ok || !data.length) {
      list.innerHTML = '<div class="device-loading" style="color:var(--text-muted);font-size:.83rem;padding:20px">No trusted devices.</div>';
      return;
    }

    list.innerHTML = data.map(d => `
      <div class="device-item" id="device-${d.id}">
        <div class="device-icon"><i class="bi bi-laptop"></i></div>
        <div class="device-info">
          <div class="device-name">${escHtml(d.device_name)}</div>
          <div class="device-meta">
            ${d.ip_address ? 'IP ' + d.ip_address + ' · ' : ''}
            ${d.last_seen ? 'Last seen ' + BioPay.timeAgo(d.last_seen) : 'Never'}
          </div>
        </div>
        <button class="btn-device-remove" onclick="removeDevice('${d.id}')">
          <i class="bi bi-trash"></i> Remove
        </button>
      </div>`).join('');
  }

  window.removeDevice = async (id) => {
    if (!confirm('Remove this trusted device?')) return;
    const { ok } = await BioPay.del(`/profile/api/devices/${id}`);
    if (ok) { BioPay.toast('Device removed'); loadDevices(); }
    else    BioPay.toast('Failed to remove device', 'error');
  };

  /* ── Security logs ────────────────────────────────────── */
  const EVENT_ICONS = {
    login_success:       { dot: 'log-dot-success',  icon: 'bi-shield-check',         label: 'Signed in' },
    login_failed:        { dot: 'log-dot-danger',   icon: 'bi-shield-x',             label: 'Login failed' },
    biometric_registered:{ dot: 'log-dot-success',  icon: 'bi-fingerprint',          label: 'Biometric registered' },
    biometric_removed:   { dot: 'log-dot-warning',  icon: 'bi-fingerprint',          label: 'Biometric removed' },
    transfer_completed:  { dot: 'log-dot-info',     icon: 'bi-arrow-up-right-circle',label: 'Transfer sent' },
    transfer_initiated:  { dot: 'log-dot-info',     icon: 'bi-arrow-up-right-circle',label: 'Transfer initiated' },
    device_trusted:      { dot: 'log-dot-success',  icon: 'bi-laptop',               label: 'Device trusted' },
    device_removed:      { dot: 'log-dot-warning',  icon: 'bi-laptop',               label: 'Device removed' },
    session_expired:     { dot: 'log-dot-warning',  icon: 'bi-clock',                label: 'Session expired' },
    account_updated:     { dot: 'log-dot-info',     icon: 'bi-person-check',         label: 'Profile updated' },
  };

  async function loadSecurityLogs() {
    const list = document.getElementById('securityLogsList');
    if (!list) return;

    const { ok, data } = await BioPay.get('/profile/api/security-logs');
    if (!ok || !data.length) {
      list.innerHTML = '<div class="device-loading" style="color:var(--text-muted);font-size:.83rem;padding:20px">No activity recorded yet.</div>';
      return;
    }

    list.innerHTML = data.map(log => {
      const meta = EVENT_ICONS[log.event_type] || { dot: 'log-dot-info', label: log.event_type };
      return `
        <div class="security-log-item">
          <div class="log-dot ${meta.dot}"></div>
          <div>
            <div class="log-event">${meta.label}</div>
            <div class="log-meta">
              ${BioPay.formatDateTime(log.created_at)}
              ${log.ip_address ? ' · ' + log.ip_address : ''}
              ${log.details?.device_name ? ' · ' + escHtml(log.details.device_name) : ''}
            </div>
          </div>
        </div>`;
    }).join('');
  }

  /* ── Edit profile ─────────────────────────────────────── */
  document.getElementById('saveProfileBtn')?.addEventListener('click', async () => {
    const displayName = document.getElementById('editDisplayName')?.value.trim();
    const avatarColor = document.getElementById('editAvatarColor')?.value;
    const phoneNumber = document.getElementById('editPhoneNumber')?.value.trim() || null;
    const upiId       = document.getElementById('editUpiId')?.value.trim() || null;
    BioPay.hideError('editProfileError');

    if (!displayName) return BioPay.showError('editProfileError', 'Display name cannot be empty.');

    const btn = document.getElementById('saveProfileBtn');
    BioPay.setLoading(btn, true);

    const { ok, data } = await BioPay.put('/profile/api/update', {
      display_name:  displayName,
      avatar_color:  avatarColor,
      phone_number:  phoneNumber,
      upi_id:        upiId,
    });
    BioPay.setLoading(btn, false);

    if (!ok) return BioPay.showError('editProfileError', data.detail || 'Update failed.');

    document.getElementById('profileDisplayName').textContent = data.display_name;
    const modal = bootstrap.Modal.getInstance(document.getElementById('editProfileModal'));
    if (modal) modal.hide();
    BioPay.toast('Profile updated successfully');
  });

  function escHtml(str) {
    return String(str).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  /* ── Bank Accounts ────────────────────────────────────── */
  async function loadBankAccounts() {
    const list = document.getElementById('bankAccountsList');
    if (!list) return;
    const { ok, data } = await BioPay.get('/profile/api/bank-accounts');
    if (!ok || !data.length) {
      list.innerHTML = '<div class="device-loading" style="color:var(--text-muted);font-size:.83rem;padding:20px">No bank accounts added yet.</div>';
      return;
    }
    list.innerHTML = data.map(acc => `
      <div class="device-item" id="bank-${acc.id}">
        <div class="device-icon"><i class="bi bi-bank"></i></div>
        <div class="device-info">
          <div class="device-name">${escHtml(acc.bank_name)} ${acc.is_primary ? '<span class="badge" style="background:rgba(0,200,150,0.15);color:#00c896;font-size:.65rem;margin-left:6px">Primary</span>' : ''}</div>
          <div class="device-meta">${escHtml(acc.account_holder_name)} · ****${escHtml(acc.account_number.slice(-4))} · ${escHtml(acc.account_type)}</div>
          ${acc.ifsc_code ? `<div class="device-meta">${escHtml(acc.ifsc_code)}</div>` : ''}
        </div>
        <button class="btn-device-remove" onclick="removeBankAccount('${acc.id}')">
          <i class="bi bi-trash"></i> Remove
        </button>
      </div>`).join('');
  }

  window.removeBankAccount = async (id) => {
    if (!confirm('Remove this bank account?')) return;
    const { ok } = await BioPay.del(`/profile/api/bank-accounts/${id}`);
    if (ok) { BioPay.toast('Bank account removed'); loadBankAccounts(); }
    else    BioPay.toast('Failed to remove account', 'error');
  };

  // Open modal — reset to verify step
  document.getElementById('addBankBtn')?.addEventListener('click', () => {
    document.getElementById('bankVerifyStep').classList.remove('d-none');
    document.getElementById('bankFormStep').classList.add('d-none');
    BioPay.hideError('bankVerifyError');
    BioPay.hideError('bankFormError');
    new bootstrap.Modal(document.getElementById('addBankModal')).show();
  });

  // Biometric verify step
  document.getElementById('bankVerifyBtn')?.addEventListener('click', async () => {
    const btn = document.getElementById('bankVerifyBtn');
    BioPay.hideError('bankVerifyError');
    if (!WebAuthnHelper.isSupported()) {
      return BioPay.showError('bankVerifyError', 'WebAuthn not supported on this browser.');
    }
    BioPay.setLoading(btn, true);
    try {
      const { ok, data } = await BioPay.post('/auth/api/webauthn/login/begin', { username: window.BIOPAY_USER?.username });
      if (!ok) throw new Error('Could not initiate biometric verification.');
      await WebAuthnHelper.authenticate(data);
      // Biometric passed — show form
      document.getElementById('bankVerifyStep').classList.add('d-none');
      document.getElementById('bankFormStep').classList.remove('d-none');
    } catch (err) {
      let msg = err.message || 'Verification failed.';
      if (err.name === 'NotAllowedError') msg = 'Biometric verification was cancelled.';
      BioPay.showError('bankVerifyError', msg);
    } finally {
      BioPay.setLoading(btn, false);
    }
  });

  // Save bank account
  document.getElementById('saveBankBtn')?.addEventListener('click', async () => {
    const btn = document.getElementById('saveBankBtn');
    BioPay.hideError('bankFormError');

    const holderName    = document.getElementById('bankHolderName')?.value.trim();
    const bankName      = document.getElementById('bankName')?.value.trim();
    const accountNumber = document.getElementById('bankAccountNumber')?.value.trim();
    const ifscCode      = document.getElementById('bankIfsc')?.value.trim() || null;
    const accountType   = document.getElementById('bankAccountType')?.value;
    const isPrimary     = document.getElementById('bankIsPrimary')?.checked;

    if (!holderName || !bankName || !accountNumber) {
      return BioPay.showError('bankFormError', 'Please fill in all required fields.');
    }

    BioPay.setLoading(btn, true);
    const { ok, data } = await BioPay.post('/profile/api/bank-accounts', {
      account_holder_name: holderName,
      bank_name:           bankName,
      account_number:      accountNumber,
      ifsc_code:           ifscCode,
      account_type:        accountType,
      is_primary:          isPrimary,
    });
    BioPay.setLoading(btn, false);

    if (!ok) return BioPay.showError('bankFormError', data.detail || 'Failed to save account.');

    bootstrap.Modal.getInstance(document.getElementById('addBankModal'))?.hide();
    BioPay.toast('Bank account added successfully');
    loadBankAccounts();
  });

  /* ── Init ─────────────────────────────────────────────── */
  await Promise.all([loadCredentials(), loadDevices(), loadSecurityLogs(), loadBankAccounts()]);
});
