from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _


class AsmaAdminSite(AdminSite):
    site_header = "Asma Store Admin"
    site_title = "Asma Store Admin"
    index_title = "Store Management"

    def display(self, *args, **kwargs):
        """Display decorator for custom admin site."""
        from django.contrib.admin import display
        return display(*args, **kwargs)

    def index(self, request, extra_context=None):
        """
        Override the default admin index to show our custom dashboard.
        """
        from django.template.response import TemplateResponse
        from django.shortcuts import render
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Sum
        from django.db.models import F
        from django.contrib.admin.models import LogEntry
        from .models import Order, Product, OrderItem
        from accounts.models import OTP, UserProfile, VerifiedGuestPhone

        # Check if user is staff
        if not request.user.is_active or not request.user.is_staff:
            return self.login(request)

        # Generate the same context as staff_dashboard
        orders = Order.objects.all()
        total_revenue = sum((o.total for o in orders), start=0)
        today_orders = orders.filter(created_at__date=timezone.now().date())
        today_revenue = sum((o.total for o in today_orders), start=0)
        avg_order_value = (total_revenue / orders.count()) if orders.count() else 0

        products = Product.objects.filter(is_active=True)
        low_stock = products.filter(stock__gt=0, stock__lte=8).order_by('stock')
        out_of_stock = products.filter(stock=0)

        # OTP and verification counts
        otp_count = OTP.objects.count()
        unverified_otp_count = OTP.objects.filter(is_verified=False).count()
        verified_guest_phone_count = VerifiedGuestPhone.objects.filter(is_active=True).count()
        user_profile_count = UserProfile.objects.count()
        phone_verified_count = UserProfile.objects.filter(is_phone_verified=True).count()

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
            day_total = sum((o.total for o in day_orders), start=0)
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

        # Get admin log entries for the recent actions section
        # Not sliced here to allow template tags to filter/slice if needed
        log_entries = LogEntry.objects.filter(user=request.user).order_by('-action_time')

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
            'otp_count': otp_count,
            'unverified_otp_count': unverified_otp_count,
            'verified_guest_phone_count': verified_guest_phone_count,
            'user_profile_count': user_profile_count,
            'phone_verified_count': phone_verified_count,
            'trend_labels': trend_labels,
            'trend_values': trend_values,
            'trend_max': trend_max,
            'donut_data': donut_data,
            'log_entries': log_entries,
            'available_apps': self.get_app_list(request),
        }

        # Add the extra_context if provided
        if extra_context:
            context.update(extra_context)

        request.current_app = self.name

        return TemplateResponse(request, "store/dashboard.html", context)


# Create an instance of our custom admin site
admin_site = AsmaAdminSite(name='asma_admin')