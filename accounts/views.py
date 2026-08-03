from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
import json
import logging

from .forms import SignUpForm, OTPVerificationForm
from .services.otp_service import OTPService
from .models import OTP

logger = logging.getLogger(__name__)
User = get_user_model()
otp_service = OTPService()


def signup_view(request):
    """
    User registration view.
    Collects email, password, and phone number.
    Sends OTP to phone number upon successful form submission.
    """
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Deactivate until OTP verified
            user.save()
            phone_number = form.cleaned_data['phone_number']
            # Send OTP
            success, message, otp_record = otp_service.send_otp(user, phone_number)
            if success:
                # Store user id and phone number in session for verification
                request.session['pre_verified_user_id'] = user.id
                request.session['phone_number'] = phone_number
                messages.success(request, message)
                return redirect('accounts:verify_otp')
            else:
                messages.error(request, message)
                # Delete the user if OTP sending failed
                user.delete()
                return render(request, 'accounts/signup.html', {'form': form})
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})


def verify_otp_view(request):
    """
    OTP verification view.
    User enters the OTP sent to their phone.
    Handles both regular form submission and AJAX requests.
    """
    phone_number = request.session.get('phone_number')
    user_id = request.session.get('pre_verified_user_id')
    if not phone_number or not user_id:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Session expired. Please sign up again.'})
        messages.error(request, "Session expired. Please sign up again.")
        return redirect('accounts:signup')

    if request.method == 'POST':
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            success, message, otp_record = otp_service.verify_otp(phone_number, otp)
            if success:
                # Activate user and log them in
                user = User.objects.get(id=user_id)
                user.is_active = True
                user.save()
                login(request, user)
                # Clear session
                request.session.pop('pre_verified_user_id', None)
                request.session.pop('phone_number', None)
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': 'Account verified successfully!', 'redirect_url': '/'})
                messages.success(request, "Account verified and logged in successfully.")
                return redirect('store:home')  # Redirect to home page after login
            else:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': message})
                messages.error(request, message)
                # If OTP verification fails, we keep the session for retries (within limits)
                return render(request, 'accounts/verify_otp.html', {'form': form, 'phone_number': phone_number})
        else:
            error_msg = "Please enter a valid OTP."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            return render(request, 'accounts/verify_otp.html', {'form': form, 'phone_number': phone_number})
    else:
        form = OTPVerificationForm()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Invalid request method.'})
    return render(request, 'accounts/verify_otp.html', {'form': form, 'phone_number': phone_number})


def login_view(request):
    """
    Custom login view using Django's authentication.
    After login, we check if phone is verified; if not, we redirect to OTP verification.
    """
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Check if phone is verified
            try:
                if user.profile.is_phone_verified:
                    return redirect('store:home')
                else:
                    # Phone not verified, send OTP for verification
                    phone_number = user.profile.phone_number
                    success, message, otp_record = otp_service.send_otp(user, phone_number)
                    if success:
                        request.session['pre_verified_user_id'] = user.id
                        request.session['phone_number'] = phone_number
                        messages.info(request, "Please verify your phone number to complete login.")
                        return redirect('accounts:verify_otp')
                    else:
                        messages.error(request, message)
                        logout(request)
                        return render(request, 'accounts/login.html')
            except Exception as e:
                logger.error(f"Error checking phone verification: {e}")
                messages.error(request, "An error occurred. Please try again.")
                logout(request)
                return render(request, 'accounts/login.html')
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('store:home')


@require_http_methods(["POST"])
def resend_otp_view(request):
    """
    AJAX view to resend OTP.
    """
    user_id = request.session.get('pre_verified_user_id')
    phone_number = request.session.get('phone_number')
    if not user_id or not phone_number:
        return JsonResponse({'success': False, 'message': 'Session expired.'})
    user = User.objects.get(id=user_id)
    success, message, otp_record = otp_service.resend_otp(user, phone_number)
    return JsonResponse({'success': success, 'message': message})