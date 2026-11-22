from django.conf import settings
from django.db import models


class SmsLog(models.Model):
    """Every SMS the system tried to send, so staff can see what went out and what failed."""
    SENT, FAILED, SKIPPED = 'sent', 'failed', 'skipped'
    STATUS_CHOICES = [(SENT, 'Sent'), (FAILED, 'Failed'), (SKIPPED, 'Not sent')]
    KIND_CHOICES = [('receipt', 'Receipt'), ('payment_link', 'Payment link'), ('low_stock', 'Low-stock alert'),
                    ('manual', 'Manual message')]
    recipient = models.CharField(max_length=30)
    message = models.TextField()
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='manual')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    detail = models.CharField(max_length=300, blank=True)       # provider answer or reason
    order = models.ForeignKey('sales.Order', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
