from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.utils import audit
from sales.models import Order

from .models import Document

TYPES = {'invoice': Document.INVOICE, 'delivery': Document.DELIVERY}


def _form_page(request, tab, order=None, error=None, number=''):
    orders = Order.objects.filter(status=Order.FINAL).order_by('-finalized_at')[:50]
    return render(request, 'documents/index.html', {
        'tab': tab, 'orders': orders, 'order': order, 'error': error, 'number': number,
        'existing': order.documents.filter(doc_type=TYPES[tab]).first() if order else None})


@login_required
def index(request):
    tab = request.GET.get('tab', 'invoice')
    if tab == 'reprint':
        q = request.GET.get('q', '').strip()
        docs = Document.objects.select_related('order', 'printed_by')
        if q:
            docs = docs.filter(Q(number__icontains=q) | Q(order__client_name__icontains=q)
                               | Q(order__client_business__icontains=q))
        return render(request, 'documents/index.html', {'tab': tab, 'docs': docs[:100], 'q': q})
    if tab not in TYPES:
        tab = 'invoice'
    order = None
    if request.GET.get('order'):
        order = (Order.objects.filter(pk=request.GET['order'], status=Order.FINAL)
                 .prefetch_related('items__product').first())
    return _form_page(request, tab, order)


@login_required
@require_POST
def print_doc(request):
    tab = request.POST.get('doc_type', 'invoice')
    if tab not in TYPES:
        tab = 'invoice'
    order = get_object_or_404(Order.objects.prefetch_related('items__product'),
                              pk=request.POST.get('order'), status=Order.FINAL)
    number = request.POST.get('number', '').strip()
    doc_type = TYPES[tab]
    error = None
    if not number:
        error = 'Required: enter the serial number printed on the form.'
    elif Document.objects.filter(doc_type=doc_type, number__iexact=number).exists():
        error = 'Duplicate: that document number was already used.'
    elif order.documents.filter(doc_type=doc_type).exists():
        error = 'This order already has this document. Use Reprint instead.'
    if error:
        return _form_page(request, tab, order, error, number)
    doc = Document.objects.create(doc_type=doc_type, number=number, order=order,
                                  printed_by=request.user)
    audit(request.user, f'{doc.get_doc_type_display()} printed', f'{doc.number} for {order.number}')
    return redirect('documents:print_view', pk=doc.pk)


@login_required
def print_view(request, pk):
    """Print-only page: just the variable data, positioned to land on the pre-printed form."""
    doc = get_object_or_404(Document.objects.select_related('order').prefetch_related('order__items__product'), pk=pk)
    return render(request, 'documents/print.html', {
        'doc': doc, 'order': doc.order, 'items': doc.order.items.all(),
        'auto_print': request.GET.get('noprint') != '1'})


@login_required
@require_POST
def reprint(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    doc.reprint_count += 1
    doc.save(update_fields=['reprint_count'])
    audit(request.user, 'Document reprinted', f'{doc.number} (reprint #{doc.reprint_count})')
    return redirect('documents:print_view', pk=doc.pk)

