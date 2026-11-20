from django.test import SimpleTestCase
from django.urls import reverse

NAMES = ['login', 'register', 'dashboard', 'products', 'stock', 'sales', 'returns',
         'documents', 'reports', 'staff']


class ScreenTests(SimpleTestCase):
    def test_every_screen_opens(self):
        for name in NAMES:
            with self.subTest(name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
