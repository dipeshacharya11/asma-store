# Migration Instructions for OTP Status Fields

## Issue
The OTP model has been updated to include a `status` field (replacing the deprecated `is_verified` and `is_used` fields), but the database migration has not been applied, causing an `OperationalError: no such column: accounts_otp.status` when accessing the admin interface.

## Files Modified
1. **accounts/models.py** - Added `status` field with choices, `resend_count`, and `order` ForeignKey
2. **accounts/migrations/0008_add_otp_status_fields.py** - Migration to add the new fields
3. **accounts/utils/otp.py** - Updated to work with status-based logic
4. **accounts/services/otp_service.py** - Updated to work with status-based logic
5. **accounts/views.py** - Fixed syntax error in `resend_otp_view` and updated flow logic
6. **store/admin.py** - Fixed to import OTP from accounts.models and use status field
7. **store/admin_site.py** - Updated to use status-based filtering instead of is_verified
8. **accounts/templates/accounts/guest_verify_success.html** - New template for verification success page
9. **accounts/urls.py** - Added URL pattern for guest verification success

## How to Apply the Migration

### Option 1: Using Django Management Command (Recommended)
Once the bash tool is available again, run:
```bash
python manage.py migrate accounts
```

### Option 2: Manual SQL Execution
If you prefer to run the SQL directly, the migration adds these columns to the accounts_otp table:

```sql
ALTER TABLE accounts_otp ADD COLUMN status varchar(20) NOT NULL DEFAULT 'PENDING';
ALTER TABLE accounts_otp ADD COLUMN resend_count integer NOT NULL DEFAULT 0;
ALTER TABLE accounts_otp ADD COLUMN order_id integer NULL REFERENCES store_order(id) ON DELETE SET NULL;
```

### Option 3: Using the Provided Script
A script has been created at `apply_migration.py` that can be run when the bash tool is available:
```bash
python apply_migration.py
```

## Verification
After applying the migration, verify that:
1. The admin interface loads without errors at `/admin/`
2. The OTP model shows the new fields: status, resend_count, order
3. Existing functionality still works (signup, login, guest checkout, etc.)
4. The guest checkout flow properly shows verification success before proceeding to order confirmation

## Expected Behavior After Migration
- OTP records will have a status field tracking their state (PENDING, SENT, VERIFIED, CONSUMED, etc.)
- The admin interface will show OTP records with their current status instead of the deprecated is_verified/is_used fields
- All OTP flows (signup, login, guest checkout, password reset, change phone) will work correctly with the new status-based system
- Guest checkout will show a verification success page before proceeding to order confirmation