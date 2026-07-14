/* ==========================================================================
   search.js — fullscreen overlay + real live search (debounced fetch against
   the Django /search/ endpoint, which queries the Product table directly).
   ========================================================================== */
(function () {
  const overlay = document.getElementById('searchOverlay');
  const trigger = document.getElementById('searchTrigger');
  const closeBtn = document.getElementById('searchClose');
  const input = document.getElementById('searchInput');
  const defaultState = document.getElementById('searchDefaultState');
  const resultsState = document.getElementById('searchResultsState');
  const resultsTarget = document.getElementById('searchResultsTarget');

  if (!overlay) return;

  function openSearch() {
    overlay.classList.add('is-open');
    setTimeout(() => input.focus(), 300);
  }
  function closeSearch() {
    overlay.classList.remove('is-open');
  }
  trigger && trigger.addEventListener('click', openSearch);
  closeBtn && closeBtn.addEventListener('click', closeSearch);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeSearch();
  });

  document.querySelectorAll('.search-chip-fill').forEach((chip) => {
    chip.addEventListener('click', () => {
      input.value = chip.textContent.trim();
      input.dispatchEvent(new Event('input'));
    });
  });

  let debounceTimer;
  input && input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const query = input.value.trim();
    if (!query) {
      defaultState.style.display = '';
      resultsState.style.display = 'none';
      return;
    }
    debounceTimer = setTimeout(() => {
      fetch(`/search/?q=${encodeURIComponent(query)}`, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then((r) => r.json())
        .then((data) => {
          defaultState.style.display = 'none';
          resultsState.style.display = '';
          resultsTarget.innerHTML = data.html;
        });
    }, 280);
  });
})();
