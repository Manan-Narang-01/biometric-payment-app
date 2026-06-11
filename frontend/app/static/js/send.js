/* BioPay Send Money Flow */
document.addEventListener('DOMContentLoaded', () => {

  let selectedRecipient = null;

  /* ── Step navigation ──────────────────────────────────── */
  function showStep(n) {
    document.querySelectorAll('.send-step').forEach((s, i) => {
      s.classList.toggle('active', i + 1 === n);
    });
  }
  showStep(1);

  /* ── Recipient autocomplete ───────────────────────────── */
  const recipientInput      = document.getElementById('recipientInput');
  const recipientSuggestions = document.getElementById('recipientSuggestions');
  const recipientInfo       = document.getElementById('recipientInfo');
  let searchTimeout = null;

  recipientInput?.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    const q = recipientInput.value.trim();
    if (q.length < 2) {
      hideSuggestions();
      hideRecipient();
      return;
    }
    searchTimeout = setTimeout(() => fetchSuggestions(q), 300);
  });

  async function fetchSuggestions(q) {
    const { ok, data } = await BioPay.get(`/payment/api/search-users?q=${encodeURIComponent(q)}`);
    if (!ok || !Array.isArray(data) || !data.length) { hideSuggestions(); return; }

    recipientSuggestions.innerHTML = data.map(u => {
      const sub = u.upi_id
        ? `<span class="sug-username">@${escHtml(u.username)}</span> · <span class="text-muted">${escHtml(u.upi_id)}</span>`
        : u.phone_number
          ? `<span class="sug-username">@${escHtml(u.username)}</span> · <span class="text-muted">${escHtml(u.phone_number)}</span>`
          : `<span class="sug-username">@${escHtml(u.username)}</span>`;
      return `
      <div class="suggestion-item" data-username="${escHtml(u.username)}" data-name="${escHtml(u.display_name)}">
        <div class="recipient-avatar" style="width:28px;height:28px;font-size:.75rem">${u.display_name[0].toUpperCase()}</div>
        <div>
          <div>${escHtml(u.display_name)}</div>
          <div>${sub}</div>
        </div>
      </div>`;
    }).join('');
    recipientSuggestions.style.display = 'block';

    recipientSuggestions.querySelectorAll('.suggestion-item').forEach(item => {
      item.addEventListener('click', () => {
        selectRecipient(item.dataset.username, item.dataset.name);
      });
    });
  }

  function selectRecipient(username, displayName) {
    selectedRecipient = username;
    recipientInput.value = username;
    hideSuggestions();
    document.getElementById('recipientAvatar').textContent = displayName[0].toUpperCase();
    document.getElementById('recipientDisplayName').textContent = displayName;
    document.getElementById('recipientUsername').textContent = '@' + username;
    recipientInfo.classList.remove('d-none');
    updateReviewButton();
  }

  function hideSuggestions() { recipientSuggestions.style.display = 'none'; }
  function hideRecipient()   { recipientInfo.classList.add('d-none'); selectedRecipient = null; }

  document.addEventListener('click', e => {
    if (!recipientSuggestions?.contains(e.target) && e.target !== recipientInput) hideSuggestions();
  });

  /* ── Amount input ─────────────────────────────────────── */
  const amountInput = document.getElementById('amountInput');

  document.querySelectorAll('.quick-amount-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      amountInput.value = btn.dataset.amount;
      updateFeeEstimate();
      updateReviewButton();
    });
  });

  amountInput?.addEventListener('input', () => {
    updateFeeEstimate();
    updateReviewButton();
  });

  function updateFeeEstimate() {
    const amount = parseFloat(amountInput?.value || 0);
    if (isNaN(amount) || amount <= 0) {
      ['feeAmount', 'feeFee', 'feeTotal'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '—';
      });
      return;
    }
    const fee   = amount * 0.001;
    const total = amount + fee;
    const setEl = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = BioPay.formatCurrency(val);
    };
    setEl('feeAmount', amount);
    setEl('feeFee', fee);
    setEl('feeTotal', total);
  }

  function updateReviewButton() {
    const btn    = document.getElementById('sendReviewBtn');
    const amount = parseFloat(amountInput?.value || 0);
    if (btn) btn.disabled = !(selectedRecipient && amount > 0);
  }

  /* ── Review step ──────────────────────────────────────── */
  document.getElementById('sendReviewBtn')?.addEventListener('click', () => {
    const amount = parseFloat(amountInput.value || 0);
    const fee    = amount * 0.001;

    if (!selectedRecipient || amount <= 0) return;
    BioPay.hideError('sendStep1Error');

    document.getElementById('confirmRecipient').textContent  = '@' + selectedRecipient;
    document.getElementById('confirmAmount').textContent     = BioPay.formatCurrency(amount);
    document.getElementById('confirmFee').textContent        = BioPay.formatCurrency(fee);
    document.getElementById('confirmTotal').textContent      = BioPay.formatCurrency(amount + fee);

    showStep(2);
  });

  document.getElementById('sendBackBtn')?.addEventListener('click', () => showStep(1));

  /* ── Biometric confirm & send ─────────────────────────── */
  document.getElementById('confirmSendBtn')?.addEventListener('click', async () => {
    const btn    = document.getElementById('confirmSendBtn');
    const amount = parseFloat(amountInput.value || 0);
    const desc   = document.getElementById('descInput')?.value.trim() || '';

    BioPay.hideError('sendStep2Error');

    if (!WebAuthnHelper.isSupported()) {
      return BioPay.showError('sendStep2Error', 'WebAuthn not supported.');
    }

    BioPay.setLoading(btn, true);

    try {
      // Re-authenticate biometric before sending
      const { ok: optOk, data: optData } = await BioPay.post(
        '/auth/api/webauthn/login/begin',
        { username: window.BIOPAY_USER?.username }
      );
      if (!optOk) throw new Error('Could not initiate biometric verification.');

      await WebAuthnHelper.authenticate(optData);

      // Execute transfer
      const { ok, data } = await BioPay.post('/payment/api/transfer', {
        receiver_username: selectedRecipient,
        amount,
        description: desc || undefined,
      });

      if (!ok) throw new Error(data.detail || 'Transfer failed.');

      document.getElementById('successMsg').textContent =
        `${BioPay.formatCurrency(amount)} sent to @${selectedRecipient} successfully.`;
      document.getElementById('successRef').textContent = 'Ref: ' + data.reference_id;
      showStep(3);

    } catch (err) {
      let msg = err.message || 'Transfer failed.';
      if (err.name === 'NotAllowedError') msg = 'Biometric verification was cancelled.';
      BioPay.showError('sendStep2Error', msg);
    } finally {
      BioPay.setLoading(btn, false);
    }
  });

  document.getElementById('sendAnotherBtn')?.addEventListener('click', () => {
    selectedRecipient = null;
    recipientInput.value = '';
    amountInput.value = '';
    document.getElementById('descInput').value = '';
    hideRecipient();
    updateFeeEstimate();
    updateReviewButton();
    showStep(1);
  });

  function escHtml(str) {
    return String(str).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
});
