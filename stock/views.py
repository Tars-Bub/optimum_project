from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render

from catalog.models import Category, Product
from core.utils import audit

from .forms import AdjustForm, IncomingForm
from .models import StockMovement
from .services import apply_movement, set_quantity


@login_required
def index(request):
    tab = request.GET.get('tab', 'levels')
    incoming_form, adjust_form = IncomingForm(), AdjustForm()

    if request.method == 'POST':
        kind = request.POST.get('form')
        if kind == 'incoming':
            incoming_form = IncomingForm(request.POST)
            if incoming_form.is_valid():
                d = incoming_form.cleaned_data
                apply_movement(d['product'], d['quantity'], 'incoming', request.user,
                               note=d['note'], reference=d['reference'])
                audit(request.user, 'Incoming stock', f"{d['product'].code} +{d['quantity']}")
                messages.success(request, f"Recorded {d['quantity']} x {d['product'].name}.")
                return redirect('/stock/?tab=incoming')
            tab = 'incoming'
        elif kind == 'adjust':
            adjust_form = AdjustForm(request.POST)
            if adjust_form.is_valid():
                d = adjust_form.cleaned_data
                move = set_quantity(d['product'], d['counted'], request.user, note=d['reason'])
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
           'all_categories': Category.objects.all()}

    if tab == 'levels':
        items = products
        if q:
            items = items.filter(Q(name__icontains=q) | Q(code__icontains=q))
        if cat.isdigit():
            items = items.filter(category_id=int(cat))
        ctx['items'] = items[:300]
    elif tab == 'movements':
        moves = StockMovement.objects.select_related('product', 'user')
        if q:
            moves = moves.filter(Q(product__name__icontains=q) | Q(product__code__icontains=q)
                                 | Q(reference__icontains=q))
        ctx['moves'] = moves[:200]
    elif tab == 'alerts':
        ctx['alerts'] = alerts
    return render(request, 'stock/index.html', ctx)
