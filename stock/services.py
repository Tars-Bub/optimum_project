from django.db import transaction

from catalog.models import Product

from .models import StockMovement


class StockError(ValueError):
    """Raised when a stock change would make quantity on hand negative."""


def apply_movement(product, change, kind, user=None, note='', reference=''):
    """Change quantity on hand and record the movement, all in one transaction.

    The product row is locked first, so two staff selling the last item at the
    same time cannot both succeed.
    """
    with transaction.atomic():
        locked = Product.objects.select_for_update().get(pk=product.pk)
        new_qty = locked.quantity + change
        if new_qty < 0:
            raise StockError(f'Not enough stock for {locked.name} (available: {locked.quantity}).')
        locked.quantity = new_qty
        locked.save(update_fields=['quantity'])
        return StockMovement.objects.create(
            product=locked, kind=kind, change=change, balance_after=new_qty,
            note=note, reference=reference, user=user)


def set_quantity(product, counted, user=None, note=''):
    """Adjustment from a physical count: set on-hand to `counted`."""
    with transaction.atomic():
        locked = Product.objects.select_for_update().get(pk=product.pk)
        change = counted - locked.quantity
        if change == 0:
            return None
        return apply_movement(locked, change, 'adjustment', user, note=note)
