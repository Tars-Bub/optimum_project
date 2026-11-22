from collections import defaultdict
from datetime import date, timedelta
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

PERIODS = [('week', '7 days'), ('month', '30 days'), ('quarter', 'Quarter'), ('ytd', 'Year to date')]


def _since(period):
    today = timezone.localdate()
    quarter_start = date(today.year, 3 * ((today.month - 1) // 3) + 1, 1)
    return {'week': today - timedelta(days=6), 'month': today - timedelta(days=29),
            'quarter': quarter_start, 'ytd': date(today.year, 1, 1)}.get(period, today - timedelta(days=6))


def _transactions(request, ctx):
    f = request.GET
    qs = Order.objects.exclude(status=Order.DRAFT).select_related('created_by', 'created_by__profile').prefetch_related('items', 'returns', 'documents')
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
        if digits and q.upper().startswith(('SL', 'SO')):
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
    ctx['range_label'] = dict(PERIODS).get(ctx['period'], '')
    period = ctx['period']
    by_bucket = defaultdict(Decimal)

    def bucket(d):
        if period == 'week':
            return d, d.strftime('%a')
        if period == 'month':
            start = since + timedelta(days=((d - since).days // 3) * 3)
            return start, start.strftime('%b %d').replace(' 0', ' ')
        if period == 'quarter':
            start = since + timedelta(days=((d - since).days // 7) * 7)
            return start, start.strftime('%b %d').replace(' 0', ' ')
        return date(d.year, d.month, 1), d.strftime('%b')
    labels = {}
    for o in rows:
        key, label = bucket(timezone.localtime(o.finalized_at).date())
        by_bucket[key] += o.total
        labels[key] = label
    peak = max(by_bucket.values(), default=Decimal('0'))
    chart = [{'label': labels[k], 'value': v, 'pct': max(int(v / peak * 100), 3) if peak else 0}
             for k, v in sorted(by_bucket.items())]
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
    peak = max((c['value'] for c in cats), default=0)
    for c in cats:
        c['pct'] = int(c['value'] / peak * 100) if peak else 0
        c['lowall'] = c['low'] + c['depleted']
    ctx.update({'cats': cats, 'totals': totals, 'cat_count': len(cats), 'low_all': totals['low'] + totals['depleted']})


AREAS = [('Sales', ('sale', 'payment', 'draft', 'return', 'exchange', 'void', 'maya')),
         ('Documents', ('document', 'invoice', 'receipt', 'purchase order', 'printed', 'reprint')),
         ('Access', ('logged', 'registration', 'staff', 'password', 'account', 'approved', 'rejected', 'login')),
         ('Inventory', ('stock', 'incoming', 'adjust', 'product', 'item', 'categor', 'import', 'export', 'backup', 'restore', 'data'))]
KINDS = [('SALE', 'cart', ('sale', 'payment', 'draft', 'maya')), ('VOID', 'alert', ('void',)),
         ('RETURN', 'refresh', ('return', 'exchange')), ('DOCUMENT', 'file', ('document', 'invoice', 'receipt', 'purchase order', 'printed', 'reprint')),
         ('STOCK', 'download', ('stock', 'incoming', 'adjust', 'product', 'categor', 'import')),
         ('ACCESS', 'user', ('logged', 'registration', 'staff', 'password', 'account')), ('DATA', 'database', ('export', 'backup', 'restore'))]


def _classify(action, table):
    a = action.lower()
    return next((name for name, keys in table if any(k in a for k in keys)), None)


def _log(request, ctx, own_only, feed=False):
    logs = AuditLog.objects.select_related('user', 'user__profile')
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
    rows = list(logs[:500])
    for l in rows:
        l.area = _classify(l.action, AREAS) or 'Inventory'
        kind = next(((n, i) for n, i, keys in KINDS if any(k in l.action.lower() for k in keys)), ('ACTIVITY', 'clock'))
        l.kind, l.icon = kind
    area = request.GET.get('area', 'all')
    ctx['counts'] = {'all': len(rows), **{n: sum(1 for l in rows if l.area == n) for n, _ in AREAS}}
    ctx['area'] = area
    ctx['areas'] = [('all', 'All')] + [(n, n) for n in ('Sales', 'Inventory', 'Documents', 'Access')]
    if area != 'all':
        rows = [l for l in rows if l.area == area]
    if feed:
        today = timezone.localdate()
        cutoff = today - timedelta(days=6)
        rows = [l for l in rows if timezone.localtime(l.created_at).date() >= cutoff]
        for l in rows:
            d = timezone.localtime(l.created_at).date()
            l.when = timezone.localtime(l.created_at).strftime('%I:%M %p').lstrip('0') if d == today else (
                'Yesterday' if d == today - timedelta(days=1) else d.strftime('%b %d'))
    ctx.update({'logs': rows[:200], 'q': q})


@login_required
def index(request):
    tab = request.GET.get('tab', 'transactions')
    ctx = {'tab': tab, 'periods': PERIODS, 'period': request.GET.get('period', 'month')}
    if tab == 'audit' and not request.user.profile.is_admin:
        messages.error(request, 'The Audit Log is for the Admin / Owner only.')
        return redirect('/reports/?tab=transactions')
    if tab == 'sales':
        _sales(request, ctx)
    elif tab == 'inventory':
        _inventory(request, ctx)
    elif tab == 'activity':
        _log(request, ctx, own_only=not request.user.profile.is_admin, feed=True)
    elif tab == 'audit':
        _log(request, ctx, own_only=False)
    else:
        ctx['tab'] = 'transactions'
        _transactions(request, ctx)
    return render(request, 'reports/index.html', ctx)
