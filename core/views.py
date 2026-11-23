from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from catalog.models import Category, Product
from sales.models import Order, OrderItem


def health(request):
    """Used by the host / uptime monitor to check the app is alive."""
    return JsonResponse({'status': 'ok'})


@login_required
def dashboard(request):
    today = timezone.localdate()
    line = ExpressionWrapper(F('quantity') * F('unit_price'),
                             output_field=DecimalField(max_digits=14, decimal_places=2))
    sales_today = OrderItem.objects.filter(
        order__status=Order.FINAL, order__finalized_at__date=today
    ).aggregate(t=Sum(line))['t'] or Decimal('0')
    products = Product.objects.filter(is_active=True)
    ctx = {
        'sales_today': sales_today,
        'low_items': products.filter(quantity__gt=0, quantity__lte=F('reorder_level')).count(),
        'depleted_items': products.filter(quantity__lte=0).count(),
        'total_items': products.count(),
        'categories': Category.objects.count(),
        'low_total': products.filter(quantity__lte=F('reorder_level')).count(),
        'urgent': products.filter(quantity__lte=0).count(),
        'greeting': 'Good morning' if timezone.localtime().hour < 12 else (
            'Good afternoon' if timezone.localtime().hour < 18 else 'Good evening'),
        'first_name': (request.user.first_name or request.user.username).split()[0],
        'today': today,
        'recent': Order.objects.exclude(status=Order.DRAFT).prefetch_related('items')
                       .order_by('-finalized_at', '-id')[:6],
    }
    return render(request, 'core/dashboard.html', ctx)


@login_required
def search(request):
    """Top-bar search across items, sales and printed documents."""
    from documents.models import Document
    q = request.GET.get('q', '').strip()
    items = orders = docs = []
    if q:
        items = Product.objects.filter(is_active=True).filter(
            Q(name__icontains=q) | Q(code__icontains=q)).select_related('category')[:20]
        cond = Q(client_name__icontains=q) | Q(client_business__icontains=q) | Q(po_number__icontains=q)
        digits = ''.join(ch for ch in q if ch.isdigit())
        if digits and q.upper().startswith(('SL', 'SO')):
            cond |= Q(pk=int(digits))
        orders = Order.objects.exclude(status=Order.DRAFT).filter(cond).prefetch_related('items')[:20]
        docs = Document.objects.filter(Q(number__icontains=q)).select_related('order', 'purchase_order')[:20]
    return render(request, 'core/search.html', {'q': q, 'items': items, 'orders': orders, 'docs': docs})


@login_required
def style_guide(request):
    tab = request.GET.get('tab', 'foundations')
    if tab not in ('foundations', 'components', 'patterns'):
        tab = 'foundations'
    return render(request, 'core/style_guide.html', {'tab': tab})
