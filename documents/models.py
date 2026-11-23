from django.conf import settings
from django.db import models


class Document(models.Model):
    """D5 Documents: every invoice / delivery receipt printed on a pre-printed form."""
    INVOICE, DELIVERY, PO = 'invoice', 'delivery', 'po'
    TYPE_CHOICES = [(INVOICE, 'Receipt / Invoice'), (PO, 'Purchase Order'), (DELIVERY, 'Delivery Receipt')]

    doc_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    number = models.CharField(max_length=30)          # serial number printed on the form
    order = models.ForeignKey('sales.Order', null=True, blank=True, on_delete=models.PROTECT, related_name='documents')
    purchase_order = models.ForeignKey('documents.PurchaseOrder', null=True, blank=True,
                                       on_delete=models.PROTECT, related_name='documents')
    printed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='+')
    printed_at = models.DateTimeField(auto_now_add=True)
    reprint_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-printed_at', '-id']
        unique_together = [('doc_type', 'number')]

    def __str__(self):
        return f'{self.get_doc_type_display()} {self.number}'


class PurchaseOrder(models.Model):
    """Order placed with a supplier to restock items (printed on the pre-printed PO form)."""
    supplier = models.CharField(max_length=120)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'PO-{self.pk:04d}'

    @property
    def number(self):
        return f'PO-{self.pk:04d}'

    @property
    def total(self):
        return sum((i.line_total for i in self.items.all()), 0)


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT, related_name='+')
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['id']

    @property
    def line_total(self):
        return self.quantity * self.unit_cost
