/* BioPay Session Timeout Manager
   15-minute sliding window with countdown UI */

const SessionManager = (() => {
  const TIMEOUT_MS   = 15 * 60 * 1000;  // 15 minutes
  const WARNING_MS   =  2 * 60 * 1000;  // warn at 2 minutes remaining
  const TICK_MS      = 1000;

  let deadline     = Date.now() + TIMEOUT_MS;
  let ticker       = null;
  let toastShown   = false;
  let bsToast      = null;

  const timerEl    = document.getElementById('timerDisplay');
  const timerWrap  = document.querySelector('.session-timer');
  const toastEl    = document.getElementById('sessionToast');
  const toastTimer = document.getElementById('toastTimer');

  function reset() {
    deadline   = Date.now() + TIMEOUT_MS;
    toastShown = false;
    if (bsToast) bsToast.hide();
    if (timerWrap) timerWrap.classList.remove('warning');
  }

  function formatTime(ms) {
    const total = Math.max(0, Math.floor(ms / 1000));
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  function tick() {
    const remaining = deadline - Date.now();

    if (timerEl) timerEl.textContent = formatTime(remaining);

    if (remaining <= WARNING_MS && !toastShown) {
      toastShown = true;
      if (timerWrap) timerWrap.classList.add('warning');
      if (toastEl && !bsToast) bsToast = new bootstrap.Toast(toastEl, { autohide: false });
      if (bsToast) bsToast.show();
    }

    if (toastTimer) toastTimer.textContent = formatTime(remaining);

    if (remaining <= 0) {
      clearInterval(ticker);
      window.location.href = '/auth/logout?reason=timeout';
    }
  }

  /* Reset on user activity */
  ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'].forEach(evt => {
    document.addEventListener(evt, reset, { passive: true });
  });

  ticker = setInterval(tick, TICK_MS);
  tick();

  return { reset };
})();
