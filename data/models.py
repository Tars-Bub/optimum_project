from django.conf import settings
from django.db import models


class Backup(models.Model):
    """A recovery point: the whole business data set, compressed JSON kept in the database."""
    MANUAL, AUTO = 'manual', 'auto'
    KIND_CHOICES = [(MANUAL, 'Manual'), (AUTO, 'Automatic')]
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=MANUAL)
    status = models.CharField(max_length=12, default='Completed')   # Completed / Verified
    payload = models.BinaryField()
    size = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    @property
    def size_label(self):
        kb = self.size / 1024
        return f'{kb / 1024:.1f} MB' if kb >= 1024 else f'{max(kb, 0.1):.1f} KB'
