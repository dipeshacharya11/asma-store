# Checkout Phone Verification Fix Summary

## Issue
Registered users were being incorrectly prompted for OTP verification during checkout even when their phone number was already verified. This was caused by incorrect usage of the `is_phone_verified_for_user` method in the store/views.py file.

## Root Cause
Three instances in store/views.py were using `phone_verification_service.is_phone_verified_for_user(request.user)` without specifying a phone number parameter. This method, when called without a phone number, checks if the user has ANY verified phone number rather than checking if a specific phone number is verified for the user.

## Fixes Applied

### 1. GET Request Handling (Lines 249-287)
**Problem**: When loading the checkout form for an authenticated user, the code checked if the user had ANY verified phone number to decide whether to show profile data or send an OTP for verification.

**Solution**: Changed to check if the user's specific profile phone number is verified:
```python
# Before
is_verified = phone_verification_service.is_phone_verified_for_user(request.user)

# After
is_verified = False
try:
    profile = request.user.profile
    if profile.phone_number:
        is_verified = phone_verification_service.is_phone_verified_for_user(
            request.user, phone=profile.phone_number
        )
except UserProfile.DoesNotExist:
    pass
```

### 2. POST Request Handling - Verification Check (Around Line 397)
**Problem**: When processing a checkout submission, the code checked if the user had ANY verified phone number to determine if OTP verification was needed for the phone number they were trying to checkout with.

**Solution**: Changed to check if the specific phone number they're trying to checkout with is verified for them:
```python
# Before
if not phone_verification_service.is_phone_verified_for_user(request.user):
    needs_verification = True

# After
if not phone_verification_service.is_phone_verified_for_user(request.user, phone=normalized_phone):
    needs_verification = True
```

### 3. POST Request Handling - Profile Update After Order (Around Line 498)
**Problem**: After successfully creating an order, the code checked if the user had ANY verified phone number to decide whether to update their profile to show `is_phone_verified = True`.

**Solution**: Changed to check if the user's specific profile phone number is verified:
```python
# Before
if not profile.is_phone_verified and phone_verification_service.is_phone_verified_for_user(request.user):
    profile.is_phone_verified = True
    profile.save(update_fields=['is_phone_verified'])

# After
if not profile.is_phone_verified and profile.phone_number and phone_verification_service.is_phone_verified_for_user(request.user, phone=profile.phone_number):
    profile.is_phone_verified = True
    profile.save(update_fields=['is_phone_verified'])
```

## Impact
These changes ensure that:
- Registered users with verified phone numbers can checkout without being prompted for OTP verification
- The system correctly distinguishes between having ANY verified phone number and having a SPECIFIC phone number verified
- Profile data is only shown in the checkout form when the user's actual profile phone number is verified
- After successful OTP verification for a phone change, the profile is correctly updated only when appropriate

## Verification
The OTPServiceTestCase tests continue to pass, confirming that the core phone verification service functionality remains intact.