/* ==========================================================================
   header.js — sticky header state, mobile drawer, mega menu open/close
   ========================================================================== */
(function () {
  const header = document.getElementById('siteHeader');

  function updateHeaderState() {
    header.classList.toggle('is-scrolled', window.scrollY > 40);
  }
  window.addEventListener('scroll', updateHeaderState, { passive: true });
  updateHeaderState();

  // Mega menu logic now lives in mega_menu.js

  // ---------- Mobile drawer ----------
  const burger = document.getElementById('burgerBtn');
  const mobileDrawer = document.getElementById('mobileDrawer');
  const drawerOverlay = document.getElementById('drawerOverlay');

  function closeAllOverlays() {
    mobileDrawer && mobileDrawer.classList.remove('is-open');
    drawerOverlay && drawerOverlay.classList.remove('is-open');
    document.getElementById('cartDrawer') && document.getElementById('cartDrawer').classList.remove('is-open');
    document.getElementById('searchOverlay') && document.getElementById('searchOverlay').classList.remove('is-open');
  }

  if (burger) {
    burger.addEventListener('click', () => {
      mobileDrawer.classList.add('is-open');
      drawerOverlay.classList.add('is-open');
    });
  }
  if (drawerOverlay) {
    drawerOverlay.addEventListener('click', closeAllOverlays);
  }
  document.querySelectorAll('.mobile-acc-head').forEach((head) => {
    head.addEventListener('click', () => {
      const body = head.nextElementSibling;
      const isOpen = body.style.maxHeight;
      document.querySelectorAll('.mobile-acc-body').forEach((b) => (b.style.maxHeight = null));
      if (!isOpen) body.style.maxHeight = body.scrollHeight + 'px';
    });
  });

  window.closeAllOverlays = closeAllOverlays;
})();
