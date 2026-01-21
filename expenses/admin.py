from django.contrib import admin
from .models import (
    UtilityType, UtilityBill, Unit, RawMaterial, RawMaterialPurchase,
    StaffSalaryPayment, OtherExpense
)

admin.site.register(UtilityType)
admin.site.register(UtilityBill)
admin.site.register(Unit)
admin.site.register(RawMaterial)
admin.site.register(RawMaterialPurchase)
admin.site.register(StaffSalaryPayment)
admin.site.register(OtherExpense)
