from decimal import Decimal

from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F, Count, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce, TruncDate
from django.shortcuts import render, redirect
from django.utils import timezone
from django.urls import reverse
from datetime import timedelta

from orders.models import Order, Payment
from catalog.models import Product
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
    week_start = today - timedelta(days=today.weekday())  # Monday

    raw_total_expr = ExpressionWrapper(
        F("quantity") * F("unit_price"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    def _get_expenses_total(from_d, to_d):
        utility = UtilityBill.objects.filter(bill_date__range=(from_d, to_d)).aggregate(
            total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
        raw = RawMaterialPurchase.objects.filter(purchase_date__range=(from_d, to_d)).annotate(
            t=raw_total_expr).aggregate(total=Coalesce(Sum("t"), Decimal("0.00")))["total"]
        salary = StaffSalaryPayment.objects.filter(pay_date__range=(from_d, to_d)).aggregate(
            total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
        other = OtherExpense.objects.filter(expense_date__range=(from_d, to_d)).aggregate(
            total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
        return {"utility": utility, "raw": raw, "salary": salary, "other": other,
                "total": utility + raw + salary + other}

    # ── Today ──
    today_orders_qs = Order.objects.filter(created_at__date=today).exclude(status=Order.Status.CANCELLED)
    today_agg = today_orders_qs.aggregate(
        revenue=Coalesce(Sum("grand_total"), Decimal("0.00")),
        cogs=Coalesce(Sum("total_cost"), Decimal("0.00")),
        gross_profit=Coalesce(Sum("gross_profit"), Decimal("0.00")),
        paid=Coalesce(Sum("paid_total"), Decimal("0.00")),
        due=Coalesce(Sum("due_total"), Decimal("0.00")),
        count=Count("id"),
    )
    today_expense = _get_expenses_total(today, today)
    today_net_profit = today_agg["gross_profit"] - today_expense["total"]

    # ── This Week ──
    week_orders_qs = Order.objects.filter(created_at__date__range=(week_start, today)).exclude(status=Order.Status.CANCELLED)
    week_agg = week_orders_qs.aggregate(
        revenue=Coalesce(Sum("grand_total"), Decimal("0.00")),
        gross_profit=Coalesce(Sum("gross_profit"), Decimal("0.00")),
        count=Count("id"),
    )
    week_expense = _get_expenses_total(week_start, today)
    week_net_profit = week_agg["gross_profit"] - week_expense["total"]

    # ── This Month ──
    month_orders_qs = Order.objects.filter(created_at__date__range=(month_start, today)).exclude(status=Order.Status.CANCELLED)
    month_agg = month_orders_qs.aggregate(
        revenue=Coalesce(Sum("grand_total"), Decimal("0.00")),
        cogs=Coalesce(Sum("total_cost"), Decimal("0.00")),
        gross_profit=Coalesce(Sum("gross_profit"), Decimal("0.00")),
        paid=Coalesce(Sum("paid_total"), Decimal("0.00")),
        due=Coalesce(Sum("due_total"), Decimal("0.00")),
        count=Count("id"),
    )
    month_expense = _get_expenses_total(month_start, today)
    month_net_profit = month_agg["gross_profit"] - month_expense["total"]

    # ── 7-day trend data ──
    seven_days_ago = today - timedelta(days=6)
    daily_trend = (
        Order.objects
        .filter(created_at__date__range=(seven_days_ago, today))
        .exclude(status=Order.Status.CANCELLED)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            revenue=Coalesce(Sum("grand_total"), Decimal("0.00")),
            profit=Coalesce(Sum("gross_profit"), Decimal("0.00")),
            orders=Count("id"),
        )
        .order_by("day")
    )
    trend_labels = [d["day"].strftime("%d %b") for d in daily_trend]
    trend_revenue = [str(d["revenue"]) for d in daily_trend]
    trend_profit = [str(d["profit"]) for d in daily_trend]

    # ── Top selling products this month ──
    from orders.models import OrderItem
    top_products = (
        OrderItem.objects
        .filter(
            order__created_at__date__range=(month_start, today),
            order__status__in=[Order.Status.COMPLETED, Order.Status.PENDING],
        )
        .values("product__name")
        .annotate(
            total_qty=Sum("qty"),
            total_revenue=Coalesce(Sum("line_total"), Decimal("0.00")),
            total_profit=Coalesce(Sum("line_profit"), Decimal("0.00")),
        )
        .order_by("-total_revenue")[:5]
    )

    # ── Recent Activity ──
    recent_orders = Order.objects.order_by("-created_at")[:5]

    # ── Recent Expenses ──
    expense_rows = []
    for x in UtilityBill.objects.select_related("utility_type").order_by("-bill_date", "-id")[:3]:
        expense_rows.append({"date": x.bill_date, "category": "Utility", "amount": x.amount,
            "edit_url": reverse("expenses:utility_edit", args=[x.pk]),
            "delete_url": reverse("expenses:utility_delete", args=[x.pk])})
    for x in RawMaterialPurchase.objects.select_related("material", "unit").order_by("-purchase_date", "-id")[:3]:
        expense_rows.append({"date": x.purchase_date, "category": "Raw", "amount": (x.quantity or 0) * (x.unit_price or 0),
            "edit_url": reverse("expenses:raw_edit", args=[x.pk]),
            "delete_url": reverse("expenses:raw_delete", args=[x.pk])})
    for x in StaffSalaryPayment.objects.select_related("staff").order_by("-pay_date", "-id")[:3]:
        expense_rows.append({"date": x.pay_date, "category": "Salary", "amount": x.amount or Decimal("0.00"),
            "edit_url": reverse("expenses:salary_edit", args=[x.pk]),
            "delete_url": reverse("expenses:salary_delete", args=[x.pk])})
    for x in OtherExpense.objects.order_by("-expense_date", "-id")[:3]:
        expense_rows.append({"date": x.expense_date, "category": "Other", "amount": x.amount,
            "edit_url": reverse("expenses:other_edit", args=[x.pk]),
            "delete_url": reverse("expenses:other_delete", args=[x.pk])})
    expense_rows = sorted([r for r in expense_rows if r["date"]], key=lambda r: r["date"], reverse=True)[:5]

    # ── Profit margin ──
    month_gross_margin = (
        (month_agg["gross_profit"] / month_agg["revenue"] * 100).quantize(Decimal("0.1"))
        if month_agg["revenue"] > 0 else Decimal("0.0")
    )
    month_net_margin = (
        (month_net_profit / month_agg["revenue"] * 100).quantize(Decimal("0.1"))
        if month_agg["revenue"] > 0 else Decimal("0.0")
    )

    context = {
        "server_now": now,

        # Today
        "today_revenue": today_agg["revenue"],
        "today_orders": today_agg["count"],
        "today_cogs": today_agg["cogs"],
        "today_gross_profit": today_agg["gross_profit"],
        "today_expense": today_expense["total"],
        "today_net_profit": today_net_profit,
        "today_paid": today_agg["paid"],
        "today_due": today_agg["due"],

        # Week
        "week_revenue": week_agg["revenue"],
        "week_orders": week_agg["count"],
        "week_expense": week_expense["total"],
        "week_net_profit": week_net_profit,

        # Month
        "month_revenue": month_agg["revenue"],
        "month_orders": month_agg["count"],
        "month_cogs": month_agg["cogs"],
        "month_gross_profit": month_agg["gross_profit"],
        "month_expense": month_expense,
        "month_expense_total": month_expense["total"],
        "month_net_profit": month_net_profit,
        "month_paid": month_agg["paid"],
        "month_due": month_agg["due"],
        "month_gross_margin": month_gross_margin,
        "month_net_margin": month_net_margin,

        # Trend
        "trend_labels": trend_labels,
        "trend_revenue": trend_revenue,
        "trend_profit": trend_profit,

        # Top Products
        "top_products": list(top_products),

        # Recent
        "recent_orders": recent_orders,
        "recent_expenses": expense_rows,
    }
    return render(request, "accounts/home.html", context)


@login_required
def server_clock(request):
    now = timezone.localtime()
    return JsonResponse({
        "date": now.strftime("%d %b %Y"),
        "time": now.strftime("%I:%M:%S %p"),
    })
