/* BioPay Login Flow */
document.addEventListener('DOMContentLoaded', () => {

  const usernameInput = document.getElementById('username');
  const loginBtn      = document.getElementById('loginBtn');
  const loginBtnContent = document.getElementById('loginBtnContent');
  const loginBtnLoading = document.getElementById('loginBtnLoading');
  const loginError    = document.getElementById('loginError');

  function setLoading(loading) {
    loginBtn.disabled = loading;
    loginBtnContent.classList.toggle('d-none', loading);
    loginBtnLoading.classList.toggle('d-none', !loading);
  }

  function showError(msg) {
    loginError.textContent = msg;
    loginError.classList.remove('d-none');
  }

  function hideError() {
    loginError.classList.add('d-none');
  }

  /* ── Trigger login on Enter ───────────────────────────── */
  usernameInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') loginBtn.click();
  });

  loginBtn.addEventListener('click', async () => {
    const username = usernameInput.value.trim().toLowerCase();
    hideError();

    if (!username) return showError('Please enter your username.');

    if (!WebAuthnHelper.isSupported()) {
      return showError('Your browser does not support WebAuthn biometric authentication.');
    }

    setLoading(true);

    try {
      // 1. Get authentication options
      const { ok: optOk, data: optData } = await BioPay.post(
        '/auth/api/webauthn/login/begin',
        { username }
      );
      if (!optOk) {
        throw new Error(optData.detail || 'User not found or no biometrics registered.');
      }

      // 2. Biometric prompt
      const credential = await WebAuthnHelper.authenticate(optData);

      // 3. Complete authentication
      const { ok: authOk, data: authData } = await BioPay.post(
        '/auth/api/webauthn/login/complete',
        {
          username,
          credential,
          device_fingerprint: WebAuthnHelper.getDeviceFingerprint(),
          device_name: WebAuthnHelper.getDeviceName(),
        }
      );

      if (!authOk) {
        throw new Error(authData.detail || 'Authentication failed.');
      }

      // Redirect to dashboard on success
      window.location.href = '/';

    } catch (err) {
      let msg = err.message || 'Authentication failed.';
      if (err.name === 'NotAllowedError')   msg = 'Biometric prompt was dismissed or timed out. Please try again.';
      if (err.name === 'SecurityError')     msg = 'Security error — ensure you are on a secure (HTTPS) connection.';
      if (err.name === 'InvalidStateError') msg = 'No registered credential found for this device.';
      showError(msg);
    } finally {
      setLoading(false);
    }
  });
});
