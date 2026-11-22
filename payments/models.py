from django.conf import settings
from django.db import models


class MayaPayment(models.Model):
    """One Maya Checkout attempt for an order. The order's `amount_paid` only changes
    when Maya itself confirms the payment (see payments.services.sync_payment)."""
    PENDING, PAID, FAILED, EXPIRED, CANCELLED = 'pending', 'paid', 'failed', 'expired', 'cancelled'
    STATUS_CHOICES = [(PENDING, 'Pending'), (PAID, 'Paid'), (FAILED, 'Failed'),
                      (EXPIRED, 'Expired'), (CANCELLED, 'Cancelled')]

    order = models.ForeignKey('sales.Order', on_delete=models.PROTECT, related_name='maya_payments')
    reference = models.CharField(max_length=64, unique=True)       # our requestReferenceNumber
    checkout_id = models.CharField(max_length=64, blank=True, db_index=True)
    checkout_url = models.CharField(max_length=500, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    maya_status = models.CharField(max_length=40, blank=True)      # last raw status from Maya
    note = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.reference} ({self.status})'

    @property
    def is_final(self):
        return self.status != self.PENDING
