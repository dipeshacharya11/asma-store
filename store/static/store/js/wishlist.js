/* ==========================================================================
   wishlist.js — AJAX toggle for the heart icon on product cards / detail page
   ========================================================================== */
(function () {
  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : null;
  }
  const csrftoken = getCookie('csrftoken');

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.wishlist-toggle-btn');
    if (!btn) return;
    e.preventDefault();
    const pid = btn.dataset.productId;

    fetch(`/wishlist/toggle/${pid}/`, {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrftoken,
      },
    })
      .then((r) => r.json())
      .then((data) => {
        btn.classList.toggle('is-active', data.saved);
        btn.textContent = data.saved ? '♥' : '♡';

        const badge = document.getElementById('wishlistBadge');
        if (data.count > 0) {
          if (badge) badge.textContent = data.count;
        } else if (badge) {
          badge.remove();
        }

        // On the wishlist page itself, unliking an item removes its card.
        if (!data.saved) {
          const onWishlistPage = document.querySelector('.wishlist-wrap');
          const card = btn.closest('.prod-card');
          if (onWishlistPage && card) {
            card.style.transition = 'opacity .4s ease, transform .4s ease';
            card.style.opacity = '0';
            card.style.transform = 'scale(.94)';
            setTimeout(() => card.remove(), 400);
          }
        }
      });
  });
})();
