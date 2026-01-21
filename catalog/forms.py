from django import forms
from .models import Product
from django import forms
from .models import Product, Category

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["category", "name", "sku", "sale_price", "cost_price", "is_active"]



class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["category", "name", "sku", "sale_price", "cost_price", "is_active"]


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "parent", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Category name"}),
        }
