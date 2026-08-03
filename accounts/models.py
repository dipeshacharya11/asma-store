from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import secrets


class OTP(models.Model):
    """
    Model to store OTP verification records.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_records')
    phone_number = models.CharField(max_length=15)
    otp_hash = models.CharField(max_length=128)  # Format: salt:hash (PBKDF2 with SHA256)
    verification_token = models.CharField(max_length=64, unique=True)  # For secure verification link
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=5)  # Default, will be overridden by setting when creating
    is_verified = models.BooleanField(default=False)
    is_used = models.BooleanField(default=False)  # One-time use

    class Meta:
        indexes = [
            models.Index(fields=['phone_number', 'created_at']),
            models.Index(fields=['verification_token']),
        ]

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid_attempt(self):
        return self.attempts < self.max_attempts and not self.is_expired() and not self.is_used

    def increment_attempts(self):
        self.attempts += 1
        self.save(update_fields=['attempts'])

    def mark_verified(self):
        self.is_verified = True
        self.is_used = True
        self.save(update_fields=['is_verified', 'is_used'])

    def __str__(self):
        return f"OTP for {self.phone_number} - {'Verified' if self.is_verified else 'Pending'}"


class UserProfile(models.Model):
    """
    Extended user profile for phone number and other details.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    is_phone_verified = models.BooleanField(default=False)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Profile for {self.user.username}"