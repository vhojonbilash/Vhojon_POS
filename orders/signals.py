from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import OrderItem, Payment


@receiver([post_save, post_delete], sender=OrderItem)
def orderitem_changed(sender, instance, **kwargs):
    instance.order.recalc_totals()


@receiver([post_save, post_delete], sender=Payment)
def payment_changed(sender, instance, **kwargs):
    # payments affect paid_total/due_total
    instance.order.recalc_payments()
