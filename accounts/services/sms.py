import logging
import time
import re
import requests
from django.conf import settings
from requests.exceptions import RequestException, Timeout, ConnectionError

logger = logging.getLogger(__name__)

class SparrowSMSService:
    """
    Service for sending SMS via Sparrow SMS API.
    """
    BASE_URL = "https://api.sparrowsms.com/v2/sms/"

    def __init__(self):
        self.token = getattr(settings, 'SPARROW_TOKEN', None)
        self.sender_id = getattr(settings, 'SPARROW_SENDER', None)
        if not self.token or not self.sender_id:
            logger.error("Sparrow SMS credentials not configured in settings.")

    def _format_phone_number(self, phone_number):
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
            phone_number = phone_number[2:]
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
            # This maintains backward compatibility for numbers already in correct format
            return str(phone_number).strip()

    def _send_sms_single_attempt(self, phone_number, text):
        """
        Single attempt to send SMS via Sparrow API.
        Returns a tuple (success, message_id, raw_response)
        """
        if not self.token or not self.sender_id:
            return False, None, {"error": "Sparrow SMS credentials not configured"}

        # Format phone number for the API
        formatted_phone_number = self._format_phone_number(phone_number)

        payload = {
            'token': self.token,
            'from': self.sender_id,
            'to': formatted_phone_number,
            'text': text
        }

        try:
            # DEBUG: Log the payload we're sending
            logger.info(f"Sparrow SMS request payload: {payload}")

            response = requests.post(
                self.BASE_URL,
                data=payload,
                timeout=15
            )
            response.raise_for_status()  # Raises HTTPError for bad responses
            result = response.json()

            logger.info(f"Sparrow SMS response: {result}")

            # Check for success
            if result.get('response_code') == 200:
                message_id = result.get('message_id')
                return True, message_id, result
            else:
                # Handle specific error codes
                error_msg = result.get('response', 'Unknown error')
                logger.error(f"Sparrow SMS error: {error_msg} (code: {result.get('response_code')})")
                # Check for specific errors that should not be retried
                if result.get('response_code') in [101, 102]:  # Example: Invalid token, insufficient credits
                    return False, None, result
                # For other errors, we might retry if it's a transient issue
                return False, None, result

        except Timeout:
            logger.error("Sparrow SMS request timed out")
            return False, None, {"error": "Request timed out"}
        except ConnectionError:
            logger.error("Sparrow SMS connection error")
            return False, None, {"error": "Connection error"}
        except RequestException as e:
            logger.error(f"Sparrow SMS request failed: {str(e)}")
            return False, None, {"error": str(e)}
        except ValueError as e:  # JSON decode error
            logger.error(f"Failed to parse Sparrow SMS response: {str(e)}")
            return False, None, {"error": "Invalid response from SMS provider"}

    def send_otp(self, phone_number, otp):
        """
        Send OTP via SMS with retries for transient errors.
        """
        text = f"Your Asma Store verification code is {otp}. This code expires in 5 minutes. Do not share this code with anyone."
        return self._send_with_retry(phone_number, text)

    def send_message(self, phone_number, text):
        """
        Send a custom SMS message with retries for transient errors.
        """
        return self._send_with_retry(phone_number, text)

    def _send_with_retry(self, phone_number, text, max_retries=3, backoff_factor=1):
        """
        Send SMS with retry logic for transient errors.
        """
        retries = 0
        while retries < max_retries:
            success, message_id, response = self._send_sms_single_attempt(phone_number, text)
            if success:
                return True, message_id, response
            # If we got a response, check if it's a permanent error
            if response and 'error' not in response:
                # Check response_code for non-retryable errors
                try:
                    response_code = int(response.get('response_code', 0))
                except (ValueError, TypeError):
                    response_code = 0
                if response_code in [101, 102, 1013]:  # Example: Invalid token, insufficient credits
                    logger.error(f"Non-retryable error from Sparrow SMS: {response.get('response')}")
                    return False, None, response
            # Check if the error is an HTTP 4xx error (client error) which should not be retried
            elif response and 'error' in response:
                error_msg = response.get('error', '')
                # Check if error looks like an HTTP 4xx error (400-499)
                import re
                if re.match(r'4\d\d Client Error', error_msg):
                    logger.error(f"Non-retryable HTTP error from Sparrow SMS: {error_msg}")
                    return False, None, response
            # If we have an error that might be transient (like timeout, connection error) or we don't have a response, retry
            retries += 1
            if retries < max_retries:
                wait_time = backoff_factor * (2 ** (retries - 1))  # Exponential backoff
                logger.info(f"Retrying SMS send in {wait_time} seconds... (attempt {retries + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to send SMS after {max_retries} attempts.")
                return False, None, response
        return False, None, {"error": "Max retries exceeded"}