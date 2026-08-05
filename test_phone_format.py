#!/usr/bin/env python3
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'asma_backend.settings')
sys.path.append('/d/desktop/virtualenv.worktrees/asma_backend-1')
django.setup()

from accounts.services.sms import SparrowSMSService

def test_phone_formatting():
    """Test the phone number formatting logic"""
    sms_service = SparrowSMSService()

    # Test cases
    test_cases = [
        "+9779817052570",  # From .env
        "9779817052570",   # Without +
        "09817052570",     # With leading 0
        "009779817052570", # With 00
        "9817052570",      # Already formatted
        "9812345678",      # Another valid number
    ]

    print("Testing phone number formatting:")
    for phone in test_cases:
        formatted = sms_service._format_phone_number(phone)
        print(f"  Input:  {phone}")
        print(f"  Output: {formatted}")
        # Check if it's a valid Nepalese number (starts with 97 or 98, 10 digits)
        import re
        is_valid = bool(re.match(r'^(97|98)\d{8}$', formatted))
        print(f"  Valid:  {is_valid}")
        print()

if __name__ == "__main__":
    test_phone_formatting()