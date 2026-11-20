from django import forms

from catalog.models import Product


class IncomingForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.none())
    quantity = forms.IntegerField(min_value=1)
    reference = forms.CharField(max_length=60, required=False, label='Delivery receipt / supplier')
    note = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(is_active=True)


class AdjustForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.none())
    counted = forms.IntegerField(min_value=0, label='Counted quantity')
    reason = forms.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
