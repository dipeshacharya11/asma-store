from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-otp/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/', views.resend_otp_view, name='resend_otp'),
    # Guest checkout
    path('guest-checkout/otp-request/', views.guest_checkout_otp_request_view, name='guest_checkout_otp_request'),
    # Change phone
    path('change-phone/', views.change_phone_view, name='change_phone'),
    # Password reset
    path('password-reset/request/', views.password_reset_request_view, name='password_reset_request'),
    path('password-reset/set-new-password/', views.password_reset_set_password_view, name='password_reset_set_password'),
]