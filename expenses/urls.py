from django.urls import path
from . import views

app_name = "expenses"

urlpatterns = [
    # Dashboard
    path("", views.expense_dashboard, name="dashboard"),

    # ---------------- Utility ----------------
    path("utility/", views.UtilityBillListView.as_view(), name="utility_list"),
    path("utility/create/", views.UtilityBillCreateView.as_view(), name="utility_create"),
    path("utility/<int:pk>/edit/", views.UtilityBillUpdateView.as_view(), name="utility_edit"),
    path("utility/<int:pk>/delete/", views.UtilityBillDeleteView.as_view(), name="utility_delete"),

    # ---------------- Raw Material ----------------
    path("raw/", views.RawPurchaseListView.as_view(), name="raw_list"),
    path("raw/create/", views.RawPurchaseCreateView.as_view(), name="raw_create"),
    path("raw/<int:pk>/edit/", views.RawPurchaseUpdateView.as_view(), name="raw_edit"),
    path("raw/<int:pk>/delete/", views.RawPurchaseDeleteView.as_view(), name="raw_delete"),

    # ---------------- Staff Salary ----------------
    path("salary/", views.SalaryPaymentListView.as_view(), name="salary_list"),
    path("salary/create/", views.SalaryPaymentCreateView.as_view(), name="salary_create"),
    path("salary/<int:pk>/edit/", views.SalaryPaymentUpdateView.as_view(), name="salary_edit"),
    path("salary/<int:pk>/delete/", views.SalaryPaymentDeleteView.as_view(), name="salary_delete"),

    # ---------------- Other Expense ----------------
    path("other/", views.OtherExpenseListView.as_view(), name="other_list"),
    path("other/create/", views.OtherExpenseCreateView.as_view(), name="other_create"),
    path("other/<int:pk>/edit/", views.OtherExpenseUpdateView.as_view(), name="other_edit"),
    path("other/<int:pk>/delete/", views.OtherExpenseDeleteView.as_view(), name="other_delete"),

    # API
    path("api/staff-salary/", views.staff_salary_api, name="staff_salary_api"),
]
