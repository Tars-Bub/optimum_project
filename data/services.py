import gzip
import io
import json
from datetime import timedelta

from django.core import serializers
from django.core.management import call_command
from django.db import connection, transaction
from django.utils import timezone

from .models import Backup

EXCLUDE = ['data.backup', 'sessions', 'contenttypes', 'auth.permission', 'admin.logentry']


def dump_json():
    out = io.StringIO()
    call_command('dumpdata', exclude=EXCLUDE, indent=None, stdout=out)
    return out.getvalue()


def create_backup(user=None, kind=Backup.MANUAL):
    raw = gzip.compress(dump_json().encode('utf-8'))
    backup = Backup.objects.create(kind=kind, payload=raw, size=len(raw),
                                   created_by=user if getattr(user, 'pk', None) else None)
    try:                                   # verify: it must decompress and parse
        json.loads(gzip.decompress(bytes(backup.payload)).decode('utf-8'))
        backup.status = 'Verified'
        backup.save(update_fields=['status'])
    except Exception:
        pass
    # keep the 30 newest so the database does not grow forever
    for old in Backup.objects.all()[30:]:
        old.delete()
    return backup


def ensure_daily_backup():
    """Free hosts have no scheduler, so make the daily automatic backup the first time Data is opened each day."""
    last = Backup.objects.filter(kind=Backup.AUTO).first()
    if last is None or timezone.now() - last.created_at > timedelta(hours=24):
        create_backup(kind=Backup.AUTO)


def restore_backup(backup):
    """Replace all business data with the backup. Backups themselves are kept."""
    text = gzip.decompress(bytes(backup.payload)).decode('utf-8')
    objects = list(serializers.deserialize('json', text))     # fail before touching anything
    keep = list(Backup.objects.all().values('kind', 'status', 'payload', 'size', 'created_at'))
    with transaction.atomic():
        call_command('flush', interactive=False, verbosity=0, reset_sequences=False)
        with connection.constraint_checks_disabled():
            for obj in objects:
                obj.save()
        for row in keep:
            when = row.pop('created_at')
            b = Backup.objects.create(**row)
            Backup.objects.filter(pk=b.pk).update(created_at=when)
        connection.check_constraints()
    return len(objects)
