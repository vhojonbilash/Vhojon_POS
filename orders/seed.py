from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import OrderSource, OrderStatus
from payments.models import PaymentMethod


@receiver(post_migrate)
def seed_initial_data(sender, **kwargs):
    # Only seed when orders app migrates (safe guard)
    if sender.name != "orders":
        return

    for s in ["POS", "WEBSITE"]:
        OrderSource.objects.get_or_create(name=s)

    for st in ["HELD", "PENDING", "COMPLETED", "CANCELLED"]:
        OrderStatus.objects.get_or_create(name=st)

    # Payment methods (optional seed)
    defaults = [
        ("Cash", "cash"),
        ("Card", "card"),
        ("bKash", "mobile"),
        ("Nagad", "mobile"),
        ("Rocket", "mobile"),
    ]
    for name, typ in defaults:
        PaymentMethod.objects.get_or_create(name=name, defaults={"type": typ})
