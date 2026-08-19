from django.contrib import admin
from accounts.models import OTP


class OTPAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'user', 'status', 'created_at', 'expires_at')
    list_filter = ('status', 'created_at', 'expires_at')
    search_fields = ('phone_number', 'user__username', 'user__email')
    readonly_fields = ('verification_token', 'created_at', 'expires_at')
    ordering = ('-created_at',)