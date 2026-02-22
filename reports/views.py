# reports/views.py
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import (
    Sum, Count, Avg, F, DecimalField, ExpressionWrapper, Q,
)
from django.db.models.functions import Coalesce, TruncDate
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from orders.models import Order, OrderItem
from catalog.models import Product, Category
from expenses.models import (
    UtilityBill, RawMaterialPurchase, StaffSalaryPayment, OtherExpense,
)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _parse_dates(request):
    """Return (from_date, to_date) from GET params with sensible defaults."""
    from_str = request.GET.get("from_date", "").strip()
    to_str = request.GET.get("to_date", "").strip()

    today = timezone.localdate()
    from_date = date.fromisoformat(from_str) if from_str else today.replace(day=1)
    to_date = date.fromisoformat(to_str) if to_str else today

    return from_date, to_date


RAW_TOTAL_EXPR = ExpressionWrapper(
    F("quantity") * F("unit_price"),
    output_field=DecimalField(max_digits=12, decimal_places=2),
)


def _get_expenses(from_date, to_date):
    """Return dict of expense category totals and grand total."""
    utility = UtilityBill.objects.filter(
        bill_date__range=(from_date, to_date)
    ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

    raw = RawMaterialPurchase.objects.filter(
        purchase_date__range=(from_date, to_date)
    ).annotate(t=RAW_TOTAL_EXPR).aggregate(
        total=Coalesce(Sum("t"), Decimal("0.00"))
    )["total"]

    salary = StaffSalaryPayment.objects.filter(
        pay_date__range=(from_date, to_date)
    ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

    other = OtherExpense.objects.filter(
        expense_date__range=(from_date, to_date)
    ).aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]

    return {
        "utility": utility,
        "raw_material": raw,
        "salary": salary,
        "other": other,
        "total": utility + raw + salary + other,
    }


# ─────────────────────────────────────────────
# PROFIT & LOSS REPORT
# ─────────────────────────────────────────────
@login_required
def profit_loss_report(request):
    from_date, to_date = _parse_dates(request)

    # ── Revenue ──
    orders_qs = Order.objects.filter(
        created_at__date__range=(from_date, to_date),
    ).exclude(status=Order.Status.CANCELLED)

    agg = orders_qs.aggregate(
        revenue=Coalesce(Sum("grand_total"), Decimal("0.00")),
        cogs=Coalesce(Sum("total_cost"), Decimal("0.00")),
        gross_profit=Coalesce(Sum("gross_profit"), Decimal("0.00")),
        discount=Coalesce(Sum("discount_amount"), Decimal("0.00")),
        total_paid=Coalesce(Sum("paid_total"), Decimal("0.00")),
        total_due=Coalesce(Sum("due_total"), Decimal("0.00")),
        order_count=Count("id"),
    )

    revenue = agg["revenue"]
    cogs = agg["cogs"]
    gross_profit = agg["gross_profit"]
    discount = agg["discount"]
    total_paid = agg["total_paid"]
    total_due = agg["total_due"]
    order_count = agg["order_count"]

    # ── Expenses ──
    expenses = _get_expenses(from_date, to_date)
    operating_expenses = expenses["total"]

    # ── Net Profit ──
    net_profit = gross_profit - operating_expenses

    # ── Margins ──
    gross_margin = (
        (gross_profit / revenue * Decimal("100")).quantize(Decimal("0.01"))
        if revenue > 0 else Decimal("0.00")
    )
    net_margin = (
        (net_profit / revenue * Decimal("100")).quantize(Decimal("0.01"))
        if revenue > 0 else Decimal("0.00")
    )

    # ── Previous period comparison ──
    period_days = (to_date - from_date).days + 1
    prev_from = from_date - timedelta(days=period_days)
    prev_to = from_date - timedelta(days=1)

    prev_orders = Order.objects.filter(
        created_at__date__range=(prev_from, prev_to),
    ).exclude(status=Order.Status.CANCELLED)

    prev_revenue = prev_orders.aggregate(
        total=Coalesce(Sum("grand_total"), Decimal("0.00"))
    )["total"]

    prev_expenses = _get_expenses(prev_from, prev_to)
    prev_gross = prev_orders.aggregate(
        total=Coalesce(Sum("gross_profit"), Decimal("0.00"))
    )["total"]
    prev_net = prev_gross - prev_expenses["total"]

    def _pct_change(current, previous):
        if previous > 0:
            return ((current - previous) / previous * Decimal("100")).quantize(Decimal("0.1"))
        return None

    context = {
        "from_date": from_date,
        "to_date": to_date,

        # Revenue
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "gross_margin": gross_margin,
        "discount": discount,
        "total_paid": total_paid,
        "total_due": total_due,
        "order_count": order_count,

        # Expenses
        "expenses": expenses,
        "operating_expenses": operating_expenses,

        # Net
        "net_profit": net_profit,
        "net_margin": net_margin,

        # Trend
        "revenue_change": _pct_change(revenue, prev_revenue),
        "profit_change": _pct_change(net_profit, prev_net),
        "prev_revenue": prev_revenue,
        "prev_net_profit": prev_net,
    }
    return render(request, "reports/profit_loss.html", context)


# ─────────────────────────────────────────────
# SALES REPORT
# ─────────────────────────────────────────────
@login_required
def sales_report(request):
    from_date, to_date = _parse_dates(request)

    orders_qs = Order.objects.filter(
        created_at__date__range=(from_date, to_date),
    ).exclude(status=Order.Status.CANCELLED)

    # Stats
    agg = orders_qs.aggregate(
        total_revenue=Coalesce(Sum("grand_total"), Decimal("0.00")),
        total_orders=Count("id"),
        avg_order=Coalesce(Avg("grand_total"), Decimal("0.00")),
        total_paid=Coalesce(Sum("paid_total"), Decimal("0.00")),
        total_due=Coalesce(Sum("due_total"), Decimal("0.00")),
    )

    # Daily breakdown
    daily = (
        orders_qs
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            revenue=Coalesce(Sum("grand_total"), Decimal("0.00")),
            orders=Count("id"),
            profit=Coalesce(Sum("gross_profit"), Decimal("0.00")),
        )
        .order_by("day")
    )

    # By source
    by_source = (
        orders_qs
        .values("source")
        .annotate(
            revenue=Coalesce(Sum("grand_total"), Decimal("0.00")),
            orders=Count("id"),
        )
        .order_by("-revenue")
    )

    # By status
    all_orders_qs = Order.objects.filter(
        created_at__date__range=(from_date, to_date),
    )
    by_status = (
        all_orders_qs
        .values("status")
        .annotate(
            count=Count("id"),
            revenue=Coalesce(Sum("grand_total"), Decimal("0.00")),
        )
        .order_by("-count")
    )

    context = {
        "from_date": from_date,
        "to_date": to_date,
        **agg,
        "daily": list(daily),
        "by_source": list(by_source),
        "by_status": list(by_status),
    }
    return render(request, "reports/sales.html", context)


# ─────────────────────────────────────────────
# EXPENSE REPORT
# ─────────────────────────────────────────────
@login_required
def expense_report(request):
    from_date, to_date = _parse_dates(request)
    expenses = _get_expenses(from_date, to_date)

    # Monthly trend (last 6 months)
    import calendar
    today = timezone.localdate()
    monthly_data = []
    for i in range(5, -1, -1):
        m_start = (today.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        _, last_day = calendar.monthrange(m_start.year, m_start.month)
        m_end = m_start.replace(day=last_day)
        m_exp = _get_expenses(m_start, m_end)
        monthly_data.append({
            "month": m_start.strftime("%b %Y"),
            "total": m_exp["total"],
            "utility": m_exp["utility"],
            "raw_material": m_exp["raw_material"],
            "salary": m_exp["salary"],
            "other": m_exp["other"],
        })

    context = {
        "from_date": from_date,
        "to_date": to_date,
        "expenses": expenses,
        "monthly_data": monthly_data,
    }
    return render(request, "reports/expenses.html", context)


# ─────────────────────────────────────────────
# PRODUCT PERFORMANCE
# ─────────────────────────────────────────────
@login_required
def product_performance(request):
    from_date, to_date = _parse_dates(request)

    items_qs = OrderItem.objects.filter(
        order__created_at__date__range=(from_date, to_date),
        order__status__in=[Order.Status.COMPLETED, Order.Status.PENDING],
    )

    # Top products by revenue
    top_products = (
        items_qs
        .values("product__name", "product__category__name")
        .annotate(
            total_qty=Sum("qty"),
            total_revenue=Coalesce(Sum("line_total"), Decimal("0.00")),
            total_cost=Coalesce(Sum("line_cost"), Decimal("0.00")),
            total_profit=Coalesce(Sum("line_profit"), Decimal("0.00")),
        )
        .order_by("-total_revenue")[:20]
    )

    # By category
    by_category = (
        items_qs
        .values("product__category__name")
        .annotate(
            total_qty=Sum("qty"),
            total_revenue=Coalesce(Sum("line_total"), Decimal("0.00")),
            total_profit=Coalesce(Sum("line_profit"), Decimal("0.00")),
        )
        .order_by("-total_revenue")
    )

    # Overall stats
    overall = items_qs.aggregate(
        total_items=Coalesce(Sum("qty"), 0),
        total_revenue=Coalesce(Sum("line_total"), Decimal("0.00")),
        total_profit=Coalesce(Sum("line_profit"), Decimal("0.00")),
        total_cost=Coalesce(Sum("line_cost"), Decimal("0.00")),
    )

    context = {
        "from_date": from_date,
        "to_date": to_date,
        "top_products": list(top_products),
        "by_category": list(by_category),
        **overall,
    }
    return render(request, "reports/products.html", context)


# ─────────────────────────────────────────────
# API ENDPOINTS (for Chart.js)
# ─────────────────────────────────────────────
@login_required
def api_daily_revenue(request):
    from_date, to_date = _parse_dates(request)

    daily = (
        Order.objects
        .filter(
            created_at__date__range=(from_date, to_date),
        )
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

    return JsonResponse({
        "labels": [d["day"].strftime("%d %b") for d in daily],
        "revenue": [str(d["revenue"]) for d in daily],
        "profit": [str(d["profit"]) for d in daily],
        "orders": [d["orders"] for d in daily],
    })


@login_required
def api_expense_breakdown(request):
    from_date, to_date = _parse_dates(request)
    expenses = _get_expenses(from_date, to_date)

    return JsonResponse({
        "labels": ["Utility", "Raw Material", "Salary", "Other"],
        "values": [
            str(expenses["utility"]),
            str(expenses["raw_material"]),
            str(expenses["salary"]),
            str(expenses["other"]),
        ],
    })


@login_required
def api_daily_profit(request):
    from_date, to_date = _parse_dates(request)

    daily = (
        Order.objects
        .filter(created_at__date__range=(from_date, to_date))
        .exclude(status=Order.Status.CANCELLED)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            revenue=Coalesce(Sum("grand_total"), Decimal("0.00")),
            cogs=Coalesce(Sum("total_cost"), Decimal("0.00")),
            gross_profit=Coalesce(Sum("gross_profit"), Decimal("0.00")),
        )
        .order_by("day")
    )

    return JsonResponse({
        "labels": [d["day"].strftime("%d %b") for d in daily],
        "revenue": [str(d["revenue"]) for d in daily],
        "cogs": [str(d["cogs"]) for d in daily],
        "gross_profit": [str(d["gross_profit"]) for d in daily],
    })
