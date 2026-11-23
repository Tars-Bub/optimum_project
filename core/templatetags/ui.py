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


from django.utils.html import format_html  # noqa: E402
from django.utils.safestring import mark_safe  # noqa: E402

ICONS = {
    'dashboard': '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/>',
    'box': '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
    'layers': '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    'cart': '<circle cx="9" cy="20" r="1.5"/><circle cx="18" cy="20" r="1.5"/><path d="M2 3h3l2.5 12h11L21 7H6"/>',
    'refresh': '<path d="M21 12a9 9 0 0 1-15.5 6.2L3 16"/><path d="M3 12a9 9 0 0 1 15.5-6.2L21 8"/><path d="M21 3v5h-5M3 21v-5h5"/>',
    'file': '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
    'chart': '<path d="M3 3v18h18"/><path d="M8 16v-5M13 16V8M18 16v-8"/>',
    'database': '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    'card': '<rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/>',
    'users': '<circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0M16 4a4 4 0 0 1 0 8M22 21a7 7 0 0 0-5-6.7"/>',
    'bell': '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10 21a2 2 0 0 0 4 0"/>',
    'search': '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
    'user': '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    'logout': '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
    'plus': '<path d="M12 5v14M5 12h14"/>',
    'pencil': '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    'trash': '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6M10 11v6M14 11v6"/>',
    'download': '<path d="M12 3v12m0 0-4-4m4 4 4-4"/><path d="M4 17v3h16v-3"/>',
    'upload': '<path d="M12 15V3m0 0L8 7m4-4 4 4"/><path d="M4 17v3h16v-3"/>',
    'check': '<path d="m5 12 5 5L20 7"/>',
    'alert': '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17.5v.5"/>',
    'chevron': '<path d="m6 9 6 6 6-6"/>',
    'chevron-right': '<path d="m9 6 6 6-6 6"/>',
    'x': '<path d="M6 6l12 12M18 6 6 18"/>',
    'type': '<path d="M4 7V5h16v2M12 5v14M9 19h6"/>',
    'clock': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'dollar': '<path d="M12 2v20M17 6.5C16 5 14.3 4.5 12 4.5c-3 0-4.5 1.3-4.5 3s1.3 2.5 4.5 3 4.5 1.3 4.5 3.2-1.5 3.3-4.5 3.3c-2.5 0-4.3-.7-5.2-2.3"/>',
    'print': '<path d="M6 9V3h12v6M6 18H4v-7h16v7h-2"/><path d="M6 14h12v7H6z"/>',
    'message': '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/><path d="M8.5 11h7M8.5 14h4"/>',
    'calendar': '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
}


@register.simple_tag
def icon(name, size=18):
    return format_html('<svg class="ic" width="{0}" height="{0}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                       'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{1}</svg>',
                       size, mark_safe(ICONS.get(name, ICONS['box'])))


@register.filter
def initials(value):
    parts = str(value or '').replace('-', ' ').split()
    return ''.join(w[0] for w in parts[:2]).upper() or '?'


@register.filter
def money(value):
    """Plain amount without a currency sign (for cards that show the sign separately)."""
    try:
        return f'{Decimal(value):,.2f}'
    except (InvalidOperation, TypeError, ValueError):
        return '0.00'


@register.filter
def get(mapping, key):
    try:
        return mapping.get(key, 0)
    except AttributeError:
        return 0
