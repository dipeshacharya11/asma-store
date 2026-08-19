from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile


User = get_user_model()


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254,
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        validators=[
            RegexValidator(
                regex=r'^(97|98)\d{8}$',
                message='Phone number must be 10 digits starting with 97 or 98 (e.g., 98XXXXXXXX or 97XXXXXXXX)'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your phone number (e.g., 98XXXXXXXX)'
        })
    )
    name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Full name'
        })
    )
    address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter your current address'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'name', 'email', 'phone_number', 'address', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Customize widget for username and passwords
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        # Remove any spaces or special characters for validation check
        cleaned_phone = ''.join(filter(str.isdigit, phone_number))
        # Check if already exists (checking against stored format)
        if UserProfile.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone_number

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        # Split name into first_name and last_name
        name = self.cleaned_data.get('name', '')
        if name:
            name_parts = name.strip().split(' ', 1)
            user.first_name = name_parts[0]
            user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        else:
            user.first_name = ''
            user.last_name = ''
        if commit:
            user.save()
            # Update the profile created by the signal
            user.profile.phone_number = self.cleaned_data['phone_number']
            user.profile.address = self.cleaned_data.get('address', '')
            user.profile.save()
        return user


class OTPVerificationForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': 'Enter 6-digit OTP',
            'inputmode': 'numeric',
            'style': 'letter-spacing: 0.5em;'
        })
    )


class SetNewPasswordForm(forms.Form):
    new_password = forms.CharField(
        label="New Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        }),
        help_text="Your password must contain at least 8 characters."
    )
    confirm_password = forms.CharField(
        label="Confirm New Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        }),
        help_text="Enter the same password as before, for verification."
    )

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")
        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("Passwords don't match")
        return cleaned_data


class PhoneVerificationForm(forms.Form):
    """
    Form for phone verification during checkout
    """
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        validators=[
            RegexValidator(
                regex=r'^(97|98)\d{8}$',
                message='Phone number must be 10 digits starting with 97 or 98 (e.g., 98XXXXXXXX or 97XXXXXXXX)'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your phone number (e.g., 98XXXXXXXX)',
            'inputmode': 'tel'
        })
    )
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        required=False,  # Will be made required when needed via JavaScript
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center',
            'placeholder': 'Enter 6-digit OTP',
            'inputmode': 'numeric',
            'style': 'letter-spacing: 0.5em;'
        })
    )

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        # Normalize the phone number
        cleaned = ''.join(filter(str.isdigit, phone_number))
        # Remove Nepal country code if present
        if cleaned.startswith('977') and len(cleaned) > 3:
            cleaned = cleaned[3:]
        # Remove leading zeros
        while cleaned.startswith('0') and len(cleaned) > 1:
            cleaned = cleaned[1:]
        return cleaned


class ChangePhoneForm(forms.Form):
    """
    Form for changing user's phone number
    """
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        validators=[
            RegexValidator(
                regex=r'^(97|98)\d{8}$',
                message='Phone number must be 10 digits starting with 97 or 98 (e.g., 98XXXXXXXX or 97XXXXXXXX)'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your new phone number (e.g., 98XXXXXXXX)',
            'inputmode': 'tel'
        })
    )

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        # Normalize the phone number
        cleaned = ''.join(filter(str.isdigit, phone_number))
        # Remove Nepal country code if present
        if cleaned.startswith('977') and len(cleaned) > 3:
            cleaned = cleaned[3:]
        # Remove leading zeros
        while cleaned.startswith('0') and len(cleaned) > 1:
            cleaned = cleaned[1:]
        return cleaned


class ForgotPasswordForm(forms.Form):
    """
    Form for requesting password reset via phone number
    """
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        validators=[
            RegexValidator(
                regex=r'^(97|98)\d{8}$',
                message='Phone number must be 10 digits starting with 97 or 98 (e.g., 98XXXXXXXX or 97XXXXXXXX)'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your registered phone number (e.g., 98XXXXXXXX)',
            'inputmode': 'tel'
        })
    )

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        # Normalize the phone number
        cleaned = ''.join(filter(str.isdigit, phone_number))
        # Remove Nepal country code if present
        if cleaned.startswith('977') and len(cleaned) > 3:
            cleaned = cleaned[3:]
        # Remove leading zeros
        while cleaned.startswith('0') and len(cleaned) > 1:
            cleaned = cleaned[1:]
        return cleaned