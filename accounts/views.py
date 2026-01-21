from decimal import Decimal

from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.shortcuts import render, redirect
from django.utils import timezone
from django.urls import reverse

from orders.models import Order, Payment
from expenses.models import UtilityBill, RawMaterialPurchase, StaffSalaryPayment, OtherExpense


def admin_login(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        user = authenticate(request, username=username, password=password)
        if user is not None and (user.is_staff or user.is_superuser):
            login(request, user)
            return redirect("home")

        messages.error(request, "Invalid credentials or not an admin account.")

    return render(request, "accounts/login.html")


def admin_logout(request):
    logout(request)
    return redirect("login")


@login_required
def home(request):
    now = timezone.localtime()
    today = now.date()
    month_start = today.replace(day=1)
    

    # -----------------------------
    # Orders (show 5 recent)
    # -----------------------------
    today_orders = Order.objects.filter(created_at__date=today).count()
    recent_orders = Order.objects.order_by("-created_at")[:5]

    # -----------------------------
    # Sales (Payments)
    # ✅ your Payment model uses paid_at (not created_at)
    # -----------------------------
    today_sales = Payment.objects.filter(paid_at__date=today).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]

    month_sales = Payment.objects.filter(paid_at__date__gte=month_start).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]

    # -----------------------------
    # Expenses
    # -----------------------------
    expense_rows = []

    raw_total_expr = ExpressionWrapper(
        F("quantity") * F("unit_price"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    today_expense = Decimal("0.00")
    month_expense = Decimal("0.00")

    # ---- Utility ----
    today_expense += UtilityBill.objects.filter(bill_date=today).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]
    month_expense += UtilityBill.objects.filter(bill_date__gte=month_start).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]

    for x in UtilityBill.objects.select_related("utility_type").order_by("-bill_date", "-id")[:5]:
        expense_rows.append({
            "date": x.bill_date,
            "category": "Utility",
            "amount": x.amount,
            "edit_url": reverse("expenses:utility_edit", args=[x.pk]),
            "delete_url": reverse("expenses:utility_delete", args=[x.pk]),
        })

    # ---- Raw ----
    today_expense += RawMaterialPurchase.objects.filter(purchase_date=today).annotate(
        t=raw_total_expr
    ).aggregate(total=Coalesce(Sum("t"), Decimal("0.00")))["total"]

    month_expense += RawMaterialPurchase.objects.filter(purchase_date__gte=month_start).annotate(
        t=raw_total_expr
    ).aggregate(total=Coalesce(Sum("t"), Decimal("0.00")))["total"]

    for x in RawMaterialPurchase.objects.select_related("material", "unit").order_by("-purchase_date", "-id")[:5]:
        expense_rows.append({
            "date": x.purchase_date,
            "category": "Raw",
            "amount": (x.quantity or Decimal("0")) * (x.unit_price or Decimal("0")),
            "edit_url": reverse("expenses:raw_edit", args=[x.pk]),
            "delete_url": reverse("expenses:raw_delete", args=[x.pk]),
        })

    # ---- Salary ----
    today_expense += StaffSalaryPayment.objects.filter(pay_date=today).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]

    month_expense += StaffSalaryPayment.objects.filter(pay_date__gte=month_start).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]

    for x in StaffSalaryPayment.objects.select_related("staff").order_by("-pay_date", "-id")[:5]:
        expense_rows.append({
            "date": x.pay_date,
            "category": "Salary",
            "amount": x.amount or Decimal("0.00"),
            "edit_url": reverse("expenses:salary_edit", args=[x.pk]),
            "delete_url": reverse("expenses:salary_delete", args=[x.pk]),
        })

    # ---- Other ----
    today_expense += OtherExpense.objects.filter(expense_date=today).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]

    month_expense += OtherExpense.objects.filter(expense_date__gte=month_start).aggregate(
        total=Coalesce(Sum("amount"), Decimal("0.00"))
    )["total"]

    for x in OtherExpense.objects.order_by("-expense_date", "-id")[:5]:
        expense_rows.append({
            "date": x.expense_date,
            "category": "Other",
            "amount": x.amount,
            "edit_url": reverse("expenses:other_edit", args=[x.pk]),
            "delete_url": reverse("expenses:other_delete", args=[x.pk]),
        })

    # ✅ top 5 expenses overall
    expense_rows = [r for r in expense_rows if r["date"] is not None]
    expense_rows.sort(key=lambda r: r["date"], reverse=True)
    recent_expenses = expense_rows[:5]

    # -----------------------------
    # Profit
    # -----------------------------
    today_profit = today_sales - today_expense
    month_profit = month_sales - month_expense

    context = {
        "today_sales": today_sales,
        "today_orders": today_orders,
        "recent_orders": recent_orders,

        "today_expense": today_expense,
        "today_profit": today_profit,

        "month_sales": month_sales,
        "month_expense": month_expense,
        "month_profit": month_profit,

        "recent_expenses": recent_expenses,
        "server_now": now,
    }
    return render(request, "accounts/home.html", context)


@login_required
def server_clock(request):
    now = timezone.localtime()
    return JsonResponse({
        "date": now.strftime("%d %b %Y"),
        "time": now.strftime("%I:%M:%S %p"),
    })
