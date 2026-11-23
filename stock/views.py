from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone

from catalog.models import Category, Product
from core.utils import audit

from .forms import AdjustForm, IncomingForm
from .models import StockMovement
from .services import apply_movement, set_quantity


@login_required
def index(request):
    tab = request.GET.get('tab', 'levels')
    pre = Product.objects.filter(code__iexact=request.GET.get('item', ''), is_active=True).first()
    init = {'product': f'{pre.code} \u2014 {pre.name}'} if pre else {}
    incoming_form = IncomingForm(initial={**init, 'received_on': timezone.localdate()})
    adjust_form = AdjustForm(initial=init)

    if request.method == 'POST':
        kind = request.POST.get('form')
        if kind == 'incoming':
            incoming_form = IncomingForm(request.POST)
            if incoming_form.is_valid():
                d = incoming_form.cleaned_data
                apply_movement(d['product'], d['quantity'], 'incoming', request.user,
                               note=d['note'], reference=d['reference'], supplier=d['supplier'],
                               received_on=d['received_on'] or timezone.localdate())
                audit(request.user, 'Incoming stock', f"{d['product'].code} +{d['quantity']}")
                messages.success(request, f"Recorded {d['quantity']} x {d['product'].name}.")
                return redirect('/stock/?tab=incoming')
            tab = 'incoming'
        elif kind == 'adjust':
            adjust_form = AdjustForm(request.POST)
            if adjust_form.is_valid():
                d = adjust_form.cleaned_data
                reason = d['reason'] + (f": {d['note']}" if d['note'] else '')
                move = set_quantity(d['product'], d['counted'], request.user, note=reason)
                if move:
                    audit(request.user, 'Stock adjusted',
                          f"{d['product'].code} {move.change:+d} ({d['reason']})")
                    messages.success(request, f"{d['product'].name} adjusted to {d['counted']}.")
                else:
                    messages.info(request, 'Counted quantity matches the system, nothing to adjust.')
                return redirect('/stock/?tab=adjust')
            tab = 'adjust'

    q = request.GET.get('q', '').strip()
    cat = request.GET.get('category', '')
    products = Product.objects.filter(is_active=True).select_related('category')
    alerts = [p for p in products if p.status in ('low', 'depleted')]
    alerts.sort(key=lambda p: (p.quantity, p.name))
    ctx = {'tab': tab, 'q': q, 'cat': cat, 'incoming_form': incoming_form,
           'adjust_form': adjust_form, 'alert_count': len(alerts),
           'all_categories': Category.objects.all(),
           'movement_types': [('all', 'All'), ('in', 'In'), ('out', 'Out'), ('adjust', 'Adjust')]}

    if tab == 'levels':
        items = products
        if q:
            items = items.filter(Q(name__icontains=q) | Q(code__icontains=q))
        if cat.isdigit():
            items = items.filter(category_id=int(cat))
        ctx['items'] = items[:300]
    elif tab == 'movements':
        moves = StockMovement.objects.select_related('product', 'user')
        mtype = request.GET.get('type', 'all')
        groups = {'in': ['opening', 'incoming', 'return', 'exchange_in', 'void'],
                  'out': ['sale', 'exchange_out'], 'adjust': ['adjustment']}
        ctx['counts'] = {'all': moves.count(), **{k: moves.filter(kind__in=v).count() for k, v in groups.items()}}
        ctx['mtype'] = mtype
        if mtype in groups:
            moves = moves.filter(kind__in=groups[mtype])
        if q:
            moves = moves.filter(Q(product__name__icontains=q) | Q(product__code__icontains=q)
                                 | Q(reference__icontains=q))
        ctx['moves'] = moves[:200]
    elif tab == 'alerts':
        ctx['alerts'] = alerts
    return render(request, 'stock/index.html', ctx)
