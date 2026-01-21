from django.db import models
from django.utils import timezone
from staff.models import Staff

class UtilityType(models.Model):
    name = models.CharField(max_length=80, unique=True)  # e.g. Current Bill, Gas Bill

    def __str__(self):
        return self.name


class UtilityBill(models.Model):
    utility_type = models.ForeignKey(UtilityType, on_delete=models.PROTECT, related_name="bills")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    bill_date = models.DateField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.utility_type} - {self.amount}"


class Unit(models.Model):
    """
    You can keep it flexible:
    kg, liter, pcs, packet, etc.
    """
    name = models.CharField(max_length=30, unique=True)   # "kg", "liter", "pcs"
    symbol = models.CharField(max_length=10, blank=True)  # "kg", "L", "pcs"

    def __str__(self):
        return self.symbol or self.name


class RawMaterial(models.Model):
    name = models.CharField(max_length=120, unique=True)  # "Rice", "Oil", "Chicken"
    default_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="materials")

    def __str__(self):
        return self.name


class RawMaterialPurchase(models.Model):
    material = models.ForeignKey(RawMaterial, on_delete=models.PROTECT, related_name="purchases")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)  # allow 1.250 kg
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)  # price per unit
    purchase_date = models.DateField(default=timezone.now)
    vendor = models.CharField(max_length=120, blank=True)
    note = models.CharField(max_length=255, blank=True)

    @property
    def total(self):
        return (self.quantity or 0) * (self.unit_price or 0)

    def __str__(self):
        return f"{self.material} - {self.total}"


class StaffSalaryPayment(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name="salary_payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    pay_date = models.DateField(default=timezone.now)
    month = models.DateField(help_text="Use first day of the month (e.g. 2026-01-01).")
    note = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        if self.amount in (None, ""):
            self.amount = self.staff.monthly_salary
        super().save(*args, **kwargs)



class OtherExpense(models.Model):
    title = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    expense_date = models.DateField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.title} - {self.amount}"
