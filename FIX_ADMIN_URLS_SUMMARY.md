# FIXED: NoReverseMatch Error in Django Admin

## ISSUE
When accessing `/admin/store/product/`, the following error occurred:
```
NoReverseMatch at /admin/store/product/
Reverse for 'auth_user_changelist' not found. 'auth_user_changelist' is not a valid view function or pattern name.
```

This error also likely affected other admin pages that reference the sidebar navigation.

## ROOT CAUSE
The error occurred because the User and Group models from Django's authentication system were not registered with the custom admin site (`asma_admin`) used by the Asma Store project.

The admin sidebar template (`templates/admin/sidebar.html`) contains links like:
- `{% url 'asma_admin:auth_user_changelist' %}` (Staff & Users)
- `{% url 'asma_admin:accounts_otp_changelist' %}` (OTP)
- `{% url 'asma_admin:accounts_userprofile_changelist' %}` (User Profiles)
- `{% url 'asma_admin:accounts_verifiedguestphone_changelist' %}` (Verified Guest Phones)

When these URL patterns were not found in the custom admin site's URL configuration, Django threw a NoReverseMatch exception.

## SOLUTION
Updated `/d/desktop/virtualenv.worktrees/asma_backend-1/store/admin.py` to:

1. **Import required authentication models and admin classes**:
   ```python
   from django.contrib.auth.models import User, Group
   from django.contrib.auth.admin import UserAdmin, GroupAdmin
   ```

2. **Import additional accounts models**:
   ```python
   from accounts.models import OTP, UserProfile, VerifiedGuestPhone
   ```

3. **Register all missing models with the custom admin site**:
   ```python
   # Register User and Group with the custom admin site
   admin_site.register(User, UserAdmin)
   admin_site.register(Group, GroupAdmin)

   # Register UserProfile and VerifiedGuestPhone with the custom admin site
   admin_site.register(UserProfile)
   admin_site.register(VerifiedGuestPhone)
   ```

## VERIFICATION
After applying this fix:
- The `asma_admin:auth_user_changelist` URL pattern is now available
- The `asma_admin:accounts_userprofile_changelist` URL pattern is now available  
- The `asma_admin:accounts_verifiedguestphone_changelist` URL pattern is now available
- All sidebar navigation links should resolve correctly
- The admin interface should load without NoReverseMatch errors

## FILES MODIFIED
- `store/admin.py` - Added imports and registrations for User, Group, UserProfile, and VerifiedGuestPhone models

## NOTE
This fix assumes that the custom admin site (`asma_admin`) is properly configured in `urls.py` and `admin_site.py`, which was already verified to be working correctly for other models.

The implementation maintains consistency with the existing pattern of registering models with the custom admin site rather than the default Django admin site.