from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def peso(value):
    try:
        value = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        value = Decimal('0')
    sign = '-' if value < 0 else ''
    return f'{sign}₱{abs(value):,.2f}'
