from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from accounts.models import OTP, UserProfile, VerifiedGuestPhone
from .admin_site import admin_site
from .models import Category, Product, HeroSlide, Testimonial, Coupon, Order, OrderItem, BlogPost, SignatureCollection


class OTPAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'user', 'status', 'created_at', 'expires_at')
    list_filter = ('status', 'created_at', 'expires_at')
    search_fields = ('phone_number', 'user__username', 'user__email')
    readonly_fields = ('verification_token', 'created_at', 'expires_at')
    ordering = ('-created_at',)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active', 'sort_order', 'product_count')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['sort_order', 'name']


class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'price', 'stock', 'is_active', 'is_featured')
    list_filter = ('is_active', 'is_featured', 'is_new', 'is_top_rated', 'category')
    search_fields = ('name', 'sku', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['-created_at']


class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ('title', 'eyebrow', 'cta_text', 'sort_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title', 'eyebrow', 'description')
    ordering = ['sort_order']


class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'rating', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'role', 'quote')
    ordering = ['-rating']


class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'published_at', 'is_published')
    list_filter = ('is_published', 'published_at')
    search_fields = ('title', 'excerpt', 'content')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ['-published_at']


class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'percent_off', 'is_active', 'expires_at')
    list_filter = ('is_active', 'expires_at')
    search_fields = ('code',)
    ordering = ['-expires_at']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'quantity', 'unit_price', 'line_total')


class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'email', 'phone', 'status', 'total', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('full_name', 'email', 'phone')
    readonly_fields = ('subtotal', 'discount', 'total', 'created_at')
    inlines = [OrderItemInline]
    ordering = ['-created_at']


class SignatureCollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'subtitle', 'is_active', 'sort_order', 'product_count')
    list_filter = ('is_active',)
    search_fields = ('name', 'subtitle', 'description')
    filter_horizontal = ('products',)
    ordering = ['sort_order', 'name']

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Product Count'


# Register all models with the custom admin site
admin_site.register(OTP, OTPAdmin)
admin_site.register(Category, CategoryAdmin)
admin_site.register(Product, ProductAdmin)
admin_site.register(HeroSlide, HeroSlideAdmin)
admin_site.register(Testimonial, TestimonialAdmin)
admin_site.register(BlogPost, BlogPostAdmin)
admin_site.register(Coupon, CouponAdmin)
admin_site.register(Order, OrderAdmin)
admin_site.register(SignatureCollection, SignatureCollectionAdmin)
admin_site.register(OrderItem)  # Using default ModelAdmin for OrderItem since it's mainly used as inline

# Register User and Group with the custom admin site
admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin)

# Register UserProfile and VerifiedGuestPhone with the custom admin site
admin_site.register(UserProfile)
admin_site.register(VerifiedGuestPhone)