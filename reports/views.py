from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import F, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from catalog.models import Category, Product
from core.models import AuditLog
from sales.models import Order, OrderItem

PERIODS = [('today', 'Today'), ('week', '7 days'), ('month', '30 days'), ('all', 'All time')]


def _since(period):
    today = timezone.localdate()
    return {'today': today, 'week': today - timedelta(days=6),
            'month': today - timedelta(days=29)}.get(period)


def _transactions(request, ctx):
    f = request.GET
    qs = Order.objects.exclude(status=Order.DRAFT).prefetch_related('items', 'returns', 'documents')
    d1, d2 = parse_date(f.get('from', '')), parse_date(f.get('to', ''))
    if d1:
        qs = qs.filter(finalized_at__date__gte=d1)
    if d2:
        qs = qs.filter(finalized_at__date__lte=d2)
    q = f.get('q', '').strip()
    if q:
        cond = (Q(client_name__icontains=q) | Q(client_business__icontains=q)
                | Q(po_number__icontains=q) | Q(documents__number__icontains=q))
        digits = ''.join(ch for ch in q if ch.isdigit())
        if digits and q.upper().startswith('SO'):
            cond |= Q(pk=int(digits))
        qs = qs.filter(cond).distinct()
    status = f.get('status', '')
    if status == 'voided':
        qs = qs.filter(status=Order.VOID)
    elif status == 'returned':
        qs = qs.filter(status=Order.FINAL, returns__isnull=False).distinct()
    elif status == 'completed':
        qs = qs.filter(status=Order.FINAL, returns__isnull=True)
    ctx.update({'orders': qs.order_by('-finalized_at', '-id')[:200], 'q': q, 'status': status,
                'date_from': f.get('from', ''), 'date_to': f.get('to', '')})


def _sales(request, ctx):
    since = _since(ctx['period'])
    orders = Order.objects.filter(status=Order.FINAL)
    items = OrderItem.objects.filter(order__status=Order.FINAL)
    if since:
        orders = orders.filter(finalized_at__date__gte=since)
        items = items.filter(order__finalized_at__date__gte=since)
    rows = list(orders.prefetch_related('items').order_by('-finalized_at'))
    by_day = defaultdict(Decimal)
    for o in rows:
        by_day[timezone.localtime(o.finalized_at).date()] += o.total
    peak = max(by_day.values(), default=Decimal('0'))
    chart = [{'label': d.strftime('%b %d'), 'value': v, 'pct': int(v / peak * 100) if peak else 0}
             for d, v in sorted(by_day.items())]
    top = (items.values('product__name').annotate(qty=Sum(F('quantity') - F('returned_qty')))
           .order_by('-qty').first())
    ctx.update({'rows': rows[:200], 'order_count': len(rows), 'chart': chart,
                'total_sales': sum((o.total for o in rows), Decimal('0')),
                'top_item': top['product__name'] if top and top['qty'] else '-'})


def _stock(request, ctx):
    since = _since(ctx['period'])
    base = Q(movements__created_at__date__gte=since) if since else Q()
    rows = list(Product.objects.filter(is_active=True).select_related('category').annotate(
        stock_in=Coalesce(Sum('movements__change', filter=base & Q(movements__change__gt=0)), 0),
        stock_out=Coalesce(Sum('movements__change', filter=base & Q(movements__change__lt=0)), 0),
    ))
    for r in rows:
        r.out_abs = -r.stock_out
        r.net = r.stock_in + r.stock_out
    ctx['rows'] = rows


def _inventory(request, ctx):
    cats = []
    totals = {'products': 0, 'units': 0, 'value': Decimal('0'), 'low': 0, 'depleted': 0}
    for cat in Category.objects.all():
        prods = list(Product.objects.filter(category=cat, is_active=True))
        row = {'name': cat.name, 'products': len(prods), 'units': sum(p.quantity for p in prods),
               'value': sum((p.quantity * p.unit_cost for p in prods), Decimal('0')),
               'low': sum(1 for p in prods if p.status == 'low'),
               'depleted': sum(1 for p in prods if p.status == 'depleted')}
        cats.append(row)
        for k in totals:
            totals[k] += row[k]
    ctx.update({'cats': cats, 'totals': totals})


def _log(request, ctx, own_only):
    logs = AuditLog.objects.select_related('user')
    if own_only:
        logs = logs.filter(user=request.user)
    else:
        who = request.GET.get('user', '')
        if who:
            logs = logs.filter(user__username=who)
        ctx['users'] = get_user_model().objects.order_by('username')
        ctx['who'] = who
    q = request.GET.get('q', '').strip()
    if q:
        logs = logs.filter(Q(action__icontains=q) | Q(detail__icontains=q))
    ctx.update({'logs': logs[:200], 'q': q})


@login_required
def index(request):
    tab = request.GET.get('tab', 'transactions')
    ctx = {'tab': tab, 'periods': PERIODS, 'period': request.GET.get('period', 'week')}
    if tab == 'audit' and not request.user.profile.is_admin:
        messages.error(request, 'The Audit Log is for the Admin / Owner only.')
        return redirect('/reports/?tab=transactions')
    if tab == 'sales':
        _sales(request, ctx)
    elif tab == 'stock':
        _stock(request, ctx)
    elif tab == 'inventory':
        _inventory(request, ctx)
    elif tab == 'activity':
        _log(request, ctx, own_only=True)
    elif tab == 'audit':
        _log(request, ctx, own_only=False)
    else:
        ctx['tab'] = 'transactions'
        _transactions(request, ctx)
    return render(request, 'reports/index.html', ctx)
