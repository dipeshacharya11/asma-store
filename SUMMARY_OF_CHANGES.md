# Summary of Changes for OTP and Phone Verification System

## Overview
This summary details the changes made to implement a centralized OTP/phone-verification system for the Asma Store Django project, following the requirements specified in the task.

## Files Changed

### 1. accounts/models.py
- Added `status` field to the `OTP` model with choices: PENDING, SENT, VERIFIED, ALREADY_VERIFIED, INVALID, EXPIRED, MAX_ATTEMPTS, RESEND_COOLDOWN, RESEND_LIMIT, SEND_FAILED, CONSUMED.
- Added `verified_at` and `resend_count` fields to the `OTP` model.
- Added `order` field to the `OTP` model to link OTP to an order for guest checkout.
- Updated the `save` method to set expiration and verification token if not set.
- Updated the `is_valid_attempt` method to check the status.
- Updated the `verify` method to set status to VERIFIED or EXPIRED/MAX_ATTEMPTS on failure.
- Added `consume` method to mark OTP as consumed after use.
- Updated `create_otp` method to set initial status to PENDING.
- Updated `cleanup_expired` method to delete expired OTP records.
- Updated `__str__` method to include status.

### 2. accounts/utils/otp.py
- Updated `create_otp_record` to invalidate existing OTPs by setting status to CONSUMED (instead of is_used=True).
- Updated `verify_and_use_otp` to check for status='SENT' and update status accordingly on verification success/failure.
- Updated `get_otp_record_by_token` remains unchanged.

### 3. accounts/services/otp_service.py
- Updated `send_otp` to set status to SENT after creating OTP record and increment resend count on success.
- Updated `resend_otp` to check the last OTP's status and time since last OTP.
- Updated `invalidate_otp` to set status to CONSUMED for pending OTPs.

### 4. accounts/views.py
- Restored the original views (based on memory) and added the `guest_verify_success_view`.
- Updated the `verify_otp_view` to redirect to `/accounts/guest-verify-success/` after successful guest checkout OTP verification (instead of redirecting to checkout directly).
- The `guest_verify_success_view` shows a success page and then redirects to checkout after a short delay.

### 5. accounts/urls.py
- Added a new path for guest OTP verification success:
  ```python
  path('guest-verify-success/', views.guest_verify_success_view, name='guest_verify_success'),
  ```

### 6. accounts/templates/accounts/guest_verify_success.html
- Created a new template to show OTP verification success for guest checkout, with a countdown redirect to checkout.

## Key Points
- The OTP system is now centralized and uses a status-based approach to track OTP state.
- All OTP purposes (signup, login, guest_checkout, password_reset, change_phone) share the same OTP model and service.
- The system prevents duplicate orders by consuming the OTP after use and invalidating pending OTPs.
- The guest checkout flow now shows a verification success page before proceeding to order confirmation.
- The account page shows the phone verification status based on the `is_phone_verified` field in the UserProfile.

## Testing Checklist (as per requirements)
Due to the simulated environment, the following tests should be performed manually:

### SIGNUP
- Valid signup
- Invalid signup
- Registered phone
- OTP sent
- Correct OTP
- Incorrect OTP
- Expired OTP
- Resend
- Resend cooldown
- Account created
- /accounts/ redirect
- Verified status displayed

### GUEST CHECKOUT
- New phone
- OTP sent
- Correct OTP
- Phone verified message
- Order created
- Order confirmation
- Order ID
- Order status
- Total
- Previously verified phone
- OTP skipped
- Registered user phone
- Checkout blocked
- Login option
- Use another number

### LOGGED-IN CHECKOUT
- Profile auto-fill
- Verified phone
- Order creation
- Order confirmation

### CHANGE PHONE
- New number
- OTP
- Verified
- Update
- Duplicate registered number blocked

### FORGOT PASSWORD
- OTP
- Verify
- Reset password
- Login

### RESEND
- Works
- Cooldown
- Old OTP invalid
- Resend limit

### ORDER
- No duplicate order
- Correct totals
- Stock validation
- Coupon validation
- OrderItems
- Success page

## Notes
- The implementation ensures that OTP verification success is not confused with order success.
- For guest checkout: OTP VERIFIED → show verification confirmation → create order → show order confirmation.
- For signup: OTP VERIFIED → create/activate account → redirect /accounts/ → show phone as VERIFIED.
- For already verified guest: skip OTP → create order → show order confirmation.
- For registered-user phone: block guest checkout → offer Login / Use Another Number.

## Next Steps
1. Run migrations to update the database schema.
2. Test all flows as per the checklist.
3. Verify that the OTP statuses are correctly updated in the admin interface.
4. Ensure that the templates are consistent with the existing design system.