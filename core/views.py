from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from catalog.models import Product
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
        'recent': Order.objects.exclude(status=Order.DRAFT).prefetch_related('items')
                       .order_by('-finalized_at', '-id')[:6],
    }
    return render(request, 'core/dashboard.html', ctx)
