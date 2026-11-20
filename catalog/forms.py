from django import forms

from .models import Category, Product


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']


class ProductForm(forms.ModelForm):
    opening_stock = forms.IntegerField(min_value=0, initial=0, required=False,
                                       help_text='Quantity on hand when the product is first added.')

    class Meta:
        model = Product
        fields = ['code', 'name', 'category', 'unit_cost', 'price', 'reorder_level']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            del self.fields['opening_stock']  # on-hand changes go through the Stock screen
        self.fields['category'].queryset = Category.objects.all()

    def clean_code(self):
        return self.cleaned_data['code'].strip().upper()

    def clean(self):
        data = super().clean()
        if data.get('price') is not None and data['price'] < 0:
            self.add_error('price', 'Price cannot be negative.')
        if data.get('unit_cost') is not None and data['unit_cost'] < 0:
            self.add_error('unit_cost', 'Unit cost cannot be negative.')
        return data
