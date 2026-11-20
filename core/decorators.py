from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def admin_required(view):
    """Only the Admin / Owner role may open the view."""
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        profile = getattr(request.user, 'profile', None)
        if not (profile and profile.role == 'admin'):
            messages.error(request, 'That page is for the Admin / Owner only.')
            return redirect('core:dashboard')
        return view(request, *args, **kwargs)
    return wrapper
