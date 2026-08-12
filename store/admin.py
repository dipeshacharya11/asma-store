from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count

from store.models import (
    Category,
    Product,
    HeroSlide,
    Testimonial,
    Coupon,
    Order,
    OrderItem,
    BlogPost,
    SignatureCollection,
)
from django.contrib.auth.models import User
from store.admin_site import admin_site

from accounts.models import OTP, UserProfile, VerifiedGuestPhone

# Configure the admin site
admin_site.site_header = "Asma Store Admin"
admin_site.site_title = "Asma Store Admin"
admin_site.index_title = "Store Management"

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('username',)


class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail",
        "indented_name",
        "parent",
        "slug",
        "total_product_count",
        "is_active",
        "sort_order",
    )

    list_filter = ("parent", "is_active")
    autocomplete_fields = ("parent",)
    search_fields = ("name", "slug")

    prepopulated_fields = {
        "slug": ("name",),
    }

    list_editable = (
        "is_active",
        "sort_order",
    )

    actions = ['delete_selected']

    @admin_site.display(description="Category")
    def indented_name(self, obj):
        if obj.parent_id:
            return format_html("&nbsp;&nbsp;&nbsp;&nbsp;→ {}", obj.name)
        return format_html("<b>{}</b>", obj.name)

    @admin_site.display(description="Products (incl. subcategories)")
    def total_product_count(self, obj):
        return obj.total_product_count

    @admin_site.display(description="Photo")
    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" '
                'style="height:40px; width:40px; object-fit:cover; '
                'border-radius:6px;">',
                obj.image.url,
            )

        return "—"

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'parent')
        }),
        ('Description & Image', {
            'fields': ('description', 'image', 'hero_gradient')
        }),
        ('Display Settings', {
            'fields': ('is_active', 'sort_order'),
        }),
    )


class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "thumbnail",
        "name",
        "sku",
        "category",
        "price",
        "stock_status",
        "is_active",
        "is_featured",
        "is_new",
        "is_top_rated",
        "rating",
    )

    actions = [
        "mark_as_featured",
        "remove_from_featured",
        "mark_as_new",
        "remove_from_new",
        "mark_as_top_rated",
        "remove_from_top_rated",
        "activate_products",
        "deactivate_products",
        "delete_selected",
    ]

    @admin.action(description="Mark selected products as Featured")
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} product(s) marked as featured.")

    @admin.action(description="Remove selected products from Featured")
    def remove_from_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"{updated} product(s) removed from featured.")

    @admin.action(description="Mark selected products as New Arrivals")
    def mark_as_new(self, request, queryset):
        updated = queryset.update(is_new=True)
        self.message_user(request, f"{updated} product(s) marked as new arrivals.")

    @admin.action(description="Remove selected products from New Arrivals")
    def remove_from_new(self, request, queryset):
        updated = queryset.update(is_new=False)
        self.message_user(request, f"{updated} product(s) removed from new arrivals.")

    @admin.action(description="Mark selected products as Top Rated")
    def mark_as_top_rated(self, request, queryset):
        updated = queryset.update(is_top_rated=True)
        self.message_user(request, f"{updated} product(s) marked as top rated.")

    @admin.action(description="Remove selected products from Top Rated")
    def remove_from_top_rated(self, request, queryset):
        updated = queryset.update(is_top_rated=False)
        self.message_user(request, f"{updated} product(s) removed from top rated.")

    @admin.action(description="Activate selected products (re-establish)")
    def activate_products(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} product(s) activated.")

    @admin.action(description="Deactivate selected products")
    def deactivate_products(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} product(s) deactivated.")

    list_filter = (
        "category",
        "is_active",
        "is_featured",
        "is_new",
        "is_top_rated",
    )

    search_fields = (
        "name",
        "sku",
    )

    list_editable = (
        "is_active",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }

    @admin_site.display(description="Photo")
    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" '
                'style="height:44px; width:44px; object-fit:cover; '
                'border-radius:8px;">',
                obj.image.url,
            )

        return "—"

    @admin_site.display(description="Stock")
    def stock_status(self, obj):
        if obj.is_out_of_stock:
            return format_html(
                '<span style="color:{}; font-weight:700;">{}</span>',
                "#E0637A",
                "Out of stock",
            )

        if obj.is_low_stock:
            return format_html(
                '<span style="color:{}; font-weight:700;">{} left — low</span>',
                "#D9A441",
                obj.stock,
            )

        return format_html(
            '<span>{} in stock</span>',
            obj.stock,
        )

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'sku', 'category')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Pricing', {
            'fields': ('price', 'compare_at_price')
        }),
        ('Inventory', {
            'fields': ('stock',)
        }),
        ('Product Images', {
            'fields': ('image', 'image_secondary', 'image_gradient', 'image_gradient_secondary')
        }),
        ('Product Details', {
            'fields': ('is_active', 'is_featured', 'is_new', 'is_top_rated', 'rating', 'rating_count')
        }),
    )


class HeroSlideAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "eyebrow",
        "sort_order",
        "is_active",
    )

    list_editable = (
        "sort_order",
        "is_active",
    )

    actions = ['delete_selected']

    fieldsets = (
        (None, {
            'fields': ('title', 'eyebrow', 'description')
        }),
        ('Call to Action', {
            'fields': ('cta_text', 'cta_url')
        }),
        ('Image', {
            'fields': ('image', 'image_url')
        }),
        ('Display Settings', {
            'fields': ('vertical_label', 'sort_order', 'is_active')
        }),
    )


class BlogPostAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "author",
        "is_published",
        "published_at",
    )

    prepopulated_fields = {
        "slug": ("title",),
    }

    list_editable = (
        "is_published",
    )

    actions = ['delete_selected']

    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author')
        }),
        ('Content', {
            'fields': ('excerpt', 'content', 'image_gradient')
        }),
        ('Publication', {
            'fields': ('is_published', 'published_at')
        }),
    )


class TestimonialAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "rating",
        "role",
        "is_active",
    )

    list_editable = (
        "is_active",
        "rating",
    )

    actions = ['delete_selected']

    fieldsets = (
        (None, {
            'fields': ('name', 'role', 'quote', 'rating')
        }),
        ('Display', {
            'fields': ('is_active',)
        }),
    )


class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "percent_off",
        "is_active",
        "expires_at",
    )

    list_editable = (
        "is_active",
    )

    actions = ['delete_selected']

    fieldsets = (
        (None, {
            'fields': ('code', 'percent_off', 'expires_at', 'is_active')
        }),
    )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

    readonly_fields = (
        "product_name",
        "unit_price",
        "line_total",
    )


class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "email",
        "status",
        "total",
        "created_at",
    )

    list_filter = (
        "status",
    )

    list_editable = (
        "status",
    )

    actions = ['delete_selected']

    inlines = [
        OrderItemInline,
    ]

    fieldsets = (
        (None, {
            'fields': ('full_name', 'email', 'phone', 'address', 'city')
        }),
        ('Order Details', {
            'fields': ('status', 'coupon', 'shipping_cost')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )


class SignatureCollectionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "product_total",
        "sort_order",
        "is_active",
        "created_at",
    )

    list_editable = (
        "sort_order",
        "is_active",
    )

    actions = ['delete_selected']

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "subtitle",
        "description",
    )

    filter_horizontal = (
        "products",
    )

    ordering = (
        "sort_order",
        "name",
    )

    @admin_site.display(description="Products")
    def product_total(self, obj):
        return obj.products.count()

    fieldsets = (
        (None, {
            'fields': ('name', 'subtitle', 'description')
        }),
        ('Products', {
            'fields': ('products',)
        }),
        ('Display Settings', {
            'fields': ('sort_order', 'is_active')
        }),
    )


class OTPAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'user', 'is_verified', 'is_used', 'created_at', 'expires_at')
    list_filter = ('is_verified', 'is_used', 'created_at', 'expires_at')
    search_fields = ('phone_number', 'user__username', 'user__email')
    readonly_fields = ('verification_token', 'created_at', 'expires_at')
    ordering = ('-created_at',)


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'is_phone_verified')
    list_filter = ('is_phone_verified',)
    search_fields = ('user__username', 'user__email', 'phone_number')


class VerifiedGuestPhoneAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'verified_at', 'expires_at', 'is_active', 'converted_to_user')
    list_filter = ('is_active', 'verified_at', 'expires_at')
    search_fields = ('phone_number', 'converted_to_user__username')
    readonly_fields = ('verified_at',)
    ordering = ('-verified_at',)


# Register models with our custom admin site
admin_site.register(OTP, OTPAdmin)
admin_site.register(UserProfile, UserProfileAdmin)
admin_site.register(VerifiedGuestPhone, VerifiedGuestPhoneAdmin)
admin_site.register(Category, CategoryAdmin)
admin_site.register(Product, ProductAdmin)
admin_site.register(HeroSlide, HeroSlideAdmin)
admin_site.register(BlogPost, BlogPostAdmin)
admin_site.register(Testimonial, TestimonialAdmin)
admin_site.register(Coupon, CouponAdmin)
admin_site.register(Order, OrderAdmin)
admin_site.register(SignatureCollection, SignatureCollectionAdmin)
admin_site.register(User, UserAdmin)