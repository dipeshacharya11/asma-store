import logging
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from accounts.services.sms import SparrowSMSService
from accounts.utils.otp import generate_otp, hash_otp, create_otp_record, verify_and_use_otp, get_otp_record_by_token
from accounts.models import OTP
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

class OTPService:
    """
    Service for handling OTP generation, sending, and verification.
    """
    def __init__(self):
        self.sms_service = SparrowSMSService()

    def _is_rate_limited(self, phone_number):
        """
        Check if the phone number has exceeded the OTP request rate limit.
        Returns True if rate limited, False otherwise.
        """
        key = f"otp_rate_limit_{phone_number}"
        count = cache.get(key, 0)
        if count >= getattr(settings, 'OTP_RATE_LIMIT_COUNT', 3):
            return True
        return False

    def _increment_rate_limit(self, phone_number):
        """
        Increment the rate limit counter for the phone number.
        """
        key = f"otp_rate_limit_{phone_number}"
        timeout = getattr(settings, 'OTP_RATE_LIMIT_WINDOW', 600)  # seconds
        count = cache.get(key, 0)
        cache.set(key, count + 1, timeout)

    def send_otp(self, user, phone_number, purpose):
        """
        Generate and send OTP to the user's phone number for a specific purpose.
        Returns tuple (success, message, otp_record)
        """
        # Rate limiting
        if self._is_rate_limited(phone_number):
            wait_time = getattr(settings, 'OTP_RATE_LIMIT_WINDOW', 600)
            return False, f"Too many OTP requests. Please wait {wait_time//60} minutes before trying again.", None

        # Generate OTP
        otp = generate_otp()
        # Create OTP record (this also invalidates old OTPs for the same purpose)
        otp_record, otp = create_otp_record(user, phone_number, purpose)
        # Update status to SENT
        otp_record.status = 'SENT'
        otp_record.save(update_fields=['status'])
        # Send OTP via SMS
        success, message_id, raw_response = self.sms_service.send_otp(phone_number, otp)
        if success:
            # Increment rate limit counter on success
            self._increment_rate_limit(phone_number)
            # Increment resend count
            otp_record.resend_count += 1
            otp_record.save(update_fields=['resend_count'])
            logger.info(f"OTP sent to {phone_number} for user {user.username if user else 'None'} (purpose: {purpose}). Message ID: {message_id}")
            return True, "OTP sent successfully.", otp_record
        else:
            logger.error(f"Failed to send OTP to {phone_number}: {raw_response}")
            # Delete the OTP record if SMS failed
            otp_record.delete()
            return False, "Failed to send OTP. Please try again.", None

    def verify_otp(self, phone_number, otp, purpose):
        """
        Verify the OTP for the given phone number and purpose.
        Returns tuple (success, message, otp_record)
        """
        return verify_and_use_otp(phone_number, otp, purpose)

    def resend_otp(self, user, phone_number, purpose):
        """
        Resend OTP to the user's phone number for a specific purpose.
        Returns tuple (success, message, otp_record)
        """
        # Check resend cooldown (30 seconds)
        last_otp = OTP.objects.filter(
            user=user,
            phone_number=phone_number,
            purpose=purpose
        ).order_by('-created_at').first()
        if last_otp:
            time_since_last = timezone.now() - last_otp.created_at
            if time_since_last.total_seconds() < 30:
                return False, f"Please wait {30 - int(time_since_last.total_seconds())} seconds before resending.", None

        return self.send_otp(user, phone_number, purpose)

    def invalidate_otp(self, phone_number, purpose):
        """
        Invalidate any pending OTPs for the given phone number and purpose.
        """
        OTP.objects.filter(
            phone_number=phone_number,
            purpose=purpose,
            status='SENT'
        ).update(status='CONSUMED')

    def cleanup_expired(self):
        """Delete expired OTP records"""
        OTP.cleanup_expired()