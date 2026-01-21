from django import forms
from .models import UtilityBill, RawMaterialPurchase, StaffSalaryPayment, OtherExpense

class UtilityBillForm(forms.ModelForm):
    class Meta:
        model = UtilityBill
        fields = ["utility_type", "amount", "bill_date", "note"]
        widgets = {
            "bill_date": forms.DateInput(attrs={"type": "date"}),
        }

class RawMaterialPurchaseForm(forms.ModelForm):
    class Meta:
        model = RawMaterialPurchase
        fields = ["material", "unit", "quantity", "unit_price", "purchase_date", "vendor", "note"]
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
        }

class StaffSalaryPaymentForm(forms.ModelForm):
    class Meta:
        model = StaffSalaryPayment
        fields = ["staff", "amount", "pay_date", "month", "note"]
        widgets = {
            "pay_date": forms.DateInput(attrs={"type": "date"}),
            "month": forms.DateInput(attrs={"type": "date"}),
        }

class OtherExpenseForm(forms.ModelForm):
    class Meta:
        model = OtherExpense
        fields = ["title", "amount", "expense_date", "note"]
        widgets = {
            "expense_date": forms.DateInput(attrs={"type": "date"}),
        }
