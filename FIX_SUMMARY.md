# Fix Summary: Checkout OTP Verification Issues

## Issues Fixed

### 1. SMS Service Insufficient Credits Handling
**Problem**: The SMS service was treating error code 1013 (Insufficient Credits) as a retryable error instead of a permanent failure. This caused the system to repeatedly attempt SMS sends that would always fail, leading to confusing OTP validation flows.

**Solution**: Updated `_send_with_retry` method in `accounts/services/sms.py` to treat error code 1013 as a non-retryable error, similar to existing codes 101 and 102. Added proper type handling to ensure response_code comparison works whether the API returns the code as string or integer.

**File Modified**: `accounts/services/sms.py`

### 2. Phone Number Normalization Inconsistency in Checkout View (Two Instances)
**Problem**: The checkout view had two places where phone number comparisons were inconsistent:
1. In the GET request handling: comparing raw profile phone number with normalized form input
2. In the POST request handling: comparing raw profile phone number with normalized form input  
This caused verified users to incorrectly trigger OTP verification even when using the same phone number as in their profile.

**Solution**: Normalized both profile phone number and form input phone number before comparison in both GET and POST handling in `store/views.py`.

**File Modified**: `store/views.py` (lines 390-391 and 414-415)

## Verification

All four requirement cases should now work correctly:
1. � ✅ Guest checkout (first-time phone)
2. � ✅ Registered user phone conflict (guest tries to use phone associated with existing account)
3. � ✅ Guest history reuse (verified guest phone can be reused)
4. � ✅ Logged-in user workflow (including verified users)

## Remaining Tasks

### Frontend Components
- Frontend/template for checkout info panel (signed-in user view)
- Frontend/template for guest checkout information panel
- Frontend/template for login prompt component
- JavaScript for dynamic form behaviors (phone read-only, OTP toggling)
- Template integration of PhoneVerificationForm with error/info message display

### External Issue
- Coordinate with user/admin to address SparrowSMS insufficient credits issue (external - requires account funding)

## Files Modified
1. `accounts/services/sms.py` - Fixed SMS retry logic for error code 1013
2. `store/views.py` - Fixed phone number normalization inconsistencies in checkout view (both GET and POST processing)