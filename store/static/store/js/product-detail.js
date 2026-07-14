/* ==========================================================================
   Product Detail Page Specific JavaScript
   ========================================================================== */
document.addEventListener('DOMContentLoaded', function () {
  'use strict';

  // Elements
  const mainMedia = document.getElementById('pdpMainMedia');
  const mainImage = document.getElementById('pdpMainImage');
  const thumbnails = document.querySelectorAll('.pdp-thumbnail');
  const quantityInput = document.getElementById('pdpQuantity');
  const minusButton = document.getElementById('pdpQtyMinus');
  const plusButton = document.getElementById('pdpQtyPlus');
  const addToCartButton = document.querySelector('.pdp-add.cart-add-btn');
  const stickyBar = document.getElementById('pdpStickyBar');
  const stickyBarPrice = document.getElementById('pdpStickyBarPrice');
  const stickyBarAddToCart = document.getElementById('pdpStickyBarAddToCart');
  const lightbox = document.getElementById('pdpLightbox');
  const lightboxImage = document.getElementById('pdpLightboxImage');
  const lightboxPrev = document.getElementById('pdpLightboxPrev');
  const lightboxNext = document.getElementById('pdpLightboxNext');
  const lightboxClose = document.getElementById('pdpLightboxClose');
  const lightboxCaption = document.getElementById('pdpLightboxCaption');

  // State
  let currentImageIndex = 0;
  const images = [];
  let isLightboxOpen = false;

  // Initialize
  function init() {
    // Collect image URLs from thumbnails
    thumbnails.forEach((thumb, index) => {
      images.push(thumb.dataset.image);
    });

    // Set initial lightbox image
    if (images.length) {
      updateLightboxImage(0);
    }

    // Event listeners
    if (mainImage && thumbnails.length) {
      thumbnails.forEach((thumb, index) => {
        thumb.addEventListener('click', () => {
          switchImage(index);
        });
      });
    }

    // Main image click to open lightbox
    if (mainImage) {
      mainImage.addEventListener('click', () => {
        if (images.length > 1) {
          openLightbox();
        }
      });
    }

    // Quantity controls
    if (quantityInput && minusButton && plusButton) {
      const getMax = () => {
        const max = parseInt(quantityInput.max, 10);
        return Number.isFinite(max) ? max : Infinity;
      };
      const normalize = (value) => {
        const num = parseInt(value, 10) || 1;
        return Math.max(1, Math.min(num, getMax()));
      };
      minusButton.addEventListener('click', () => {
        quantityInput.value = normalize(parseInt(quantityInput.value, 10) - 1);
        quantityInput.dispatchEvent(new Event('change', { bubbles: true }));
      });
      plusButton.addEventListener('click', () => {
        quantityInput.value = normalize(parseInt(quantityInput.value, 10) + 1);
        quantityInput.dispatchEvent(new Event('change', { bubbles: true }));
      });
      quantityInput.addEventListener('change', () => {
        quantityInput.value = normalize(quantityInput.value);
        // Update data-quantity on add to cart buttons
        document.querySelectorAll('.pdp-add[data-product-id]').forEach(btn => {
          btn.dataset.quantity = quantityInput.value;
        });
        // Update sticky bar button if exists
        if (stickyBarAddToCart) {
          stickyBarAddToCart.dataset.quantity = quantityInput.value;
        }
      });
    }

    // Sticky bar
    if (stickyBar && stickyBarAddToCart) {
      // Update sticky bar price
      const priceElement = document.querySelector('.pdp-price-now');
      if (priceElement) {
        stickyBarPrice.textContent = priceElement.textContent;
      }
      // Set initial quantity data
      if (quantityInput) {
        stickyBarAddToCart.dataset.quantity = quantityInput.value;
      }
      // Add to cart click (delegated to cart_drawer.js, but we need to ensure quantity is sent)
      // We'll rely on the data-quantity attribute set by the quantity change listener above.
      // However, we need to set it when the sticky button is clicked as well.
      stickyBarAddToCart.addEventListener('click', () => {
        if (quantityInput) {
          stickyBarAddToCart.dataset.quantity = quantityInput.value;
        }
      });
      // Show/hide sticky bar based on scroll? We'll just show it on mobile.
      // We'll add a class to body to adjust bottom padding.
      const updateBodyPadding = () => {
        if (window.innerWidth <= 991) {
          document.body.classList.add('pdp-sticky-bar-visible');
        } else {
          document.body.classList.remove('pdp-sticky-bar-visible');
        }
      };
      window.addEventListener('resize', updateBodyPadding);
      updateBodyPadding();
    }

    // Lightbox controls
    if (lightboxPrev) {
      lightboxPrev.addEventListener('click', () => {
        prevImage();
      });
    }
    if (lightboxNext) {
      lightboxNext.addEventListener('click', () => {
        nextImage();
      });
    }
    if (lightboxClose) {
      lightboxClose.addEventListener('click', () => {
        closeLightbox();
      });
    }
    // Close on backdrop click
    if (lightbox) {
      lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox) {
          closeLightbox();
        }
      });
    }
    // Close on Escape
    document.addEventListener('keydown', (e) => {
      if (isLightboxOpen && e.key === 'Escape') {
        closeLightbox();
      }
      if (isLightboxOpen && e.key === 'ArrowLeft') {
        prevImage();
      }
      if (isLightboxOpen && e.key === 'ArrowRight') {
        nextImage();
      }
    });

    // Touch swipe for lightbox
    let touchStartX = 0;
    let touchEndX = 0;
    if (lightbox) {
      lightbox.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
      }, { passive: true });
      lightbox.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
      }, { passive: true });
    }

    function handleSwipe() {
      const diff = touchStartX - touchEndX;
      if (Math.abs(diff) > 30) {
        if (diff > 0) {
          // Swipe left -> next
          nextImage();
        } else {
          // Swipe right -> previous
          prevImage();
        }
      }
    }

    // Hover zoom (desktop only)
    if (mainMedia && mainImage && window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
      mainMedia.addEventListener('mousemove', (e) => {
        const rect = mainMedia.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        mainImage.style.transformOrigin = `${x}% ${y}%`;
        mainImage.style.transform = 'scale(1.8)';
      });
      mainMedia.addEventListener('mouseleave', () => {
        mainImage.style.transformOrigin = 'center';
        mainImage.style.transform = 'scale(1)';
      });
    }

    // Initialize sticky bar visibility
    const updateStickyBarVisibility = () => {
      if (window.innerWidth <= 991) {
        stickyBar.style.display = 'flex';
      } else {
        stickyBar.style.display = 'none';
      }
    };
    window.addEventListener('resize', updateStickyBarVisibility);
    updateStickyBarVisibility();
  }

  // Image switching
  function switchImage(index) {
    if (index < 0 || index >= images.length) return;
    if (mainImage) {
      mainMedia.classList.add('is-loading');
      const img = new Image();
      img.onload = () => {
        mainImage.src = images[index];
        mainMedia.classList.remove('is-loading');
        updateThumbnails(index);
        currentImageIndex = index;
        if (isLightboxOpen) {
          updateLightboxImage(index);
        }
      };
      img.onerror = () => {
        mainMedia.classList.remove('is-loading');
      };
      img.src = images[index];
    }
  }

  function updateThumbnails(activeIndex) {
    thumbnails.forEach((thumb, index) => {
      if (index === activeIndex) {
        thumb.classList.add('is-active');
        thumb.setAttribute('aria-current', 'true');
      } else {
        thumb.classList.remove('is-active');
        thumb.setAttribute('aria-current', 'false');
      }
    });
  }

  function nextImage() {
    const next = (currentImageIndex + 1) % images.length;
    switchImage(next);
  }

  function prevImage() {
    const prev = (currentImageIndex - 1 + images.length) % images.length;
    switchImage(prev);
  }

  // Lightbox
  function openLightbox() {
    if (!images.length) return;
    isLightboxOpen = true;
    lightbox.classList.add('is-open');
    // Lock body scroll
    document.body.style.overflow = 'hidden';
    // Ensure focus is trapped? We'll keep simple.
  }

  function closeLightbox() {
    isLightboxOpen = false;
    lightbox.classList.remove('is-open');
    // Restore body scroll
    document.body.style.overflow = '';
    // Return focus to the main image? We'll focus the main image when closing.
    if (mainImage) {
      mainImage.focus();
    }
  }

  function updateLightboxImage(index) {
    lightboxImage.src = images[index];
    lightboxImage.alt = document.querySelector('.pdp-title')?.textContent || 'Product image';
    // Update caption if needed
    // We could show current/total
    // But we'll keep it simple for now.
    // Update navigation button states
    if (lightboxPrev) {
      lightboxPrev.disabled = index === 0;
    }
    if (lightboxNext) {
      lightboxNext.disabled = index === images.length - 1;
    }
  }

  // Initialize
  try {
    init();
  } catch (error) {
    console.error("Error initializing product detail page:", error);
    // Optionally show a user-friendly message
    const mainContent = document.querySelector('.pdp-page');
    if (mainContent) {
      mainContent.innerHTML = '<div style="text-align: center; padding: 50px; color: var(--text-primary);">Failed to load product details. Please try again later.</div>';
    }
  }
});