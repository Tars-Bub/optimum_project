import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from sales.models import Order

from . import maya
from .models import MayaPayment
from .services import PaymentError, public_base, start_checkout, sync_payment

LABELS = {'pending': 'Waiting for payment', 'paid': 'Paid', 'failed': 'Payment failed',
          'expired': 'Checkout expired', 'cancelled': 'Cancelled'}


def _qr_svg(url):
    try:
        import segno
    except ImportError:  # the QR picture is a convenience; the link still works without it
        return ''
    return mark_safe(segno.make(url, error='m').svg_inline(scale=4, border=1, dark='#2b3946'))


@login_required
def index(request):
    payments = MayaPayment.objects.select_related('order')[:200]
    return render(request, 'payments/index.html', {'payments': payments})


@login_required
def pay(request, order_id):
    """Confirm the amount, then create the Maya checkout (POST)."""
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), pk=order_id)
    if request.method == 'POST':
        try:
            payment = start_checkout(order, request.user, public_base(request))
        except (PaymentError, maya.MayaError) as exc:
            messages.error(request, str(exc))
            return redirect('payments:maya_pay', order_id=order.pk)
        return redirect('payments:maya_detail', pk=payment.pk)
    return render(request, 'payments/pay.html', {
        'order': order, 'attempts': order.maya_payments.all()[:10],
        'can_pay': order.status == Order.FINAL and order.balance > 0})


@login_required
def detail(request, pk):
    """Staff page: shows the checkout link and QR code for the customer and the live status."""
    payment = get_object_or_404(MayaPayment.objects.select_related('order'), pk=pk)
    return render(request, 'payments/detail.html', {
        'payment': payment, 'label': LABELS[payment.status],
        'qr_svg': _qr_svg(payment.checkout_url) if payment.checkout_url else ''})


@login_required
@require_POST
def check(request, pk):
    payment = get_object_or_404(MayaPayment, pk=pk)
    try:
        payment = sync_payment(payment)
    except maya.MayaError as exc:
        messages.error(request, str(exc))
    else:
        messages.info(request, f'Status: {LABELS[payment.status]}.')
    return redirect('payments:maya_detail', pk=payment.pk)


@login_required
def status_json(request, pk):
    """Polled by the staff page every few seconds while the customer pays."""
    payment = get_object_or_404(MayaPayment, pk=pk)
    try:
        payment = sync_payment(payment)
    except maya.MayaError:
        pass                                    # keep showing the last known status
    return JsonResponse({'status': payment.status, 'label': LABELS[payment.status],
                         'maya_status': payment.maya_status, 'final': payment.is_final})


def maya_return(request, reference):
    """Where Maya sends the customer after checkout. Public on purpose: the customer's phone is
    not logged in. It shows only the order number and amount, and re-checks the status with Maya
    instead of trusting the `result` in the address."""
    payment = get_object_or_404(MayaPayment.objects.select_related('order'), reference=reference)
    unverified = False
    if not payment.is_final:
        try:
            payment = sync_payment(payment)
        except maya.MayaError:
            unverified = True
    result = request.GET.get('result', '')
    waiting = not payment.is_final and result != 'cancel'
    return render(request, 'payments/result.html', {
        'payment': payment, 'result': result, 'waiting': waiting, 'unverified': unverified})


@csrf_exempt
@require_POST
def maya_webhook(request):
    """Maya calls this when a payment changes. We only use it as a signal to look the payment up
    again with our secret key, so the content of the request is never trusted as proof of payment."""
    try:
        payload = json.loads(request.body or b'{}')
    except ValueError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'error': 'Invalid payload.'}, status=400)
    reference = str(payload.get('requestReferenceNumber') or '')
    checkout_id = str(payload.get('id') or payload.get('checkoutId') or '')
    payment = None
    if reference:
        payment = MayaPayment.objects.filter(reference=reference).first()
    if payment is None and checkout_id:
        payment = MayaPayment.objects.filter(checkout_id=checkout_id).first()
    if payment is None:
        return JsonResponse({'status': 'ignored'})
    try:
        sync_payment(payment)
    except maya.MayaError:
        return JsonResponse({'status': 'retry'}, status=502)   # ask Maya to send it again later
    return JsonResponse({'status': 'ok'})
