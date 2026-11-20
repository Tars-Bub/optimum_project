from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import Profile
from catalog.models import Category, Product
from stock.services import apply_movement

User = get_user_model()

CATEGORIES = ['Paper & Notebooks', 'Writing Supplies', 'Ink & Toner', 'Desk Accessories',
              'Filing & Storage', 'Labels']
# code, name, category, unit cost, price, opening stock, reorder level
PRODUCTS = [
    ('PAP-1001', 'Copy Paper, Letter', 'Paper & Notebooks', '210.00', '285.00', 4, 15),
    ('NOT-3012', 'Sticky Notes, Yellow', 'Paper & Notebooks', '28.00', '45.00', 86, 20),
    ('WRT-2042', 'Blue Ballpoint Pens (box)', 'Writing Supplies', '95.00', '140.00', 9, 20),
    ('INK-3108', 'Black Toner Cartridge', 'Ink & Toner', '1450.00', '1890.00', 0, 8),
    ('DSK-1098', 'Desk Organizer, Mesh', 'Desk Accessories', '180.00', '265.00', 42, 12),
    ('DSK-2214', 'Heavy Duty Stapler', 'Desk Accessories', '240.00', '350.00', 16, 8),
    ('FIL-4021', 'Manila File Folders (pack)', 'Filing & Storage', '120.00', '185.00', 12, 10),
    ('LBL-5034', 'Shipping Labels 2x4', 'Labels', '150.00', '225.00', 7, 10),
]


class Command(BaseCommand):
    help = 'Create demo accounts, categories and products (safe to run more than once).'

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username='admin', defaults={'first_name': 'Owner', 'email': 'owner@example.com',
                                        'is_staff': True, 'is_superuser': True})
        if created:
            admin.set_password('admin12345')
            admin.save()
        Profile.objects.filter(user=admin).update(role='admin', position='Owner', status='active')

        staff, created = User.objects.get_or_create(
            username='staff1', defaults={'first_name': 'Taylor Reed', 'email': 'staff1@example.com'})
        if created:
            staff.set_password('staff12345')
            staff.save()
        Profile.objects.filter(user=staff).update(role='staff', position='Cashier', contact='09171234567')

        cats = {name: Category.objects.get_or_create(name=name)[0] for name in CATEGORIES}
        for code, name, cat, cost, price, qty, reorder in PRODUCTS:
            product, made = Product.objects.get_or_create(code=code, defaults={
                'name': name, 'category': cats[cat], 'unit_cost': Decimal(cost),
                'price': Decimal(price), 'reorder_level': reorder})
            if made and qty:
                apply_movement(product, qty, 'opening', admin, note='Opening stock')
        self.stdout.write(self.style.SUCCESS(
            'Demo data ready.  Admin: admin / admin12345   Staff: staff1 / staff12345'))
