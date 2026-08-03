from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime

from ..models import OTP
from ..utils.otp import generate_otp, hash_otp, verify_otp, create_otp_record, verify_and_use_otp

User = get_user_model()

class OTPUtilsTestCase(TestCase):
    def test_generate_otp(self):
        otp = generate_otp(6)
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())

    def test_hash_and_verify(self):
        otp = '123456'
        hashed = hash_otp(otp)
        self.assertTrue(verify_otp(otp, hashed))
        self.assertFalse(verify_otp('654321', hashed))

class OTPModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass')
        self.otp = OTP.objects.create(
            user=self.user,
            phone_number='+1234567890',
            otp_hash='dummyhash',
            verification_token='sometoken',
            expires_at=timezone.now() + datetime.timedelta(minutes=5)
        )

    def test_is_expired(self):
        self.assertFalse(self.otp.is_expired())
        # Set expiry in the past
        self.otp.expires_at = timezone.now() - datetime.timedelta(seconds=1)
        self.otp.save()
        self.assertTrue(self.otp.is_expired())

    def test_is_valid_attempt(self):
        self.assertTrue(self.otp.is_valid_attempt())
        self.otp.attempts = 5
        self.otp.max_attempts = 5
        self.assertFalse(self.otp.is_valid_attempt())

class OTPCreateTestCase(TestCase):
    def test_create_otp_record(self):
        user = User.objects.create_user(username='testuser2', password='pass')
        otp_record, otp = create_otp_record(user, '+1234567890')
        self.assertEqual(otp_record.user, user)
        self.assertEqual(otp_record.phone_number, '+1234567890')
        self.assertIsNotNone(otp_record.verification_token)
        self.assertTrue(len(otp) == 6)
        # Ensure OTP is not stored plain
        self.assertNotEqual(otp_record.otp_hash, otp)
        # Verify the OTP matches
        self.assertTrue(verify_otp(otp, otp_record.otp_hash))

    def test_verify_and_use_otp(self):
        user = User.objects.create_user(username='testuser3', password='pass')
        otp_record, otp = create_otp_record(user, '+1234567890')
        success, msg, record = verify_and_use_otp('+1234567890', otp)
        self.assertTrue(success)
        self.assertEqual(msg, 'OTP verified successfully.')
        self.assertTrue(record.is_verified)
        self.assertTrue(record.is_used)
        # Wrong OTP
        success2, msg2, record2 = verify_and_use_otp('+1234567890', '000000')
        self.assertFalse(success2)
        self.assertIn('Invalid OTP', msg2)
        # Ensure attempts increased
        self.assertEqual(record2.attempts, 1)