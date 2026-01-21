# orders/views.py
from decimal import Decimal

from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator

from customers.models import CustomerAddress
from catalog.models import Product

from .forms import CustomerCreateOrSelectForm, OrderForm, OrderItemFormSet, PaymentFormSet
from .models import Order
from .utils import generate_order_no

# ✅ Printer helpers (USB-Windows printing if you replaced orders/pos_printer.py)
from .pos_printer import print_chef_kot, print_customer_receipt


def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


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
# ✅ CREATE ORDER
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

        if cust_form.is_valid() and form.is_valid() and items_formset.is_valid() and pay_formset.is_valid():
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

            # ✅ redirect to print options page
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
                "cust_errors": cust_form.errors,
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

    # 🔥 force show exact message
    if not ok:
        return JsonResponse({
            "ok": False,
            "error": msg
        }, status=400)

    return JsonResponse({"ok": True, "message": msg})


@login_required
def order_print_customer(request, pk):
    order = get_object_or_404(Order, pk=pk)

    ok, msg = print_customer_receipt(order)

    if not ok:
        return JsonResponse({
            "ok": False,
            "error": msg
        }, status=400)

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

    items = order.items.all()
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
# ✅ ORDER LIST
# =====================================================
@login_required
def order_list(request):
    qs = Order.objects.select_related("customer").order_by("-id")

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    source = request.GET.get("source", "").strip()
    due = request.GET.get("due", "").strip()

    if q:
        qs = qs.filter(
            Q(order_no__icontains=q) |
            Q(customer__name__icontains=q) |
            Q(customer__phone__icontains=q)
        )

    if status:
        qs = qs.filter(status=status)

    if source:
        qs = qs.filter(source=source)

    if due == "1":
        qs = qs.filter(due_total__gt=0)
    elif due == "0":
        qs = qs.filter(due_total__lte=0)

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
