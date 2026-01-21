# customers/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from .models import Customer, CustomerAddress
from .forms import CustomerForm, CustomerAddressFormSet
from decimal import Decimal

from django.db.models import Q, Sum, Value, DecimalField
from django.db.models.functions import Coalesce

from orders.models import Order


# ---------- Your existing AJAX ----------
@require_GET
def phone_suggest(request):
    q = (request.GET.get("q") or "").strip()
    if not q:
        return JsonResponse({"results": []})

    results = list(
        Customer.objects
        .filter(phone__icontains=q)
        .order_by("phone")
        .values("phone")[:10]
    )
    return JsonResponse({"results": results})


@require_GET
def customer_by_phone(request):
    phone = (request.GET.get("phone") or "").strip()
    if not phone:
        return JsonResponse({"found": False})

    try:
        c = Customer.objects.get(phone=phone)
    except Customer.DoesNotExist:
        return JsonResponse({"found": False})

    addr = (
        CustomerAddress.objects
        .filter(customer=c)
        .order_by("-is_primary", "-created_at")
        .values_list("address_line", flat=True)
        .first()
    ) or ""

    return JsonResponse({
        "found": True,
        "id": c.id,
        "name": c.name,
        "phone": c.phone,
        "address": addr,
    })


# ---------- NEW: Customer CRUD ----------



@login_required
def customer_list(request):
    q = (request.GET.get("q") or "").strip()
    due_filter = (request.GET.get("due") or "").strip()      # "" | "due" | "clear"
    min_due = (request.GET.get("min_due") or "").strip()     # numeric string
    sort = (request.GET.get("sort") or "new").strip()        # new | name | due_desc | due_asc

    qs = (
        Customer.objects
        .annotate(
            total_due_calc=Coalesce(
                Sum(
                    "orders__due_total",                           # ✅ FIXED: orders__
                    filter=~Q(orders__status=Order.Status.CANCELLED)  # ✅ FIXED: orders__
                ),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
    )

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q))

    if due_filter == "due":
        qs = qs.filter(total_due_calc__gt=0)
    elif due_filter == "clear":
        qs = qs.filter(total_due_calc__lte=0)

    if min_due:
        try:
            qs = qs.filter(total_due_calc__gte=Decimal(min_due))
        except Exception:
            pass

    if sort == "name":
        qs = qs.order_by("name")
    elif sort == "due_desc":
        qs = qs.order_by("-total_due_calc", "-id")
    elif sort == "due_asc":
        qs = qs.order_by("total_due_calc", "-id")
    else:
        qs = qs.order_by("-id")

    return render(request, "customers/customer_list.html", {
        "customers": qs,
        "q": q,
        "due": due_filter,
        "min_due": min_due,
        "sort": sort,
    })




@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    addresses = customer.addresses.all().order_by("-is_primary", "-created_at")

    recent_orders = []
    due_orders = []

    try:
        from orders.models import Order

        recent_orders = Order.objects.filter(customer=customer).order_by("-id")[:10]
        due_orders = (
            Order.objects
            .filter(customer=customer, due_total__gt=0)
            .exclude(status__iexact="cancelled")   # optional if you use cancelled
            .order_by("-id")[:20]
        )
    except Exception:
        recent_orders = []
        due_orders = []

    return render(request, "customers/customer_detail.html", {
        "customer": customer,
        "addresses": addresses,
        "recent_orders": recent_orders,
        "due_orders": due_orders,
    })


@login_required
@transaction.atomic
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":
        form = CustomerForm(request.POST, instance=customer)
        formset = CustomerAddressFormSet(request.POST, instance=customer)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()

            # Ensure only 1 primary address (optional cleanup)
            primaries = customer.addresses.filter(is_primary=True).order_by("-created_at")
            if primaries.count() > 1:
                keep = primaries.first()
                customer.addresses.exclude(pk=keep.pk).update(is_primary=False)

            messages.success(request, "Customer updated successfully.")
            return redirect("customers:customer_detail", pk=customer.pk)

        messages.error(request, "Please fix the errors below.")
    else:
        form = CustomerForm(instance=customer)
        formset = CustomerAddressFormSet(instance=customer)

    return render(request, "customers/customer_update.html", {
        "customer": customer,
        "form": form,
        "formset": formset,
    })


@login_required
@transaction.atomic
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":
        name = str(customer)
        customer.delete()
        messages.success(request, f"Customer deleted: {name}")
        return redirect("customers:customer_list")

    return render(request, "customers/customer_delete.html", {
        "customer": customer
    })
