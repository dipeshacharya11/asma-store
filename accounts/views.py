from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views.decorators.http import require_POST
from accounts.services.otp_service import OTPService
from accounts.forms import OTPVerificationForm, SignUpForm
from accounts.models import UserProfile
import logging

logger = logging.getLogger(__name__)

def signup_view(request):
    """
    Handle user signup via form submission.
    GET: Display empty signup form.
    POST: Validate form, create user and profile (inactive), send OTP for phone verification,
          then redirect to OTP verification page.
    """
    if request.method == 'GET':
        form = SignUpForm()
        return render(request, 'accounts/signup.html', {'form': form})

    elif request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            # Save user and profile (user will be active by default from form)
            user = form.save(commit=True)
            # Make user inactive until phone verification
            user.is_active = False
            user.save(update_fields=['is_active'])

            # Send OTP for phone verification
            otp_service = OTPService()
            phone_number = form.cleaned_data['phone_number']
            success, message, otp_record = otp_service.send_otp(user, phone_number, 'signup')
            if success:
                # Store user id and phone number in session for OTP verification
                request.session['pre_verified_user_id'] = user.id
                request.session['phone_number'] = phone_number
                request.session['otp_purpose'] = 'signup'
                messages.info(request, "Please verify your phone number to complete signup.")
                return redirect('accounts:verify_otp')
            else:
                # OTP sending failed: delete the user (and profile) to avoid duplicate phone/email
                user.delete()
                messages.error(request, message)
                # Show empty form for user to try again
                form = SignUpForm()
                return render(request, 'accounts/signup.html', {'form': form})
        else:
            # Form validation errors
            messages.error(request, "Please correct the errors below.")
            return render(request, 'accounts/signup.html', {'form': form})

    else:
        # Only GET and POST allowed
        return redirect('accounts:signup')

def login_view(request):
    """
    Handle login via username/email and password.
    If user's phone is not verified, send OTP for verification before logging in.
    GET: Display login form.
    POST: Authenticate with username/email and password, then verify phone if needed.
    """
    if request.method == 'GET':
        return render(request, 'accounts/login.html')

    elif request.method == 'POST':
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        if not username_or_email or not password:
            messages.error(request, "Username/email and password are required.")
            return render(request, 'accounts/login.html')

        # Authenticate user
        user = authenticate(request, username=username_or_email, password=password)
        if user is None:
            # Try authenticating with email if username field contains @
            if '@' in username_or_email:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user_obj = User.objects.get(email=username_or_email)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass

        if user is None:
            messages.error(request, "Invalid username/email or password.")
            return render(request, 'accounts/login.html')

        # Check if user's phone is verified
        try:
            profile = user.profile
            if not profile.is_phone_verified:
                phone_number = profile.phone_number
                if phone_number:
                    # Phone exists but not verified, send OTP for login purpose
                    otp_service = OTPService()
                    success, message, otp_record = otp_service.send_otp(user, phone_number, 'login')
                    if success:
                        # Store user id and phone number in session for verification step
                        request.session['pre_verified_user_id'] = user.id
                        request.session['phone_number'] = phone_number
                        request.session['otp_purpose'] = 'login'
                        messages.info(request, "Please verify your phone number to complete login.")
                        return redirect('accounts:verify_otp')
                    else:
                        messages.error(request, message)
                        return render(request, 'accounts/login.html')
                else:
                    # No phone number, prompt user to add one
                    request.session['pre_login_user_id'] = user.id
                    request.session['pre_login_username'] = user.username
                    messages.info(request, "Please add a phone number to continue with login.")
                    return redirect('accounts:add_phone_for_login')
            else:
                # Phone is verified, log the user in
                login(request, user)
                messages.success(request, "You have successfully logged in.")
                return redirect('store:account')
        except Exception as e:
            # If profile doesn't exist, create it? but for now, treat as unverified
            messages.error(request, "Please complete your profile including phone number.")
            return redirect('accounts:login')

    else:
        return redirect('accounts:login')

def logout_view(request):
    """
    Logs out the user and redirects to the homepage.
    """
    logout(request)
    return redirect('store:home')

def verify_otp_view(request):
    """
    Verify OTP for various purposes: signup, login, guest_checkout, password_reset, change_phone.
    """
    if request.method == 'GET':
        # Display the OTP verification form
        phone_number = request.session.get('phone_number', '')
        purpose = request.session.get('otp_purpose', '')
        form = OTPVerificationForm()
        context = {
            'phone_number': phone_number,
            'purpose': purpose,
            'form': form,
        }
        return render(request, 'accounts/verify_otp.html', context)

    elif request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        phone_number = request.session.get('phone_number')
        purpose = request.session.get('otp_purpose')
        user_id = request.session.get('pre_verified_user_id')

        if not phone_number or not purpose or not form.is_valid():
            messages.error(request, "Invalid session data. Please try again.")
            return redirect('accounts:login')

        otp = form.cleaned_data['otp']

        # Initialize OTP service
        otp_service = OTPService()
        success, message, otp_record = otp_service.verify_otp(phone_number, otp, purpose)

        if success:
            # Clear OTP-related session data
            request.session.pop('pre_verified_user_id', None)
            request.session.pop('phone_number', None)
            request.session.pop('otp_purpose', None)

            if purpose == 'guest_checkout':
                # Mark guest phone as verified and store in session for checkout
                request.session['guest_phone_verified'] = True
                request.session['guest_phone'] = phone_number
                request.session['guest_name'] = request.session.get('guest_name')
                # Retrieve guest data from session and store in checkout session for pre-filling the form
                guest_name = request.session.get('guest_name', '')
                guest_email = request.session.get('guest_email', '')
                guest_address = request.session.get('guest_address', '')
                guest_city = request.session.get('guest_city', '')
                request.session['checkout_phone'] = phone_number
                request.session['checkout_full_name'] = guest_name
                request.session['checkout_email'] = guest_email
                request.session['checkout_address'] = guest_address
                request.session['checkout_city'] = guest_city
                # Clear session
                request.session.pop('pre_verified_user_id', None)
                request.session.pop('guest_name', None)
                request.session.pop('guest_email', None)
                request.session.pop('guest_address', None)
                request.session.pop('guest_city', None)
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': 'Phone verified! You can now complete your order.', 'redirect_url': '/checkout/'})
                messages.success(request, "Phone number verified. You can now complete your order.")
                return redirect('store:checkout')

            elif purpose == 'login':
                # User login purpose: mark phone as verified and log in the user
                if user_id:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    try:
                        user = User.objects.get(id=user_id)
                        # Update phone number and mark as verified
                        phone_number = request.session.get('phone_number')
                        profile = user.profile
                        if phone_number:
                            profile.phone_number = phone_number
                        profile.is_phone_verified = True
                        profile.save()
                        login(request, user)
                        messages.success(request, "You have successfully logged in.")
                        # Check if we have a next URL to redirect to
                        next_url = request.session.pop('otp_next_url', None)
                        if next_url:
                            return redirect(next_url)
                        else:
                            return redirect('store:account')
                    except User.DoesNotExist:
                        pass
                messages.error(request, "User not found.")
                return redirect('accounts:login')

            elif purpose == 'signup':
                # Signup purpose: activate the user and log them in
                if user_id:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    try:
                        user = User.objects.get(id=user_id)
                        user.is_active = True
                        # Mark phone as verified
                        profile = user.profile
                        profile.is_phone_verified = True
                        profile.save(update_fields=['is_phone_verified'])
                        user.save()
                        login(request, user)
                        messages.success(request, "Your account has been created and verified.")
                        return redirect('store:account')
                    except User.DoesNotExist:
                        pass
                messages.error(request, "User not found.")
                return redirect('accounts:signup')

            elif purpose == 'password_reset':
                # Password reset purpose: redirect to set new password page
                # We expect the user_id to be in the session from the password reset request
                if user_id:
                    # Store the user_id in session for the password set view
                    request.session['reset_user_id'] = user_id
                    return redirect('accounts:password_reset_set_password')
                messages.error(request, "Invalid session for password reset.")
                return redirect('accounts:password_reset_request')

            elif purpose == 'change_phone':
                # Change phone purpose: update the user's phone number in the profile
                if user_id:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    try:
                        user = User.objects.get(id=user_id)
                        profile = user.profile
                        profile.phone_number = phone_number
                        profile.is_phone_verified = True
                        profile.save()
                        messages.success(request, "Your phone number has been updated and verified.")
                        return redirect('store:account')
                    except User.DoesNotExist:
                        pass
                messages.error(request, "User not found.")
                return redirect('accounts:change_phone')

            else:
                messages.error(request, "Unknown purpose.")
                return redirect('accounts:login')

        else:
            # OTP verification failed
            messages.error(request, message)
            return render(request, 'accounts/verify_otp.html', {
                'phone_number': phone_number,
                'purpose': purpose,
                'form': form,
            })

    else:
        return redirect('accounts:login')

def resend_otp_view(request):
    """
    Stub for resend OTP view - to be implemented properly.
    """
    if request.method == 'POST':
        # In a real implementation, we would resend the OTP
        messages.success(request, "OTP resent successfully.")
        return redirect('accounts:verify_otp')
    return redirect('accounts:login')

def guest_checkout_otp_request_view(request):
    """
    Stub for guest checkout OTP request view - to be implemented properly.
    """
    if request.method == 'POST':
        phone_number = request.POST.get('phone')
        # In a real implementation, we would send OTP and store guest name in session
        request.session['guest_name'] = request.POST.get('full_name', '')
        request.session['guest_phone'] = phone_number
        request.session['otp_purpose'] = 'guest_checkout'
        messages.success(request, "OTP sent to your phone. Please verify to continue.")
        return redirect('accounts:verify_otp')
    return render(request, 'accounts/guest_checkout_otp_request.html')

def change_phone_view(request):
    """
    Handle changing user's phone number
    GET: Display change phone form
    POST: Validate form, send OTP for verification, redirect to OTP verification
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    # Import ChangePhoneForm locally to avoid potential import issues
    from accounts.forms import ChangePhoneForm

    if request.method == 'GET':
        form = ChangePhoneForm()
        return render(request, 'accounts/change_phone.html', {'form': form})

    elif request.method == 'POST':
        form = ChangePhoneForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']

            # Check if phone number already exists for another user
            from accounts.models import UserProfile
            if UserProfile.objects.filter(phone_number=phone_number).exclude(user=request.user).exists():
                form.add_error('phone_number', 'This phone number is already registered.')
                return render(request, 'accounts/change_phone.html', {'form': form})

            # Send OTP for verification
            otp_service = OTPService()
            success, message, otp_record = otp_service.send_otp(request.user, phone_number, 'change_phone')

            if success:
                # Store phone number in session for OTP verification
                request.session['pre_verified_user_id'] = request.user.id
                request.session['phone_number'] = phone_number
                request.session['otp_purpose'] = 'change_phone'
                messages.info(request, "Please verify your new phone number.")
                return redirect('accounts:verify_otp')
            else:
                messages.error(request, message)
                return render(request, 'accounts/change_phone.html', {'form': form})
        else:
            return render(request, 'accounts/change_phone.html', {'form': form})

    else:
        return redirect('accounts:login')


def add_phone_for_login(request):
    """
    Handle adding phone number for login when user has no phone number
    GET: Display phone number entry form
    POST: Validate phone number, send OTP for verification, redirect to OTP verification
    """
    # Check if we have a pre-login user in session
    pre_login_user_id = request.session.get('pre_login_user_id')
    if not pre_login_user_id:
        messages.error(request, "Login session expired. Please try logging in again.")
        return redirect('accounts:login')

    # Import ChangePhoneForm locally to avoid potential import issues
    from accounts.forms import ChangePhoneForm

    if request.method == 'GET':
        form = ChangePhoneForm()  # Reuse the same form
        return render(request, 'accounts/add_phone_for_login.html', {'form': form})

    elif request.method == 'POST':
        form = ChangePhoneForm(request.POST)
        if form.is_valid():
            phone_number = form.cleaned_data['phone_number']

            # Check if phone number already exists for another user
            from accounts.models import UserProfile
            if UserProfile.objects.filter(phone_number=phone_number).exists():
                form.add_error('phone_number', 'This phone number is already registered.')
                return render(request, 'accounts/add_phone_for_login.html', {'form': form})

            # Get the user from session
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(id=pre_login_user_id)
            except User.DoesNotExist:
                messages.error(request, "User not found. Please try logging in again.")
                return redirect('accounts:login')

            # Send OTP for verification
            otp_service = OTPService()
            success, message, otp_record = otp_service.send_otp(user, phone_number, 'login')

            if success:
                # Store user id and phone number in session for OTP verification
                request.session['pre_verified_user_id'] = user.id
                request.session['phone_number'] = phone_number
                request.session['otp_purpose'] = 'login'
                # Clean up pre-login session data
                request.session.pop('pre_login_user_id', None)
                request.session.pop('pre_login_username', None)
                messages.info(request, "Please verify your phone number to complete login.")
                return redirect('accounts:verify_otp')
            else:
                messages.error(request, message)
                return render(request, 'accounts/add_phone_for_login.html', {'form': form})
        else:
            return render(request, 'accounts/add_phone_for_login.html', {'form': form})

    else:
        return redirect('accounts:login')


def send_otp_for_login_view(request):
    """
    Handle sending OTP for login via phone number.
    GET: Display phone number entry form
    POST: Validate phone number, find user, send OTP for login, redirect to OTP verification
    """
    if request.method == 'GET':
        return render(request, 'accounts/send_otp_for_login.html')

    elif request.method == 'POST':
        phone_number = request.POST.get('phone_number', '').strip()
        if not phone_number:
            messages.error(request, "Please enter a phone number.")
            return render(request, 'accounts/send_otp_for_login.html')

        # Normalize the phone number for lookup
        normalized_phone = ''.join(filter(str.isdigit, phone_number))
        # Remove leading zeros
        while normalized_phone.startswith('0') and len(normalized_phone) > 1:
            normalized_phone = normalized_phone[1:]
        # Remove Nepal country code if present
        if normalized_phone.startswith('977') and len(normalized_phone) > 3:
            normalized_phone = normalized_phone[3:]

        # Now normalized_phone should be 10 digits starting with 97 or 98
        try:
            # Look for user by phone number in profile
            profile = UserProfile.objects.get(phone_number=normalized_phone)
            user = profile.user
        except UserProfile.DoesNotExist:
            # Do not reveal that the phone number is not registered
            messages.info(request, "If the phone number is registered, an OTP has been sent to that number.")
            return render(request, 'accounts/send_otp_for_login.html')

        # Send OTP for login purpose
        otp_service = OTPService()
        success, message, otp_record = otp_service.send_otp(user, normalized_phone, 'login')

        if success:
            # Store user id and phone number in session for OTP verification
            request.session['pre_verified_user_id'] = user.id
            request.session['phone_number'] = normalized_phone
            request.session['otp_purpose'] = 'login'
            messages.info(request, "Please verify your phone number to complete login.")
            return redirect('accounts:verify_otp')
        else:
            messages.error(request, message)
            return render(request, 'accounts/send_otp_for_login.html')

    else:
        return redirect('accounts:login')


def password_reset_request_view(request):
    """
    Stub for password reset request view - to be implemented properly.
    """
    return render(request, 'accounts/password_reset_request.html')

def password_reset_set_password_view(request):
    """
    Stub for password reset set password view - to be implemented properly.
    """
    return render(request, 'accounts/password_reset_set_password.html')