from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Customer(TimeStampedModel):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"

    @property
    def total_due(self) -> Decimal:
        """
        Total outstanding due across all non-cancelled orders.
        """
        from orders.models import Order  # avoid circular import

        agg = (
            Order.objects
            .filter(customer=self)
            .exclude(status=Order.Status.CANCELLED)
            .aggregate(total=Sum("due_total"))
        )
        return agg["total"] or Decimal("0.00")


class CustomerAddress(TimeStampedModel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="addresses"
    )
    address_line = models.TextField()
    is_primary = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.customer.name} - {self.address_line[:30]}"
