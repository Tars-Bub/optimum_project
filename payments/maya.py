"""Thin client for the Maya Checkout REST API (https://developers.maya.ph).

Authentication is HTTP Basic: the key is the username and the password is blank.
  * Create Checkout            POST /checkout/v1/checkouts                  PUBLIC key
  * Retrieve Payment via ID    GET  /payments/v1/payments/{id}              SECRET key
  * Retrieve Payment via RRN   GET  /payments/v1/payment-rrns/{rrn}         SECRET key
The keys come from environment variables (see config/settings.py), never from the code.
"""
import base64
import logging
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings

log = logging.getLogger(__name__)

SUCCESS = {'PAYMENT_SUCCESS'}
FAILED = {'PAYMENT_FAILED', 'AUTH_FAILED'}
EXPIRED = {'PAYMENT_EXPIRED'}
CANCELLED = {'PAYMENT_CANCELLED'}
KNOWN = SUCCESS | FAILED | EXPIRED | CANCELLED | {
    'PENDING_TOKEN', 'PENDING_PAYMENT', 'FOR_AUTHENTICATION', 'AUTHENTICATING',
    'AUTH_SUCCESS', 'PAYMENT_PROCESSING'}


class MayaError(Exception):
    """Maya could not be reached, rejected the request, or is not configured."""

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def _auth_header(key):
    token = base64.b64encode(f'{key.strip()}:'.encode()).decode()
    return {'Authorization': f'Basic {token}', 'Content-Type': 'application/json',
            'Accept': 'application/json'}


def _request(method, path, key, json=None):
    if not key:
        raise MayaError('Maya is not configured: set MAYA_PUBLIC_KEY and MAYA_SECRET_KEY.')
    url = settings.MAYA_BASE_URL.rstrip('/') + path
    try:
        resp = requests.request(method, url, headers=_auth_header(key), json=json,
                                timeout=settings.MAYA_TIMEOUT)
    except requests.RequestException as exc:
        log.warning('Maya %s %s failed: %s', method, path, exc.__class__.__name__)
        raise MayaError('Could not reach Maya. Please try again.') from exc
    try:
        data = resp.json() if resp.content else {}
    except ValueError:
        data = {}
    if resp.status_code >= 400:
        detail = ''
        if isinstance(data, dict):
            detail = data.get('message') or data.get('error') or data.get('code') or ''
        log.warning('Maya %s %s returned %s', method, path, resp.status_code)
        raise MayaError(f'Maya rejected the request ({resp.status_code}). {detail}'.strip(),
                        resp.status_code, data)
    return data


def create_checkout(reference, total, items, redirect_urls, metadata=None):
    """Create a checkout page. Returns the Maya response with `checkoutId` and `redirectUrl`."""
    body = {
        'totalAmount': {'value': float(total), 'currency': 'PHP'},
        'items': items,
        'redirectUrl': redirect_urls,
        'requestReferenceNumber': reference,
        'metadata': metadata or {},
    }
    data = _request('POST', '/checkout/v1/checkouts', settings.MAYA_PUBLIC_KEY, json=body)
    if not isinstance(data, dict) or not data.get('checkoutId') or not data.get('redirectUrl'):
        raise MayaError('Maya did not return a checkout link.', payload=data)
    return data


def get_payment(payment_id):
    return _request('GET', f'/payments/v1/payments/{payment_id}', settings.MAYA_SECRET_KEY)


def get_payment_by_rrn(rrn):
    return _request('GET', f'/payments/v1/payment-rrns/{rrn}', settings.MAYA_SECRET_KEY)


def first_record(data):
    """Maya may answer with one object or an array of payment records."""
    if isinstance(data, list):
        return data[0] if data and isinstance(data[0], dict) else {}
    return data if isinstance(data, dict) else {}


def read_status(record):
    """The payment status string (for example PAYMENT_SUCCESS) from a Maya record."""
    values = [str(record.get(k) or '').upper() for k in ('paymentStatus', 'status')]
    for v in values:
        if v in KNOWN:
            return v
    return next((v for v in values if v), '')


def _dec(value):
    if isinstance(value, dict):
        value = value.get('value', value.get('amount'))
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def read_amount(record):
    """Amount Maya says was charged, or None when the record does not show one."""
    for key in ('totalAmount', 'amount'):
        if record.get(key) is not None:
            amount = _dec(record[key])
            if amount is not None:
                return amount
    return None
