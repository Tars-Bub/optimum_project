from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from catalog.models import Category, Product
from sales.models import Order, OrderItem
from sales.services import finalize_order, process_return, void_order
from stock.models import StockMovement
from stock.services import StockError, apply_movement, set_quantity

User = get_user_model()


class AccountTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'a@x.com', 'pass12345!x', first_name='Owner')
        self.staff = User.objects.create_user('staff', 's@x.com', 'pass12345!x', first_name='Staff One')

    def test_registration_stays_pending_until_approved(self):
        resp = self.client.post(reverse('accounts:register'), {
            'full_name': 'New Person', 'position': 'Clerk', 'email': 'n@x.com', 'contact': '0917',
            'username': 'newbie', 'password1': 'Str0ng!pass99', 'password2': 'Str0ng!pass99'})
        self.assertRedirects(resp, reverse('accounts:login'))
        user = User.objects.get(username='newbie')
        self.assertFalse(user.is_active)
        self.assertEqual(user.profile.status, 'pending')
        resp = self.client.post(reverse('accounts:login'), {'username': 'newbie', 'password': 'Str0ng!pass99'})
        self.assertContains(resp, 'waiting for approval')
        self.client.login(username='admin', password='pass12345!x')
        self.client.post(reverse('accounts:staff_approve', args=[user.profile.pk]))
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_staff_cannot_open_admin_pages(self):
        self.client.login(username='staff', password='pass12345!x')
        self.assertRedirects(self.client.get(reverse('accounts:staff')), reverse('core:dashboard'))

    def test_login_required(self):
        resp = self.client.get(reverse('core:dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])


class ProductAndStockTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u', password='pass12345!x')
        cat = Category.objects.create(name='Paper')
        self.p = Product.objects.create(code='P-1', name='Copy Paper', category=cat,
                                        unit_cost=Decimal('10'), price=Decimal('20'), reorder_level=5)

    def test_status_follows_quantity_and_reorder_level(self):
        self.p.quantity = 0
        self.assertEqual(self.p.status, 'depleted')
        self.p.quantity = 5
        self.assertEqual(self.p.status, 'low')
        self.p.quantity = 6
        self.assertEqual(self.p.status, 'in')

    def test_incoming_stock_updates_quantity_and_history(self):
        move = apply_movement(self.p, 10, 'incoming', self.user, reference='DR-1')
        self.p.refresh_from_db()
        self.assertEqual(self.p.quantity, 10)
        self.assertEqual((move.change, move.balance_after), (10, 10))

    def test_quantity_can_never_go_negative(self):
        apply_movement(self.p, 3, 'incoming', self.user)
        with self.assertRaises(StockError):
            apply_movement(self.p, -4, 'sale', self.user)
        self.p.refresh_from_db()
        self.assertEqual(self.p.quantity, 3)

    def test_adjustment_from_a_physical_count(self):
        apply_movement(self.p, 10, 'incoming', self.user)
        move = set_quantity(self.p, 7, self.user, note='Recount')
        self.p.refresh_from_db()
        self.assertEqual((self.p.quantity, move.change), (7, -3))


class SalesBase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'a@x.com', 'pass12345!x', first_name='Owner')
        self.staff = User.objects.create_user('staff', 's@x.com', 'pass12345!x', first_name='Staff One')
        cat = Category.objects.create(name='Paper')
        self.p1 = Product.objects.create(code='P-1', name='Copy Paper', category=cat,
                                         unit_cost=Decimal('10'), price=Decimal('20'), reorder_level=5)
        self.p2 = Product.objects.create(code='P-2', name='Pens', category=cat,
                                         unit_cost=Decimal('5'), price=Decimal('8'), reorder_level=5)
        apply_movement(self.p1, 10, 'opening', self.admin)
        apply_movement(self.p2, 3, 'opening', self.admin)

    def cart(self, **qty):
        order = Order.objects.create(created_by=self.staff)
        for product, n in qty.items():
            OrderItem.objects.create(order=order, product=getattr(self, product),
                                     quantity=n, unit_price=getattr(self, product).price)
        return order


class SalesFlowTests(SalesBase):
    def test_finalize_deducts_stock_and_logs_movements(self):
        order = finalize_order(self.cart(p1=4, p2=1), self.staff)
        self.p1.refresh_from_db(); self.p2.refresh_from_db()
        self.assertEqual((self.p1.quantity, self.p2.quantity), (6, 2))
        self.assertEqual(order.status, Order.FINAL)
        self.assertEqual(StockMovement.objects.filter(kind='sale').count(), 2)

    def test_insufficient_stock_changes_nothing(self):
        order = self.cart(p1=2, p2=9)  # p2 only has 3
        with self.assertRaises(StockError):
            finalize_order(order, self.staff)
        self.p1.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.p1.quantity, 10)           # first item was rolled back too
        self.assertEqual(order.status, Order.DRAFT)

    def test_return_restores_stock_and_calculates_refund(self):
        order = finalize_order(self.cart(p1=4), self.staff)
        item = order.items.get()
        record = process_return(order, self.staff, 'return', 'Wrong size', {item.pk: 1})
        self.p1.refresh_from_db(); item.refresh_from_db()
        self.assertEqual(self.p1.quantity, 7)
        self.assertEqual(item.returned_qty, 1)
        self.assertEqual(record.refund_amount, Decimal('20'))
        with self.assertRaises(ValueError):               # cannot return more than was sold
            process_return(order, self.staff, 'return', 'Again', {item.pk: 4})

    def test_exchange_swaps_stock_and_records_price_difference(self):
        order = finalize_order(self.cart(p1=2), self.staff)
        item = order.items.get()
        record = process_return(order, self.staff, 'exchange', 'Prefer pens', {item.pk: 1}, self.p2)
        self.p1.refresh_from_db(); self.p2.refresh_from_db()
        self.assertEqual((self.p1.quantity, self.p2.quantity), (9, 2))
        self.assertEqual(record.refund_amount, Decimal('12'))

    def test_void_puts_unreturned_items_back(self):
        order = finalize_order(self.cart(p1=4), self.staff)
        process_return(order, self.staff, 'return', 'Damaged', {order.items.get().pk: 1})
        void_order(order, self.staff, 'Customer cancelled')
        self.p1.refresh_from_db(); order.refresh_from_db()
        self.assertEqual(self.p1.quantity, 10)
        self.assertEqual(order.status, Order.VOID)

    def test_payment_status(self):
        order = finalize_order(self.cart(p1=2), self.staff)   # total 40
        self.assertEqual(order.payment_status, 'Unpaid')
        order.amount_paid = Decimal('10'); self.assertEqual(order.payment_status, 'Partial')
        order.amount_paid = Decimal('40'); self.assertEqual(order.payment_status, 'Paid')

    def test_add_to_cart_and_finalize_through_the_views(self):
        self.client.login(username='staff', password='pass12345!x')
        self.client.post(reverse('sales:cart_add', args=[self.p1.pk]))
        self.client.post(reverse('sales:cart_add', args=[self.p1.pk]))
        resp = self.client.post(reverse('sales:cart_save'), {
            'action': 'finalize', 'client_name': 'Ana', 'amount_paid': '40'})
        self.assertEqual(resp.status_code, 302)
        order = Order.objects.get(status=Order.FINAL)
        self.assertEqual(order.total, Decimal('40'))
        self.assertEqual(order.payment_status, 'Paid')
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.quantity, 8)


class SmokeTests(SalesBase):
    """Every screen built so far opens for the Admin."""
    def test_pages_render(self):
        order = finalize_order(self.cart(p1=2), self.staff)
        self.client.login(username='admin', password='pass12345!x')
        urls = [
            '/',
            '/health/',
            '/accounts/staff/',
            '/accounts/staff/?tab=pending',
            '/accounts/staff/add/',
            '/catalog/',
            '/catalog/?tab=categories',
            '/stock/',
            '/stock/?tab=incoming',
            '/stock/?tab=adjust',
            '/stock/?tab=movements',
            '/stock/?tab=alerts',
            '/sales/',
            '/sales/?tab=drafts',
            '/sales/returns/',
            f'/sales/returns/?tab=return&order={order.pk}',
            f'/sales/returns/?tab=void&order={order.pk}',
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
