import secrets
import hashlib
import hmac
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from accounts.models import OTP
import logging

logger = logging.getLogger(__name__)

# PBKDF2 iterations (can be configured in settings)
PBKDF2_ITERATIONS = getattr(settings, 'PBKDF2_ITERATIONS', 100000)
HASH_NAME = 'sha256'
SALT_LENGTH = 16  # 16 bytes = 128 bits
KEY_LENGTH = 32   # 32 bytes = 256 bits (for SHA256)

# Argon2 settings
ARGON2_ENABLED = getattr(settings, 'ARGON2_ENABLED', False)
if ARGON2_ENABLED:
    try:
        from argon2 import PasswordHasher
        argon2_hasher = PasswordHasher()
    except ImportError:
        ARGON2_ENABLED = False
        logger.warning("ARGON2_ENABLED is True but argon2-cffi is not installed. Falling back to PBKDF2.")

def generate_otp(length=6):
    """
    Generate a numeric OTP of specified length.
    """
    return ''.join(secrets.choice('0123456789') for _ in range(length))

def hash_otp(otp):
    """
    Hash the OTP using Argon2 if available, else PBKDF2 with a random salt.
    Returns a string that includes the method and the hash.
    For Argon2: returns the hash string directly from argon2.
    For PBKDF2: returns a string in the format: pbkdf2_sha256$salt$hash
    """
    if ARGON2_ENABLED:
        return argon2_hasher.hash(otp)
    else:
        # Generate a random salt
        salt = secrets.token_bytes(SALT_LENGTH)
        # Derive the key using PBKDF2
        dk = hashlib.pbkdf2_hmac(
            HASH_NAME,
            otp.encode('utf-8'),
            salt,
            PBKDF2_ITERATIONS,
            dklen=KEY_LENGTH
        )
        # Return salt and hex digest in a format that includes the algorithm
        return f"pbkdf2_sha256${salt.hex()}${dk.hex()}"

def verify_otp(otp, hashed):
    """
    Verify the OTP against the hash.
    Returns True if valid, False otherwise.
    Uses constant-time comparison to avoid timing attacks.
    """
    if ARGON2_ENABLED:
        try:
            argon2_hasher.verify(hashed, otp)
            return True
        except Exception:
            return False
    else:
        # PBKDF2 verification
        if not hashed.startswith('pbkdf2_sha256$'):
            return False
        try:
            _, salt_hex, hash_hex = hashed.split('$', 2)
            salt = bytes.fromhex(salt_hex)
            # Compute the hash of the provided OTP with the same salt
            dk = hashlib.pbkdf2_hmac(
                HASH_NAME,
                otp.encode('utf-8'),
                salt,
                PBKDF2_ITERATIONS,
                dklen=KEY_LENGTH
            )
            # Compare the derived key with the stored hash using constant-time comparison
            return hmac.compare_digest(dk.hex(), hash_hex)
        except (ValueError, AttributeError):
            # If the hash string is malformed, return False
            return False

def create_otp_record(user, phone_number, purpose):
    """
    Create a new OTP record for the user, phone_number, and purpose.
    Invalidates any existing unverified OTPs for the same phone number and purpose.
    """
    # Invalidate any existing unverified OTPs for this phone number and purpose
    OTP.objects.filter(
        phone_number=phone_number,
        purpose=purpose,
        is_verified=False,
        is_used=False
    ).update(is_used=True)  # Mark as used to prevent reuse

    # Generate OTP
    otp = generate_otp()
    otp_hash = hash_otp(otp)
    verification_token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

    otp_record = OTP.objects.create(
        user=user,
        phone_number=phone_number,
        purpose=purpose,
        otp_hash=otp_hash,
        verification_token=verification_token,
        expires_at=expires_at,
        max_attempts=settings.OTP_MAX_ATTEMPTS
    )

    logger.info(f"Generated OTP for {phone_number} (purpose: {purpose}, user: {user.username if user else 'None'})")
    return otp_record, otp

def verify_and_use_otp(phone_number, otp, purpose):
    """
    Validate the OTP and mark it as used if valid.
    Returns tuple (success, message, otp_record)
    """
    # Find the most recent unused OTP for this phone number and purpose
    try:
        otp_record = OTP.objects.filter(
            phone_number=phone_number,
            purpose=purpose,
            is_verified=False,
            is_used=False
        ).order_by('-created_at').first()
    except OTP.DoesNotExist:
        return False, "No pending OTP found for this number and purpose.", None

    if not otp_record:
        return False, "No pending OTP found for this number and purpose.", None

    if not otp_record.is_valid_attempt():
        if otp_record.is_expired():
            return False, "OTP has expired.", otp_record
        else:
            return False, "Too many attempts. Please request a new OTP.", otp_record

    # Verify the OTP
    if verify_otp(otp, otp_record.otp_hash):
        # Mark as verified and used
        otp_record.is_verified = True
        otp_record.is_used = True
        otp_record.save(update_fields=['is_verified', 'is_used'])
        # Also mark the user's phone as verified in their profile if user exists
        if otp_record.user:
            try:
                profile = otp_record.user.profile
                profile.is_phone_verified = True
                profile.save(update_fields=['is_phone_verified'])
            except Exception as e:
                logger.error(f"Failed to update phone verification status for user {otp_record.user.username}: {e}")
        return True, "OTP verified successfully.", otp_record
    else:
        # Increment attempts
        otp_record.attempts += 1
        otp_record.save(update_fields=['attempts'])
        remaining_attempts = otp_record.max_attempts - otp_record.attempts
        if remaining_attempts <= 0:
            return False, "Maximum attempts exceeded. Please request a new OTP.", otp_record
        else:
            return False, f"Invalid OTP. {remaining_attempts} attempts remaining.", otp_record

def get_otp_record_by_token(verification_token):
    """
    Retrieve an OTP record by its verification token.
    """
    try:
        return OTP.objects.get(verification_token=verification_token)
    except OTP.DoesNotExist:
        return None