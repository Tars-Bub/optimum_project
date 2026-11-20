from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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


class SmokeTests(AccountTests):
    """Every screen built so far opens for the Admin."""
    def test_pages_render(self):
        self.client.login(username='admin', password='pass12345!x')
        urls = [
            '/',
            '/health/',
            '/accounts/staff/',
            '/accounts/staff/?tab=pending',
            '/accounts/staff/add/',
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
