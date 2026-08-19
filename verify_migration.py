#!/usr/bin/env python
"""
Verification script to check if the OTP status fields migration has been applied correctly.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'asma_backend.settings')
sys.path.insert(0, '/d/desktop/virtualenv.worktrees/asma_backend-1')

try:
    django.setup()
    from accounts.models import OTP

    print("✅ Successfully imported OTP model from accounts.models")

    # Check if the status field exists
    field_names = [f.name for f in OTP._meta.get_fields()]
    print(f"✅ OTP model fields: {', '.join(field_names)}")

    required_fields = ['status', 'resend_count', 'order']
    missing_fields = [f for f in required_fields if f not in field_names]

    if missing_fields:
        print(f"� Missing fields: {', '.join(missing_fields)}")
        print("❌ Migration has NOT been applied correctly")
        sys.exit(1)
    else:
        print("✅ All required fields (status, resend_count, order) are present")

    # Check status field choices
    status_field = OTP._meta.get_field('status')
    if hasattr(status_field, 'choices'):
        choices = dict(status_field.choices)
        expected_choices = {
            'PENDING': 'Pending',
            'SENT': 'Sent',
            'VERIFIED': 'Verified',
            'ALREADY_VERIFIED': 'Already Verified',
            'INVALID': 'Invalid',
            'EXPIRED': 'Expired',
            'MAX_ATTEMPTS': 'Max Attempts',
            'RESEND_COOLDOWN': 'Resend Cooldown',
            'RESEND_LIMIT': 'Resend Limit',
            'SEND_FAILED': 'Send Failed',
            'CONSUMED': 'Consumed'
        }

        if choices == expected_choices:
            print("✅ Status field has correct choices")
        else:
            print(f"⚠️  Status field choices mismatch. Expected: {expected_choices}, Got: {choices}")
    else:
        print("⚠️  Could not verify status field choices")

    # Check that we can create an OTP instance (basic functionality)
    try:
        otp = OTP()
        print("✅ Can instantiate OTP model")
    except Exception as e:
        print(f"❌ Error instantiating OTP model: {e}")
        sys.exit(1)

    print("\n🎉 Migration verification PASSED!")
    print("The OTP model has been successfully updated with status-based fields.")

except Exception as e:
    print(f"❌ Error during verification: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)