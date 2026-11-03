"""
SMS delivery for phone-number verification codes.

There's no free, keyless way to send a real SMS -- every provider
needs a paid account. This module defines a tiny interface
(`send_sms(phone_number, message)`) so swapping in a real provider
later is a one-line settings change (`SMS_BACKEND`), not a rewrite.

Two providers are sketched below as a starting point:
- Africa's Talking (https://africastalking.com) is the most commonly
  used SMS gateway for Rwanda/East Africa and has a simple HTTP API.
- Twilio (https://www.twilio.com) is the most common choice globally.

Until you set SMS_API_KEY (and switch SMS_BACKEND to one of these),
`ConsoleSMSBackend` is used, which just prints the code to the
console/log -- fine for development and testing the verification flow
end-to-end, not something to leave on in production.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class ConsoleSMSBackend:
    """Development fallback: logs the message instead of sending a
    real SMS, and also emails it to the user if email is configured,
    so the OTP flow is testable without a paid SMS account."""

    def send_sms(self, phone_number, message, user=None):
        logger.info("SMS to %s: %s", phone_number, message)
        if user and user.email:
            send_mail(
                subject="KazeB verification code",
                message=message,
                from_email=None,
                recipient_list=[user.email],
                fail_silently=True,
            )
        return True


class AfricasTalkingSMSBackend:
    """
    Real SMS delivery via Africa's Talking. Requires:
      pip install africastalking
      SMS_API_KEY=<your API key>
      AFRICASTALKING_USERNAME=<your username, "sandbox" while testing>
    This class intentionally doesn't import the africastalking package
    at module load time (so the project runs fine without it
    installed) -- only when actually selected and used.
    """

    def send_sms(self, phone_number, message, user=None):
        import africastalking

        africastalking.initialize(
            getattr(settings, "AFRICASTALKING_USERNAME", "sandbox"),
            settings.SMS_API_KEY,
        )
        sms = africastalking.SMS
        response = sms.send(message, [phone_number], sender_id=settings.SMS_SENDER_ID)
        logger.info("Africa's Talking response: %s", response)
        return True


class TwilioSMSBackend:
    """
    Real SMS delivery via Twilio. Requires:
      pip install twilio
      SMS_API_KEY=<account_sid>:<auth_token>  (colon-separated)
      TWILIO_FROM_NUMBER=<your Twilio phone number>
    """

    def send_sms(self, phone_number, message, user=None):
        from twilio.rest import Client

        account_sid, auth_token = settings.SMS_API_KEY.split(":", 1)
        client = Client(account_sid, auth_token)
        client.messages.create(
            body=message,
            from_=settings.TWILIO_FROM_NUMBER,
            to=phone_number,
        )
        return True


def get_sms_backend():
    backend_class = import_string(settings.SMS_BACKEND)
    return backend_class()


def send_verification_sms(user, code):
    message = f"Kode yawe ya KazeB ni: {code}. Ntuyihe undi muntu."
    backend = get_sms_backend()
    return backend.send_sms(user.phone_number, message, user=user)
