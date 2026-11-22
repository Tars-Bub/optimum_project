from decimal import Decimal

from django.conf import settings
from django.db import models


class Order(models.Model):
    """D4 Orders, clients. A draft is the open cart; finalizing deducts stock."""
    DRAFT, FINAL, VOID = 'draft', 'finalized', 'voided'
    STATUS_CHOICES = [(DRAFT, 'Draft'), (FINAL, 'Finalized'), (VOID, 'Voided')]

    client_name = models.CharField(max_length=120, blank=True)
    client_business = models.CharField(max_length=120, blank=True)
    client_phone = models.CharField(max_length=30, blank=True)
    client_tin = models.CharField(max_length=30, blank=True)
    client_address = models.CharField(max_length=255, blank=True)
    po_number = models.CharField(max_length=50, blank=True)
    payment_terms = models.CharField(max_length=60, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=DRAFT)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return self.number

    @property
    def number(self):
        return f'SL-{self.pk:04d}'

    @property
    def total(self):
        return sum((i.line_total for i in self.items.all()), Decimal('0'))

    @property
    def payment_status(self):
        total = self.total
        if self.amount_paid <= 0:
            return 'Unpaid'
        return 'Paid' if self.amount_paid >= total else 'Partial'

    @property
    def balance(self):
        return max(self.total - self.amount_paid, Decimal('0'))

    @property
    def client_label(self):
        return self.client_name or self.client_business or 'Walk-in customer'

    @property
    def status_label(self):
        if self.status == self.VOID:
            return 'Voided'
        if self.status == self.DRAFT:
            return 'Draft'
        return 'Returned' if self.returns.all() else 'Completed'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    returned_qty = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['id']
        unique_together = [('order', 'product')]

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    @property
    def remaining(self):
        return self.quantity - self.returned_qty


class ReturnRecord(models.Model):
    """D6 Returns, voids (voids are stored on the Order itself)."""
    RETURN, EXCHANGE = 'return', 'exchange'
    KIND_CHOICES = [(RETURN, 'Return'), (EXCHANGE, 'Exchange')]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='returns')
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    reason = models.CharField(max_length=200)
    # Positive: refunded to the customer. Negative: customer pays the difference (exchange).
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    replacement_product = models.ForeignKey('catalog.Product', null=True, blank=True,
                                            on_delete=models.PROTECT, related_name='+')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']


class ReturnLine(models.Model):
    record = models.ForeignKey(ReturnRecord, on_delete=models.CASCADE, related_name='lines')
    item = models.ForeignKey(OrderItem, on_delete=models.PROTECT, related_name='+')
    quantity = models.PositiveIntegerField()
