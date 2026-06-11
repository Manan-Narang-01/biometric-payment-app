/* BioPay Registration Flow */
document.addEventListener('DOMContentLoaded', () => {

  let userId = null;

  const step1 = document.getElementById('step1');
  const step2 = document.getElementById('step2');
  const step3 = document.getElementById('step3');

  function showStep(n) {
    [step1, step2, step3].forEach((s, i) => {
      s.classList.toggle('active', i + 1 === n);
    });
  }

  /* ── Warn if no biometric support ────────────────────── */
  (async () => {
    const available = await WebAuthnHelper.isPlatformAuthenticatorAvailable();
    if (!available && WebAuthnHelper.isSupported()) {
      const sub = document.querySelector('.auth-subtitle');
      if (sub) sub.innerHTML +=
        ' <span class="text-warning"><i class="bi bi-exclamation-triangle me-1"></i>No platform authenticator detected — you may need an external security key.</span>';
    }
    if (!WebAuthnHelper.isSupported()) {
      BioPay.showError('step1Error',
        'Your browser does not support WebAuthn. Please use Chrome, Edge, Safari, or Firefox.');
      BioPay.show('step1Error');
    }
  })();

  /* ── Step 1: account info ─────────────────────────────── */
  document.getElementById('step1Btn').addEventListener('click', async () => {
    const displayName = document.getElementById('displayName').value.trim();
    const username    = document.getElementById('username').value.trim();
    const email       = document.getElementById('email').value.trim();

    BioPay.hideError('step1Error');

    if (!displayName || !username || !email) {
      return BioPay.showError('step1Error', 'Please fill in all fields.');
    }
    if (!/^[a-zA-Z0-9_]{3,50}$/.test(username)) {
      return BioPay.showError('step1Error', 'Username must be 3–50 alphanumeric characters or underscores.');
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return BioPay.showError('step1Error', 'Enter a valid email address.');
    }

    const btn = document.getElementById('step1Btn');
    BioPay.setLoading(btn, true);

    const { ok, data } = await BioPay.post('/auth/api/register', { username, email, display_name: displayName });
    BioPay.setLoading(btn, false);

    if (!ok) {
      return BioPay.showError('step1Error', data.detail || 'Registration failed. Username or email may already be taken.');
    }

    userId = data.id;
    showStep(2);
  });

  /* ── Step 2: biometric enroll ─────────────────────────── */
  document.getElementById('enrollBtn').addEventListener('click', async () => {
    if (!userId) return showStep(1);

    const deviceName = document.getElementById('deviceName').value.trim() || 'My Device';
    BioPay.hideError('step2Error');

    const btn = document.getElementById('enrollBtn');
    BioPay.setLoading(btn, true);

    try {
      // 1. Get registration options from backend
      const { ok: optOk, data: optData } = await BioPay.post(
        '/auth/api/webauthn/register/begin',
        { user_id: userId, device_name: deviceName }
      );
      if (!optOk) throw new Error(optData.detail || 'Could not begin registration.');

      // 2. Invoke browser biometric
      const credential = await WebAuthnHelper.register(optData);

      // 3. Complete registration
      const { ok: compOk, data: compData } = await BioPay.post(
        '/auth/api/webauthn/register/complete',
        { user_id: userId, credential, device_name: deviceName }
      );
      if (!compOk) throw new Error(compData.detail || 'Biometric registration failed.');

      showStep(3);

    } catch (err) {
      let msg = err.message || 'Biometric enrollment failed.';
      if (err.name === 'NotAllowedError')   msg = 'Biometric prompt was dismissed. Please try again.';
      if (err.name === 'NotSupportedError') msg = 'This biometric type is not supported on your device.';
      if (err.name === 'InvalidStateError') msg = 'This device is already registered.';
      BioPay.showError('step2Error', msg);
    } finally {
      BioPay.setLoading(btn, false);
    }
  });

  document.getElementById('backBtn').addEventListener('click', () => showStep(1));
});
