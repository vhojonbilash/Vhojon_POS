# orders/models.py

from decimal import Decimal
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

from customers.models import Customer, CustomerAddress
from catalog.models import Product
from payments.models import PaymentMethod


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Order(TimeStampedModel):
    # -----------------------------
    # ENUMS
    # -----------------------------
    class Source(models.TextChoices):
        ONLINE = "online", "Online"
        STORE = "store", "Physical Store"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    class DiscountType(models.TextChoices):
        FIXED = "fixed", "Fixed"
        PERCENT = "percent", "Percent"

    # -----------------------------
    # FIELDS
    # -----------------------------
    order_no = models.CharField(max_length=50, unique=True)

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    customer_address = models.ForeignKey(
        CustomerAddress,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    source = models.CharField(
        max_length=10,
        choices=Source.choices,
        default=Source.STORE,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Order-level discount (optional, can be used in addition to item discount if you want)
    discount_type = models.CharField(
        max_length=10,
        choices=DiscountType.choices,
        null=True,
        blank=True,
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    paid_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    due_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    notes = models.TextField(blank=True, null=True)
    ordered_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.order_no

    # -----------------------------
    # DERIVED STATUS
    # -----------------------------
    @property
    def payment_status(self):
        if self.due_total <= Decimal("0.00"):
            return "PAID"
        if self.paid_total > Decimal("0.00"):
            return "PARTIAL"
        return "DUE"

    # -----------------------------
    # CALCULATIONS
    # -----------------------------
    def _calc_discount_amount(self) -> Decimal:
        """
        Order-level discount applied on subtotal (after item-level discounts).
        """
        if not self.discount_type or self.discount_value in (None, ""):
            return Decimal("0.00")

        value = Decimal(self.discount_value)

        if self.discount_type == self.DiscountType.FIXED:
            return max(Decimal("0.00"), min(value, self.subtotal))

        percent = min(max(value, Decimal("0.00")), Decimal("100.00"))
        return (self.subtotal * percent / Decimal("100.00")).quantize(Decimal("0.01"))

    @transaction.atomic
    def recalc_totals(self):
        """
        Subtotal comes from OrderItem.line_total (already discounted per item).
        Then order-level discount applies, then tax, then payments => due.
        """
        items_total = self.items.aggregate(total=Sum("line_total"))["total"] or Decimal("0.00")
        self.subtotal = items_total

        self.discount_amount = self._calc_discount_amount()

        self.grand_total = max(
            Decimal("0.00"),
            (self.subtotal - self.discount_amount + (self.tax_amount or Decimal("0.00"))),
        ).quantize(Decimal("0.01"))

        # update paid & due
        self.recalc_payments(save=False)

        self.save(update_fields=[
            "subtotal",
            "discount_amount",
            "grand_total",
            "paid_total",
            "due_total",
            "updated_at",
        ])

    @transaction.atomic
    def recalc_payments(self, save=True):
        paid = self.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        self.paid_total = paid
        self.due_total = max(Decimal("0.00"), (self.grand_total or Decimal("0.00")) - paid).quantize(Decimal("0.01"))

        if save:
            self.save(update_fields=["paid_total", "due_total", "updated_at"])


class OrderItem(TimeStampedModel):
    class DiscountType(models.TextChoices):
        FIXED = "fixed", "Fixed"
        PERCENT = "percent", "Percent"

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
    )

    qty = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    # ✅ Per-item discount
    discount_type = models.CharField(
        max_length=10,
        choices=DiscountType.choices,
        null=True,
        blank=True,
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # net line total AFTER item discount
    line_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    def __str__(self):
        return f"{self.product.name} x {self.qty}"

    def _calc_discount_amount(self, gross: Decimal) -> Decimal:
        if not self.discount_type or self.discount_value in (None, ""):
            return Decimal("0.00")

        dv = Decimal(self.discount_value)

        if self.discount_type == self.DiscountType.FIXED:
            return max(Decimal("0.00"), min(dv, gross))

        pct = max(Decimal("0.00"), min(Decimal("100.00"), dv))
        return (gross * pct / Decimal("100.00")).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        gross = (Decimal(self.qty) * Decimal(self.unit_price)).quantize(Decimal("0.01"))
        self.discount_amount = self._calc_discount_amount(gross)
        self.line_total = max(Decimal("0.00"), (gross - self.discount_amount)).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)


class Payment(TimeStampedModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference_no = models.CharField(max_length=100, blank=True, null=True)
    paid_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.order.order_no} - {self.amount}"
