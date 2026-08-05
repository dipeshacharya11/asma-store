from django.contrib import admin
from .models import OTP, UserProfile, VerifiedGuestPhone


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'user', 'is_verified', 'is_used', 'created_at', 'expires_at')
    list_filter = ('is_verified', 'is_used', 'created_at', 'expires_at')
    search_fields = ('phone_number', 'user__username', 'user__email')
    readonly_fields = ('verification_token', 'created_at', 'expires_at')
    ordering = ('-created_at',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'is_phone_verified')
    list_filter = ('is_phone_verified',)
    search_fields = ('user__username', 'user__email', 'phone_number')


@admin.register(VerifiedGuestPhone)
class VerifiedGuestPhoneAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'verified_at', 'expires_at', 'is_active', 'converted_to_user')
    list_filter = ('is_active', 'verified_at', 'expires_at')
    search_fields = ('phone_number', 'converted_to_user__username')
    readonly_fields = ('verified_at',)
    ordering = ('-verified_at',)