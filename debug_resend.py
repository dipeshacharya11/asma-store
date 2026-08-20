#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'asma_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.services.otp_service import OTPService
from accounts.models import OTP
from unittest.mock import patch
import time

User = get_user_model()

# Create user with unique username
timestamp = int(time.time())
user = User.objects.create_user(username=f'testuser_{timestamp}', password='testpass', email='test@example.com')
print(f"Created user: {user.id}")

# Create OTP service
otp_service = OTPService()

# Mock the SMS service send_otp method
with patch('accounts.services.sms.SparrowSMSService.send_otp') as mock_send_otp:
    mock_send_otp.return_value = (True, 'msg123', {'response_code': 200})

    # Send OTP
    print("Sending first OTP...")
    success, message, otp_record = otp_service.send_otp(user, '9841234567', 'signup')
    print(f"Send OTP result: success={success}, message='{message}'")
    if otp_record:
        print(f"OTP record: id={otp_record.id}, user={otp_record.user_id}, phone={otp_record.phone_number}, purpose={otp_record.purpose}")
        print(f"OTP record created_at: {otp_record.created_at}")

    # Check what's in the database
    otps = OTP.objects.filter(user=user, phone_number='9841234567', purpose='signup')
    print(f"Number of matching OTP records: {otps.count()}")
    for otp in otps:
        print(f"  OTP: id={otp.id}, created_at={otp.created_at}")

    # Try to resend immediately
    print("Trying to resend immediately...")
    success, message, otp_record2 = otp_service.resend_otp(user, '9841234567', 'signup')
    print(f"Resend OTP result: success={success}, message='{message}'")
    if otp_record2:
        print(f"OTP record: id={otp_record2.id}, user={otp_record2.user_id}, phone={otp_record2.phone_number}, purpose={otp_record2.purpose}")

    # Check what the resend_otp method is seeing
    print("Checking what resend_otp sees:")
    last_otp = OTP.objects.filter(
        user=user,
        phone_number='9841234567',
        purpose='signup'
    ).order_by('-created_at').first()
    if last_otp:
        from django.utils import timezone
        time_since_last = timezone.now() - last_otp.created_at
        print(f"Last OTP: id={last_otp.id}, created_at={last_otp.created_at}")
        print(f"Time since last: {time_since_last.total_seconds()} seconds")
        print(f"Should cooldown: {time_since_last.total_seconds() < 30}")
    else:
        print("No OTP found!")