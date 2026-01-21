# orders/utils/pos_printer.py

from escpos.printer import Network
from django.conf import settings

def get_printer():
    cfg = getattr(settings, "POS_PRINTER", {})

    host = cfg.get("HOST")
    port = cfg.get("PORT", 9100)

    # ✅ DEV SAFE: printer not purchased yet
    if not host:
        raise Exception("POS_PRINTER['HOST'] is not set in settings.py")

    return Network(host, port=port, timeout=10)
