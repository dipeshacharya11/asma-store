/* ==========================================================================
   product_gallery.js — thumbnail switching + cursor-follow zoom on the main
   product image, plus the description/specs/reviews accordion.
   ========================================================================== */
(function () {
  const mainImg = document.getElementById('pdpMainImage');
  if (mainImg) {
    document.querySelectorAll('.pdp-thumb').forEach((thumb) => {
      thumb.addEventListener('click', () => {
        document.querySelectorAll('.pdp-thumb').forEach((t) => t.classList.remove('is-active'));
        thumb.classList.add('is-active');
        const bg = thumb.style.backgroundImage;
        mainImg.style.backgroundImage = bg;
      });
    });

    mainImg.addEventListener('mousemove', (e) => {
      const rect = mainImg.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      mainImg.style.backgroundSize = '160%';
      mainImg.style.backgroundPosition = `${x}% ${y}%`;
    });
    mainImg.addEventListener('mouseleave', () => {
      mainImg.style.backgroundSize = '100%';
      mainImg.style.backgroundPosition = 'center';
    });
  }

  // Variant selection (color/size) — purely presentational state, updates labels
  document.querySelectorAll('.swatch').forEach((s) => {
    s.addEventListener('click', () => {
      document.querySelectorAll('.swatch').forEach((x) => x.classList.remove('is-active'));
      s.classList.add('is-active');
      const label = document.getElementById('selectedColorLabel');
      if (label) label.textContent = s.dataset.name || '';
    });
  });
  document.querySelectorAll('.size-pill').forEach((p) => {
    p.addEventListener('click', () => {
      document.querySelectorAll('.size-pill').forEach((x) => x.classList.remove('is-active'));
      p.classList.add('is-active');
      const label = document.getElementById('selectedSizeLabel');
      if (label) label.textContent = p.textContent.trim();
    });
  });

  // Quantity stepper on the PDP (separate from the cart drawer's stepper)
  const qtyVal = document.getElementById('pdpQtyVal');
  if (qtyVal) {
    let qty = 1;
    document.getElementById('pdpQtyPlus').addEventListener('click', () => {
      qty++;
      qtyVal.textContent = qty;
    });
    document.getElementById('pdpQtyMinus').addEventListener('click', () => {
      if (qty > 1) {
        qty--;
        qtyVal.textContent = qty;
      }
    });
  }

  // Accordion (Description / Specifications / Reviews / Shipping)
  document.querySelectorAll('.acc-head').forEach((head) => {
    head.addEventListener('click', () => {
      const item = head.parentElement;
      const body = item.querySelector('.acc-body');
      const isOpen = item.classList.contains('is-open');
      document.querySelectorAll('.pdp-accordion .acc-item').forEach((i) => {
        i.classList.remove('is-open');
        i.querySelector('.acc-body').style.maxHeight = null;
      });
      if (!isOpen) {
        item.classList.add('is-open');
        body.style.maxHeight = body.scrollHeight + 'px';
      }
    });
  });
})();
