const status = document.getElementById('copy-status');
for (const button of document.querySelectorAll('[data-copy]')) {
  if (!navigator.clipboard?.writeText) continue;
  button.hidden = false;
  button.addEventListener('click', async () => {
    const code = document.getElementById(button.dataset.copy);
    try {
      await navigator.clipboard.writeText(code.textContent);
      button.textContent = 'Copied';
      status.textContent = 'Commands copied. Review them before running.';
      setTimeout(() => { button.textContent = 'Copy'; }, 2000);
    } catch {
      status.textContent = 'Clipboard unavailable. Select and copy the commands directly.';
    }
  });
}
