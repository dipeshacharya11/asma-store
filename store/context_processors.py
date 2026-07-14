from django.core.cache import cache
from django.middleware.csrf import get_token
from .models import Category
from .cart_utils import get_cart_context

NAV_CATEGORIES_CACHE_KEY = 'nav_categories_v1'


def ensure_csrf(request):
    """Guarantees the csrftoken cookie is set on every page load, since the
    cart/wishlist/search AJAX calls fire from pages that may not otherwise
    render any {% csrf_token %} form (e.g. the homepage's product grid)."""
    get_token(request)
    return {}


def cart_drawer_context(request):
    """The cart drawer is included in base.html on every page (not just
    /cart/), so its full context (items, subtotal, free-shipping progress,
    upsell products) needs to be available globally, not just inside the
    cart_view. Without this, pages other than /cart/ render the drawer with
    an empty context and {% url %} tags inside it fail on missing IDs."""
    return get_cart_context(request)


def cart_summary(request):
    """Makes the cart item count available in every template (header badge)."""
    cart = request.session.get('cart', {})
    count = sum(cart.values()) if cart else 0
    return {'cart_count': count}


def wishlist_summary(request):
    """Makes the wishlist item count available in every template (header badge)."""
    wishlist = request.session.get('wishlist', [])
    return {'wishlist_count': len(wishlist), 'wishlist_ids': wishlist}


def nav_categories(request):
    """
    Makes the active category list available for the header mega menu and footer.
    Cached for 10 minutes since it's identical for every visitor — this is a real
    cache, not a placeholder: it's invalidated immediately whenever a Category is
    saved or deleted (see store/signals.py), so admin edits still show up right away.
    """
    categories = cache.get(NAV_CATEGORIES_CACHE_KEY)
    if categories is None:
        categories = list(Category.objects.filter(is_active=True))
        cache.set(NAV_CATEGORIES_CACHE_KEY, categories, timeout=600)
    return {'nav_categories': categories}
