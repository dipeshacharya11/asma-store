/* ==========================================================================
   header.js — sticky header state, mobile drawer, mega menu open/close
   ========================================================================== */
(function () {
  const header = document.getElementById('siteHeader');

  function updateHeaderState() {
    if (!header) return;

    const scrollY = window.pageYOffset || document.documentElement.scrollTop;
    const isScrolled = scrollY > 40;
    header.classList.toggle('is-scrolled', isScrolled);

    // Update mega-menu top position based on header height
    const megaMenu = document.querySelector('.mega-menu');
    if (megaMenu) {
      // Header height is 104px when not scrolled, 82px when scrolled
      megaMenu.style.top = isScrolled ? '82px' : '104px';
    }
  }
  window.addEventListener('scroll', updateHeaderState, { passive: true });
  window.addEventListener('resize', updateHeaderState, { passive: true });
  updateHeaderState();

  // ---------- Amazon-style hide-on-scroll-down / show-on-scroll-up ----------
  (function () {
    if (!header) return;

    const HIDE_THRESHOLD = 12;   // ignore tiny/jittery scroll movements
    const REVEAL_TOP_ZONE = 80;  // always show header near the very top

    let lastScrollY = window.pageYOffset || document.documentElement.scrollTop;
    let ticking = false;

    function anyOverlayOpen() {
      const megaOpen = document.querySelector('.mega-menu.is-open');
      const drawerOpen = document.getElementById('mobileDrawer') &&
        document.getElementById('mobileDrawer').classList.contains('is-open');
      const searchOpen = document.getElementById('searchOverlay') &&
        document.getElementById('searchOverlay').classList.contains('is-open');
      return !!(megaOpen || drawerOpen || searchOpen);
    }

    function onScrollFrame() {
      ticking = false;
      const currentY = window.pageYOffset || document.documentElement.scrollTop;
      const delta = currentY - lastScrollY;

      if (anyOverlayOpen() || currentY <= REVEAL_TOP_ZONE) {
        header.classList.remove('header-hidden');
      } else if (Math.abs(delta) > HIDE_THRESHOLD) {
        if (delta > 0) {
          header.classList.add('header-hidden');   // scrolling down -> hide
        } else {
          header.classList.remove('header-hidden'); // scrolling up -> reveal immediately
        }
      }

      lastScrollY = currentY;
    }

    window.addEventListener('scroll', function () {
      if (!ticking) {
        window.requestAnimationFrame(onScrollFrame);
        ticking = true;
      }
    }, { passive: true });
  })();

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

  // Mobile category toggles for shop menu
  document.querySelectorAll('.mobile-category-header').forEach((header) => {
    header.addEventListener('click', () => {
      const item = header.parentElement;
      const isOpen = item.classList.contains('active');
      const children = item.querySelector('.mobile-category-children');
      const toggle = header.querySelector('.mobile-category-toggle');

      // Close all other categories
      document.querySelectorAll('.mobile-category-item').forEach((item) => {
        item.classList.remove('active');
        const childList = item.querySelector('.mobile-category-children');
        if (childList) {
          childList.style.maxHeight = null;
        }
      });

      // Toggle current category
      if (!isOpen) {
        item.classList.add('active');
        if (children) {
          children.style.maxHeight = children.scrollHeight + 'px';
        }
        if (toggle) {
          toggle.textContent = '−';
        }
      } else {
        item.classList.remove('active');
        if (children) {
          children.style.maxHeight = null;
        }
        if (toggle) {
          toggle.textContent = '+';
        }
      }
    });
  });

  window.closeAllOverlays = closeAllOverlays;
})();
