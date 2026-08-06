#!/usr/bin/env python
import os
import django
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'asma_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import UserProfile

User = get_user_model()

# Use timestamp to make username unique
timestamp = int(time.time())
username = f'testuser_{timestamp}'

print("Creating user...")
user = User.objects.create_user(username=username, password='testpass', email='test@example.com')
print(f"User created: {user.id}")

print("Checking if profile exists...")
try:
    profile = user.profile
    print(f"Profile exists: {profile.id}")
    print(f"Profile phone_number: {profile.phone_number}")
    print(f"Profile is_phone_verified: {profile.is_phone_verified}")
except UserProfile.DoesNotExist:
    print("Profile does not exist")

print("Saving user again...")
user.save()
print("User saved")

print("Checking profile after save...")
try:
    profile = user.profile
    print(f"Profile exists: {profile.id}")
    print(f"Profile phone_number: {profile.phone_number}")
    print(f"Profile is_phone_verified: {profile.is_phone_verified}")
except UserProfile.DoesNotExist:
    print("Profile does not exist")