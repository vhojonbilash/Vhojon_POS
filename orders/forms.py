# orders/forms.py
from decimal import Decimal
from django import forms
from django.forms import inlineformset_factory

from .models import Order, OrderItem, Payment
from customers.models import Customer, CustomerAddress
from catalog.models import Product


# =====================================================
# CUSTOMER (SEARCH BY PHONE OR CREATE NEW)
# =====================================================
class CustomerCreateOrSelectForm(forms.Form):
    existing_phone = forms.CharField(max_length=20, required=False, label="Phone Number")

    name = forms.CharField(max_length=150, required=False, label="Name")
    phone = forms.CharField(max_length=20, required=False, label="Phone")
    address = forms.CharField(
        required=False,
        label="Address",
        widget=forms.Textarea(attrs={"rows": 2})
    )

    def clean(self):
        data = super().clean()

        existing_phone = (data.get("existing_phone") or "").strip()
        name = (data.get("name") or "").strip()
        phone = (data.get("phone") or "").strip()
        address = (data.get("address") or "").strip()

        # mirror search phone into phone field for new customer creation
        if existing_phone and not phone:
            data["phone"] = existing_phone
            phone = existing_phone

        # If phone exists -> valid existing customer
        if existing_phone and Customer.objects.filter(phone=existing_phone).exists():
            return data

        # New customer path: if phone provided, require name + address
        if phone:
            if not name:
                raise forms.ValidationError("Customer name is required for a new customer.")
            if not address:
                raise forms.ValidationError("Customer address is required for a new customer.")

        return data

    def get_or_create_customer(self):
        existing_phone = (self.cleaned_data.get("existing_phone") or "").strip()
        if existing_phone:
            existing = Customer.objects.filter(phone=existing_phone).first()
            if existing:
                return existing

        name = (self.cleaned_data.get("name") or "").strip()
        phone = (self.cleaned_data.get("phone") or "").strip()
        address = (self.cleaned_data.get("address") or "").strip()

        if not phone:
            return None  # walk-in

        customer, _ = Customer.objects.get_or_create(
            phone=phone,
            defaults={"name": name or "Customer"},
        )

        # Update name if needed
        if name and customer.name != name:
            customer.name = name
            customer.save(update_fields=["name", "updated_at"])

        # Create/update primary address
        if address:
            addr = CustomerAddress.objects.filter(customer=customer, is_primary=True).first()
            if addr:
                if addr.address_line != address:
                    addr.address_line = address
                    addr.save(update_fields=["address_line", "updated_at"])
            else:
                CustomerAddress.objects.create(customer=customer, address_line=address, is_primary=True)

        return customer


# =====================================================
# ORDER FORM
# =====================================================
class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["source", "status", "discount_type", "discount_value", "tax_amount", "notes"]

    def clean_discount_value(self):
        dv = self.cleaned_data.get("discount_value")
        if dv is None:
            return dv
        if dv < Decimal("0.00"):
            raise forms.ValidationError("Discount value cannot be negative.")
        return dv


# =====================================================
# ORDER ITEM FORM (✅ updated product widget for AJAX search)
# =====================================================
class OrderItemForm(forms.ModelForm):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        widget=forms.Select(attrs={
            "class": "js-product-search",  # ✅ used by JS to enable search dropdown
        })
    )

    # unit_price optional (auto-fill)
    unit_price = forms.DecimalField(required=False)

    # discount_value optional
    discount_value = forms.DecimalField(required=False)

    class Meta:
        model = OrderItem
        fields = ["product", "qty", "unit_price", "discount_type", "discount_value"]

    def clean_qty(self):
        qty = self.cleaned_data.get("qty") or 0
        if qty <= 0:
            raise forms.ValidationError("Quantity must be greater than 0.")
        return qty

    def clean_unit_price(self):
        up = self.cleaned_data.get("unit_price")
        if up is None:
            return up
        if up < Decimal("0.00"):
            raise forms.ValidationError("Unit price cannot be negative.")
        return up

    def clean_discount_value(self):
        dv = self.cleaned_data.get("discount_value")
        if dv is None:
            return dv
        if dv < Decimal("0.00"):
            raise forms.ValidationError("Discount value cannot be negative.")
        return dv

    def save(self, commit=True):
        obj = super().save(commit=False)

        # Auto-fill unit_price from product if empty
        if obj.unit_price in (None, ""):
            obj.unit_price = obj.product.sale_price

        if commit:
            obj.save()
        return obj


OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    extra=1,
    can_delete=True,
)


# =====================================================
# PAYMENT FORM
# =====================================================
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["payment_method", "amount", "reference_no"]

    def clean_amount(self):
        amt = self.cleaned_data.get("amount") or Decimal("0.00")
        if amt < Decimal("0.00"):
            raise forms.ValidationError("Amount cannot be negative.")
        return amt


PaymentFormSet = inlineformset_factory(
    Order,
    Payment,
    form=PaymentForm,
    extra=1,
    can_delete=True,
)
