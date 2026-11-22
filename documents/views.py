from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from catalog.models import Product
from core.utils import audit
from sales.models import Order

from .models import Document, PurchaseOrder, PurchaseOrderItem

TYPES = {'invoice': Document.INVOICE, 'delivery': Document.DELIVERY, 'po': Document.PO}


def _ctx(tab, **extra):
    base = {'tab': tab, 'doc_count': Document.objects.count()}
    base.update(extra)
    return base


def _form_page(request, tab, order=None, po=None, error=None, number=''):
    ctx = _ctx(tab, order=order, po=po, error=error, number=number)
    if tab == 'po':
        pos = PurchaseOrder.objects.prefetch_related('items')[:50]
        low = Product.objects.filter(is_active=True, quantity__lte=F('reorder_level'))
        ctx.update({'pos': pos, 'products': Product.objects.filter(is_active=True),
                    'suggested': [(p, max(p.reorder_level * 2 - p.quantity, 1)) for p in low]})
        ctx['existing'] = po.documents.first() if po else None
    else:
        ctx['orders'] = Order.objects.filter(status=Order.FINAL).order_by('-finalized_at')[:50]
        ctx['existing'] = order.documents.filter(doc_type=TYPES[tab]).first() if order else None
    return render(request, 'documents/index.html', ctx)


@login_required
def index(request):
    tab = request.GET.get('tab', 'invoice')
    if tab == 'reprint':
        q = request.GET.get('q', '').strip()
        docs = Document.objects.select_related('order', 'purchase_order', 'printed_by')
        if q:
            docs = docs.filter(Q(number__icontains=q) | Q(order__client_name__icontains=q)
                               | Q(order__client_business__icontains=q) | Q(purchase_order__supplier__icontains=q))
        return render(request, 'documents/index.html', _ctx(tab, docs=docs[:100], q=q))
    if tab not in TYPES:
        tab = 'invoice'
    order = po = None
    if tab == 'po':
        if request.GET.get('po'):
            po = PurchaseOrder.objects.prefetch_related('items__product').filter(pk=request.GET['po']).first()
    elif request.GET.get('order'):
        order = (Order.objects.filter(pk=request.GET['order'], status=Order.FINAL)
                 .prefetch_related('items__product').first())
    return _form_page(request, tab, order, po)


@login_required
@require_POST
def po_create(request):
    supplier = request.POST.get('supplier', '').strip()
    codes, qtys, costs = (request.POST.getlist(k) for k in ('code', 'qty', 'cost'))
    if not supplier:
        messages.error(request, 'Enter the supplier for this purchase order.')
        return redirect('/documents/?tab=po')
    lines = []
    for code, qty, cost in zip(codes, qtys, costs):
        code = code.split('\u2014')[0].strip()
        if not code and not qty:
            continue
        product = Product.objects.filter(code__iexact=code, is_active=True).first()
        try:
            n = int(qty)
            c = Decimal(cost) if cost.strip() else (product.unit_cost if product else Decimal('0'))
        except (ValueError, InvalidOperation):
            n, c = 0, Decimal('0')
        if product is None or n < 1 or c < 0:
            messages.error(request, f'Check the line for "{code or "?"}": use an existing item code and a quantity of 1 or more.')
            return redirect('/documents/?tab=po')
        lines.append((product, n, c))
    if not lines:
        messages.error(request, 'Add at least one item to the purchase order.')
        return redirect('/documents/?tab=po')
    with transaction.atomic():
        po = PurchaseOrder.objects.create(supplier=supplier, created_by=request.user)
        for product, n, c in lines:
            PurchaseOrderItem.objects.create(purchase_order=po, product=product, quantity=n, unit_cost=c)
    audit(request.user, 'Purchase order created', f'{po.number} for {supplier}')
    messages.success(request, f'{po.number} created. Record the serial number to print it.')
    return redirect(f'/documents/?tab=po&po={po.pk}')


@login_required
@require_POST
def print_doc(request):
    tab = request.POST.get('doc_type', 'invoice')
    if tab not in TYPES:
        tab = 'invoice'
    doc_type = TYPES[tab]
    order = po = None
    if tab == 'po':
        po = get_object_or_404(PurchaseOrder.objects.prefetch_related('items__product'), pk=request.POST.get('po'))
    else:
        order = get_object_or_404(Order.objects.prefetch_related('items__product'),
                                  pk=request.POST.get('order'), status=Order.FINAL)
    number = request.POST.get('number', '').strip()
    error = None
    if not number:
        error = 'Required: enter the serial number printed on the form.'
    elif Document.objects.filter(doc_type=doc_type, number__iexact=number).exists():
        error = 'Duplicate: that document number was already used.'
    elif (po.documents.exists() if po else order.documents.filter(doc_type=doc_type).exists()):
        error = 'This record already has this document. Use Reprint instead.'
    if error:
        return _form_page(request, tab, order, po, error, number)
    doc = Document.objects.create(doc_type=doc_type, number=number, order=order, purchase_order=po,
                                  printed_by=request.user)
    audit(request.user, f'{doc.get_doc_type_display()} printed', f'{doc.number} for {(order or po).number}')
    return redirect('documents:print_view', pk=doc.pk)


@login_required
def print_view(request, pk):
    """Print-only page: just the variable data, positioned to land on the pre-printed form."""
    doc = get_object_or_404(Document.objects.select_related('order', 'purchase_order'), pk=pk)
    if doc.purchase_order_id:
        items = doc.purchase_order.items.select_related('product')
    else:
        items = doc.order.items.select_related('product')
    return render(request, 'documents/print.html', {
        'doc': doc, 'order': doc.order, 'po': doc.purchase_order, 'items': items,
        'auto_print': request.GET.get('noprint') != '1'})


@login_required
@require_POST
def reprint(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    doc.reprint_count += 1
    doc.save(update_fields=['reprint_count'])
    audit(request.user, 'Document reprinted', f'{doc.number} (reprint #{doc.reprint_count})')
    return redirect('documents:print_view', pk=doc.pk)
