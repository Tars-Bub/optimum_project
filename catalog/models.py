from decimal import Decimal

from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    """D2 Items, categories. `quantity` is the on-hand stock and only changes through stock.services."""
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=120)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    quantity = models.IntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} {self.name}'

    @property
    def status(self):
        if self.quantity <= 0:
            return 'depleted'
        if self.quantity <= self.reorder_level:
            return 'low'
        return 'in'

    @property
    def status_label(self):
        return {'depleted': 'Depleted', 'low': 'Low', 'in': 'In stock'}[self.status]

    @property
    def stock_percent(self):
        """Bar for 'Stock vs reorder level': full bar means at least twice the reorder level."""
        if self.quantity <= 0:
            return 0
        if self.reorder_level <= 0:
            return 100
        return min(100, round(self.quantity / (self.reorder_level * 2) * 100))
