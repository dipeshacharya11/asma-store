#!/usr/bin/env python3

# Test the phone formatting function directly
import re

def format_phone_number(phone_number):
    """
    Format phone number to the format expected by Sparrow SMS API.
    Expected format: 10-digit Nepalese mobile number (starting with 97 or 98)
    """
    if not phone_number:
        return phone_number

    # Convert to string and strip whitespace
    phone_number = str(phone_number).strip()

    # Remove leading +, 00, or 0
    if phone_number.startswith('+'):
        phone_number = phone_number[1:]
    elif phone_number.startswith('00'):
        phone_number = phone_number[2:]  # Fixed: was 'number[2:]'
    elif phone_number.startswith('0'):
        phone_number = phone_number[1:]

    # Remove Nepal country code (977) if present
    if phone_number.startswith('977') and len(phone_number) > 3:
        phone_number = phone_number[3:]

    # Remove any non-digit characters
    phone_number = re.sub(r'\D', '', phone_number)

    # Validate: should be 10 digits starting with 97 or 98
    if re.match(r'^(97|98)\d{8}$', phone_number):
        return phone_number
    else:
        # If format is invalid, return original and let API handle the error
        return str(phone_number).strip()

# Test cases
test_cases = [
    "+9779817052570",  # From .env
    "9779817052570",   # Without +
    "09817052570",     # With leading 0
    "009779817052570", # With 00 (this was causing the NameError)
    "9817052570",      # Already formatted
    "9812345678",      # Another valid number
]

print("Testing phone number formatting:")
for phone in test_cases:
    try:
        formatted = format_phone_number(phone)
        print(f"  Input:  {phone}")
        print(f"  Output: {formatted}")
        # Check if it's a valid Nepalese number (starts with 97 or 98, 10 digits)
        is_valid = bool(re.match(r'^(97|98)\d{8}$', formatted))
        print(f"  Valid:  {is_valid}")
        print()
    except Exception as e:
        print(f"  Input:  {phone}")
        print(f"  Error:  {e}")
        print()