from django import forms

from .models import Category, Product


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']


class ProductForm(forms.ModelForm):
    opening_stock = forms.IntegerField(min_value=0, initial=0, required=False, label='Initial stock',
                                       widget=forms.NumberInput(attrs={'placeholder': '0'}))

    class Meta:
        model = Product
        fields = ['name', 'category', 'price', 'opening_stock', 'reorder_level', 'code', 'unit_cost']
        labels = {'name': 'Item name', 'reorder_level': 'Low-stock threshold', 'code': 'Item code (optional)',
                  'unit_cost': 'Unit cost (optional)'}
        widgets = {'name': forms.TextInput(attrs={'placeholder': 'e.g. Copy Paper, Legal'}),
                   'price': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01'}),
                   'unit_cost': forms.NumberInput(attrs={'placeholder': '0.00', 'step': '0.01'}),
                   'code': forms.TextInput(attrs={'placeholder': 'Auto-generated if empty'}),
                   'reorder_level': forms.NumberInput(attrs={'placeholder': 'Notify staff when stock reaches...'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            del self.fields['opening_stock']  # on-hand changes go through the Stock screen
        self.fields['category'].queryset = Category.objects.all()
        self.fields['category'].empty_label = None
        self.fields['code'].required = False
        self.fields['unit_cost'].required = False

    def clean_unit_cost(self):
        return self.cleaned_data.get('unit_cost') or 0

    def clean_code(self):
        code = (self.cleaned_data.get('code') or '').strip().upper()
        if not code:
            return ''
        if Product.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('An item with this code already exists.')
        return code

    def save(self, commit=True):
        obj = super().save(commit=False)
        if not obj.code:
            prefix = ''.join(ch for ch in obj.category.name.upper() if ch.isalpha())[:3].ljust(3, 'X')
            n = Product.objects.count() + 1001
            while Product.objects.filter(code=f'{prefix}-{n}').exists():
                n += 1
            obj.code = f'{prefix}-{n}'
        if commit:
            obj.save()
        return obj

    def clean(self):
        data = super().clean()
        if data.get('price') is not None and data['price'] < 0:
            self.add_error('price', 'Price cannot be negative.')
        if data.get('unit_cost') is not None and data['unit_cost'] < 0:
            self.add_error('unit_cost', 'Unit cost cannot be negative.')
        return data
