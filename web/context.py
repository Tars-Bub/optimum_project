from django.urls import reverse

ITEMS = [('Dashboard', 'dashboard'), ('Categories & Products', 'products'), ('Stock', 'stock'),
         ('Sales', 'sales'), ('Returns & Voids', 'returns'), ('Documents', 'documents'),
         ('Reports & Search', 'reports'), ('Staff Accounts (Admin)', 'staff')]


def nav(request):
    current = request.resolver_match.url_name if request.resolver_match else ''
    return {'nav_items': [{'label': label, 'url': reverse(name), 'active': name == current}
                          for label, name in ITEMS]}
