from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import format_html
from django.views.decorators.http import require_POST

from catalog.models import Product
from core.utils import audit
from stock.services import StockError

from .models import Order, OrderItem, ReturnRecord
from .services import finalize_order, get_cart, parse_money, process_return, void_order

CLIENT_FIELDS = ['client_name', 'client_phone', 'client_business', 'client_tin', 'client_address',
                 'po_number', 'payment_terms']


# ---------------------------------------------------------------- Sales
@login_required
def index(request):
    if request.GET.get('resume'):
        draft = get_object_or_404(Order, pk=request.GET['resume'], status=Order.DRAFT)
        request.session['cart_order'] = draft.pk
        return redirect('sales:index')
    tab = request.GET.get('tab', 'new')
    ctx = {'tab': tab, 'draft_count': Order.objects.filter(status=Order.DRAFT).annotate(n=Count('items')).filter(n__gt=0).count()}
    if tab == 'drafts':
        ctx['drafts'] = (Order.objects.filter(status=Order.DRAFT)
                         .annotate(n=Count('items')).filter(n__gt=0)
                         .prefetch_related('items').order_by('-created_at'))
    else:
        q = request.GET.get('q', '').strip()
        products = Product.objects.filter(is_active=True)
        if q:
            products = products.filter(Q(name__icontains=q) | Q(code__icontains=q))
        cart = get_cart(request)
        ctx.update({'q': q, 'products': products[:40], 'avail': products.filter(quantity__gt=0).count(), 'cart': cart,
                    'cart_items': cart.items.select_related('product') if cart else []})
    return render(request, 'sales/index.html', ctx)


@login_required
@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    if product.quantity <= 0:
        messages.error(request, f'{product.name} is out of stock.')
        return redirect('sales:index')
    cart = get_cart(request, create=True)
    item, _ = OrderItem.objects.get_or_create(order=cart, product=product,
                                              defaults={'quantity': 0, 'unit_price': product.price})
    if item.quantity + 1 > product.quantity:
        messages.warning(request, f'Only {product.quantity} of {product.name} in stock.')
        if item.quantity == 0:
            item.delete()
    else:
        item.quantity += 1
        item.save(update_fields=['quantity'])
    return redirect('sales:index')


@login_required
@require_POST
def cart_update(request, item_id, op):
    cart = get_cart(request)
    item = get_object_or_404(OrderItem.objects.select_related('product'), pk=item_id, order=cart) if cart else None
    if item is None:
        return redirect('sales:index')
    if op == 'inc':
        if item.quantity + 1 > item.product.quantity:
            messages.warning(request, f'Only {item.product.quantity} of {item.product.name} in stock.')
        else:
            item.quantity += 1
            item.save(update_fields=['quantity'])
    elif op == 'dec' and item.quantity > 1:
        item.quantity -= 1
        item.save(update_fields=['quantity'])
    elif op == 'remove' or op == 'dec':
        item.delete()
    return redirect('sales:index')


@login_required
@require_POST
def cart_save(request):
    cart = get_cart(request)
    if cart is None or not cart.items.exists():
        messages.error(request, 'Add at least one item to the cart first.')
        return redirect('sales:index')
    for field in CLIENT_FIELDS:
        setattr(cart, field, request.POST.get(field, '').strip())
    raw_paid = request.POST.get('amount_paid', '').strip()
    action = request.POST.get('action')
    try:
        if raw_paid:
            cart.amount_paid = min(parse_money(raw_paid), cart.total)
        elif action == 'record_payment':
            raise ValueError('Enter the amount received.')
    except ValueError as exc:
        cart.save()
        messages.error(request, str(exc))
        return redirect('sales:index')
    cart.save()

    if action == 'save_draft':
        request.session.pop('cart_order', None)
        audit(request.user, 'Draft saved', cart.number)
        messages.success(request, f'{cart.number} saved as a draft.')
        return redirect('/sales/?tab=drafts')
    if action == 'record_payment':
        audit(request.user, 'Payment recorded', f'{cart.number} {cart.amount_paid}')
        messages.success(request, f'Payment recorded: {cart.payment_status}.')
        return redirect('sales:index')
    if action == 'finalize':
        try:
            order = finalize_order(cart, request.user)
        except (ValueError, StockError) as exc:
            messages.error(request, str(exc))
            return redirect('sales:index')
        request.session.pop('cart_order', None)
        audit(request.user, 'Sale finalized', f'{order.number} {order.total}')
        if order.client_phone:
            from notifications.services import send_receipt
            sms = send_receipt(order, request.user)
            if sms and sms.status != 'sent':
                messages.warning(request, f'The SMS receipt was not sent: {sms.detail}')
        link = reverse('documents:index') + f'?tab=invoice&order={order.pk}'
        if order.balance > 0:
            messages.success(request, format_html(
                '{} finalized. <a href="{}">Print the invoice</a> or '
                '<a href="{}">pay the {} balance with Maya</a>.',
                order.number, link, reverse('payments:maya_pay', args=[order.pk]), order.balance))
        else:
            messages.success(request, format_html(
                '{} finalized. <a href="{}">Print the invoice</a>.', order.number, link))
        return redirect('sales:index')
    return redirect('sales:index')


@login_required
@require_POST
def draft_delete(request, pk):
    draft = get_object_or_404(Order, pk=pk, status=Order.DRAFT)
    if request.session.get('cart_order') == draft.pk:
        request.session.pop('cart_order', None)
    audit(request.user, 'Draft deleted', draft.number)
    draft.delete()
    messages.success(request, 'Draft deleted.')
    return redirect('/sales/?tab=drafts')


@login_required
@require_POST
def payment_add(request, pk):
    order = get_object_or_404(Order, pk=pk, status=Order.FINAL)
    try:
        amount = parse_money(request.POST.get('amount', ''))
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        order.amount_paid = min(order.amount_paid + amount, order.total)
        order.save(update_fields=['amount_paid'])
        audit(request.user, 'Payment recorded', f'{order.number} +{amount}')
        messages.success(request, f'{order.number} is now {order.payment_status}.')
    nxt = request.POST.get('next', '')
    return redirect(nxt if nxt.startswith('/') and not nxt.startswith('//') else 'reports:index')


# ----------------------------------------------------- Returns & Voids
def _order_matches(q):
    qs = Order.objects.filter(status=Order.FINAL).prefetch_related('items')
    cond = (Q(client_name__icontains=q) | Q(client_business__icontains=q) | Q(po_number__icontains=q))
    digits = ''.join(ch for ch in q if ch.isdigit())
    if digits:
        cond |= Q(pk=int(digits))
    return qs.filter(cond)[:20]


@login_required
def returns_index(request):
    tab = request.GET.get('tab', 'return')
    q = request.GET.get('q', '').strip()
    order = None
    if request.GET.get('order'):
        order = (Order.objects.filter(pk=request.GET['order'], status=Order.FINAL)
                 .prefetch_related('items__product').first())
    return render(request, 'sales/returns.html', {
        'tab': tab, 'q': q, 'matches': _order_matches(q) if q else [],
        'order': order, 'products': Product.objects.filter(is_active=True)})


@login_required
@require_POST
def returns_process(request):
    order = get_object_or_404(Order, pk=request.POST.get('order'), status=Order.FINAL)
    kind = request.POST.get('kind', ReturnRecord.RETURN)
    reason = request.POST.get('reason', '').strip()
    back = f'/sales/returns/?tab=return&order={order.pk}'
    if kind not in (ReturnRecord.RETURN, ReturnRecord.EXCHANGE):
        kind = ReturnRecord.RETURN
    if not reason:
        messages.error(request, 'Enter the reason.')
        return redirect(back)
    quantities = {}
    for item in order.items.all():
        raw = request.POST.get(f'qty_{item.pk}', '0').strip() or '0'
        if not raw.isdigit():
            messages.error(request, 'Quantities must be whole numbers.')
            return redirect(back)
        quantities[item.pk] = int(raw)
    replacement = None
    if kind == ReturnRecord.EXCHANGE and request.POST.get('replacement', '').isdigit():
        replacement = Product.objects.filter(pk=int(request.POST['replacement']), is_active=True).first()
    try:
        record = process_return(order, request.user, kind, reason, quantities, replacement)
    except (ValueError, StockError) as exc:
        messages.error(request, str(exc))
        return redirect(back)
    audit(request.user, f'{record.get_kind_display()} processed', f'{order.number} {record.refund_amount}')
    if record.refund_amount >= 0:
        messages.success(request, f'{record.get_kind_display()} saved. Refund: ₱{record.refund_amount:,.2f}.')
    else:
        messages.success(request, f'Exchange saved. Customer pays the difference: ₱{-record.refund_amount:,.2f}.')
    return redirect('/sales/returns/?tab=return')


@login_required
@require_POST
def returns_void(request):
    if not request.user.profile.is_admin:
        messages.error(request, 'Voiding a sale is restricted to the Admin / Owner.')
        return redirect('/sales/returns/?tab=void')
    order = get_object_or_404(Order, pk=request.POST.get('order'), status=Order.FINAL)
    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, 'Enter the reason for the void.')
        return redirect(f'/sales/returns/?tab=void&order={order.pk}')
    try:
        void_order(order, request.user, reason)
    except (ValueError, StockError) as exc:
        messages.error(request, str(exc))
        return redirect(f'/sales/returns/?tab=void&order={order.pk}')
    audit(request.user, 'Sale voided', f'{order.number} ({reason})')
    messages.success(request, f'{order.number} voided and its items put back in stock.')
    return redirect('/sales/returns/?tab=void')
