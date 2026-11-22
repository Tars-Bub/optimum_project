from django import forms
from django.utils.html import format_html, format_html_join

from catalog.models import Product


class ProductInput(forms.TextInput):
    """Text box with a type-ahead list of products (code, name, qty on hand)."""

    def render(self, name, value, attrs=None, renderer=None):
        attrs = dict(attrs or {})
        list_id = f'{attrs.get("id", name)}_options'
        attrs.update({'list': list_id, 'autocomplete': 'off',
                      'placeholder': 'Type a code or item name, e.g. PAP-1001'})
        box = super().render(name, value, attrs, renderer)
        products = Product.objects.filter(is_active=True).order_by('code')
        options = format_html_join(
            '', '<option value="{}" data-qty="{}">{} (on hand: {})</option>',
            ((f'{p.code} \u2014 {p.name}', p.quantity, p.name, p.quantity) for p in products))
        return format_html('{}<datalist id="{}">{}</datalist>', box, list_id, options)


class ProductField(forms.Field):
    """Accepts a product code, the full 'CODE — Name' text, or an exact / unique partial name."""
    widget = ProductInput

    def to_python(self, value):
        text = (value or '').strip()
        if not text:
            return None
        qs = Product.objects.filter(is_active=True)
        code = text.split('\u2014')[0].strip()
        found = qs.filter(code__iexact=code).first() or qs.filter(name__iexact=text).first()
        if found:
            return found
        partial = list(qs.filter(name__icontains=text)[:2]) or list(qs.filter(code__icontains=text)[:2])
        if len(partial) == 1:
            return partial[0]
        if len(partial) > 1:
            raise forms.ValidationError('More than one item matches. Type the full item code.')
        raise forms.ValidationError('No active item matches that. Check the code or add the item in Catalog first.')

    def validate(self, value):
        if value is None and self.required:
            raise forms.ValidationError(self.error_messages['required'], code='required')


class IncomingForm(forms.Form):
    product = ProductField(label='Item')
    quantity = forms.IntegerField(min_value=1, label='Quantity received',
                                  widget=forms.NumberInput(attrs={'placeholder': '0'}))
    received_on = forms.DateField(label='Date received', required=False, widget=forms.DateInput(
        attrs={'type': 'date'}, format='%Y-%m-%d'))
    supplier = forms.CharField(max_length=120, required=False,
                               widget=forms.TextInput(attrs={'placeholder': 'e.g. Office Supply Co.'}))
    reference = forms.CharField(max_length=60, required=False,
                                widget=forms.TextInput(attrs={'placeholder': 'PO or invoice number'}))
    note = forms.CharField(max_length=255, required=False, label='Notes',
                           widget=forms.Textarea(attrs={'placeholder': 'Add receiving notes (optional)', 'rows': 3}))


REASONS = ['Cycle count', 'Damaged goods', 'Lost or missing', 'Found stock', 'Data entry correction', 'Other']


class AdjustForm(forms.Form):
    product = ProductField(label='Item')
    counted = forms.IntegerField(min_value=0, label='New count', widget=forms.NumberInput(attrs={'placeholder': '0'}))
    reason = forms.ChoiceField(choices=[('', 'Select an adjustment reason')] + [(r, r) for r in REASONS])
    note = forms.CharField(max_length=200, required=False, label='Notes',
                           widget=forms.Textarea(attrs={'placeholder': 'Describe why this adjustment is needed', 'rows': 3}))
