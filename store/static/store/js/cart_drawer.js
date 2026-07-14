/* ==========================================================================
   cart_drawer.js — AJAX add-to-cart, quantity steppers, remove, drawer open/close.
   Uses event delegation throughout because the drawer's inner HTML is
   replaced wholesale on every server response (it's server-rendered, not
   a client-side template), so directly-bound listeners would go stale.
   ========================================================================== */
(function () {
  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
  }
  const csrftoken = getCookie('csrftoken');

  const cartDrawer = document.getElementById('cartDrawer');
  const drawerOverlay = document.getElementById('drawerOverlay');
  const cartTrigger = document.getElementById('cartTrigger');

  function openCartDrawer() {
    cartDrawer.classList.add('is-open');
    drawerOverlay.classList.add('is-open');
  }
  function closeCartDrawer() {
    cartDrawer.classList.remove('is-open');
    drawerOverlay.classList.remove('is-open');
  }
  window.openCartDrawer = openCartDrawer;
  window.closeCartDrawer = closeCartDrawer;

  function renderDrawer(html, count) {
    cartDrawer.innerHTML = html;
    const badge = document.getElementById('cartBadge');
    if (badge) {
      badge.textContent = count;
    } else {
      const newBadge = document.createElement('span');
      newBadge.className = 'cart-badge';
      newBadge.id = 'cartBadge';
      newBadge.textContent = count;
      cartTrigger.appendChild(newBadge);
    }
    const freshBadge = document.getElementById('cartBadge');
    if (freshBadge) {
      freshBadge.classList.remove('bump');
      void freshBadge.offsetWidth; // restart animation
      freshBadge.classList.add('bump');
    }
  }

  function postJSON(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrftoken,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: body || '',
    }).then((r) => r.json());
  }

  // Open drawer from header cart icon (fetches current contents, doesn't add anything)
  if (cartTrigger) {
    cartTrigger.addEventListener('click', () => {
      fetch('/cart/drawer/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then((r) => r.json())
        .then((data) => {
          renderDrawer(data.html, data.count);
          openCartDrawer();
        });
    });
  }

  // Delegated: any "Add to Cart" / quick-add button anywhere on the site
  document.addEventListener('click', (e) => {
    const addBtn = e.target.closest('.cart-add-btn');
    if (addBtn) {
      e.preventDefault();
      const pid = addBtn.dataset.productId;
      addBtn.disabled = true;

      // Determine quantity: if we are on a product detail page with a quantity input, use it; else default to 1.
      let qty = 1;
      const qtyInput = document.getElementById('pdpQuantity');
      if (qtyInput) {
        const val = parseInt(qtyInput.value, 10);
        if (!isNaN(val) || val < 1 ? qty = 1 : qty = val;
      }

      postJSON(`/cart/add/${pid}/`, `quantity=${qty}`).then((data) => {
        addBtn.disabled = false;
        if (data.error) {
          alert(data.error);
          return;
        }
        renderDrawer(data.html, data.count);
        openCartDrawer();
      });
    }

    // Drawer-internal controls (delegated since drawer re-renders)
    const closeBtn = e.target.closest('#drawerClose, #continueShoppingBtn');
    if (closeBtn) closeCartDrawer();

    const incBtn = e.target.closest('.qty-increment');
    if (incBtn) {
      const pid = incBtn.dataset.productId;
      const qty = incBtn.dataset.qty;
      postJSON(`/cart/update/${pid}/`, `qty=${qty}`).then((data) => renderDrawer(data.html, data.count));
    }
    const decBtn = e.target.closest('.qty-decrement');
    if (decBtn) {
      const pid = decBtn.dataset.productId;
      const qty = decBtn.dataset.qty;
      postJSON(`/cart/update/${pid}/`, `qty=${qty}`).then((data) => renderDrawer(data.html, data.count));
    }
    const removeBtn = e.target.closest('.cart-remove-btn');
    if (removeBtn) {
      e.preventDefault();
      const pid = removeBtn.dataset.productId;
      const item = removeBtn.closest('.drawer-item');
      if (item) item.classList.add('removing');
      postJSON(`/cart/remove/${pid}/`).then((data) => renderDrawer(data.html, data.count));
    }
  });

  if (drawerOverlay) drawerOverlay.addEventListener('click', closeCartDrawer);
})();