from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from catalog.models import Category, Product
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


class SmokeTests(AccountTests):
    """Every screen built so far opens for the Admin."""
    def test_pages_render(self):
        Category.objects.create(name='Paper')
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
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
