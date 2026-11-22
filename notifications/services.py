import logging

from django.conf import settings
from django.utils import timezone

from . import philsms
from .models import SmsLog

log = logging.getLogger(__name__)


def send_sms(number, message, kind='manual', order=None, user=None):
    """Send an SMS and record it. Never raises: a failed SMS must not break a sale or a payment."""
    to = philsms.normalize_number(number)
    log_row = SmsLog(recipient=to or (number or '')[:30], message=message, kind=kind, order=order,
                     created_by=user if getattr(user, 'pk', None) else None)
    if not settings.SMS_ENABLED:
        log_row.status, log_row.detail = SmsLog.SKIPPED, 'SMS is switched off (SMS_ENABLED=0).'
    elif not to:
        log_row.status, log_row.detail = SmsLog.SKIPPED, 'Not a valid Philippine mobile number.'
    elif not settings.PHILSMS_API_TOKEN:
        log_row.status, log_row.detail = SmsLog.SKIPPED, 'SMS is not configured (no PHILSMS_API_TOKEN).'
    else:
        try:
            log_row.detail = philsms.send(to, message)
            log_row.status = SmsLog.SENT
        except philsms.SmsError as exc:
            log_row.status, log_row.detail = SmsLog.FAILED, str(exc)
        except Exception:                                        # pragma: no cover - safety net
            log.exception('Unexpected SMS error')
            log_row.status, log_row.detail = SmsLog.FAILED, 'Unexpected error while sending.'
    log_row.save()
    return log_row


def _peso(value):
    return f'PHP {value:,.2f}'


def send_receipt(order, user=None):
    """Text the customer a short receipt after the sale is finalized (only if a number was entered)."""
    if not order.client_phone:
        return None
    paid, total = order.amount_paid, order.total
    tail = 'Paid in full.' if paid >= total else f'Balance: {_peso(total - paid)}.'
    msg = (f'Optimum Business Products: thank you! Sale {order.number} on '
           f'{timezone.localtime(order.finalized_at or timezone.now()):%b %d, %Y}. '
           f'Total {_peso(total)}. {tail}')
    return send_sms(order.client_phone, msg, 'receipt', order, user)


def send_payment_link(payment, number, user=None):
    msg = (f'Optimum Business Products: please pay {_peso(payment.amount)} for sale {payment.order.number} '
           f'using this Maya link: {payment.checkout_url}')
    return send_sms(number, msg, 'payment_link', payment.order, user)


def notify_low_stock(product, before, user=None):
    """Text the owner once, when an item drops to its reorder level or below."""
    if not settings.SMS_OWNER_NUMBER or product.reorder_level is None:
        return None
    if before > product.reorder_level and product.quantity <= product.reorder_level:
        state = 'is OUT of stock' if product.quantity <= 0 else f'is low ({product.quantity} left)'
        msg = f'Optimum low-stock alert: {product.name} ({product.code}) {state}. Reorder level: {product.reorder_level}.'
        return send_sms(settings.SMS_OWNER_NUMBER, msg, 'low_stock', None, user)
    return None
