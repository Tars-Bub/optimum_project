from django.conf import settings
from django.db import models


class Profile(models.Model):
    """D1 Staff accounts: role, position, contact and approval status for each user."""
    ROLE_CHOICES = [('staff', 'Staff'), ('admin', 'Admin / Owner')]
    STATUS_CHOICES = [('active', 'Active'), ('inactive', 'Inactive'), ('pending', 'Pending')]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')
    position = models.CharField(max_length=60, blank=True)
    contact = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def display_name(self):
        return self.user.get_full_name().strip() or self.user.username

    def __str__(self):
        return f'{self.display_name} ({self.get_role_display()})'
