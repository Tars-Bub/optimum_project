from .models import AuditLog


def audit(user, action, detail=''):
    AuditLog.objects.create(user=user if getattr(user, 'pk', None) else None,
                            action=action, detail=detail[:255])
