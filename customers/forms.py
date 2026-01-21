# customers/forms.py
from django import forms
from django.forms import inlineformset_factory
from .models import Customer, CustomerAddress


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone"]


CustomerAddressFormSet = inlineformset_factory(
    Customer,
    CustomerAddress,
    fields=["address_line", "is_primary"],
    extra=1,           # show 1 empty address row
    can_delete=True
)
