# orders/views.py
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.core.paginator import Paginator

from customers.models import CustomerAddress
from catalog.models import Product

from .forms import CustomerCreateOrSelectForm, OrderForm, OrderItemFormSet, PaymentFormSet
from .models import Order
from .utils import generate_order_no

from .pos_printer import print_chef_kot, print_customer_receipt


def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _filter_date_range(qs, field_name, from_date, to_date):
    """
    Filters a queryset by date range using a DateTimeField or DateField.
    If it's a DateTimeField (common: created_at), we compare using __date.
    """
    if not from_date and not to_date:
        return qs

    # ✅ If your model uses a DateField like order_date, change these lookups:
    #   - remove "__date__" from below.
    # Example for DateField:
    #   f"{field_name}__range"
    #   f"{field_name}__gte"
    #   f"{field_name}__lte"

    if from_date and to_date:
        return qs.filter(**{f"{field_name}__date__range": (from_date, to_date)})
    if from_date:
        return qs.filter(**{f"{field_name}__date__gte": from_date})
    return qs.filter(**{f"{field_name}__date__lte": to_date})


# =====================================================
# ✅ PRODUCT SEARCH (AJAX)
# =====================================================
@login_required
def product_search(request):
    q = (request.GET.get("q") or "").strip()
    page = int(request.GET.get("page") or 1)
    page_size = 10

    qs = Product.objects.filter(is_active=True).order_by("name")

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))

    start = (page - 1) * page_size
    end = start + page_size

    results = []
    for p in qs[start:end]:
        label = p.name
        if getattr(p, "sku", None):
            label = f"{p.name} ({p.sku})"

        results.append({
            "id": p.id,
            "text": label,
            "price": str(p.sale_price),
        })

    return JsonResponse({
        "results": results,
        "pagination": {"more": qs.count() > end},
    })


# =====================================================
# ✅ CREATE ORDER (Customer optional)
# =====================================================
@login_required
@transaction.atomic
def order_create(request):
    if request.method == "POST":
        cust_form = CustomerCreateOrSelectForm(request.POST)
        form = OrderForm(request.POST)

        temp_order = Order(order_no=generate_order_no())
        items_formset = OrderItemFormSet(request.POST, instance=temp_order)
        pay_formset = PaymentFormSet(request.POST, instance=temp_order)

        # ✅ validate core parts first
        base_ok = form.is_valid() and items_formset.is_valid() and pay_formset.is_valid()

        # ✅ detect if user actually entered customer info
        entered_existing_phone = (request.POST.get("existing_phone") or "").strip()
        entered_phone = (request.POST.get("phone") or "").strip()
        entered_name = (request.POST.get("name") or "").strip()
        entered_address = (request.POST.get("address") or "").strip()

        customer_requested = bool(entered_existing_phone or entered_phone or entered_name or entered_address)

        # ✅ only validate customer form if user provided something
        cust_ok = cust_form.is_valid() if customer_requested else True

        if base_ok and cust_ok:
            customer = None

            if customer_requested:
                customer = cust_form.get_or_create_customer()

            order = form.save(commit=False)
            order.order_no = generate_order_no()
            order.customer = customer

            if customer:
                addr = (
                    CustomerAddress.objects.filter(customer=customer)
                    .order_by("-is_primary", "-created_at")
                    .first()
                )
                order.customer_address = addr
                # clear guest fields (optional)
                order.guest_name = None
                order.guest_phone = None
                order.guest_address = None
            else:
                # ✅ store guest info directly on order (phone can be null)
                order.guest_name = entered_name or None
                order.guest_phone = entered_phone or None
                order.guest_address = entered_address or None
                order.customer_address = None

            if not order.source:
                order.source = Order.Source.STORE
            if not order.status:
                order.status = Order.Status.PENDING

            order.save()

            items_formset.instance = order
            items_formset.save()

            pay_formset.instance = order
            pay_formset.save()

            order.recalc_totals()

            if is_ajax(request):
                return JsonResponse({
                    "ok": True,
                    "redirect_url": redirect("orders:order_print_options", pk=order.pk).url,
                    "order_id": order.id,
                    "order_no": order.order_no,
                    "payment_status": order.payment_status,
                    "subtotal": str(order.subtotal),
                    "discount_amount": str(order.discount_amount),
                    "grand_total": str(order.grand_total),
                    "paid_total": str(order.paid_total),
                    "due_total": str(order.due_total),
                })

            messages.success(request, f"Order created: {order.order_no} | Due: {order.due_total}")
            return redirect("orders:order_print_options", pk=order.pk)

        # invalid
        if is_ajax(request):
            return JsonResponse({
                "ok": False,
                "cust_errors": (cust_form.errors if customer_requested else {}),
                "order_errors": form.errors,
                "item_errors": [f.errors for f in items_formset],
                "payment_errors": [f.errors for f in pay_formset],
            }, status=400)

        messages.error(request, "Please fix the errors below.")

    else:
        cust_form = CustomerCreateOrSelectForm()
        form = OrderForm(initial={
            "source": Order.Source.STORE,
            "status": Order.Status.PENDING
        })
        temp_order = Order(order_no="TEMP")
        items_formset = OrderItemFormSet(instance=temp_order)
        pay_formset = PaymentFormSet(instance=temp_order)

    return render(request, "orders/order_create.html", {
        "cust_form": cust_form,
        "form": form,
        "items_formset": items_formset,
        "pay_formset": pay_formset,
    })


# =====================================================
# ✅ PRINT OPTIONS PAGE
# =====================================================
@login_required
def order_print_options(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("customer", "customer_address"),
        pk=pk
    )
    return render(request, "orders/order_print_options.html", {"order": order})


# =====================================================
# ✅ PRINT CHEF KOT (AJAX)
# =====================================================
@login_required
def order_print_chef(request, pk):
    order = get_object_or_404(Order, pk=pk)

    ok, msg = print_chef_kot(order)

    if not ok:
        return JsonResponse({"ok": False, "error": msg}, status=400)

    return JsonResponse({"ok": True, "message": msg})


@login_required
def order_print_customer(request, pk):
    order = get_object_or_404(Order, pk=pk)

    ok, msg = print_customer_receipt(order)

    if not ok:
        return JsonResponse({"ok": False, "error": msg}, status=400)

    return JsonResponse({"ok": True, "message": msg})


# =====================================================
# ✅ ORDER DETAIL
# =====================================================
@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("customer", "customer_address"),
        pk=pk
    )

    # ✅ to show product info fast + avoid N+1 query
    items = order.items.select_related("product").all()
    payments = order.payments.all()

    return render(request, "orders/order_detail.html", {
        "order": order,
        "items": items,
        "payments": payments,
    })


@login_required
def create_pos_order(request):
    return render(request, "orders/create_pos_order.html")


# =====================================================
# ✅ ORDER LIST (✅ Updated: Date range + Totals)
# =====================================================
@login_required
def order_list(request):
    qs = Order.objects.select_related("customer").order_by("-id")

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    source = request.GET.get("source", "").strip()
    due = request.GET.get("due", "").strip()

    # ✅ NEW: date range inputs
    from_str = request.GET.get("from_date", "").strip()
    to_str = request.GET.get("to_date", "").strip()
    from_date = date.fromisoformat(from_str) if from_str else None
    to_date = date.fromisoformat(to_str) if to_str else None

    # ✅ Choose the date field used for filtering
    # Most common is created_at (DateTimeField). Change if needed.
    DATE_FIELD = "created_at"

    if q:
        qs = qs.filter(
            Q(order_no__icontains=q) |
            Q(customer__name__icontains=q) |
            Q(customer__phone__icontains=q) |
            Q(guest_name__icontains=q) |
            Q(guest_phone__icontains=q)
        )

    if status:
        qs = qs.filter(status=status)

    if source:
        qs = qs.filter(source=source)

    if due == "1":
        qs = qs.filter(due_total__gt=0)
    elif due == "0":
        qs = qs.filter(due_total__lte=0)

    # ✅ NEW: apply date filter
    qs = _filter_date_range(qs, DATE_FIELD, from_date, to_date)

    # ✅ NEW: totals for currently filtered qs (whole set, not only current page)
    totals = qs.aggregate(
        total_revenue=Sum("grand_total"),
        total_paid=Sum("paid_total"),
        total_due=Sum("due_total"),
        total_discount=Sum("discount_amount"),
    )

    total_orders = qs.count()
    total_revenue = totals["total_revenue"] or Decimal("0")
    total_paid = totals["total_paid"] or Decimal("0")
    total_due = totals["total_due"] or Decimal("0")
    total_discount = totals["total_discount"] or Decimal("0")

    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "orders": page_obj.object_list,

        "q": q,
        "status": status,
        "source": source,
        "due": due,

        # ✅ NEW: keep date filter values in template
        "from_date": from_date,
        "to_date": to_date,

        # ✅ NEW: totals
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "total_paid": total_paid,
        "total_due": total_due,
        "total_discount": total_discount,

        "status_choices": getattr(Order.Status, "choices", []),
        "source_choices": getattr(Order.Source, "choices", []),
        "due_choices": [
            ("", "All"),
            ("1", "Due Only"),
            ("0", "Paid Only"),
        ],
    }
    return render(request, "orders/order_list.html", context)


# =====================================================
# ✅ UPDATE ORDER
# =====================================================
@login_required
@transaction.atomic
def order_update(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == "POST":
        form = OrderForm(request.POST, instance=order)
        items_formset = OrderItemFormSet(request.POST, instance=order)
        pay_formset = PaymentFormSet(request.POST, instance=order)

        if form.is_valid() and items_formset.is_valid() and pay_formset.is_valid():
            order = form.save()
            items_formset.save()
            pay_formset.save()

            order.recalc_totals()

            messages.success(request, f"Order updated: {order.order_no}")
            return redirect("orders:order_detail", pk=order.pk)

        messages.error(request, "Please fix the errors below.")

    else:
        form = OrderForm(instance=order)
        items_formset = OrderItemFormSet(instance=order)
        pay_formset = PaymentFormSet(instance=order)

    return render(request, "orders/order_update.html", {
        "order": order,
        "form": form,
        "items_formset": items_formset,
        "pay_formset": pay_formset,
    })


# =====================================================
# ✅ DELETE ORDER
# =====================================================
@login_required
@transaction.atomic
def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)

    if request.method == "POST":
        order_no = order.order_no
        order.delete()
        messages.success(request, f"Order deleted: {order_no}")
        return redirect("orders:order_list")

    return render(request, "orders/order_delete.html", {"order": order})
