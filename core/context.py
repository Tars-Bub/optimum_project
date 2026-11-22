from django.apps import apps
from django.db.models import F
from django.urls import NoReverseMatch, reverse


def layout(request):
    """Sidebar items (with the active one marked) and the low-stock badge.

    Items whose screen does not exist yet are skipped, so the app also runs while it is being built up.
    """
    user = request.user
    if not user.is_authenticated:
        return {}
    profile = getattr(user, 'profile', None)
    is_admin = bool(profile and profile.role == 'admin')
    match = request.resolver_match
    view_name = match.view_name if match else ''

    low = 0
    if apps.is_installed('catalog'):
        from catalog.models import Product
        low = Product.objects.filter(is_active=True, quantity__lte=F('reorder_level')).count()

    items = [
        ('Dashboard', 'dashboard', 'core:dashboard', ('core:dashboard',), 0),
        ('Categories & Items', 'box', 'catalog:products', ('catalog:',), 0),
        ('Stock', 'layers', 'stock:index', ('stock:',), low),
        ('Sales', 'cart', 'sales:index', ('sales:index', 'sales:cart', 'sales:draft'), 0),
        ('Returns & Voids', 'refresh', 'sales:returns_index', ('sales:returns',), 0),
        ('Documents', 'file', 'documents:index', ('documents:',), 0),
        ('Reports & Search', 'chart', 'reports:index', ('reports:',), 0),
        ('Data', 'database', 'data:index', ('data:',), 0),
        ('Maya Payments', 'card', 'payments:index', ('payments:',), 0),
        ('SMS Messages', 'message', 'notifications:index', ('notifications:',), 0),
    ]
    if is_admin:
        items.append(('Staff Accounts', 'users', 'accounts:staff', ('accounts:staff',), 0))
    nav_items = []
    for label, icon, name, prefixes, badge in items:
        try:
            url = reverse(name)
        except NoReverseMatch:
            continue
        nav_items.append({'label': label, 'icon': icon, 'url': url, 'badge': badge,
                          'active': any(view_name.startswith(p) for p in prefixes)})
    name = profile.display_name if profile else user.username
    initials = ''.join(w[0] for w in name.split()[:2]).upper() or 'U'
    return {'nav_items': nav_items, 'is_admin': is_admin, 'user_name': name, 'user_initials': initials,
            'user_role': (profile.position or profile.get_role_display().split(' /')[0]) if profile else '',
            'low_total': low, 'style_active': view_name.startswith('core:style')}
