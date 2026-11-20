from django.conf import settings
from django.db import models


class StockMovement(models.Model):
    """D3 Stock movements: append-only history of every change to quantity on hand."""
    KIND_CHOICES = [
        ('opening', 'Opening stock'), ('incoming', 'Incoming delivery'), ('sale', 'Sale'),
        ('return', 'Customer return'), ('exchange_in', 'Exchange: item back'),
        ('exchange_out', 'Exchange: replacement'), ('void', 'Voided sale'),
        ('adjustment', 'Adjustment'),
    ]
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='movements')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    change = models.IntegerField()
    balance_after = models.IntegerField()
    reference = models.CharField(max_length=60, blank=True)
    note = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='stock_movements')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.product.code} {self.change:+d} ({self.kind})'
