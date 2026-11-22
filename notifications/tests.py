from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from catalog.models import Category, Product
from payments.models import MayaPayment
from sales.models import Order, OrderItem
from sales.services import finalize_order
from stock.services import apply_movement

from . import philsms
from .models import SmsLog
from .services import notify_low_stock, send_receipt, send_sms

User = get_user_model()
CFG = dict(PHILSMS_API_TOKEN='tok', PHILSMS_BASE_URL='https://sms.test/api/v3', SMS_ENABLED=True)


def ok_response(status=200, body=None):
    r = mock.Mock()
    r.status_code = status
    r.json.return_value = body if body is not None else {'status': 'success', 'message': 'Your message was successfully delivered'}
    return r


class SmsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('boss', 'b@x.com', 'pass12345!x')
        cat = Category.objects.create(name='Paper')
        self.p = Product.objects.create(code='PAP-1', name='Copy Paper', category=cat, price=Decimal('9'), reorder_level=3)
        apply_movement(self.p, 5, 'opening', self.admin)

    def test_number_formats(self):
        for raw in ('09171234567', '+63 917 123 4567', '639171234567', '9171234567'):
            self.assertEqual(philsms.normalize_number(raw), '639171234567')
        for bad in ('', '12345', '0817123456', 'abc'):
            self.assertEqual(philsms.normalize_number(bad), '')

    @override_settings(**CFG)
    def test_send_posts_to_philsms_and_logs(self):
        with mock.patch('notifications.philsms.requests.post', return_value=ok_response()) as post:
            row = send_sms('0917 123 4567', 'Hello', 'manual')
        self.assertEqual(row.status, 'sent')
        url = post.call_args.args[0]
        self.assertEqual(url, 'https://sms.test/api/v3/sms/send')
        self.assertEqual(post.call_args.kwargs['headers']['Authorization'], 'Bearer tok')
        self.assertEqual(post.call_args.kwargs['json']['recipient'], '639171234567')
        self.assertEqual(post.call_args.kwargs['json']['type'], 'plain')

    @override_settings(**CFG)
    def test_provider_error_is_logged_not_raised(self):
        err = ok_response(422, {'status': 'error', 'message': 'Insufficient balance'})
        with mock.patch('notifications.philsms.requests.post', return_value=err):
            row = send_sms('09171234567', 'Hello')
        self.assertEqual((row.status, row.detail), ('failed', 'Insufficient balance'))

    @override_settings(PHILSMS_API_TOKEN='', SMS_ENABLED=True)
    def test_not_configured_is_skipped(self):
        with mock.patch('notifications.philsms.requests.post') as post:
            row = send_sms('09171234567', 'Hello')
        self.assertEqual(row.status, 'skipped')
        post.assert_not_called()

    @override_settings(**CFG)
    def test_invalid_number_is_skipped(self):
        self.assertEqual(send_sms('123', 'x').status, 'skipped')

    @override_settings(**CFG)
    def test_receipt_after_finalize_view(self):
        self.client.force_login(self.admin)
        with mock.patch('notifications.philsms.requests.post', return_value=ok_response()) as post:
            self.client.post(f'/sales/cart/add/{self.p.pk}/')
            self.client.post('/sales/cart/save/', {'action': 'finalize', 'client_name': 'Ann', 'client_phone': '09171234567'})
        self.assertEqual(post.call_count, 1)
        row = SmsLog.objects.get()
        self.assertEqual((row.kind, row.status), ('receipt', 'sent'))
        self.assertIn('SL-', row.message)

    @override_settings(**CFG, SMS_OWNER_NUMBER='09179998888')
    def test_low_stock_alert_only_when_crossing(self):
        with mock.patch('notifications.philsms.requests.post', return_value=ok_response()) as post:
            self.p.quantity = 3
            notify_low_stock(self.p, 5, None)           # 5 -> 3 crosses the level of 3
            notify_low_stock(self.p, 3, None)           # already low: no second text
        self.assertEqual(post.call_count, 1)
        self.assertEqual(SmsLog.objects.get().kind, 'low_stock')

    @override_settings(**CFG)
    def test_payment_link_sms_view(self):
        o = Order.objects.create(created_by=self.admin, client_name='Ann')
        OrderItem.objects.create(order=o, product=self.p, quantity=1, unit_price=self.p.price)
        o = finalize_order(o, self.admin)
        pay = MayaPayment.objects.create(order=o, reference='R1', checkout_id='c', checkout_url='https://pay.test/c',
                                         amount=Decimal('9'))
        self.client.force_login(self.admin)
        with mock.patch('notifications.philsms.requests.post', return_value=ok_response()) as post:
            self.client.post(f'/payments/maya/{pay.pk}/sms/', {'number': '09171234567'})
        self.assertIn('https://pay.test/c', post.call_args.kwargs['json']['message'])
        for u in ('/sms/', '/payments/', f'/payments/maya/{pay.pk}/', f'/payments/maya/pay/{o.pk}/'):
            self.assertEqual(self.client.get(u).status_code, 200, u)

    def test_staff_cannot_send_manual(self):
        staff = User.objects.create_user('st', 's@x.com', 'pass12345!x')
        self.client.force_login(staff)
        self.client.post('/sms/send/', {'number': '09171234567', 'message': 'hi'})
        self.assertEqual(SmsLog.objects.count(), 0)
