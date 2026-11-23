from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import get_random_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from core.decorators import admin_required
from core.utils import audit

from .forms import RegisterForm, StaffForm
from .models import Profile

User = get_user_model()


def login_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if not request.POST.get('remember'):
                request.session.set_expiry(0)   # ends when the browser closes
            audit(user, 'Logged in')
            nxt = request.GET.get('next', '')
            if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
                return redirect(nxt)
            return redirect('core:dashboard')
        existing = User.objects.filter(username__iexact=username).select_related('profile').first()
        if existing and existing.check_password(password) and not existing.is_active:
            status = existing.profile.status
            error = ('Your registration is waiting for approval by the Admin / Owner.'
                     if status == 'pending' else 'This account is deactivated. Please contact the Admin / Owner.')
        else:
            error = 'Invalid username or password.'
    return render(request, 'accounts/login.html', {'error': error})


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        audit(request.user, 'Logged out')
    logout(request)
    return redirect('accounts:login')


def register_view(request):
    """Register Staff Account: the account stays Pending until the Admin / Owner approves it."""
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        user = User.objects.create_user(username=d['username'], email=d['email'],
                                        password=d['password1'], first_name=d['full_name'],
                                        is_active=False)
        Profile.objects.filter(user=user).update(position=d['position'], contact=d['contact'],
                                                 role='staff', status='pending')
        audit(None, 'Registration submitted', f"{d['username']} is waiting for approval")
        messages.success(request, 'Registration sent. You can log in once the Admin / Owner approves it.')
        return redirect('accounts:login')
    return render(request, 'accounts/register.html', {'form': form})


@admin_required
def staff_list(request):
    tab = request.GET.get('tab', 'accounts')
    profiles = Profile.objects.select_related('user').order_by('user__first_name', 'user__username')
    pending = [p for p in profiles if p.status == 'pending']
    accounts = [p for p in profiles if p.status != 'pending']
    return render(request, 'accounts/staff_list.html', {
        'tab': tab, 'accounts': accounts, 'pending': pending})


@admin_required
def staff_add(request):
    form = StaffForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        user = User.objects.create_user(username=d['username'], email=d['email'],
                                        password=d['password'], first_name=d['full_name'])
        Profile.objects.filter(user=user).update(position=d['position'], contact=d['contact'],
                                                 role=d['role'], status='active')
        audit(request.user, 'Staff account added', d['username'])
        messages.success(request, f"Account for {d['full_name']} created.")
        return redirect('accounts:staff')
    return render(request, 'accounts/staff_form.html', {'form': form, 'title': 'Add staff'})


@admin_required
def staff_edit(request, pk):
    profile = get_object_or_404(Profile.objects.select_related('user'), pk=pk)
    user = profile.user
    initial = {'full_name': user.get_full_name().strip(), 'position': profile.position,
               'email': user.email, 'contact': profile.contact, 'role': profile.role}
    form = StaffForm(request.POST or None, initial=initial, editing=True)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        if user == request.user and d['role'] != 'admin':
            messages.error(request, 'You cannot remove your own Admin / Owner role.')
        else:
            user.first_name, user.last_name, user.email = d['full_name'], '', d['email']
            user.save()
            profile.position, profile.contact, profile.role = d['position'], d['contact'], d['role']
            profile.save()
            audit(request.user, 'Staff account edited', user.username)
            messages.success(request, 'Account updated.')
            return redirect('accounts:staff')
    return render(request, 'accounts/staff_form.html', {
        'form': form, 'title': f'Edit {user.username}', 'editing': True})


@admin_required
@require_POST
def staff_toggle(request, pk):
    profile = get_object_or_404(Profile.objects.select_related('user'), pk=pk)
    if profile.user == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('accounts:staff')
    activate = profile.status != 'active'
    profile.user.is_active = activate
    profile.user.save(update_fields=['is_active'])
    profile.status = 'active' if activate else 'inactive'
    profile.save(update_fields=['status'])
    audit(request.user, 'Account activated' if activate else 'Account deactivated', profile.user.username)
    messages.success(request, f'{profile.user.username} is now {profile.status}.')
    return redirect('accounts:staff')


@admin_required
@require_POST
def staff_reset(request, pk):
    profile = get_object_or_404(Profile.objects.select_related('user'), pk=pk)
    temp = get_random_string(10)
    profile.user.set_password(temp)
    profile.user.save()
    audit(request.user, 'Password reset', profile.user.username)
    messages.success(request, f'Temporary password for {profile.user.username}: {temp} (share it privately).')
    return redirect('accounts:staff')


@admin_required
@require_POST
def staff_approve(request, pk):
    profile = get_object_or_404(Profile.objects.select_related('user'), pk=pk, status='pending')
    profile.user.is_active = True
    profile.user.save(update_fields=['is_active'])
    profile.status = 'active'
    profile.save(update_fields=['status'])
    audit(request.user, 'Registration approved', profile.user.username)
    messages.success(request, f'{profile.user.username} approved.')
    return redirect('/accounts/staff/?tab=pending')


@admin_required
@require_POST
def staff_reject(request, pk):
    profile = get_object_or_404(Profile.objects.select_related('user'), pk=pk, status='pending')
    username = profile.user.username
    profile.user.delete()
    audit(request.user, 'Registration rejected', username)
    messages.success(request, f'Registration for {username} rejected.')
    return redirect('/accounts/staff/?tab=pending')
