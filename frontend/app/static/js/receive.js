/* BioPay Receive Page */
document.addEventListener('DOMContentLoaded', () => {

  document.getElementById('copyUsernameBtn')?.addEventListener('click', async () => {
    const val = document.getElementById('shareUsername')?.textContent;
    if (val) await BioPay.copyToClipboard(val, document.getElementById('copyUsernameBtn'));
  });

  document.getElementById('copyPhoneBtn')?.addEventListener('click', async () => {
    const val = document.getElementById('sharePhone')?.textContent;
    if (val) await BioPay.copyToClipboard(val, document.getElementById('copyPhoneBtn'));
  });

  document.getElementById('copyUpiBtn')?.addEventListener('click', async () => {
    const val = document.getElementById('shareUpiId')?.textContent;
    if (val) await BioPay.copyToClipboard(val, document.getElementById('copyUpiBtn'));
  });

});
