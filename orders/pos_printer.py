# orders/pos_printer.py
from django.conf import settings

try:
    import win32print
except ImportError:
    win32print = None


# =====================================================
# Helpers
# =====================================================
def _line(n=48, ch="-"):
    return ch * n + "\n"


def _money(v):
    try:
        return f"{float(v):.2f}"
    except Exception:
        return "0.00"


def get_windows_printer_name():
    name = getattr(settings, "WINDOWS_POS_PRINTER_NAME", None)
    if not name:
        raise ValueError("WINDOWS_POS_PRINTER_NAME is not set in settings.py")
    return name


def _get_order_items(order):
    """
    Robustly fetch order items regardless of related_name.
    """
    candidates = [
        "items",
        "order_items",
        "orderitem_set",
    ]

    for attr in candidates:
        rel = getattr(order, attr, None)
        if rel and hasattr(rel, "all"):
            try:
                return rel.select_related("product").all()
            except Exception:
                return rel.all()

    return []


# =====================================================
# RAW PRINT
# =====================================================
def _raw_print(data: bytes):
    if not getattr(settings, "POS_PRINTER_ENABLED", True):
        return False, "Printer disabled (DEV MODE)."

    if win32print is None:
        return False, "pywin32 not installed"

    printer_name = get_windows_printer_name()

    try:
        hPrinter = win32print.OpenPrinter(printer_name)
        hJob = win32print.StartDocPrinter(
            hPrinter, 1, ("Vhojon Receipt", None, "RAW")
        )
        win32print.StartPagePrinter(hPrinter)
        win32print.WritePrinter(hPrinter, data)
        win32print.EndPagePrinter(hPrinter)
        win32print.EndDocPrinter(hPrinter)
        win32print.ClosePrinter(hPrinter)
        return True, "Printed"
    except Exception as e:
        try:
            win32print.ClosePrinter(hPrinter)
        except Exception:
            pass
        return False, str(e)


# =====================================================
# CHEF KOT
# =====================================================
def print_chef_kot(order):
    items = _get_order_items(order)

    lines = []
    lines.append("\x1b\x40")          # init
    lines.append("\x1b\x61\x01")      # center
    lines.append("\x1b\x21\x30")      # double size
    lines.append("KITCHEN ORDER\n")
    lines.append("\x1b\x21\x00")
    lines.append(_line(48, "="))

    lines.append("\x1b\x61\x00")
    lines.append(f"Order: {order.order_no}\n")
    lines.append(f"Time : {order.created_at.strftime('%d-%b-%Y %I:%M %p')}\n")

    if getattr(order, "customer", None):
        if order.customer.name:
            lines.append(f"Customer: {order.customer.name}\n")
        if order.customer.phone:
            lines.append(f"Phone   : {order.customer.phone}\n")

    if getattr(order, "notes", None):
        lines.append(_line())
        lines.append(f"Note: {order.notes}\n")

    lines.append(_line(48, "="))
    lines.append("ITEMS\n")
    lines.append(_line())

    # 🔴 CRITICAL FIX: ensure items exist
    if not items:
        lines.append("** NO ITEMS FOUND **\n")
    else:
        for it in items:
            pname = (it.product.name or "").strip()
            qty = it.qty or 0
            lines.append(f"{qty} x {pname}\n")

    # 🔴 FEED before cut (VERY IMPORTANT)
    lines.append("\n\n\n")
    lines.append("\x1b\x64\x03")  # feed 3 lines
    lines.append("\x1d\x56\x00")  # cut

    data = "".join(lines).encode("ascii", errors="ignore")
    return _raw_print(data)


# =====================================================
# CUSTOMER RECEIPT
# =====================================================
def print_customer_receipt(order):
    items = _get_order_items(order)

    lines = []
    lines.append("\x1b\x40")
    lines.append("\x1b\x61\x01")
    lines.append("\x1b\x21\x30")
    lines.append("VHOJON BILASH\n")
    lines.append("\x1b\x21\x00")
    lines.append("Customer Receipt\n")
    lines.append(_line(48, "="))

    lines.append("\x1b\x61\x00")
    lines.append(f"Invoice: {order.order_no}\n")
    lines.append(f"Date   : {order.created_at.strftime('%d-%b-%Y %I:%M %p')}\n")

    if getattr(order, "customer", None):
        if order.customer.name:
            lines.append(f"Customer: {order.customer.name}\n")
        if order.customer.phone:
            lines.append(f"Phone   : {order.customer.phone}\n")

    lines.append(_line())
    lines.append(f"{'Item':<24}{'Qty':>4}{'Price':>8}{'Total':>10}\n")
    lines.append(_line())

    if not items:
        lines.append("NO ITEMS\n")
    else:
        for it in items:
            name = ((it.product.name or "")[:24]).ljust(24)
            qty = it.qty or 0
            unit = it.unit_price or 0
            total = it.line_total or 0
            lines.append(
                f"{name}{qty:>4}{_money(unit):>8}{_money(total):>10}\n"
            )

    lines.append(_line())
    lines.append(f"{'Subtotal':<28}{_money(order.subtotal):>20}\n")
    if order.discount_amount > 0:
        lines.append(f"{'Discount':<28}-{_money(order.discount_amount):>19}\n")
    if order.tax_amount > 0:
        lines.append(f"{'Tax':<28}{_money(order.tax_amount):>20}\n")

    lines.append(_line(48, "="))
    lines.append(f"{'Grand Total':<28}{_money(order.grand_total):>20}\n")
    lines.append(f"{'Paid':<28}{_money(order.paid_total):>20}\n")
    lines.append(f"{'Due':<28}{_money(order.due_total):>20}\n")

    lines.append(_line())
    lines.append("\x1b\x61\x01")
    lines.append("Thank you! Come again.\n")
    lines.append("\x1b\x61\x00")

    lines.append("\n\n\n")
    lines.append("\x1b\x64\x03")
    lines.append("\x1d\x56\x00")

    data = "".join(lines).encode("ascii", errors="ignore")
    return _raw_print(data)
