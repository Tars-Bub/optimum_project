"""Phase 1: screens only. Every value on the pages is sample data written here.

Later phases replace the sample data with database models and make the buttons work.
"""
from django.shortcuts import render

PRODUCTS = [
    {'code': 'IC-001', 'name': 'Copy Paper, Letter', 'category': 'Paper & Notebooks', 'cost': '210.00', 'price': '285.00', 'qty': 80, 'status': 'in', 'label': 'In stock'},
    {'code': 'IC-002', 'name': 'Blue Ballpoint Pens', 'category': 'Writing Supplies', 'cost': '95.00', 'price': '140.00', 'qty': 3, 'status': 'low', 'label': 'Low'},
    {'code': 'IC-003', 'name': 'Black Toner Cartridge', 'category': 'Ink & Toner', 'cost': '1450.00', 'price': '1890.00', 'qty': 0, 'status': 'depleted', 'label': 'Depleted'},
]
ORDERS = [
    {'no': 'SO-0001', 'client': 'Client name', 'total': '1,250.00', 'payment': 'Paid'},
    {'no': 'SO-0002', 'client': 'Client name', 'total': '640.00', 'payment': 'Partial'},
    {'no': 'SO-0003', 'client': 'Client name', 'total': '2,100.00', 'payment': 'Unpaid'},
]


def _tab(request, default):
    return request.GET.get('tab', default)


def login_page(request):
    return render(request, 'web/login.html')


def register_page(request):
    return render(request, 'web/register.html')


def dashboard(request):
    return render(request, 'web/dashboard.html', {'orders': ORDERS})


def products(request):
    return render(request, 'web/products.html', {'tab': _tab(request, 'products'), 'products': PRODUCTS})


def stock(request):
    return render(request, 'web/stock.html', {'tab': _tab(request, 'levels'), 'products': PRODUCTS})


def sales(request):
    return render(request, 'web/sales.html', {'tab': _tab(request, 'new'), 'products': PRODUCTS})


def returns(request):
    return render(request, 'web/returns.html', {'tab': _tab(request, 'return')})


def documents(request):
    return render(request, 'web/documents.html', {'tab': _tab(request, 'invoice')})


def reports(request):
    return render(request, 'web/reports.html', {'tab': _tab(request, 'sales'), 'orders': ORDERS})


def staff(request):
    return render(request, 'web/staff.html', {'tab': _tab(request, 'accounts')})
