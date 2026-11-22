"""Thin client for the PhilSMS REST API v3 (https://app.philsms.com/developers/documentation).

  POST {base}/sms/send   Authorization: Bearer <token>
  body: recipient (639XXXXXXXXX), sender_id, type=plain, message
The token comes from the PHILSMS_API_TOKEN environment variable, never from the code.
"""
import logging
import re

import requests
from django.conf import settings

log = logging.getLogger(__name__)


class SmsError(Exception):
    pass


def normalize_number(raw):
    """09171234567, +63 917 123 4567 and 639171234567 all become 639171234567. Returns '' if invalid."""
    digits = re.sub(r'\D', '', raw or '')
    if digits.startswith('09') and len(digits) == 11:
        digits = '63' + digits[1:]
    elif digits.startswith('9') and len(digits) == 10:
        digits = '63' + digits
    return digits if re.fullmatch(r'639\d{9}', digits) else ''


def send(number, message):
    """Send one SMS. Returns the provider's text answer, raises SmsError on any problem."""
    if not settings.PHILSMS_API_TOKEN:
        raise SmsError('SMS is not configured: set PHILSMS_API_TOKEN.')
    try:
        resp = requests.post(
            f'{settings.PHILSMS_BASE_URL}/sms/send',
            headers={'Authorization': f'Bearer {settings.PHILSMS_API_TOKEN}', 'Accept': 'application/json',
                     'Content-Type': 'application/json'},
            json={'recipient': number, 'sender_id': settings.PHILSMS_SENDER_ID, 'type': 'plain',
                  'message': message},
            timeout=15)
    except requests.RequestException as exc:
        log.warning('PhilSMS request failed: %s', exc.__class__.__name__)
        raise SmsError('Could not reach the SMS provider.') from exc
    try:
        data = resp.json()
    except ValueError:
        data = {}
    ok = resp.status_code < 400 and str(data.get('status', '')).lower() == 'success'
    if not ok:
        raise SmsError(str(data.get('message') or f'The SMS provider answered {resp.status_code}.')[:250])
    return str(data.get('message') or 'Accepted by provider')[:250]
