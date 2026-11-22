import base64
import json
from decimal import Decimal
from unittest import mock

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core.tests import Base
from sales.models import Order
from sales.services import finalize_order

from . import maya
from .models import MayaPayment
from .services import PaymentError, start_checkout, sync_payment

KEYS = dict(MAYA_PUBLIC_KEY='pk-test', MAYA_SECRET_KEY='sk-test',
            MAYA_BASE_URL='https://pg-sandbox.paymaya.com', SITE_URL='https://shop.example')
CHECKOUT = {'checkoutId': 'chk-123', 'redirectUrl': 'https://payments-web-sandbox.paymaya.com/checkout?id=chk-123'}


def basic(key):
    return 'Basic ' + base64.b64encode(f'{key}:'.encode()).decode()


def fake_response(status=200, body=None):
    resp = mock.Mock()
    resp.status_code = status
    resp.content = json.dumps(body if body is not None else {}).encode()
    resp.json.return_value = body if body is not None else {}
    return resp


@override_settings(**KEYS)
class MayaClientTests(TestCase):
    def test_create_checkout_uses_public_key_and_sends_the_expected_body(self):
        with mock.patch('payments.maya.requests.request', return_value=fake_response(200, CHECKOUT)) as req:
            data = maya.create_checkout('SO-1-abc', Decimal('40.00'), [{'name': 'Pen'}],
                                        {'success': 'https://x/s', 'failure': 'https://x/f', 'cancel': 'https://x/c'},
                                        metadata={'order': 'SO-0001'})
        self.assertEqual(data['checkoutId'], 'chk-123')
        args, kwargs = req.call_args
        self.assertEqual(args, ('POST', 'https://pg-sandbox.paymaya.com/checkout/v1/checkouts'))
        self.assertEqual(kwargs['headers']['Authorization'], basic('pk-test'))
        self.assertEqual(kwargs['json']['totalAmount'], {'value': 40.0, 'currency': 'PHP'})
        self.assertEqual(kwargs['json']['requestReferenceNumber'], 'SO-1-abc')
        self.assertEqual(kwargs['json']['redirectUrl']['cancel'], 'https://x/c')

    def test_retrieve_payment_uses_the_secret_key(self):
        with mock.patch('payments.maya.requests.request', return_value=fake_response(200, {'status': 'PAYMENT_SUCCESS'})) as req:
            maya.get_payment('chk-123')
            maya.get_payment_by_rrn('SO-1-abc')
        first, second = req.call_args_list
        self.assertEqual(first.args, ('GET', 'https://pg-sandbox.paymaya.com/payments/v1/payments/chk-123'))
        self.assertEqual(second.args, ('GET', 'https://pg-sandbox.paymaya.com/payments/v1/payment-rrns/SO-1-abc'))
        self.assertEqual(first.kwargs['headers']['Authorization'], basic('sk-test'))

    def test_http_error_becomes_maya_error_with_status(self):
        with mock.patch('payments.maya.requests.request', return_value=fake_response(401, {'message': 'Invalid key'})):
            with self.assertRaises(maya.MayaError) as ctx:
                maya.get_payment('x')
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn('Invalid key', str(ctx.exception))

    def test_network_failure_becomes_maya_error(self):
        with mock.patch('payments.maya.requests.request', side_effect=maya.requests.ConnectionError('down')):
            with self.assertRaisesMessage(maya.MayaError, 'Could not reach Maya'):
                maya.get_payment('x')

    @override_settings(MAYA_PUBLIC_KEY='', MAYA_SECRET_KEY='')
    def test_missing_keys_give_a_clear_error_and_no_request(self):
        with mock.patch('payments.maya.requests.request') as req:
            with self.assertRaisesMessage(maya.MayaError, 'not configured'):
                maya.create_checkout('r', Decimal('1'), [], {})
        req.assert_not_called()

    def test_checkout_without_link_is_rejected(self):
        with mock.patch('payments.maya.requests.request', return_value=fake_response(200, {'checkoutId': 'x'})):
            with self.assertRaises(maya.MayaError):
                maya.create_checkout('r', Decimal('1'), [], {})

    def test_status_and_amount_readers(self):
        self.assertEqual(maya.read_status({'status': 'PAYMENT_SUCCESS'}), 'PAYMENT_SUCCESS')
        self.assertEqual(maya.read_status({'status': 'COMPLETED', 'paymentStatus': 'PAYMENT_FAILED'}), 'PAYMENT_FAILED')
        self.assertEqual(maya.read_status({}), '')
        self.assertEqual(maya.first_record([{'status': 'PAYMENT_SUCCESS'}]), {'status': 'PAYMENT_SUCCESS'})
        self.assertEqual(maya.first_record([]), {})
        self.assertEqual(maya.read_amount({'amount': 40.0}), Decimal('40.0'))
        self.assertEqual(maya.read_amount({'totalAmount': {'value': '40.50'}}), Decimal('40.50'))
        self.assertIsNone(maya.read_amount({}))


@override_settings(**KEYS)
class PaymentFlowTests(Base):
    def setUp(self):
        super().setUp()
        self.order = finalize_order(self.cart(p1=2), self.staff)       # total 40
        self.create = mock.patch('payments.services.maya.create_checkout', return_value=CHECKOUT)

    def pending(self, amount='40.00'):
        return MayaPayment.objects.create(order=self.order, reference=f'SO-{self.order.pk}-ref',
                                          checkout_id='chk-123', amount=Decimal(amount))

    # ---- starting a checkout
    def test_start_checkout_creates_a_pending_payment_with_item_lines(self):
        with self.create as create:
            payment = start_checkout(self.order, self.staff, 'https://shop.example')
        self.assertEqual((payment.status, payment.checkout_id, payment.amount),
                         ('pending', 'chk-123', Decimal('40.00')))
        reference, total, items, urls = create.call_args.args
        self.assertEqual(reference, payment.reference)
        self.assertEqual(total, Decimal('40.00'))
        self.assertEqual([(i['code'], i['quantity']) for i in items], [('P-1', 2)])
        self.assertTrue(urls['success'].startswith('https://shop.example/payments/maya/return/'))
        self.assertTrue(urls['success'].endswith('?result=success'))

    def test_balance_checkout_is_a_single_line_for_the_balance(self):
        self.order.amount_paid = Decimal('10')
        self.order.save()
        with self.create as create:
            payment = start_checkout(self.order, self.staff, 'https://shop.example')
        self.assertEqual(payment.amount, Decimal('30.00'))
        items = create.call_args.args[2]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['totalAmount']['value'], 30.0)

    def test_a_recent_pending_checkout_is_reused(self):
        with self.create as create:
            first = start_checkout(self.order, self.staff, 'https://shop.example')
            second = start_checkout(self.order, self.staff, 'https://shop.example')
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(create.call_count, 1)

    def test_cannot_pay_drafts_or_paid_orders(self):
        draft = self.cart(p2=1)
        with self.assertRaises(PaymentError):
            start_checkout(draft, self.staff, 'https://shop.example')
        self.order.amount_paid = Decimal('40')
        self.order.save()
        with self.assertRaises(PaymentError):
            start_checkout(self.order, self.staff, 'https://shop.example')

    # ---- applying the result from Maya
    def test_success_marks_the_order_paid_once(self):
        payment = self.pending()
        stale_copy = MayaPayment.objects.get(pk=payment.pk)            # a second request holding old data
        with mock.patch('payments.services.maya.get_payment',
                        return_value={'status': 'PAYMENT_SUCCESS', 'amount': 40.0}) as get:
            sync_payment(payment)
            sync_payment(stale_copy)                                   # duplicate webhook / double refresh
        self.order.refresh_from_db(); payment.refresh_from_db()
        self.assertEqual(payment.status, 'paid')
        self.assertIsNotNone(payment.paid_at)
        self.assertEqual(self.order.amount_paid, Decimal('40'))        # not 80
        self.assertEqual(self.order.payment_status, 'Paid')
        self.assertEqual(get.call_count, 2)

    def test_balance_payment_completes_a_part_paid_order(self):
        self.order.amount_paid = Decimal('10')
        self.order.save()
        payment = self.pending('30.00')
        with mock.patch('payments.services.maya.get_payment', return_value=[{'status': 'PAYMENT_SUCCESS'}]):
            sync_payment(payment)
        self.order.refresh_from_db()
        self.assertEqual(self.order.amount_paid, Decimal('40'))

    def test_failed_expired_and_cancelled_leave_the_order_unpaid(self):
        for maya_status, expected in [('PAYMENT_FAILED', 'failed'), ('PAYMENT_EXPIRED', 'expired'),
                                      ('PAYMENT_CANCELLED', 'cancelled')]:
            with self.subTest(maya_status):
                payment = MayaPayment.objects.create(order=self.order, reference=f'r-{maya_status}',
                                                     checkout_id='c', amount=Decimal('40'))
                with mock.patch('payments.services.maya.get_payment', return_value={'status': maya_status}):
                    sync_payment(payment)
                payment.refresh_from_db(); self.order.refresh_from_db()
                self.assertEqual(payment.status, expected)
                self.assertEqual(self.order.amount_paid, Decimal('0'))

    def test_in_progress_statuses_are_shown_but_do_not_pay_the_order(self):
        payment = self.pending()
        with mock.patch('payments.services.maya.get_payment', return_value={'status': 'FOR_AUTHENTICATION'}):
            sync_payment(payment)
        payment.refresh_from_db()
        self.assertEqual((payment.status, payment.maya_status), ('pending', 'FOR_AUTHENTICATION'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.amount_paid, Decimal('0'))

    def test_unknown_payment_at_maya_counts_as_not_paid_yet(self):
        payment = self.pending()
        with mock.patch('payments.services.maya.get_payment', side_effect=maya.MayaError('nope', 404)):
            self.assertEqual(sync_payment(payment).status, 'pending')

    def test_other_maya_errors_are_raised_to_the_caller(self):
        payment = self.pending()
        with mock.patch('payments.services.maya.get_payment', side_effect=maya.MayaError('down', 500)):
            with self.assertRaises(maya.MayaError):
                sync_payment(payment)

    def test_amount_mismatch_is_not_applied(self):
        payment = self.pending()
        with mock.patch('payments.services.maya.get_payment',
                        return_value={'status': 'PAYMENT_SUCCESS', 'amount': 1.0}):
            sync_payment(payment)
        payment.refresh_from_db(); self.order.refresh_from_db()
        self.assertEqual(payment.status, 'pending')
        self.assertIn('mismatch', payment.note)
        self.assertEqual(self.order.amount_paid, Decimal('0'))

    def test_payment_for_a_voided_order_is_recorded_with_a_refund_note(self):
        payment = self.pending()
        self.order.status = Order.VOID
        self.order.save()
        with mock.patch('payments.services.maya.get_payment', return_value={'status': 'PAYMENT_SUCCESS'}):
            sync_payment(payment)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'paid')
        self.assertIn('refund', payment.note)


@override_settings(**KEYS)
class WebhookTests(Base):
    def setUp(self):
        super().setUp()
        self.order = finalize_order(self.cart(p1=2), self.staff)
        self.payment = MayaPayment.objects.create(order=self.order, reference='SO-REF-1',
                                                  checkout_id='chk-123', amount=Decimal('40'))
        self.client = Client(enforce_csrf_checks=True)                  # Maya cannot send a CSRF token
        self.url = reverse('payments:maya_webhook')

    def post(self, body, raw=False):
        return self.client.post(self.url, data=body if raw else json.dumps(body), content_type='application/json')

    def test_known_reference_is_verified_with_maya_before_anything_changes(self):
        with mock.patch('payments.services.maya.get_payment',
                        return_value={'status': 'PAYMENT_SUCCESS', 'amount': 40}) as get:
            resp = self.post({'id': 'chk-123', 'requestReferenceNumber': 'SO-REF-1', 'status': 'PAYMENT_SUCCESS'})
        self.assertEqual((resp.status_code, resp.json()), (200, {'status': 'ok'}))
        get.assert_called_once_with('chk-123')
        self.order.refresh_from_db()
        self.assertEqual(self.order.amount_paid, Decimal('40'))

    def test_a_forged_success_does_not_mark_anything_paid(self):
        with mock.patch('payments.services.maya.get_payment', return_value={'status': 'PENDING_PAYMENT'}):
            resp = self.post({'id': 'chk-123', 'requestReferenceNumber': 'SO-REF-1', 'status': 'PAYMENT_SUCCESS'})
        self.assertEqual(resp.status_code, 200)
        self.order.refresh_from_db(); self.payment.refresh_from_db()
        self.assertEqual((self.payment.status, self.order.amount_paid), ('pending', Decimal('0')))

    def test_matches_by_checkout_id_when_reference_is_missing(self):
        with mock.patch('payments.services.maya.get_payment', return_value={'status': 'PAYMENT_FAILED'}):
            self.post({'id': 'chk-123'})
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'failed')

    def test_unknown_reference_is_ignored_without_calling_maya(self):
        with mock.patch('payments.services.maya.get_payment') as get:
            resp = self.post({'id': 'other', 'requestReferenceNumber': 'NOPE'})
        self.assertEqual((resp.status_code, resp.json()), (200, {'status': 'ignored'}))
        get.assert_not_called()

    def test_bad_input_and_wrong_method(self):
        self.assertEqual(self.post('not json{', raw=True).status_code, 400)
        self.assertEqual(self.post([1, 2]).status_code, 400)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_maya_outage_returns_502_so_maya_retries(self):
        with mock.patch('payments.services.maya.get_payment', side_effect=maya.MayaError('down', 500)):
            resp = self.post({'requestReferenceNumber': 'SO-REF-1'})
        self.assertEqual(resp.status_code, 502)


@override_settings(**KEYS)
class PaymentViewTests(Base):
    def setUp(self):
        super().setUp()
        self.order = finalize_order(self.cart(p1=2), self.staff)

    def login(self):
        self.client.login(username='staff', password='pass12345!x')

    def make_payment(self, **kw):
        defaults = dict(order=self.order, reference='SO-REF-9', checkout_id='chk-9', amount=Decimal('40'),
                        checkout_url=CHECKOUT['redirectUrl'])
        defaults.update(kw)
        return MayaPayment.objects.create(**defaults)

    def test_staff_pages_need_a_login(self):
        payment = self.make_payment()
        for url in (reverse('payments:index'), reverse('payments:maya_pay', args=[self.order.pk]),
                    reverse('payments:maya_detail', args=[payment.pk]),
                    reverse('payments:maya_status', args=[payment.pk])):
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 302)
                self.assertIn('/accounts/login/', resp['Location'])

    def test_pay_page_then_create_checkout(self):
        self.login()
        resp = self.client.get(reverse('payments:maya_pay', args=[self.order.pk]))
        self.assertContains(resp, 'Create Maya checkout')
        with mock.patch('payments.services.maya.create_checkout', return_value=CHECKOUT):
            resp = self.client.post(reverse('payments:maya_pay', args=[self.order.pk]))
        payment = MayaPayment.objects.get()
        self.assertRedirects(resp, reverse('payments:maya_detail', args=[payment.pk]))

    def test_maya_error_is_shown_to_the_cashier(self):
        self.login()
        with mock.patch('payments.services.maya.create_checkout', side_effect=maya.MayaError('Maya rejected it (401).')):
            resp = self.client.post(reverse('payments:maya_pay', args=[self.order.pk]), follow=True)
        self.assertContains(resp, 'Maya rejected it')
        # the failed attempt is kept (as Failed, never counted as paid) so the Maya Payments list shows it
        failed = MayaPayment.objects.get()
        self.assertEqual((failed.status, failed.maya_status), ('failed', 'NOT_CREATED'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.amount_paid, 0)

    def test_draft_orders_cannot_be_paid(self):
        self.login()
        draft = self.cart(p2=1)
        resp = self.client.post(reverse('payments:maya_pay', args=[draft.pk]), follow=True)
        self.assertContains(resp, 'Only finalized sales')

    def test_detail_page_shows_link_and_qr_code(self):
        self.login()
        payment = self.make_payment()
        resp = self.client.get(reverse('payments:maya_detail', args=[payment.pk]))
        self.assertContains(resp, CHECKOUT['redirectUrl'])
        self.assertContains(resp, '<svg')
        self.assertContains(resp, 'Waiting for payment')

    def test_status_endpoint_returns_json_and_updates_the_payment(self):
        self.login()
        payment = self.make_payment()
        with mock.patch('payments.services.maya.get_payment', return_value={'status': 'PAYMENT_SUCCESS'}):
            resp = self.client.get(reverse('payments:maya_status', args=[payment.pk]))
        self.assertEqual(resp.json()['status'], 'paid')
        self.assertTrue(resp.json()['final'])

    def test_check_button_reports_the_status(self):
        self.login()
        payment = self.make_payment()
        with mock.patch('payments.services.maya.get_payment', return_value={'status': 'PENDING_PAYMENT'}):
            resp = self.client.post(reverse('payments:maya_check', args=[payment.pk]), follow=True)
        self.assertContains(resp, 'Waiting for payment')

    def test_return_page_is_public_and_verifies_with_maya(self):
        payment = self.make_payment()
        with mock.patch('payments.services.maya.get_payment', return_value={'status': 'PAYMENT_SUCCESS'}):
            resp = self.client.get(reverse('payments:maya_return', args=[payment.reference]) + '?result=success')
        self.assertContains(resp, 'Payment received')
        self.order.refresh_from_db()
        self.assertEqual(self.order.amount_paid, Decimal('40'))

    def test_return_page_does_not_trust_the_result_in_the_address(self):
        payment = self.make_payment()
        with mock.patch('payments.services.maya.get_payment', return_value={'status': 'PENDING_PAYMENT'}):
            resp = self.client.get(reverse('payments:maya_return', args=[payment.reference]) + '?result=success')
        self.assertNotContains(resp, 'Payment received')
        self.assertContains(resp, 'refresh')
        self.order.refresh_from_db()
        self.assertEqual(self.order.amount_paid, Decimal('0'))

    def test_return_page_survives_a_maya_outage_and_unknown_references(self):
        payment = self.make_payment()
        with mock.patch('payments.services.maya.get_payment', side_effect=maya.MayaError('down', 500)):
            resp = self.client.get(reverse('payments:maya_return', args=[payment.reference]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.get(reverse('payments:maya_return', args=['nope'])).status_code, 404)

    def test_cancel_result_is_shown_without_changing_the_payment(self):
        payment = self.make_payment()
        with mock.patch('payments.services.maya.get_payment', return_value={'status': 'PENDING_PAYMENT'}):
            resp = self.client.get(reverse('payments:maya_return', args=[payment.reference]) + '?result=cancel')
        self.assertContains(resp, 'Checkout cancelled')

    def test_list_page_and_navigation(self):
        self.login()
        self.make_payment()
        self.assertContains(self.client.get(reverse('payments:index')), 'SO-REF-9')
        self.assertContains(self.client.get('/'), 'Maya Payments')

    def test_finalizing_with_a_balance_offers_maya(self):
        self.login()
        self.client.post(reverse('sales:cart_add', args=[self.p2.pk]))
        resp = self.client.post(reverse('sales:cart_save'), {'action': 'finalize', 'amount_paid': '2'}, follow=True)
        self.assertContains(resp, 'with Maya')

    def test_transactions_list_offers_pay_with_maya_for_unpaid_orders(self):
        self.client.login(username='admin', password='pass12345!x')
        resp = self.client.get('/reports/?tab=transactions')
        self.assertContains(resp, reverse('payments:maya_pay', args=[self.order.pk]))
