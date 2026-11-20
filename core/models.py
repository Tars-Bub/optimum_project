from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Who did what, and when (feeds Activity and the Admin-only Audit Log)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='audit_entries')
    action = models.CharField(max_length=60)
    detail = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} {self.action}'
