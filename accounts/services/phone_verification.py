from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from django.conf import settings
from django.db.models import Q
from accounts.models import OTP, VerifiedGuestPhone, UserProfile
from accounts.services.otp_service import OTPService
from accounts.services.sms import SparrowSMSService
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class PhoneVerificationService:
    """
    Service for handling phone verification specifically for checkout process.
    Implements the business rules for phone ownership and verification.
    """

    def __init__(self):
        self.otp_service = OTPService()
        self.sms_service = SparrowSMSService()

    def check_phone_ownership(self, phone_number):
        """
        Check who owns a phone number.
        Returns a tuple: (ownership_type, user_or_none, verified_guest_phone_or_none)
        ownership_type can be: 'registered_user', 'guest_verified', 'guest_unverified', 'available'
        """
        # Normalize phone number
        phone_number = self._normalize_phone_number(phone_number)

        # Check if it belongs to a registered user
        try:
            user = User.objects.get(profile__phone_number=phone_number)
            profile = user.profile
            if profile.is_phone_verified:
                return ('registered_user', user, None)
            else:
                # User exists but phone not verified
                return ('registered_user_unverified', user, None)
        except User.DoesNotExist:
            pass

        # Check if it's a verified guest phone
        try:
            verified_guest = VerifiedGuestPhone.objects.get(
                phone_number=phone_number,
                is_active=True
            )
            if not verified_guest.is_expired:
                return ('guest_verified', None, verified_guest)
            else:
                # Expired verification
                return ('guest_expired', None, verified_guest)
        except VerifiedGuestPhone.DoesNotExist:
            pass

        # Phone is available for verification
        return ('available', None, None)

    def verify_phone_for_checkout(self, phone_number, user=None):
        """
        Verify a phone number for checkout purposes.
        Handles both guest and registered user scenarios according to business rules.
        """
        # Normalize phone number
        phone_number = self._normalize_phone_number(phone_number)

        # Check ownership
        ownership_type, user_obj, verified_guest = self.check_phone_ownership(phone_number)

        # Handle different ownership scenarios
        if ownership_type == 'registered_user':
            # Phone belongs to a verified registered user
            if user and user.id == user_obj.id:
                # Current user owns this phone - already verified, no action needed
                return True, "Phone number is already verified.", None
            else:
                # Phone belongs to another registered user
                return False, "This phone number is already associated with an account. Please sign in to continue.", None

        elif ownership_type == 'registered_user_unverified':
            # Phone belongs to a registered user but not verified
            if user and user.id == user_obj.id:
                # Current user owns this phone but it's not verified
                # Send OTP for verification
                success, message, otp_record = self.otp_service.send_otp(user_obj, phone_number, 'login')
                if success:
                    return True, "Verification code sent to your phone.", otp_record
                else:
                    return False, f"Failed to send verification code: {message}", None
            else:
                # Phone belongs to another user (verified or not)
                return False, "This phone number is already associated with an account. Please sign in to continue.", None

        elif ownership_type == 'guest_verified':
            # Phone is verified for guest use
            # Check if it's been converted to a user
            if verified_guest.converted_to_user:
                if user and user.id == verified_guest.converted_to_user.id:
                    # Current user owns this phone (was converted from guest)
                    return True, "Phone number is already verified.", None
                else:
                    # Phone was converted to another user
                    return False, "This phone number is already associated with an account. Please sign in to continue.", None
            else:
                # Still available for guest use
                return True, "Phone number is already verified for guest use.", None

        elif ownership_type == 'guest_expired':
            # Previous guest verification has expired
            # Treat as new verification
            pass

        # For 'available', 'guest_expired', or when we need to send OTP
        if user:
            # Verified user trying to verify their phone
            success, message, otp_record = self.otp_service.send_otp(user, phone_number, 'change_phone')
            purpose = 'change_phone'
        else:
            # Guest user or new user
            success, message, otp_record = self.otp_service.send_otp(None, phone_number, 'guest_checkout')
            purpose = 'guest_checkout'

        # Send OTP via SMS (already done in send_otp, but we need to check the result)
        if success:
            return True, "Verification code sent to your phone.", otp_record
        else:
            return False, f"Failed to send verification code: {message}", None

    def verify_otp_for_checkout(self, phone_number, otp_code, user=None):
        """
        Verify OTP for checkout process.
        Returns tuple: (success, message, verified_guest_phone_or_user)
        """
        # Normalize phone number
        phone_number = self._normalize_phone_number(phone_number)

        # Verify the OTP using existing service
        success, message, otp_record = self.otp_service.verify_otp(phone_number, otp_code, 'guest_checkout')

        if success and otp_record:
            # OTP verified successfully
            if user:
                # User is verifying their phone (for login or change phone)
                # Mark user's phone as verified
                try:
                    profile = user.profile
                    profile.phone_number = phone_number
                    profile.is_phone_verified = True
                    profile.save(update_fields=['phone_number', 'is_phone_verified'])

                    # Also create or update verified guest record (in case they want to use as guest later)
                    verified_guest, created = VerifiedGuestPhone.objects.get_or_create(
                        phone_number=phone_number,
                        defaults={
                            'is_active': True,
                            'expires_at': timezone.now() + timedelta(days=365),  # 1 year validity
                            'converted_to_user': user
                        }
                    )
                    if not created:
                        # Update existing record
                        verified_guest.is_active = True
                        verified_guest.expires_at = timezone.now() + timedelta(days=365)
                        verified_guest.converted_to_user = user
                        verified_guest.save()

                    return True, "Phone number verified successfully.", user
                except UserProfile.DoesNotExist:
                    # Create profile if it doesn't exist
                    UserProfile.objects.create(
                        user=user,
                        phone_number=phone_number,
                        is_phone_verified=True
                    )
                    return True, "Phone number verified successfully.", user
            else:
                # Guest user verifying phone
                # Create or update verified guest record
                verified_guest, created = VerifiedGuestPhone.objects.get_or_create(
                    phone_number=phone_number,
                    defaults={
                        'is_active': True,
                        'expires_at': timezone.now() + timedelta(days=30)  # 30 days validity for guest
                    }
                )
                if not created:
                    # Update existing record
                    verified_guest.is_active = True
                    verified_guest.expires_at = timezone.now() + timedelta(days=30)
                    # Clear any previous user association when guest verifies the phone
                    verified_guest.converted_to_user = None
                    verified_guest.save()

                return True, "Phone number verified successfully for guest use.", verified_guest
        else:
            # OTP verification failed
            return False, message, None

    def is_phone_verified_for_user(self, user, phone_number=None):
        """
        Check if a user's phone number is verified.
        If phone_number is provided, check if user is verified to use that specific number.
        If phone_number is None, check if user has any verified phone number.

        Returns True if:
        1. User's profile has is_phone_verified = True with a phone number (and matches phone_number if provided), OR
        2. User has any active, non-expired VerifiedGuestPhone record that they can use
           (either already claimed by them or unclaimed)
        """
        try:
            profile = user.profile

            # If checking a specific phone number
            if phone_number is not None:
                # Normalize the phone number we're checking against
                normalized_phone_number = self._normalize_phone_number(phone_number)

                # Check 1: Direct profile verification with phone number
                if profile.is_phone_verified:
                    profile_phone_number = self._normalize_phone_number(profile.phone_number)
                    if profile_phone_number and profile_phone_number == normalized_phone_number:
                        return True

                # Check 2: Verified guest phone for this specific number that user can claim
                verified_guest = VerifiedGuestPhone.objects.filter(
                    phone_number=normalized_phone_number,
                    is_active=True
                ).first()

                if verified_guest and not verified_guest.is_expired:
                    # User can use this phone if:
                    # a) They've already claimed it (converted_to_user is them), OR
                    # b) It's unclaimed (no one has claimed it yet)
                    if verified_guest.converted_to_user == user or verified_guest.converted_to_user is None:
                        return True

                return False

            # If not checking a specific phone number, check if user has any verified phone number
            else:
                # Check 1: Direct profile verification with phone number (fast path)
                if profile.is_phone_verified and profile.phone_number:
                    return True

                # Check 2: Check if there's any VerifiedGuestPhone record that the user can use
                # (this handles both stale profile cases and cases where profile says not verified but service says verified)
                return VerifiedGuestPhone.objects.filter(
                    is_active=True,
                    expires_at__gt=timezone.now()
                ).filter(
                    Q(converted_to_user=user) | Q(converted_to_user__isnull=True)
                ).exists()
        except UserProfile.DoesNotExist:
            return False

    def get_verification_status(self, phone_number, user=None):
        """
        Get detailed verification status for a phone number.
        Returns dict with status information.
        """
        ownership_type, user_obj, verified_guest = self.check_phone_ownership(phone_number)

        status = {
            'phone_number': phone_number,
            'ownership_type': ownership_type,
            'is_verified': False,
            'can_use_for_checkout': False,
            'message': '',
            'verified_guest': verified_guest,
            'user': user_obj
        }

        if ownership_type in ['registered_user', 'guest_verified']:
            status['is_verified'] = True
            status['can_use_for_checkout'] = True
            status['message'] = "Phone number is verified and ready for use."
        elif ownership_type == 'registered_user_unverified':
            status['is_verified'] = False
            status['can_use_for_checkout'] = False
            status['message'] = "Phone number belongs to an account but is not verified."
        elif ownership_type == 'available':
            status['is_verified'] = False
            status['can_use_for_checkout'] = False
            status['message'] = "Phone number is available for verification."
        elif ownership_type == 'guest_expired':
            status['is_verified'] = False
            status['can_use_for_checkout'] = False
            status['message'] = "Previous guest verification has expired. Please verify again."

        return status

    def _normalize_phone_number(self, phone_number):
        """
        Normalize phone number to standard format.
        """
        if not phone_number:
            return ""

        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, str(phone_number)))

        # Remove leading zeros
        while digits.startswith('0') and len(digits) > 1:
            digits = digits[1:]

        # Remove Nepal country code if present
        if digits.startswith('977') and len(digits) > 3:
            digits = digits[3:]

        return digits

    def mark_guest_phone_as_converted(self, phone_number, user):
        """
        Mark a verified guest phone as converted to a registered user.
        """
        try:
            verified_guest = VerifiedGuestPhone.objects.get(
                phone_number=phone_number,
                is_active=True
            )
            verified_guest.converted_to_user = user
            verified_guest.save()
            return True
        except VerifiedGuestPhone.DoesNotExist:
            return False