#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'asma_backend.settings')
django.setup()

# Try to check the OTP model
try:
    from accounts.models import OTP
    # Get the model's fields
    fields = [f.name for f in OTP._meta.get_fields()]
    print("OTP model fields:")
    for field in sorted(fields):
        print(f"  {field}")

    # Check specifically for verified_at
    if 'verified_at' in fields:
        print("\n✓ verified_at field exists in OTP model")
    else:
        print("\n✗ verified_at field NOT found in OTP model")

except Exception as e:
    print(f"Error accessing OTP model: {e}")
    import traceback
    traceback.print_exc()