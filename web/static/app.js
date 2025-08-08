// Minimal client-side helpers for clipboard and feedback
document.addEventListener('click', async (event) => {
  const button = event.target.closest('[data-tsv]');
  if (!button) return;

  const tsv = button.dataset.tsv || '';
  try {
    await navigator.clipboard.writeText(tsv);
    showToast('Copiado');
  } catch (err) {
    showToast('No se pudo copiar');
  }
});

function showToast(message) {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = message;
  el.classList.add('is-visible');
  window.setTimeout(() => el.classList.remove('is-visible'), 1600);
}


