from django.utils import timezone


def generate_order_no(prefix="ORD"):
    # Example: ORD-20260104-000001 (you can improve with DB sequence later)
    today = timezone.localdate().strftime("%Y%m%d")
    return f"{prefix}-{today}-{timezone.now().strftime('%H%M%S%f')}"
