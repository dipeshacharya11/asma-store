from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, F, Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
import logging

from accounts.models import UserProfile
from accounts.services.phone_verification import PhoneVerificationService
from .models import Category, Product, HeroSlide, Testimonial, Coupon, Order, OrderItem, BlogPost
from .signals import FEATURED_PRODUCTS_CACHE_KEY, HERO_SLIDES_CACHE_KEY
from .cart_utils import get_cart_context, get_cart_count
from .models import SignatureCollection

FREE_SHIPPING_THRESHOLD = Decimal('5000')

logger = logging.getLogger(__name__)

# Initialize phone verification service
phone_verification_service = PhoneVerificationService()


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

    # Default values for logged-in user
    default_phone = ''
    default_name = ''
    default_email = ''
    default_address = ''
    default_city = ''

    if request.user.is_authenticated:
        # Check if user's phone is verified
        is_verified = False
        try:
            profile = request.user.profile
            if profile.phone_number:
                # Check if the specific phone number in profile is verified
                is_verified = phone_verification_service.is_phone_verified_for_user(
                    request.user, phone_number=profile.phone_number
                )
            else:
                # No phone number in profile but check if user has any verified phone number
                # (handles case where is_phone_verified=True but phone_number is empty)
                is_verified = phone_verification_service.is_phone_verified_for_user(request.user)
        except UserProfile.DoesNotExist:
            pass
        if not is_verified:
            # Phone not verified, send OTP for verification
            try:
                profile = request.user.profile
                phone_number = profile.phone_number
                if phone_number:
                    success, message, otp_record = phone_verification_service.verify_phone_for_checkout(
                        phone_number, request.user
                    )
                    if success and otp_record is not None:
                        # OTP sent successfully
                        request.session['pre_verified_user_id'] = request.user.id
                        request.session['phone_number'] = phone_number
                        request.session['otp_purpose'] = 'login'
                        request.session['otp_next_url'] = 'store:checkout'
                        messages.info(request, "Please verify your phone number to continue with checkout.")
                        return redirect('accounts:verify_otp')
                    elif success and otp_record is None:
                        # Phone already verified according to verification service
                        # Let user proceed to checkout (will be handled by verified phone logic below)
                        pass
                    else:
                        # Failed to send OTP
                        messages.error(request, message)
                        return redirect('store:account')
                else:
                    messages.error(request, "Please add a phone number to your profile.")
                    return redirect('store:account')
            except UserProfile.DoesNotExist:
                messages.error(request, "Please complete your profile including phone number.")
                return redirect('store:account')
        else:
            # Phone is verified, use profile data for defaults
            try:
                profile = request.user.profile
                default_phone = profile.phone_number or ''
                default_name = f"{request.user.first_name} {request.user.last_name}".strip()
                if not default_name:
                    default_name = request.user.username
                default_email = request.user.email or ''
                default_address = profile.address or ''
            except UserProfile.DoesNotExist:
                # No profile, user will need to fill in details
                pass

    # Handle GET requests and POST requests when OTP verification is needed
    if request.method == 'POST':
        # Check if this is a verified guest checkout attempt
        if not request.user.is_authenticated and request.session.get('guest_phone_verified'):
            # Use guest data from session for defaults
            default_phone = request.session.get('checkout_phone', '')
            default_name = request.session.get('checkout_full_name', '')
            default_email = request.session.get('checkout_email', '')
            default_address = request.session.get('checkout_address', '')
            default_city = request.session.get('checkout_city', '')
        elif not request.user.is_authenticated:
            # Guest user without verified phone - need to verify first
            phone_number = request.POST.get('phone', '').strip()
            if phone_number:
                # Use phone verification service to check ownership and send OTP if needed
                success, message, verification_obj = phone_verification_service.verify_phone_for_checkout(
                    phone_number
                )

                if success and verification_obj is not None:
                    # OTP sent successfully - need to verify
                    messages.info(request, message)
                    # Store guest data for later use
                    request.session['guest_name'] = request.POST.get('full_name', '').strip()
                    request.session['guest_email'] = request.POST.get('email', '').strip()
                    request.session['guest_address'] = request.POST.get('address', '').strip()
                    request.session['guest_city'] = request.POST.get('city', '').strip()
                    request.session['phone_number'] = phone_number
                    request.session['otp_purpose'] = 'guest_checkout'
                    return redirect('accounts:verify_otp')
                elif success and verification_obj is None:
                    # Phone already verified
                    messages.info(request, message)
                    # Proceed with order processing (will be handled below)
                    pass
                else:
                    # Failed to send OTP or phone belongs to another user
                    messages.error(request, message)
                    return render(request, 'store/checkout.html', {
                        'checkout_items': items_qs,
                        'checkout_subtotal': subtotal,
                        'default_phone': phone_number,
                        'default_name': request.POST.get('full_name', '').strip(),
                        'default_email': request.POST.get('email', '').strip(),
                        'default_address': request.POST.get('address', '').strip(),
                        'default_city': request.POST.get('city', '').strip()
                    })
            else:
                messages.error(request, "Phone number is required for guest checkout.")

        # Process the order (only if we reach here, verification should have happened)
        coupon = None
        code = request.POST.get('coupon_code', '').strip().upper()
        if code:
            coupon = Coupon.objects.filter(code=code, is_active=True).first()
            if not coupon:
                messages.warning(request, f"Coupon “{code}” isn't valid or has expired.")

        # Extract form data
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()

        # Normalize phone number for consistent comparisons
        normalized_phone = phone_verification_service._normalize_phone_number(phone)
        # Handle case where normalization returns empty string (invalid format)
        if not normalized_phone:
            normalized_phone = phone  # Fallback to raw for validation

        # For guest users with verified phone, use session data if form fields are empty
        if not request.user.is_authenticated and request.session.get('guest_phone_verified'):
            if not full_name:
                full_name = request.session.get('guest_name', '')
            if not phone:
                phone = request.session.get('guest_phone', '')
            # Note: We don't have email, address, city in session for guest checkout

        # Check if we need to verify OTP for checkout
        otp_code = request.POST.get('otp', '').strip()
        needs_verification = False

        # Determine if we need OTP verification
        if not request.user.is_authenticated:
            # Guest user - check if phone is already verified for guest use
            ownership_type, _, _ = phone_verification_service.check_phone_ownership(phone)
            if ownership_type in ['registered_user', 'registered_user_unverified']:
                # Phone belongs to a registered user (verified or not) - block checkout
                messages.error(request, "This phone number is already associated with an account. Please sign in to continue with this phone number or use another phone number.")
                return render(request, 'store/checkout.html', {
                    'checkout_items': items_qs,
                    'checkout_subtotal': subtotal,
                    'default_phone': phone,
                    'default_name': full_name,
                    'default_email': email,
                    'default_address': address,
                    'default_city': city
                })
            elif ownership_type not in ['guest_verified']:
                # Need verification (available, guest_expired)
                needs_verification = True
            # If ownership_type is 'guest_verified', no verification needed
        else:
            # Logged-in user - check if the submitted phone number is verified for this user
            try:
                # Check if user is verified to use the submitted phone number
                if not phone_verification_service.is_phone_verified_for_user(request.user, phone_number=normalized_phone):
                    needs_verification = True
            except UserProfile.DoesNotExist:
                needs_verification = True

        # Handle OTP verification
        if needs_verification and otp_code:
            # Verify the OTP
            success, message, verification_obj = phone_verification_service.verify_otp_for_checkout(
                phone, otp_code, request.user if request.user.is_authenticated else None
            )

            if success:
                # OTP verified successfully, proceed with order
                # If verified user is confirming a new phone number (different from profile), update their profile
                if request.user.is_authenticated:
                    try:
                        profile = request.user.profile
                        # Normalize profile phone number for consistent comparison
                        normalized_profile_phone = phone_verification_service._normalize_phone_number(profile.phone_number)
                        if normalized_profile_phone != normalized_phone:
                            profile.phone_number = normalized_phone
                            profile.is_phone_verified = True
                            profile.save(update_fields=['phone_number', 'is_phone_verified'])
                    except UserProfile.DoesNotExist:
                        # Should not happen for authenticated user, but handle gracefully
                        pass
                # Set session variables for guest users and for prefilling form on return visits
                if not request.user.is_authenticated:
                    # Guest user: mark phone as verified for future use
                    request.session['guest_phone_verified'] = True
                # Set checkout session data for prefilling form on subsequent visits
                request.session['checkout_phone'] = normalized_phone
                request.session['checkout_full_name'] = full_name
                request.session['checkout_email'] = email
                request.session['checkout_address'] = address
                request.session['checkout_city'] = city
            else:
                # OTP verification failed
                messages.error(request, message)
                return render(request, 'store/checkout.html', {
                    'checkout_items': items_qs,
                    'checkout_subtotal': subtotal,
                    'default_phone': phone,
                    'default_name': full_name,
                    'default_email': email,
                    'default_address': address,
                    'default_city': city,
                    'otp_required': True,
                    'otp_sent': True
                })
        elif needs_verification and not otp_code:
            # Need to send OTP first
            success, message, otp_record = phone_verification_service.verify_phone_for_checkout(
                phone, request.user if request.user.is_authenticated else None
            )

            if success and otp_record is not None:
                # OTP sent successfully - need to verify
                messages.info(request, message)
                # Store session data for OTP verification
                request.session['phone_number'] = phone
                request.session['otp_purpose'] = 'change_phone'
                return redirect('accounts:verify_otp')
            elif success and otp_record is None:
                # Phone already verified
                messages.info(request, message)
                return render(request, 'store/checkout.html', {
                    'checkout_items': items_qs,
                    'checkout_subtotal': subtotal,
                    'default_phone': phone,
                    'default_name': full_name,
                    'default_email': email,
                    'default_address': address,
                    'default_city': city
                })
            else:
                # Failed to send OTP
                messages.error(request, message)
                return render(request, 'store/checkout.html', {
                    'checkout_items': items_qs,
                    'checkout_subtotal': subtotal,
                    'default_phone': phone,
                    'default_name': full_name,
                    'default_email': email,
                    'default_address': address,
                    'default_city': city
                })

        # Set session variables for guest users and for prefilling form on return visits
        # when no OTP verification is needed (phone already verified)
        if not request.user.is_authenticated:
            # Guest user: mark phone as verified for future use
            request.session['guest_phone_verified'] = True
        else:
            # Logged-in user: if profile shows phone not verified but our service says it is, update profile
            try:
                profile = request.user.profile
                if not profile.is_phone_verified and profile.phone_number and phone_verification_service.is_phone_verified_for_user(request.user, phone_number=profile.phone_number):
                    profile.is_phone_verified = True
                    profile.save(update_fields=['is_phone_verified'])
            except UserProfile.DoesNotExist:
                pass  # Should not happen, but handle gracefully
        # Set checkout session data for prefilling form on subsequent visits
        request.session['checkout_phone'] = normalized_phone
        request.session['checkout_full_name'] = full_name
        request.session['checkout_email'] = email
        request.session['checkout_address'] = address
        request.session['checkout_city'] = city

        with transaction.atomic():
            order = Order.objects.create(
                customer=request.user if request.user.is_authenticated else None,
                full_name=full_name,
                email=email,
                phone=normalized_phone,
                address=address,
                city=city,
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

            # Send order notification to administrator
            try:
                send_order_notification(order)
            except Exception as e:
                # Log the error but don't fail the order
                logger.error(f"Failed to send order notification for order {order.id}: {e}")

            request.session['cart'] = {}
            # Clear checkout-specific session data
            request.session.pop('checkout_phone', None)
            request.session.pop('checkout_full_name', None)
            request.session.pop('checkout_email', None)
            request.session.pop('checkout_address', None)
            request.session.pop('checkout_city', None)
            # Clear guest session data after successful order
            request.session.pop('guest_phone_verified', None)
            request.session.pop('guest_phone', None)
            request.session.pop('guest_name', None)
            request.session.pop('pre_verified_user_id', None)
            request.session.pop('phone_number', None)
            request.session.pop('otp_purpose', None)

            return render(request, 'store/order_confirmation.html', {'order': order})

    # For GET requests, show form with appropriate default values
    # For verified guest users, pre-fill form with data from initial submission
    if not request.user.is_authenticated and request.session.get('guest_phone_verified'):
        # Use checkout_* session values if available (set during OTP verification or previous checkout attempt)
        # Fall back to guest_* values if checkout_* not set (e.g., first visit after OTP verification)
        default_phone = request.session.get('checkout_phone', request.session.get('guest_phone', ''))
        default_name = request.session.get('checkout_full_name', request.session.get('guest_name', ''))
        # For email, address, city, we only have checkout_* values (set during checkout form submission)
        default_email = request.session.get('checkout_email', '')
        default_address = request.session.get('checkout_address', '')
        default_city = request.session.get('checkout_city', '')

    return render(request, 'store/checkout.html', {
        'checkout_items': items_qs,
        'checkout_subtotal': subtotal,
        'default_phone': default_phone,
        'default_name': default_name,
        'default_email': default_email,
        'default_address': default_address,
        'default_city': default_city
    })


@login_required
def order_detail(request, order_id):
    """Display details for a specific order belonging to the logged-in user."""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    return render(request, 'store/order_detail.html', {'order': order})


def register(request):
    if request.method == 'POST':
        # Get form data manually since we need email and phone
        username = request.POST.get('username', '')
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        email = request.POST.get('email', '')
        phone_number = request.POST.get('phone_number', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        address = request.POST.get('address', '')

        # Basic validation
        if not username or not password1 or not password2 or not email or not phone_number:
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'store/register.html', {
                'username': username,
                'email': email,
                'phone_number': phone_number,
                'first_name': first_name,
                'last_name': last_name,
                'address': address
            })

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, 'store/register.html', {
                'username': username,
                'email': email,
                'phone_number': phone_number,
                'first_name': first_name,
                'last_name': last_name,
                'address': address
            })

        # Check if username already exists
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'store/register.html', {
                'username': username,
                'email': email,
                'phone_number': phone_number,
                'first_name': first_name,
                'last_name': last_name,
                'address': address
            })

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return render(request, 'store/register.html', {
                'username': username,
                'email': email,
                'phone_number': phone_number,
                'first_name': first_name,
                'last_name': last_name,
                'address': address
            })

        # Validate phone number format (10 digits, starting with 97 or 98)
        import re
        if not re.match(r'^(97|98)\d{8}$', phone_number):
            messages.error(request, "Phone number must be 10 digits starting with 97 or 98 (e.g., 98XXXXXXXX or 97XXXXXXXX)")
            return render(request, 'store/register.html', {
                'username': username,
                'email': email,
                'phone_number': phone_number,
                'first_name': first_name,
                'last_name': last_name,
                'address': address
            })

        # Check if phone number already exists in UserProfile
        from accounts.models import UserProfile
        if UserProfile.objects.filter(phone_number=phone_number).exists():
            messages.error(request, "This phone number is already registered.")
            return render(request, 'store/register.html', {
                'username': username,
                'email': email,
                'phone_number': phone_number,
                'first_name': first_name,
                'last_name': last_name,
                'address': address
            })

        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name
            )
            user.is_active = False  # Deactivate until OTP verified
            user.save()

            # Create user profile with phone number and address
            UserProfile.objects.create(
                user=user,
                phone_number=phone_number,
                address=address
            )

            # Send OTP
            from accounts.services.otp_service import OTPService
            otp_service = OTPService()
            success, message, otp_record = otp_service.send_otp(user, phone_number)

            if success:
                # Store user id and phone number in session for verification
                request.session['pre_verified_user_id'] = user.id
                request.session['phone_number'] = phone_number
                messages.success(request, message)
                return redirect('accounts:verify_otp')
            else:
                messages.error(request, message)
                # Delete the user if OTP sending failed
                user.delete()
                return render(request, 'store/register.html', {
                    'username': username,
                    'email': email,
                    'phone_number': phone_number,
                    'first_name': first_name,
                    'last_name': last_name,
                    'address': address
                })
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return render(request, 'store/register.html', {
                'username': username,
                'email': email,
                'phone_number': phone_number,
                'first_name': first_name,
                'last_name': last_name,
                'address': address
            })
    else:
        # GET request - show empty form
        return render(request, 'store/register.html')


def blog_list(request):
    posts = BlogPost.objects.filter(is_published=True)
    return render(request, 'store/blog_list.html', {'posts': posts})


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    recent = BlogPost.objects.filter(is_published=True).exclude(id=post.id)[:3]
    return render(request, 'store/blog_detail.html', {'post': post, 'recent': recent})


def about(request):
    return render(request, 'store/about.html')


def about(request):
    return render(request, 'store/about.html')


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
    # Check if user has a verified phone number
    try:
        profile = request.user.profile
        if not profile.phone_number or not profile.is_phone_verified:
            # User doesn't have a phone number or it's not verified
            messages.info(request, "Please verify your phone number to access your account.")
            return redirect('accounts:change_phone')
    except UserProfile.DoesNotExist:
        # User doesn't have a profile, create one or redirect to complete profile
        messages.info(request, "Please complete your profile including phone number.")
        return redirect('accounts:change_phone')

    orders = request.user.orders.all()
    return render(request, 'store/account.html', {'orders': orders})


def send_order_notification(order):
    """
    Send order notification to administrator's phone number via Sparrow SMS.
    """
    try:
        # Initialize SMS service
        from accounts.services.sms import SparrowSMSService
        sms_service = SparrowSMSService()

        # Get administrator phone number from settings
        from django.conf import settings
        admin_phone = getattr(settings, 'SPARROW_ADMIN_PHONE', '')

        # If no administrator phone is configured (empty or whitespace-only), fall back to logging only
        if not admin_phone or not admin_phone.strip():
            # Log the notification details
            notification_message = (
                f"NEW ORDER ALERT\n"
                f"Order ID: {order.id}\n"
                f"Customer: {order.full_name}\n"
                f"Phone: {order.phone}\n"
                f"Email: {order.email}\n"
                f"Address: {order.address}, {order.city}\n"
                f"Total Amount: Rs. {order.total}\n"
                f"Items Count: {order.items.count()}\n"
                f"Order Time: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            logger.info(f"ORDER NOTIFICATION:\n{notification_message}")
            return

        # Format the notification message
        notification_message = (
            f"NEW ORDER ALERT\n"
            f"Order ID: {order.id}\n"
            f"Customer: {order.full_name}\n"
            f"Phone: {order.phone}\n"
            f"Email: {order.email}\n"
            f"Address: {order.address}, {order.city}\n"
            f"Total Amount: Rs. {order.total}\n"
            f"Items Count: {order.items.count()}\n"
            f"Order Time: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )

        # Send SMS via Sparrow SMS
        # DEBUG: Log what we're sending
        logger.info(f"Sending SMS to admin_phone: '{admin_phone}' with message: '{notification_message[:100]}...'")
        success, message_id, response = sms_service.send_message(admin_phone, notification_message)

        if success:
            logger.info(f"Order notification sent via Sparrow SMS for order {order.id}. Message ID: {message_id}")
        else:
            logger.error(f"Failed to send order notification via Sparrow SMS for order {order.id}: {response}")
            # Fall back to logging only
            logger.info(f"ORDER NOTIFICATION (FALLBACK - SMS FAILED):\n{notification_message}")

    except Exception as e:
        logger.error(f"Error sending order notification for order {order.id}: {e}")
        # Fall back to logging only
        notification_message = (
            f"NEW ORDER ALERT\n"
            f"Order ID: {order.id}\n"
            f"Customer: {order.full_name}\n"
            f"Phone: {order.phone}\n"
            f"Email: {order.email}\n"
            f"Address: {order.address}, {order.city}\n"
            f"Total Amount: Rs. {order.total}\n"
            f"Items Count: {order.items.count()}\n"
            f"Order Time: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        logger.info(f"ORDER NOTIFICATION (FALLBACK - EXCEPTION):\n{notification_message}")


def search_view(request):
    """
    Search for products by name or description.
    """
    query = request.GET.get('q', '').strip()
    if query:
        # Search in product name and description
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_active=True,
            stock__gt=0
        ).select_related('category')
    else:
        products = Product.objects.filter(is_active=True, stock__gt=0).select_related('category')

    # Handle sorting
    sort = request.GET.get('sort')
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    elif sort == 'newest':
        products = products.order_by('-created_at')
    # else: default ordering (by name or id, but we'll keep the queryset order as is)

    context = {
        'products': products,
        'query': query,
        'categories': Category.objects.filter(is_active=True, parent__isnull=True),
    }
    return render(request, 'store/collection.html', context)