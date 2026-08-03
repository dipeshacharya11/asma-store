import logging
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

    def _send_sms(self, phone_number, text):
        """
        Private method to send SMS via Sparrow API.
        Returns a tuple (success, message_id, raw_response)
        """
        if not self.token or not self.sender_id:
            return False, None, {"error": "Sparrow SMS credentials not configured"}

        payload = {
            'token': self.token,
            'from': self.sender_id,
            'to': phone_number,
            'text': text
        }

        try:
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
        Send OTP via SMS.
        """
        text = f"Your Asma Store verification code is {otp}. This code expires in 5 minutes. Do not share this code with anyone."
        return self._send_sms(phone_number, text)

    def send_message(self, phone_number, text):
        """
        Send a custom SMS message.
        """
        return self._send_sms(phone_number, text)