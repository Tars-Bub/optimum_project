from django.conf import settings
from django.db import models


class Document(models.Model):
    """D5 Documents: every invoice / delivery receipt printed on a pre-printed form."""
    INVOICE, DELIVERY = 'invoice', 'delivery'
    TYPE_CHOICES = [(INVOICE, 'Invoice'), (DELIVERY, 'Delivery Receipt')]

    doc_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    number = models.CharField(max_length=30)          # serial number printed on the form
    order = models.ForeignKey('sales.Order', on_delete=models.PROTECT, related_name='documents')
    printed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='+')
    printed_at = models.DateTimeField(auto_now_add=True)
    reprint_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-printed_at', '-id']
        unique_together = [('doc_type', 'number')]

    def __str__(self):
        return f'{self.get_doc_type_display()} {self.number}'
