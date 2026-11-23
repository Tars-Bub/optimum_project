import io
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from openpyxl import Workbook, load_workbook

from catalog.models import Category, Product
from data.models import Backup
from data.services import create_backup
from documents.models import Document, PurchaseOrder
from sales.models import Order, OrderItem
from sales.services import finalize_order
from stock.services import apply_movement

User = get_user_model()


class MockupScreens(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('boss', 'b@x.com', 'pass12345!x', first_name='Jordan Lee')
        self.c = self.client
        self.c.force_login(self.admin)
        cat = Category.objects.create(name='Paper')
        self.p = Product.objects.create(code='PAP-1', name='Copy Paper', category=cat,
                                        unit_cost=Decimal('5'), price=Decimal('9'), reorder_level=10)
        apply_movement(self.p, 4, 'opening', self.admin)
        o = Order.objects.create(created_by=self.admin, client_name='Marston')
        OrderItem.objects.create(order=o, product=self.p, quantity=2, unit_price=self.p.price)
        self.order = finalize_order(o, self.admin)

    def test_every_screen_renders(self):
        urls = ['/', '/catalog/', '/catalog/?tab=items', '/stock/', '/stock/?tab=incoming', '/stock/?tab=adjust',
                '/stock/?tab=movements&type=out', '/stock/?tab=alerts', '/sales/', '/sales/?tab=drafts',
                '/sales/returns/', '/sales/returns/?tab=void', f'/sales/returns/?tab=return&order={self.order.pk}',
                '/documents/', '/documents/?tab=po', '/documents/?tab=delivery', '/documents/?tab=reprint',
                f'/documents/?tab=invoice&order={self.order.pk}', '/reports/', '/reports/?tab=sales&period=quarter',
                '/reports/?tab=sales&period=ytd', '/reports/?tab=inventory', '/reports/?tab=activity',
                '/reports/?tab=audit&area=Sales', '/data/', '/data/?tab=export', '/data/?tab=backup',
                '/data/?tab=restore', '/style-guide/', '/style-guide/?tab=components', '/style-guide/?tab=patterns',
                '/search/?q=paper', '/accounts/staff/']
        for u in urls:
            self.assertEqual(self.c.get(u).status_code, 200, u)
        self.client.logout()
        for u in ('/accounts/login/', '/accounts/register/'):
            self.assertEqual(self.client.get(u).status_code, 200)

    def test_add_item_without_code_generates_one(self):
        cat = Category.objects.get()
        r = self.c.post('/catalog/products/add/', {'name': 'Stapler', 'category': cat.pk, 'price': '50',
                                                   'opening_stock': '3', 'reorder_level': '2'})
        self.assertEqual(r.status_code, 302)
        p = Product.objects.get(name='Stapler')
        self.assertTrue(p.code.startswith('PAP-'))
        self.assertEqual(p.quantity, 3)

    def test_incoming_saves_supplier_and_date(self):
        r = self.c.post('/stock/', {'form': 'incoming', 'product': 'PAP-1', 'quantity': 6, 'supplier': 'Acme',
                                    'reference': 'PO-9', 'received_on': '2026-11-01'})
        self.assertEqual(r.status_code, 302)
        m = self.p.movements.filter(kind='incoming').first()
        self.assertEqual((m.supplier, str(m.received_on)), ('Acme', '2026-11-01'))

    def test_purchase_order_flow(self):
        r = self.c.post('/documents/po/create/', {'supplier': 'Office Supply Co.', 'code': ['PAP-1 \u2014 Copy Paper'],
                                                  'qty': ['12'], 'cost': ['5']})
        po = PurchaseOrder.objects.get()
        self.assertEqual(po.total, Decimal('60'))
        r = self.c.post('/documents/print/', {'doc_type': 'po', 'po': po.pk, 'number': 'PO-0001'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.c.get(r['Location']).status_code, 200)
        r = self.c.post('/documents/print/', {'doc_type': 'po', 'po': po.pk, 'number': 'PO-0002'})
        self.assertContains(r, 'already has this document')
        self.assertEqual(Document.objects.filter(doc_type='po').count(), 1)

    def test_import_export_backup_restore(self):
        wb = Workbook(); ws = wb.active
        ws.append(['Item code', 'Quantity']); ws.append(['PAP-1', 5]); ws.append(['NOPE', 2]); ws.append(['PAP-1', 1])
        buf = io.BytesIO(); wb.save(buf); buf.seek(0); buf.name = 'stock.xlsx'
        self.c.post('/data/import/upload/', {'file': buf})
        rows = self.c.session['import_preview']['rows']
        self.assertEqual([bool(r['error']) for r in rows], [False, True, True])
        self.c.post('/data/import/confirm/')
        self.p.refresh_from_db()
        self.assertEqual(self.p.quantity, 7)
        r = self.c.get('/data/export/?kind=items')
        sheet = load_workbook(io.BytesIO(r.content)).active
        self.assertEqual(sheet['A2'].value, 'PAP-1')
        for kind in ('movements', 'sales', 'transactions'):
            self.assertEqual(self.c.get(f'/data/export/?kind={kind}').status_code, 200)
        self.c.post('/data/backup/')
        b = Backup.objects.get()
        self.assertEqual(b.status, 'Verified')
        apply_movement(self.p, 50, 'incoming', self.admin)
        self.c.post('/data/restore/', {'backup': b.pk})
        self.p.refresh_from_db()
        self.assertEqual(self.p.quantity, 7)             # back to the backed-up state
        self.assertEqual(Backup.objects.count(), 1)      # backups survive a restore
        self.assertEqual(User.objects.filter(username='boss').count(), 1)
        self.assertEqual(User.objects.get(username='boss').profile.role, 'admin')

    def test_staff_cannot_restore_or_void(self):
        staff = User.objects.create_user('st', 's@x.com', 'pass12345!x')
        self.c.force_login(staff)
        b = create_backup(self.admin)
        self.c.post('/data/restore/', {'backup': b.pk})
        self.c.post('/sales/returns/void/', {'order': self.order.pk, 'reason': 'x'})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.FINAL)
