from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from stock.services import apply_movement

from .models import Order, ReturnLine, ReturnRecord


def get_cart(request, create=False):
    """The open draft order for this browser session."""
    order = None
    order_id = request.session.get('cart_order')
    if order_id:
        order = Order.objects.filter(pk=order_id, status=Order.DRAFT).first()
    if order is None:
        request.session.pop('cart_order', None)
        if create:
            order = Order.objects.create(created_by=request.user)
            request.session['cart_order'] = order.pk
    return order


def parse_money(raw):
    try:
        value = Decimal(str(raw).replace(',', '').strip())
    except (InvalidOperation, ValueError):
        raise ValueError('Enter a valid amount.')
    if value < 0:
        raise ValueError('Amount cannot be negative.')
    return value.quantize(Decimal('0.01'))


def finalize_order(order, user):
    """Finalize a sale: check stock, deduct it, log movements and lock the order, all or nothing."""
    with transaction.atomic():
        locked = Order.objects.select_for_update().get(pk=order.pk)
        if locked.status != Order.DRAFT:
            raise ValueError('This sale was already finalized.')
        items = list(locked.items.select_related('product'))
        if not items:
            raise ValueError('The cart is empty.')
        for item in items:
            apply_movement(item.product, -item.quantity, 'sale', user, reference=locked.number)
        locked.status = Order.FINAL
        locked.finalized_at = timezone.now()
        locked.save(update_fields=['status', 'finalized_at'])
    return locked


def process_return(order, user, kind, reason, quantities, replacement=None):
    """quantities: {OrderItem.pk: qty}. Returns the saved ReturnRecord."""
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.status != Order.FINAL:
            raise ValueError('Only finalized orders can have returns.')
        items = {i.pk: i for i in order.items.select_related('product')}
        lines, returned_value, returned_qty = [], Decimal('0'), 0
        for pk, qty in quantities.items():
            if qty <= 0:
                continue
            item = items.get(pk)
            if item is None or qty > item.remaining:
                raise ValueError('Return quantity is more than what was sold.')
            lines.append((item, qty))
            returned_value += item.unit_price * qty
            returned_qty += qty
        if not lines:
            raise ValueError('Choose at least one item to return.')
        if kind == ReturnRecord.EXCHANGE and replacement is None:
            raise ValueError('Choose the replacement item for an exchange.')

        record = ReturnRecord.objects.create(order=order, kind=kind, reason=reason,
                                             created_by=user, replacement_product=replacement)
        move_kind = 'return' if kind == ReturnRecord.RETURN else 'exchange_in'
        for item, qty in lines:
            apply_movement(item.product, qty, move_kind, user, reference=order.number, note=reason)
            item.returned_qty += qty
            item.save(update_fields=['returned_qty'])
            ReturnLine.objects.create(record=record, item=item, quantity=qty)

        if kind == ReturnRecord.EXCHANGE:
            apply_movement(replacement, -returned_qty, 'exchange_out', user,
                           reference=order.number, note=reason)
            record.refund_amount = returned_value - replacement.price * returned_qty
        else:
            record.refund_amount = returned_value
        record.save(update_fields=['refund_amount'])
        return record


def void_order(order, user, reason):
    """Cancel a finalized sale and put the not-yet-returned quantities back in stock."""
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.status != Order.FINAL:
            raise ValueError('Only finalized orders can be voided.')
        for item in order.items.select_related('product'):
            if item.remaining > 0:
                apply_movement(item.product, item.remaining, 'void', user,
                               reference=order.number, note=reason)
        order.status = Order.VOID
        order.voided_at = timezone.now()
        order.void_reason = reason
        order.save(update_fields=['status', 'voided_at', 'void_reason'])
    return order

