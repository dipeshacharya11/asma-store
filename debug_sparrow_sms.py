#!/usr/bin/env python3
"""
Sparrow SMS Debugging Script
Run this to identify why requests return HTTP 400
"""

import os
import sys
import time
import json
import re
import traceback
from typing import Dict, Any, List, Tuple, Optional

try:
    import requests
    from requests.exceptions import RequestException, Timeout, ConnectionError, HTTPError
except ImportError:
    print("Error: Install required packages: pip install requests python-dotenv")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass  # dotenv is optional, we can still read environment variables directly

# Configuration from environment
TOKEN = os.environ.get('SPARROW_TOKEN', '')
SENDER = os.environ.get('SPARROW_SENDER', '')
ADMIN_PHONE = os.environ.get('SPARROW_ADMIN_PHONE', '')

# Handle duplicate SPARROW_ADMIN_PHONE in .env (take first occurrence)
if '\n' in ADMIN_PHONE or ADMIN_PHONE.count('=') > 1:
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('SPARROW_ADMIN_PHONE='):
                    ADMIN_PHONE = line.split('=', 1)[1].strip()
                    break
    except FileNotFoundError:
        pass

if not TOKEN:
    print("ERROR: SPARROW_TOKEN not set")
    sys.exit(1)
if not SENDER:
    print("ERROR: SPARROW_SENDER not set")
    sys.exit(1)

API_URL = "https://api.sparrowsms.com/v2/sms/"
HEADERS = {'Content-Type': 'application/x-www-form-urlencoded'}

# Test phone numbers (valid Nepalese mobiles)
VALID_NEPALESE = ["9812345678", "9712345678"]

def format_phone_number(phone_number):
    """
    Format phone number to the format expected by Sparrow SMS API.
    Expected format: 10-digit Nepalese mobile number (starting with 97 or 98)
    This matches the logic in accounts/services/sms.py
    """
    if not phone_number:
        return phone_number

    # Convert to string and strip whitespace
    phone_number = str(phone_number).strip()

    # Remove leading +, 00, or 0
    if phone_number.startswith('+'):
        phone_number = phone_number[1:]
    elif phone_number.startswith('00'):
        phone_number = phone_number[2:]
    elif phone_number.startswith('0'):
        phone_number = phone_number[1:]

    # Remove Nepal country code (977) if present
    if phone_number.startswith('977') and len(phone_number) > 3:
        phone_number = phone_number[3:]

    # Remove any non-digit characters
    phone_number = re.sub(r'\D', '', phone_number)

    # Validate: should be 10 digits starting with 97 or 98
    if re.match(r'^[97|98]\d{8}$', phone_number):
        return phone_number
    else:
        # If format is invalid, return original and let API handle the error
        # This maintains backward compatibility for numbers already in correct format
        return str(phone_number).strip()

def validate_payload(payload: Dict[str, Any]) -> List[str]:
    """Validate payload before sending."""
    errors = []
    required = ['token', 'from', 'to', 'text']
    for field in required:
        if field not in payload:
            errors.append(f"Missing: {field}")
        elif payload[field] is None:
            errors.append(f"None: {field}")
        elif isinstance(payload[field], str) and not payload[field].strip():
            errors.append(f"Empty: {field}")

    if errors:
        return errors

    # Validate each field
    token = payload['token']
    if not isinstance(token, str) or len(token) < 10:
        errors.append("Invalid token")

    sender = payload['from']
    if not isinstance(sender, str) or len(sender) > 11:
        errors.append("Invalid sender (length >11 or not string)")

    phone = payload['to']
    if not isinstance(phone, str):
        errors.append("Phone must be string")
    else:
        # Clean phone number for validation (similar to how it should be sent)
        cleaned = format_phone_number(phone)
        # Validate: should be 10 digits starting with 97 or 98
        if not re.match(r'^(97|98)\d{8}$', cleaned):
            errors.append("Invalid phone format")

    text = payload['text']
    if not isinstance(text, str):
        errors.append("Text must be string")
    elif len(text) == 0:
        errors.append("Text is empty")

    return errors

def send_sms(payload: Dict[str, Any]) -> Tuple[Optional[int], Dict[str, str], str, Optional[Dict], float, Optional[Exception]]:
    """Send SMS and return response details."""
    start = time.time()
    try:
        resp = requests.post(API_URL, data=payload, headers=HEADERS, timeout=30)
        elapsed = time.time() - start
        try:
            js = resp.json()
        except:
            js = None
        return resp.status_code, dict(resp.headers), resp.text, js, elapsed, None
    except Exception as e:
        elapsed = time.time() - start
        return None, {}, str(e), None, elapsed, e

def run_test(name: str, payload: Dict[str, Any], expect_success: bool = True) -> Dict[str, Any]:
    """Run a single test case."""
    print("\n" + "="*60)
    print(f"TEST: {name}")
    print("="*60)
    print("Payload:")
    for k, v in payload.items():
        if k == 'token':
            print(f"  {k}: {v[:8]}...{v[-4:] if len(v)>12 else ''}")
        else:
            print(f"  {k}: {repr(v)}")

    # Validate
    val_errors = validate_payload(payload)
    if val_errors:
        print("VALIDATION ERRORS:")
        for err in val_errors:
            print(f"  - {err}")
        return {
            'name': name, 'passed': False, 'failure_reason': f"Validation: {', '.join(val_errors)}",
            'payload': payload, 'validation_errors': val_errors, 'http_status': None,
            'response_headers': {}, 'raw_response': '', 'json_response': None,
            'execution_time': 0, 'exception': None
        }

    # Send request
    status, headers, raw, js, elapsed, exc = send_sms(payload)

    # Debug output after request
    print(f"HTTP Status: {status}")
    print(f"Response Headers: {json.dumps(headers, indent=2)}")
    print(f"Raw Response: {raw[:500]}{'...' if len(raw) > 500 else ''}")
    if js:
        print(f"JSON Response: {json.dumps(js, indent=2)}")

    # Determine pass/fail
    passed = False
    failure = ""
    if exc:
        passed = False
        failure = f"Request exception: {exc}"
    elif status == 200 and expect_success:
        if js and js.get('response_code') == 200:
            passed = True
        else:
            passed = False
            failure = f"HTTP 200 but API indicates failure: {js}"
    elif status != 200 and not expect_success:
        passed = True  # Expected failure
    elif status == 200 and not expect_success:
        passed = False
        failure = "Expected failure but got HTTP 200"
    elif status != 200 and expect_success:
        passed = False
        failure = f"Expected success but got HTTP {status}"
    else:
        passed = False
        failure = "Unexpected condition"

    return {
        'name': name, 'passed': passed, 'failure_reason': failure,
        'payload': payload, 'validation_errors': val_errors,
        'http_status': status, 'response_headers': headers,
        'raw_response': raw, 'json_response': js,
        'execution_time': elapsed, 'exception': exc
    }

def main():
    print("Sparrow SMS Debugging Suite")
    print("="*50)
    print(f"API: {API_URL}")
    print(f"Token: {TOKEN[:8]}...{TOKEN[-4:]}")
    print(f"Sender: {SENDER}")
    print(f"Admin Phone: {ADMIN_PHONE}")

    # Show what the formatted admin phone would be
    formatted_admin = format_phone_number(ADMIN_PHONE) if ADMIN_PHONE else None
    print(f"Formatted Admin Phone: {formatted_admin}")
    print("="*50)

    # Define test cases
    tests = []

    # Test 1: Known good (should work if config is correct)
    tests.append(("Known-good payload", {
        'token': TOKEN,
        'from': SENDER,
        'to': VALID_NEPALESE[0],  # 9812345678
        'text': 'Test message from Sparrow SMS test'
    }, True))

    # Test 2: Missing token
    tests.append(("Missing token", {
        'from': SENDER,
        'to': VALID_NEPALESE[0],
        'text': 'Test message'
    }, False))

    # Test 3: Invalid token
    tests.append(("Invalid token", {
        'token': 'invalid_token_here',
        'from': SENDER,
        'to': VALID_NEPALESE[0],
        'text': 'Test message'
    }, False))

    # Test 4: Missing sender
    tests.append(("Missing sender", {
        'token': TOKEN,
        'to': VALID_NEPALESE[0],
        'text': 'Test message'
    }, False))

    # Test 5: Invalid sender (too long)
    tests.append(("Invalid sender (long)", {
        'token': TOKEN,
        'from': 'ThisSenderIsWayTooLongForSparrowSMS',
        'to': VALID_NEPALESE[0],
        'text': 'Test message'
    }, False))

    # Test 6: Invalid sender (invalid chars)
    tests.append(("Invalid sender (chars)", {
        'token': TOKEN,
        'from': 'Invalid@Sender#!',
        'to': VALID_NEPALESE[0],
        'text': 'Test message'
    }, False))

    # Test 7: Empty message
    tests.append(("Empty message", {
        'token': TOKEN,
        'from': SENDER,
        'to': VALID_NEPALESE[0],
        'text': ''
    }, False))

    # Test 8: Very long message
    tests.append(("Very long message", {
        'token': TOKEN,
        'from': SENDER,
        'to': VALID_NEPALESE[0],
        'text': 'A' * 200
    }, False))  # Might still send but we expect failure due to length concerns

    # Test 9: Phone 9817xxxxxx
    tests.append(("Phone 9817xxxxxx", {
        'token': TOKEN,
        'from': SENDER,
        'to': '9817000000',
        'text': 'Test message'
    }, True))

    # Test 10: Phone 9779817xxxxxx (with country code)
    tests.append(("Phone 9779817xxxxxx", {
        'token': TOKEN,
        'from': SENDER,
        'to': '977981700000',
        'text': 'Test message'
    }, True))

    # Test 11: Phone +9779817xxxxxx (with + and country code)
    tests.append(("Phone +9779817xxxxxx", {
        'token': TOKEN,
        'from': SENDER,
        'to': '+977981700000',
        'text': 'Test message'
    }, True))

    # Test 12: Phone with spaces
    tests.append(("Phone with spaces", {
        'token': TOKEN,
        'from': SENDER,
        'to': '9812 3456 78',
        'text': 'Test message'
    }, True))

    # Test 13: Phone with letters
    tests.append(("Phone with letters", {
        'token': TOKEN,
        'from': SENDER,
        'to': '981234567a',
        'text': 'Test message'
    }, False))

    # Test 14: None phone
    tests.append(("None phone", {
        'token': TOKEN,
        'from': SENDER,
        'to': None,
        'text': 'Test message'
    }, False))

    # Test 15: None message
    tests.append(("None message", {
        'token': TOKEN,
        'from': SENDER,
        'to': VALID_NEPALESE[0],
        'text': None
    }, False))

    # Test 16: Unicode message
    tests.append(("Unicode message", {
        'token': TOKEN,
        'from': SENDER,
        'to': VALID_NEPALESE[0],  # Use valid Nepali number
        'text': 'नमस्ते दुनिया 🌍'
    }, True))

    # Test 17: Checkout notification payload (exact format from your code)
    checkout_payload = {
        'token': TOKEN,
        'from': SENDER,
        'to': ADMIN_PHONE,  # This is what's in your .env file
        'text': (
            f"NEW ORDER ALERT\n"
            f"Order ID: 999\n"
            f"Customer: Test Customer\n"
            f"Phone: 9876543210\n"
            f"Email: test@example.com\n"
            f"Address: Kathmandu, Nepal\n"
            f"Total Amount: Rs. 1500.00\n"
            f"Items Count: 2\n"
            f"Order Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
    }
    tests.append(("Checkout notification payload", checkout_payload, True))

    # Test 18: OTP payload (typical format)
    otp_payload = {
        'token': TOKEN,
        'from': SENDER,
        'to': VALID_NEPALESE[0],  # Use a valid Nepalese number like other tests
        'text': 'Your OTP for verification is 123456. It will expire in 5 minutes.'
    }
    tests.append(("OTP payload", otp_payload, True))

    # Test 19: Checkout notification with formatted phone (what it should be after our fix)
    # This tests what the phone number SHOULD be after formatting
    formatted_admin_phone = format_phone_number(ADMIN_PHONE) if ADMIN_PHONE else None
    checkout_payload_formatted = {
        'token': TOKEN,
        'from': SENDER,
        'to': formatted_admin_phone,
        'text': (
            f"NEW ORDER ALERT\n"
            f"Order ID: 999\n"
            f"Customer: Test Customer\n"
            f"Phone: 9876543210\n"
            f"Email: test@example.com\n"
            f"Address: Kathmandu, Nepal\n"
            f"Total Amount: Rs. 1500.00\n"
            f"Items Count: 2\n"
            f"Order Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
    }
    tests.append(("Checkout notification payload (formatted)", checkout_payload_formatted, True))

    # Test 20: OTP with formatted phone to admin number
    otp_payload_formatted = {
        'token': TOKEN,
        'from': SENDER,
        'to': formatted_admin_phone,  # Try sending OTP to formatted admin number
        'text': 'Your OTP for verification is 123456. It will expire in 5 minutes.'
    }
    tests.append(("OTP payload (to formatted admin)", otp_payload_formatted, True))

    # Run all tests
    results = []
    for name, payload, expect_success in tests:
        result = run_test(name, payload, expect_success)
        results.append(result)
        status = "PASS" if result['passed'] else "FAIL"
        print(f"\nRESULT: {status}")
        if not result['passed'] and result['failure_reason']:
            print(f"REASON: {result['failure_reason']}")

    # Summary
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    for r in results:
        status = "PASS" if r['passed'] else "FAIL"
        print(f"{status:4} | {r['name']}")
        if not r['passed'] and r['failure_reason']:
            print(f"      -> {r['failure_reason']}")
    print("-"*50)
    print(f"TOTAL: {passed}/{total} passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n❌ {total - passed} TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())