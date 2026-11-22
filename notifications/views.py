from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.decorators import admin_required
from core.utils import audit

from .models import SmsLog
from .services import send_sms


@login_required
def index(request):
    logs = SmsLog.objects.select_related('order', 'created_by')
    kind = request.GET.get('kind', '')
    if kind:
        logs = logs.filter(kind=kind)
    counts = {s: SmsLog.objects.filter(status=s).count() for s in ('sent', 'failed', 'skipped')}
    return render(request, 'notifications/index.html', {
        'logs': logs[:200], 'counts': counts, 'kind': kind, 'kinds': SmsLog.KIND_CHOICES,
        'configured': bool(settings.PHILSMS_API_TOKEN), 'owner_number': settings.SMS_OWNER_NUMBER})


@admin_required
@require_POST
def send_manual(request):
    number = request.POST.get('number', '')
    text = request.POST.get('message', '').strip()[:300]
    if not text:
        messages.error(request, 'Type a message first.')
        return redirect('notifications:index')
    row = send_sms(number, text, 'manual', None, request.user)
    audit(request.user, 'SMS sent' if row.status == 'sent' else 'SMS not sent', f'{row.recipient} {row.status}')
    if row.status == 'sent':
        messages.success(request, f'Message sent to {row.recipient}.')
    else:
        messages.error(request, f'Message was not sent: {row.detail}')
    return redirect('notifications:index')


@login_required
@require_POST
def resend(request, pk):
    old = SmsLog.objects.get(pk=pk)
    row = send_sms(old.recipient, old.message, old.kind, old.order, request.user)
    (messages.success if row.status == 'sent' else messages.error)(
        request, 'Message sent again.' if row.status == 'sent' else f'Still not sent: {row.detail}')
    return redirect('notifications:index')
