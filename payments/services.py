import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from core.utils import audit
from sales.models import Order

from . import maya
from .models import MayaPayment

REUSE_WINDOW = timedelta(minutes=30)
DEMO_PREFIX = 'demo-'


class PaymentError(ValueError):
    """The payment cannot be started (for example the order is not finalized or already paid)."""


def public_base(request):
    """Absolute base URL Maya sends the customer back to. Set SITE_URL on the cloud host."""
    return settings.SITE_URL or request.build_absolute_uri('/').rstrip('/')


def checkout_items(order, amount):
    """Item lines for the checkout. A balance payment is one line so the lines add up to the amount."""
    if amount == order.total:
        return [{'name': it.product.name[:120], 'code': it.product.code, 'quantity': it.quantity,
                 'amount': {'value': float(it.unit_price)},
                 'totalAmount': {'value': float(it.line_total)}}
                for it in order.items.select_related('product')]
    return [{'name': f'Balance for {order.number}', 'quantity': 1,
             'amount': {'value': float(amount)}, 'totalAmount': {'value': float(amount)}}]


def start_checkout(order, user, base_url):
    """Create a Maya checkout for the unpaid balance of a finalized order."""
    if order.status != Order.FINAL:
        raise PaymentError('Only finalized sales can be paid with Maya.')
    amount = order.balance
    if amount <= 0:
        raise PaymentError(f'{order.number} is already fully paid.')

    # Do not open a second checkout while a recent one for the same amount is still waiting.
    recent = order.maya_payments.filter(status=MayaPayment.PENDING, amount=amount,
                                        created_at__gte=timezone.now() - REUSE_WINDOW).first()
    if recent:
        return recent

    reference = f'{order.number}-{uuid.uuid4().hex[:16]}'
    back = base_url + reverse('payments:maya_return', args=[reference])
    try:
        data = maya.create_checkout(
            reference, amount, checkout_items(order, amount),
            {'success': f'{back}?result=success', 'failure': f'{back}?result=failure',
             'cancel': f'{back}?result=cancel'},
            metadata={'order': order.number})
    except maya.MayaError as exc:
        if settings.DEMO_PAYMENTS:
            return _demo_checkout(order, amount, user, reference, base_url, exc)
        # keep a record so the Maya Payments list shows the attempt that did not go through
        MayaPayment.objects.create(order=order, reference=reference, amount=amount, created_by=user,
                                   status=MayaPayment.FAILED, maya_status='NOT_CREATED', note=str(exc)[:200])
        audit(user, 'Maya checkout failed', f'{order.number} {exc}'[:200])
        raise
    payment = MayaPayment.objects.create(
        order=order, reference=reference, checkout_id=data['checkoutId'],
        checkout_url=data['redirectUrl'], amount=amount, created_by=user,
        maya_status='PENDING_PAYMENT')
    audit(user, 'Maya checkout created', f'{order.number} {amount} {reference}')
    return payment


def _demo_checkout(order, amount, user, reference, base_url, exc):
    """DEMO_PAYMENTS only: Maya failed, so open a simulated checkout page on this site instead."""
    payment = MayaPayment.objects.create(
        order=order, reference=reference, checkout_id=DEMO_PREFIX + uuid.uuid4().hex[:16],
        checkout_url=base_url + reverse('payments:demo_pay', args=[reference]), amount=amount,
        created_by=user, maya_status='DEMO_PENDING',
        note='DEMO MODE: simulated checkout, Maya could not be reached. Nothing is charged.')
    audit(user, 'Maya demo checkout created', f'{order.number} {amount} {reference} ({str(exc)[:80]})')
    return payment


def complete_demo_payment(payment, success=True):
    """Finish a simulated checkout: mark it paid (and add to the order) or cancel it."""
    if not payment.is_demo:
        raise PaymentError('Only demo checkouts can be simulated.')
    with transaction.atomic():
        locked = MayaPayment.objects.select_for_update().get(pk=payment.pk)
        if locked.is_final:
            return locked
        if success:
            order = Order.objects.select_for_update().get(pk=locked.order_id)
            order.amount_paid = min(order.amount_paid + locked.amount, order.total)
            order.save(update_fields=['amount_paid'])
            locked.status = MayaPayment.PAID
            locked.maya_status = 'DEMO_SUCCESS'
            locked.paid_at = timezone.now()
            locked.note = 'DEMO MODE: payment simulated. Nothing was charged by Maya.'
            audit(None, 'Maya demo payment simulated', f'{order.number} {locked.amount} {locked.reference}')
        else:
            locked.status = MayaPayment.CANCELLED
            locked.maya_status = 'DEMO_CANCELLED'
        locked.save()
        return locked


def sync_payment(payment):
    """Ask Maya for the real status of a payment and apply it. Safe to call any number of times.

    The browser redirect and the webhook only tell us *when* to look; the status itself always
    comes from Maya's API (called with the secret key), so a forged request cannot mark an order paid.
    """
    if payment.is_final or payment.is_demo:     # a demo checkout has nothing to look up at Maya
        return payment
    try:
        data = (maya.get_payment(payment.checkout_id) if payment.checkout_id
                else maya.get_payment_by_rrn(payment.reference))
    except maya.MayaError as exc:
        if exc.status_code == 404:      # Maya has no payment record yet: the customer has not paid
            return payment
        raise
    record = maya.first_record(data)
    status = maya.read_status(record)
    if not status:
        return payment
    charged = maya.read_amount(record)

    with transaction.atomic():
        locked = MayaPayment.objects.select_for_update().get(pk=payment.pk)
        if locked.is_final:
            return locked
        locked.maya_status = status
        if status in maya.SUCCESS:
            if charged is not None and charged != locked.amount:
                locked.note = f'Amount mismatch: Maya {charged}, expected {locked.amount}. Not applied.'
                locked.save(update_fields=['maya_status', 'note'])
                audit(None, 'Maya amount mismatch', f'{locked.reference} {charged} vs {locked.amount}')
                return locked
            order = Order.objects.select_for_update().get(pk=locked.order_id)
            order.amount_paid = min(order.amount_paid + locked.amount, order.total)
            order.save(update_fields=['amount_paid'])
            locked.status = MayaPayment.PAID
            locked.paid_at = timezone.now()
            if order.status == Order.VOID:
                locked.note = 'The order was voided before payment arrived: refund this payment in Maya.'
            audit(None, 'Maya payment received', f'{order.number} {locked.amount} {locked.reference}')
        elif status in maya.FAILED:
            locked.status = MayaPayment.FAILED
            audit(None, 'Maya payment failed', f'{locked.order.number} {locked.reference}')
        elif status in maya.EXPIRED:
            locked.status = MayaPayment.EXPIRED
        elif status in maya.CANCELLED:
            locked.status = MayaPayment.CANCELLED
        locked.save()
        return locked
