from django.contrib import admin
from django.utils.html import format_html

from .models import (
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


admin.site.site_header = "Asma Store Admin"
admin.site.site_title = "Asma Store Admin"
admin.site.index_title = "Store Management"


@admin.register(Category)
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

    @admin.display(description="Category")
    def indented_name(self, obj):
        if obj.parent_id:
            return format_html("&nbsp;&nbsp;&nbsp;&nbsp;↳ {}", obj.name)
        return format_html("<b>{}</b>", obj.name)

    @admin.display(description="Products (incl. subcategories)")
    def total_product_count(self, obj):
        return obj.total_product_count

    @admin.display(description="Photo")
    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" '
                'style="height:40px; width:40px; object-fit:cover; '
                'border-radius:6px;">',
                obj.image.url,
            )

        return "—"


@admin.register(Product)
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
    )

    list_filter = (
        "category",
        "is_active",
        "is_featured",
        "is_new",
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

    @admin.display(description="Photo")
    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" '
                'style="height:44px; width:44px; object-fit:cover; '
                'border-radius:8px;">',
                obj.image.url,
            )

        return "—"

    @admin.display(description="Stock")
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


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "sort_order",
        "is_active",
    )

    list_editable = (
        "sort_order",
        "is_active",
    )


@admin.register(BlogPost)
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


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "rating",
        "is_active",
    )


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "percent_off",
        "is_active",
        "expires_at",
    )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

    readonly_fields = (
        "product_name",
        "unit_price",
        "line_total",
    )


@admin.register(Order)
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

    inlines = [
        OrderItemInline,
    ]
    #--------signature -------------------------------------------------------------------
@admin.register(SignatureCollection)
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

    @admin.display(description="Products")
    def product_total(self, obj):
        return obj.products.count()