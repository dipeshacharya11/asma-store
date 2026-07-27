from decimal import Decimal

from .models import Product

FREE_SHIPPING_THRESHOLD = Decimal('5000')


def get_cart_context(request):
    """Builds the full context the cart drawer template needs: line items,
    subtotal, free-shipping progress, and a few upsell products. Used both
    by the cart-modifying views (add/update/remove) AND by the global
    context processor, since the drawer is included on every page, not
    just the cart page."""
    cart = request.session.get('cart', {})
    items = []
    subtotal = Decimal('0')
    cart_product_ids = []
    for pid, qty in cart.items():
        product = Product.objects.filter(id=pid).select_related('category').first()
        if not product:
            continue
        line_total = product.price * qty
        subtotal += line_total
        items.append({'product': product, 'qty': qty, 'line_total': line_total})
        cart_product_ids.append(product.id)

    remaining = FREE_SHIPPING_THRESHOLD - subtotal
    progress_pct = min(100, int((subtotal / FREE_SHIPPING_THRESHOLD) * 100)) if FREE_SHIPPING_THRESHOLD else 100

    upsell = Product.objects.filter(is_active=True, stock__gt=0).exclude(id__in=cart_product_ids)[:4]

    return {
        'items': items,
        'subtotal': subtotal,
        'remaining_for_free_shipping': max(remaining, Decimal('0')),
        'free_shipping_progress_pct': progress_pct,
        'qualifies_free_shipping': subtotal >= FREE_SHIPPING_THRESHOLD,
        'upsell_products': upsell,
    }


def get_cart_count(request):
    cart = request.session.get('cart', {})
    return sum(cart.values()) if cart else 0
