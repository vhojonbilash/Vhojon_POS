# reports/urls.py
from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    # ── Profit & Loss ────────────────────────────
    path("profit-loss/", views.profit_loss_report, name="profit_loss"),

    # ── Sales Report ─────────────────────────────
    path("sales/", views.sales_report, name="sales"),

    # ── Expense Breakdown ────────────────────────
    path("expenses/", views.expense_report, name="expenses"),

    # ── Product Performance ──────────────────────
    path("products/", views.product_performance, name="products"),

    # ── AJAX data endpoints for charts ───────────
    path("api/daily-revenue/", views.api_daily_revenue, name="api_daily_revenue"),
    path("api/expense-breakdown/", views.api_expense_breakdown, name="api_expense_breakdown"),
    path("api/daily-profit/", views.api_daily_profit, name="api_daily_profit"),
]
