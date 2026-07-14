/* ==========================================================================
   mega_menu.js — hover-open/close with a small grace delay (no flicker)
   ========================================================================== */
(function () {
  const megaTriggers = document.querySelectorAll('[data-mega-trigger]');
  const megaMenus = document.querySelectorAll('.mega-menu');
  let closeTimer;

  function openMega(key) {
    clearTimeout(closeTimer);
    megaMenus.forEach((m) => m.classList.toggle('is-open', m.dataset.megaFor === key));
  }
  function scheduleClose() {
    clearTimeout(closeTimer);
    closeTimer = setTimeout(() => megaMenus.forEach((m) => m.classList.remove('is-open')), 200);
  }

  megaTriggers.forEach((trigger) => {
    const key = trigger.dataset.megaTrigger;
    trigger.addEventListener('mouseenter', () => openMega(key));
    trigger.addEventListener('mouseleave', scheduleClose);
  });
  megaMenus.forEach((menu) => {
    menu.addEventListener('mouseenter', () => clearTimeout(closeTimer));
    menu.addEventListener('mouseleave', scheduleClose);
  });
})();
