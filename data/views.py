import io
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from openpyxl import Workbook, load_workbook

from catalog.models import Product
from core.decorators import admin_required
from core.utils import audit
from sales.models import Order, OrderItem
from stock.models import StockMovement
from stock.services import apply_movement

from .models import Backup
from .services import create_backup, ensure_daily_backup, restore_backup

MAX_UPLOAD = 10 * 1024 * 1024
CODE_NAMES = {'code', 'item code', 'sku', 'item', 'item_code', 'product code'}
QTY_NAMES = {'quantity', 'qty', 'quantity received', 'units', 'count'}
EXPORTS = [('items', 'Items', 'Product catalog and current quantities', 'box'),
           ('movements', 'Movements', 'Incoming, outgoing, and adjustments', 'layers'),
           ('sales', 'Sales', 'Completed sales and line items', 'cart'),
           ('transactions', 'Transactions', 'Sales, returns, and voided records', 'file')]


@login_required
def index(request):
    tab = request.GET.get('tab', 'import')
    if tab not in ('import', 'export', 'backup', 'restore'):
        tab = 'import'
    today = timezone.localdate()
    ctx = {'tab': tab, 'exports': EXPORTS, 'kind': request.GET.get('kind', 'items'),
           'date_from': request.GET.get('from', (today - timedelta(days=19)).isoformat()),
           'date_to': request.GET.get('to', today.isoformat()),
           'preview': request.session.get('import_preview')}
    if tab in ('backup', 'restore'):
        if tab == 'backup':
            ensure_daily_backup()
        ctx['backups'] = Backup.objects.all()[:12]
    return render(request, 'data/index.html', ctx)


# ----------------------------------------------------------------- import
def _header_map(row):
    cols = {}
    for i, cell in enumerate(row):
        label = str(cell or '').strip().lower()
        if label in CODE_NAMES and 'code' not in cols:
            cols['code'] = i
        elif label in QTY_NAMES and 'qty' not in cols:
            cols['qty'] = i
    return cols


@login_required
@require_POST
def import_upload(request):
    f = request.FILES.get('file')
    if not f or not f.name.lower().endswith('.xlsx'):
        messages.error(request, 'Choose an .xlsx file.')
        return redirect('/data/?tab=import')
    if f.size > MAX_UPLOAD:
        messages.error(request, 'The file is larger than 10 MB.')
        return redirect('/data/?tab=import')
    try:
        wb = load_workbook(io.BytesIO(f.read()), read_only=True, data_only=True)
        rows = list(wb.active.iter_rows(values_only=True))
    except Exception:
        messages.error(request, 'That file could not be read as an Excel workbook.')
        return redirect('/data/?tab=import')
    cols = _header_map(rows[0]) if rows else {}
    if 'code' not in cols or 'qty' not in cols:
        messages.error(request, 'The first row must have an "Item code" column and a "Quantity" column.')
        return redirect('/data/?tab=import')
    products = {p.code.upper(): p for p in Product.objects.filter(is_active=True)}
    out, seen = [], set()
    for n, row in enumerate(rows[1:], start=2):
        code = str(row[cols['code']] or '').strip().upper() if len(row) > cols['code'] else ''
        raw = row[cols['qty']] if len(row) > cols['qty'] else None
        if not code and raw in (None, ''):
            continue
        error = ''
        try:
            qty = int(float(raw))
            if qty < 1 or qty != float(raw):
                raise ValueError
        except (TypeError, ValueError):
            qty, error = 0, 'Quantity must be a whole number of 1 or more.'
        p = products.get(code)
        if not error and p is None:
            error = 'No active item with this code.'
        if not error and code in seen:
            error = 'Duplicate code in this file.'
        seen.add(code)
        out.append({'row': n, 'code': code, 'name': p.name if p else '', 'qty': qty, 'error': error})
    request.session['import_preview'] = {'file': f.name, 'rows': out}
    return redirect('/data/?tab=import')


@login_required
@require_POST
def import_confirm(request):
    prev = request.session.pop('import_preview', None)
    if request.POST.get('cancel') or not prev:
        return redirect('/data/?tab=import')
    done = 0
    for r in prev['rows']:
        if r['error']:
            continue
        p = Product.objects.filter(code=r['code'], is_active=True).first()
        if p:
            apply_movement(p, r['qty'], 'incoming', request.user, note='Excel import',
                           reference=prev['file'][:60])
            done += 1
    audit(request.user, 'Stock imported', f"{done} items from {prev['file']}")
    messages.success(request, f'Imported stock for {done} items.')
    return redirect('/data/?tab=import')


# ----------------------------------------------------------------- export
@login_required
def export_xlsx(request):
    kind = request.GET.get('kind', 'items')
    d1 = parse_date(request.GET.get('from', '')) or date(2000, 1, 1)
    d2 = parse_date(request.GET.get('to', '')) or timezone.localdate()
    wb = Workbook()
    ws = wb.active
    if kind == 'movements':
        ws.title = 'Movements'
        ws.append(['Date', 'Item code', 'Item', 'Type', 'Change', 'Balance', 'Reference', 'Supplier', 'Note', 'User'])
        for m in StockMovement.objects.select_related('product', 'user').filter(
                created_at__date__gte=d1, created_at__date__lte=d2).order_by('created_at'):
            ws.append([timezone.localtime(m.created_at).strftime('%Y-%m-%d %H:%M'), m.product.code, m.product.name,
                       m.get_kind_display(), m.change, m.balance_after, m.reference, m.supplier, m.note,
                       m.user.username if m.user else ''])
    elif kind in ('sales', 'transactions'):
        ws.title = kind.title()
        qs = Order.objects.exclude(status=Order.DRAFT) if kind == 'transactions' else Order.objects.filter(status=Order.FINAL)
        qs = qs.filter(finalized_at__date__gte=d1, finalized_at__date__lte=d2).prefetch_related('items__product')
        if kind == 'sales':
            ws.append(['Order', 'Date', 'Client', 'Item code', 'Item', 'Qty', 'Unit price', 'Line total'])
            for o in qs:
                for it in o.items.all():
                    ws.append([o.number, timezone.localtime(o.finalized_at).strftime('%Y-%m-%d %H:%M'), o.client_label,
                               it.product.code, it.product.name, it.quantity, float(it.unit_price), float(it.line_total)])
        else:
            ws.append(['Order', 'Date', 'Client', 'P.O. number', 'Total', 'Paid', 'Status'])
            for o in qs:
                ws.append([o.number, timezone.localtime(o.finalized_at).strftime('%Y-%m-%d %H:%M'), o.client_label,
                           o.po_number, float(o.total), float(o.amount_paid), o.status_label])
    else:
        kind = 'items'
        ws.title = 'Items'
        ws.append(['Item code', 'Name', 'Category', 'Unit cost', 'Price', 'Quantity', 'Reorder level'])
        for p in Product.objects.filter(is_active=True).select_related('category'):
            ws.append([p.code, p.name, p.category.name, float(p.unit_cost), float(p.price), p.quantity, p.reorder_level])
    buf = io.BytesIO()
    wb.save(buf)
    audit(request.user, 'Data exported', f'{kind} {d1} to {d2}')
    resp = HttpResponse(buf.getvalue(),
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = f'attachment; filename="optimum-{kind}-{timezone.localdate()}.xlsx"'
    return resp


# ------------------------------------------------------- backup / restore
@login_required
@require_POST
def backup_now(request):
    b = create_backup(request.user)
    audit(request.user, 'Backup created', f'{b.size_label}')
    messages.success(request, 'Backup created and verified.' if b.status == 'Verified' else 'Backup created.')
    return redirect('/data/?tab=backup')


@admin_required
@require_POST
def restore(request):
    backup = get_object_or_404(Backup, pk=request.POST.get('backup'))
    try:
        n = restore_backup(backup)
    except Exception as exc:
        messages.error(request, f'Restore failed, nothing was changed: {exc}')
        return redirect('/data/?tab=restore')
    messages.success(request, f'Restored {n} records from the backup of {backup.created_at:%b %d, %Y %H:%M}. Please log in again if asked.')
    return redirect('/data/?tab=restore')
