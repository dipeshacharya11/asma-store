from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, F, Sum, Value, Case, When, IntegerField, CharField
from django.db.models.functions import Lower, Replace
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
import re
from rapidfuzz import fuzz, process

from .models import Category, Product, HeroSlide, Testimonial, Coupon, Order, OrderItem, BlogPost
from .signals import FEATURED_PRODUCTS_CACHE_KEY, HERO_SLIDES_CACHE_KEY
from .cart_utils import get_cart_context, get_cart_count
from .models import SignatureCollection

FREE_SHIPPING_THRESHOLD = Decimal('5000')


def _is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def home(request):
    # Real caching: these two queries are identical for every visitor, so
    # they're cached for 5 minutes and invalidated immediately on save/delete
    # via the signals in store/signals.py — not stale, just not re-queried
    hero_slides = cache.get(HERO_SLIDES_CACHE_KEY)
    if hero_slides is None:
        hero_slides = list(HeroSlide.objects.filter(is_active=True))
        cache.set(HERO_SLIDES_CACHE_KEY, hero_slides, timeout=300)

    featured_products = cache.get(FEATURED_PRODUCTS_CACHE_KEY)
    if featured_products is None:
        featured_products = list(
            Product.objects.filter(is_active=True, is_featured=True, stock__gt=0).select_related('category')[:8]
        )
        cache.set(FEATURED_PRODUCTS_CACHE_KEY, featured_products, timeout=300)

    # This query previously sat AFTER `return render(...)` below — completely
    # unreachable dead code, so signature_collections was never actually in
    # the template context and the whole "Our Signature Products" tabbed
    # section always rendered its empty state. Moved above the return.
    signature_collections = (
        SignatureCollection.objects
        .filter(is_active=True)
        .prefetch_related('products', 'products__category')
        .order_by('sort_order', 'name')
    )

    context = {
        'hero_slides': hero_slides,
        'categories': Category.objects.filter(is_active=True, parent__isnull=True),
        'featured_products': featured_products,
        'testimonials': Testimonial.objects.filter(is_active=True),
        'signature_collections': signature_collections,
        'transparent_hero': True,
    }
    return render(request, 'store/home.html', context)


def collection(request, slug=None):
    products = Product.objects.filter(is_active=True, stock__gt=0).select_related('category')  # avoids N+1 queries
    category = None
    subcategories = None

    if slug:
        category = get_object_or_404(Category, slug=slug, is_active=True)
        if category.is_top_level:
            # Viewing a parent category (e.g. "Perfumes") shows products from
            # every active subcategory too, not just ones filed directly
            # under the parent — customers browsing "Perfumes" expect to see
            # "Men's Perfume" and "Women's Perfume" items without having to
            # drill into each subcategory separately.
            subcategories = category.active_children
            category_ids = [category.id] + list(subcategories.values_list('id', flat=True))
            products = products.filter(category_id__in=category_ids)
        else:
            products = products.filter(category=category)

    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'newest':
        products = products.order_by('-created_at')

    return render(request, 'store/collection.html', {
        'products': products,
        'category': category,
        'subcategories': subcategories,
        'categories': Category.objects.filter(is_active=True, parent__isnull=True),
    })
    

def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related('category'), slug=slug, is_active=True)

    # "You may also like" — same category, excluding this product, up to 8.
    related_products = Product.objects.filter(
        category=product.category, is_active=True, stock__gt=0
    ).select_related('category').exclude(id=product.id)[:8]

    signature_products = Product.objects.filter(
        is_active=True, is_featured=True, stock__gt=0
    ).select_related('category').exclude(id=product.id)[:10]

    # Recently viewed — session-based, same pattern as the cart/wishlist.
    # Track this product, then look up the OTHER products already in the
    # list (most-recent-first) to display.
    viewed = request.session.get('recently_viewed', [])
    viewed = [pid for pid in viewed if pid != product.id]  # move to front if already there
    viewed.insert(0, product.id)
    request.session['recently_viewed'] = viewed[:12]

    recently_viewed_products = []
    if len(viewed) > 1:
        other_ids = viewed[1:9]  # skip the product being viewed right now
        products_by_id = Product.objects.filter(
            id__in=other_ids, is_active=True
        ).select_related('category').in_bulk()
        # preserve most-recent-first order (in_bulk doesn't guarantee it)
        recently_viewed_products = [products_by_id[pid] for pid in other_ids if pid in products_by_id]

    return render(request, 'store/product_detail.html', {
        'product': product,
        'related': related_products,
        'related_products': related_products,
        'signature_products': signature_products,
        'recently_viewed_products': recently_viewed_products,
        # The template checks `product.id in wishlist_ids` to decide whether
        # the Wishlist button shows as active — this was missing from context
        # entirely, so the button never reflected the real session wishlist.
        'wishlist_ids': request.session.get('wishlist', []),
    })


def cart_view(request):
    context = get_cart_context(request)
    return render(request, 'store/cart.html', context)


def cart_drawer_data(request):
    """Returns the rendered drawer fragment — used to open the drawer from
    the header cart icon without adding anything."""
    html = render_to_string('store/includes/cart_drawer.html', get_cart_context(request), request=request)
    return JsonResponse({'html': html, 'count': get_cart_count(request)})


def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if product.is_out_of_stock:
        if _is_ajax(request):
            return JsonResponse({'error': f"Sorry — {product.name} just sold out."}, status=400)
        messages.error(request, f"Sorry — {product.name} just sold out.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    # Get quantity from POST data, default to 1
    try:
        qty = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        qty = 1
    # Ensure quantity is at least 1
    if qty < 1:
        qty = 1

    cart = request.session.get('cart', {})
    key = str(product_id)
    cart[key] = min(cart.get(key, 0) + qty, product.stock)
    request.session['cart'] = cart

    if _is_ajax(request):
        html = render_to_string('store/includes/cart_drawer.html', get_cart_context(request), request=request)
        return JsonResponse({'html': html, 'count': get_cart_count(request), 'added': product.name})

    messages.success(request, f"Added “{product.name}” to your cart.")
    return redirect(request.META.get('HTTP_REFERER', '/'))


def cart_update(request, product_id):
    """AJAX quantity change from the drawer (+/- steppers)."""
    product = get_object_or_404(Product, id=product_id)
    try:
        qty = int(request.POST.get('qty', 1))
    except (TypeError, ValueError):
        qty = 1

    cart = request.session.get('cart', {})
    key = str(product_id)
    if qty <= 0:
        del cart[key]
    else:
        cart[key] = min(qty, product.stock)
    request.session['cart'] = cart

    if _is_ajax(request):
        html = render_to_string('store/includes/cart_drawer.html', get_cart_context(request), request=request)
        return JsonResponse({'html': html, 'count': get_cart_count(request)})
    return redirect('store:cart')


def cart_remove(request, product_id):
    cart = request.session.get('cart', {})
    cart.pop(str(product_id), None)
    request.session['cart'] = cart

    if _is_ajax(request):
        html = render_to_string('store/includes/cart_drawer.html', get_cart_context(request), request=request)
        return JsonResponse({'html': html, 'count': get_cart_count(request)})
    return redirect('store:cart')


def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('store:cart')

    items_qs = []
    subtotal = Decimal('0')
    for pid, qty in cart.items():
        product = Product.objects.filter(id=pid).first()
        if not product:
            continue
        items_qs.append((product, qty))
        subtotal += product.price * qty

    if request.method == 'POST':
        coupon = None
        code = request.POST.get('coupon_code', '').strip().upper()
        if code:
            coupon = Coupon.objects.filter(code=code, is_active=True).first()
            if not coupon:
                messages.warning(request, f"Coupon “{code}” isn't valid or has expired.")

        with transaction.atomic():
            order = Order.objects.create(
                customer=request.user if request.user.is_authenticated else None,
                full_name=request.POST.get('full_name', ''),
                email=request.POST.get('email', ''),
                phone=request.POST.get('phone', ''),
                address=request.POST.get('address', ''),
                city=request.POST.get('city', ''),
                coupon=coupon,
                shipping_cost=Decimal(request.POST.get('shipping_cost') or '0'),
            )
            for product, qty in items_qs:
                # Re-check stock at the moment of purchase (another shopper may have bought it since).
                actual_qty = min(qty, product.stock)
                if actual_qty <= 0:
                    continue
                OrderItem.objects.create(
                    order=order, product=product, product_name=product.name,
                    quantity=actual_qty, unit_price=product.price,
                )
                # Real, server-side inventory decrement.
                product.stock = max(product.stock - actual_qty, 0)
                product.save(update_fields=['stock'])

            request.session['cart'] = {}
            return render(request, 'store/order_confirmation.html', {'order': order})

    return render(request, 'store/checkout.html', {'checkout_items': items_qs, 'checkout_subtotal': subtotal})


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to Asma Store!")
            return redirect('store:home')
    else:
        form = UserCreationForm()
    return render(request, 'store/register.html', {'form': form})


def blog_list(request):
    posts = BlogPost.objects.filter(is_published=True)
    return render(request, 'store/blog_list.html', {'posts': posts})


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    recent = BlogPost.objects.filter(is_published=True).exclude(id=post.id)[:3]
    return render(request, 'store/blog_detail.html', {'post': post, 'recent': recent})



# Staff dashboard (requires staff status)
# ---------------------------------------------------------------------------
@staff_member_required
def staff_dashboard(request):
    """The full custom dashboard — sidebar, KPI cards, and two real charts.
    Every number and every chart data point comes from an actual query;
    nothing here is hardcoded or simulated."""
    orders = Order.objects.all()
    total_revenue = sum((o.total for o in orders), start=Decimal('0'))
    today_orders = orders.filter(created_at__date=timezone.now().date())
    today_revenue = sum((o.total for o in today_orders), start=Decimal('0'))
    avg_order_value = (total_revenue / orders.count()) if orders.count() else Decimal('0')

    products = Product.objects.filter(is_active=True)
    low_stock = products.filter(stock__gt=0, stock__lte=8).order_by('stock')
    out_of_stock = products.filter(stock=0)

    top_products = (
        OrderItem.objects.values('product__name')
        .annotate(total_sold=Sum('quantity'))
        .order_by('-total_sold')[:5]
    )

    # --- Real 7-day revenue trend (for the line chart) ---
    today = timezone.now().date()
    trend_labels, trend_values = [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_orders = orders.filter(created_at__date=day)
        day_total = sum((o.total for o in day_orders), start=Decimal('0'))
        trend_labels.append(day.strftime('%a'))
        trend_values.append(float(day_total))
    trend_max = max(trend_values) if any(trend_values) else 1

    # --- Real revenue-by-category breakdown (for the donut chart) ---
    category_breakdown = (
        OrderItem.objects.annotate(line_rev=F('quantity') * F('unit_price'))
        .values('product__category__name')
        .annotate(total=Sum('line_rev'))
        .order_by('-total')
    )
    cat_total = sum((c['total'] or 0) for c in category_breakdown) or 1
    donut_colors = ['#C9A227', '#E5C76B', '#202020', '#8A8A8A', '#D9C48A']
    donut_data = []
    for i, c in enumerate(category_breakdown[:5]):
        pct = round((c['total'] or 0) / cat_total * 100)
        donut_data.append({
            'name': c['product__category__name'] or 'Uncategorized',
            'pct': pct,
            'color': donut_colors[i % len(donut_colors)],
        })

    context = {
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'avg_order_value': avg_order_value,
        'order_count': orders.count(),
        'today_order_count': today_orders.count(),
        'product_count': products.count(),
        'low_stock': low_stock[:6],
        'low_stock_count': low_stock.count(),
        'out_of_stock_count': out_of_stock.count(),
        'recent_orders': orders.order_by('-created_at')[:8],
        'top_products': top_products,
        'customer_count': Order.objects.values('email').distinct().count(),
        'trend_labels': trend_labels,
        'trend_values': trend_values,
        'trend_max': trend_max,
        'donut_data': donut_data,
    }
    return render(request, 'store/dashboard.html', context)


@login_required
def account(request):
    orders = request.user.orders.all()
    return render(request, 'store/account.html', {'orders': orders})


# ---------------------------------------------------------------------------
# Wishlist — session-based (no login required), mirrors the cart pattern.
# ---------------------------------------------------------------------------
def wishlist_toggle(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist = request.session.get('wishlist', [])
    is_now_saved = product_id not in wishlist
    if is_now_saved:
        wishlist.append(product_id)
    else:
        wishlist = [pid for pid in wishlist if pid != product_id]
    request.session['wishlist'] = wishlist

    if _is_ajax(request):
        return JsonResponse({'saved': is_now_saved, 'count': len(wishlist)})
    return redirect(request.META.get('HTTP_REFERER', '/'))


def wishlist_view(request):
    ids = request.session.get('wishlist', [])
    products = Product.objects.filter(id__in=ids, is_active=True).select_related('category')
    return render(request, 'store/wishlist.html', {'products': products})


# ---------------------------------------------------------------------------
# Search — real query against the Product table (name/description/SKU),
# used by both the live-typing overlay (AJAX/JSON) and the full results page.
# ---------------------------------------------------------------------------
def search_view(request):
    query = request.GET.get('q', '').strip()

    # Handle empty search - show popular products
    if not query:
        # Get popular products (featured or recently added)
        popular_products = list(
            Product.objects.filter(
                is_active=True, stock__gt=0
            ).select_related('category').order_by('-is_featured', '-created_at')[:24]
        )

        if _is_ajax(request):
            html = render_to_string('store/includes/search_results.html',
                                  {'results': popular_products, 'query': ''}, request=request)
            return JsonResponse({'html': html, 'count': len(popular_products), 'is_empty_search': True})

        return render(request, 'store/search.html', {
            'results': popular_products,
            'query': '',
            'is_empty_search': True
        })

    # Normalize query: remove extra spaces, handle hyphens/underscores
    normalized_query = re.sub(r'[-\s_]+', ' ', query.lower().strip())

    # Get all active products with related category for efficient querying
    products_qs = Product.objects.filter(is_active=True, stock__gt=0).select_related('category')

    # Convert queryset to list for processing
    products_list = list(products_qs)

    # If no products, return empty results
    if not products_list:
        results = []
    else:
        # Implement intelligent search ranking
        scored_results = []

        for product in products_list:
            score = 0
            match_type = 0  # Lower number = higher priority

            # Prepare fields for comparison
            name_lower = product.name.lower()
            description_lower = product.description.lower() if product.description else ""
            sku_lower = product.sku.lower() if product.sku else ""
            category_name_lower = product.category.name.lower() if product.category else ""

            # 1. Product Name Exact Match (highest priority)
            if normalized_query == name_lower:
                score = 1000
                match_type = 1

            # 2. Product Name Starts With
            elif name_lower.startswith(normalized_query):
                score = 900
                match_type = 2

            # 3. Product Name Contains
            elif normalized_query in name_lower:
                score = 800
                match_type = 3

            # 4. Category Name Exact Match
            elif normalized_query == category_name_lower:
                score = 700
                match_type = 4

            # 5. Category Name Starts With
            elif category_name_lower.startswith(normalized_query):
                score = 600
                match_type = 5

            # 6. Category Name Contains
            elif normalized_query in category_name_lower:
                score = 500
                match_type = 6

            # 7. SKU Exact Match
            elif normalized_query == sku_lower:
                score = 400
                match_type = 7

            # 8. SKU Starts With
            elif sku_lower.startswith(normalized_query):
                score = 300
                match_type = 8

            # 9. SKU Contains
            elif normalized_query in sku_lower:
                score = 200
                match_type = 9

            # 10. Description Contains (lower priority)
            elif normalized_query in description_lower:
                score = 100
                match_type = 10

            # If no direct matches, try fuzzy matching
            if score == 0:
                # Use fuzzy matching on product name
                name_fuzzy_score = fuzz.partial_ratio(normalized_query, name_lower)
                if name_fuzzy_score >= 60:  # Minimum threshold for fuzzy match
                    score = name_fuzzy_score
                    match_type = 11  # Fuzzy match

                # Also check category name for fuzzy match
                elif category_name_lower:
                    category_fuzzy_score = fuzz.partial_ratio(normalized_query, category_name_lower)
                    if category_fuzzy_score >= 60:
                        score = category_fuzzy_score
                        match_type = 12  # Fuzzy category match

            # Only include results with a meaningful score
            if score > 0:
                scored_results.append((score, match_type, product))

        # Sort by score (descending) then by match_type (ascending for tie-breaking)
        scored_results.sort(key=lambda x: (-x[0], x[1]))

        # Extract just the products, limit to 24 results
        results = [item[2] for item in scored_results[:24]]

    # Handle AJAX request for autocomplete/live search
    if _is_ajax(request):
        html = render_to_string('store/includes/search_results.html',
                              {'results': results, 'query': query}, request=request)
        return JsonResponse({
            'html': html,
            'count': len(results),
            'query': query,
            'has_exact_matches': any(
                result.name.lower() == query.lower() or
                result.name.lower().startswith(query.lower())
                for result in results
            ) if results else False
        })

    # For full search results page, also get suggestions if no exact matches
    has_exact_matches = False
    suggestions = []

    if results:
        has_exact_matches = any(
            result.name.lower() == query.lower() or
            result.name.lower().startswith(query.lower())
            for result in results
        )

    # If no exact matches, generate suggestions from product names, categories, etc.
    if not has_exact_matches and results:
        # Get some related products for suggestions
        suggestions = list(
            Product.objects.filter(
                is_active=True, stock__gt=0
            ).select_related('category').exclude(
                id__in=[r.id for r in results]
            ).order_by('?')[:6]  # Random 6 products for suggestion
        )

    return render(request, 'store/search.html', {
        'results': results,
        'query': query,
        'has_exact_matches': has_exact_matches,
        'suggestions': suggestions,
        'is_empty_search': False
    })


def search_suggestions(request):
    """AJAX endpoint for search autocomplete suggestions"""
    query = request.GET.get('q', '').strip()

    if not query or len(query) < 2:
        return JsonResponse({'suggestions': []})

    # Normalize query
    normalized_query = re.sub(r'[-\s_]+', ' ', query.lower().strip())

    # Get products for suggestions
    products = Product.objects.filter(
        is_active=True, stock__gt=0
    ).select_related('category')[:50]  # Limit for performance

    suggestions = set()

    # Add product names that match
    for product in products:
        if product.name.lower().startswith(normalized_query):
            suggestions.add(product.name)
        elif normalized_query in product.name.lower():
            suggestions.add(product.name)

    # Add category names that match
    categories = Category.objects.filter(
        is_active=True
    ).values_list('name', flat=True)

    for category_name in categories:
        if category_name.lower().startswith(normalized_query):
            suggestions.add(category_name)
        elif normalized_query in category_name.lower():
            suggestions.add(category_name)

    # Convert to sorted list and limit
    suggestions_list = sorted(list(suggestions))[:10]

    return JsonResponse({'suggestions': suggestions_list})
