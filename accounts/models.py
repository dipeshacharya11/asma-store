from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
import secrets
import hashlib
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


class OTP(models.Model):
    PURPOSE_CHOICES = [
        ('signup', 'Sign Up'),
        ('login', 'Login'),
        ('guest_checkout', 'Guest Checkout'),
        ('password_reset', 'Password Reset'),
        ('change_phone', 'Change Phone'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_records', blank=True, null=True)
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(
            regex=r'^(97|98)\d{8}$',
            message='Phone number must be 10 digits starting with 97 or 98'
        )]
    )
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default='signup')
    otp_hash = models.CharField(max_length=128)  # For Argon2 or PBKDF2 hash
    verification_token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=5)  # Default, will be overridden by setting when creating
    is_verified = models.BooleanField(default=False)
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['phone_number', 'purpose', 'created_at']),
            models.Index(fields=['verification_token']),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=5)
        if not self.verification_token:
            self.verification_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid_attempt(self):
        return self.attempts < self.max_attempts and not self.is_expired() and not self.is_used

    def increment_attempts(self):
        self.attempts += 1
        self.save(update_fields=['attempts'])

    def verify(self, otp_code):
        """Verify OTP using Argon2 or PBKDF2 fallback"""
        if self.is_expired() or self.is_used or not self.is_valid_attempt():
            return False

        self.increment_attempts()

        # Verify using Argon2 if available, else PBKDF2
        try:
            # Try Argon2 first
            from argon2 import PasswordHasher
            ph = PasswordHasher()
            ph.verify(self.otp_hash, otp_code)
        except ImportError:
            # Fallback to PBKDF2
            if not hasattr(settings, 'ARGON2_ENABLED') or not settings.ARGON2_ENABLED:
                # PBKDF2 with SHA256
                expected_hash = hashlib.pbkdf2_hmac(
                    'sha256',
                    otp_code.encode('utf-8'),
                    settings.SECRET_KEY.encode('utf-8'),
                    100000
                ).hex()
                if not secrets.compare_digest(expected_hash, self.otp_hash):
                    return False
            else:
                # If Argon2 is enabled but not available, fail
                return False
        except Exception:
            return False

        # Mark as verified and used
        self.is_verified = True
        self.is_used = True
        self.save(update_fields=['is_verified', 'is_used'])
        return True

    @classmethod
    def create_otp(cls, phone_number, purpose, user=None):
        """Create a new OTP instance with a random 6-digit code"""
        # Generate a 6-digit OTP
        otp_code = ''.join(str(secrets.randbelow(10)) for _ in range(6))

        # Hash the OTP
        try:
            # Try Argon2 first
            from argon2 import PasswordHasher
            ph = PasswordHasher()
            otp_hash = ph.hash(otp_code)
        except ImportError:
            # Fallback to PBKDF2
            if not hasattr(settings, 'ARGON2_ENABLED') or not settings.ARGON2_ENABLED:
                # PBKDF2 with SHA256
                salt = secrets.token_bytes(16)
                otp_hash = hashlib.pbkdf2_hmac(
                    'sha256',
                    otp_code.encode('utf-8'),
                    salt,
                    100000
                )
                # Store as: pbkdf2_sha256$salt$hash
                otp_hash = f"pbkdf2_sha256${salt.hex()}${otp_hash.hex()}"
            else:
                # If Argon2 is enabled but not available, we cannot proceed
                raise RuntimeError("Argon2 is enabled but not installed")

        # Create and save the OTP instance
        otp = cls(
            phone_number=phone_number,
            purpose=purpose,
            user=user,
            otp_hash=otp_hash,
            verification_token=secrets.token_urlsafe(32),
            expires_at=timezone.now() + timezone.timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        )
        otp.save()
        return otp, otp_code

    @classmethod
    def cleanup_expired(cls):
        """Delete expired OTP records"""
        cls.objects.filter(expires_at__lt=timezone.now()).delete()

    def __str__(self):
        return f"OTP for {self.phone_number} ({self.purpose}) - {'Verified' if self.is_verified else 'Pending'}"


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


class VerifiedGuestPhone(models.Model):
    """
    Tracks phone numbers that have been verified for guest checkout.
    Allows guest users to reuse verified phone numbers without re-verification
    until expiration or admin reset.
    """
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^(97|98)\d{8}$',
                message='Phone number must be 10 digits starting with 97 or 98'
            )
        ],
        help_text="Phone number in format: 97XXXXXXXX or 98XXXXXXXX"
    )
    verified_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="When this verification expires and requires re-verification"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this verification is currently valid"
    )
    # Optional: track which user this phone was converted to if they create an account
    converted_to_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_guest_phone',
        help_text="If this phone was used to create an account, link to that user"
    )

    class Meta:
        verbose_name = "Verified Guest Phone"
        verbose_name_plural = "Verified Guest Phones"
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.phone_number} (verified {self.formatted_verification_date})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return self.is_active and not self.is_expired

    @property
    def formatted_verification_date(self):
        return self.verified_at.strftime("%b %d, %Y at %I:%M %p")

    def deactivate(self):
        """Deactivate this verification (e.g., when user creates account)"""
        self.is_active = False
        self.save(update_fields=['is_active'])

    def extend_validity(self, days=30):
        """Extend the validity period"""
        self.expires_at = timezone.now() + timedelta(days=days)
        self.save(update_fields=['expires_at'])


