from datetime import date

from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from staff.models import Staff
from .models import UtilityBill, RawMaterialPurchase, StaffSalaryPayment, OtherExpense
from .forms import UtilityBillForm, RawMaterialPurchaseForm, StaffSalaryPaymentForm, OtherExpenseForm


def expense_dashboard(request):
    from_str = request.GET.get("from_date")
    to_str = request.GET.get("to_date")

    from_date = date.fromisoformat(from_str) if from_str else None
    to_date = date.fromisoformat(to_str) if to_str else None

    def filter_range(qs, field):
        if from_date and to_date:
            return qs.filter(**{f"{field}__range": (from_date, to_date)})
        if from_date:
            return qs.filter(**{f"{field}__gte": from_date})
        if to_date:
            return qs.filter(**{f"{field}__lte": to_date})
        return qs

    utility_qs = filter_range(
        UtilityBill.objects.select_related("utility_type"),
        "bill_date"
    )
    raw_qs = filter_range(
        RawMaterialPurchase.objects.select_related("material", "unit"),
        "purchase_date"
    )
    salary_qs = filter_range(
        StaffSalaryPayment.objects.select_related("staff"),
        "pay_date"
    )
    other_qs = filter_range(
        OtherExpense.objects.all(),
        "expense_date"
    )

    raw_total_expr = ExpressionWrapper(
        F("quantity") * F("unit_price"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    utility_total = utility_qs.aggregate(s=Sum("amount"))["s"] or 0
    raw_total = raw_qs.annotate(t=raw_total_expr).aggregate(s=Sum("t"))["s"] or 0
    salary_total = salary_qs.aggregate(s=Sum("amount"))["s"] or 0
    other_total = other_qs.aggregate(s=Sum("amount"))["s"] or 0

    grand_total = utility_total + raw_total + salary_total + other_total

    # ✅ Combined list for dashboard table (WITH edit/delete info)
    expense_rows = []

    for x in utility_qs:
        expense_rows.append({
            "type": "Utility",
            "title": str(x.utility_type),
            "amount": x.amount,
            "date": x.bill_date,
            "note": x.note,
            "pk": x.pk,
            "edit_url": "expenses:utility_edit",
            "delete_url": "expenses:utility_delete",
        })

    for x in raw_qs:
        expense_rows.append({
            "type": "Raw",
            "title": f"{x.material} ({x.quantity} {x.unit})",
            "amount": x.total,
            "date": x.purchase_date,
            "note": x.note,
            "pk": x.pk,
            "edit_url": "expenses:raw_edit",
            "delete_url": "expenses:raw_delete",
        })

    for x in salary_qs:
        expense_rows.append({
            "type": "Salary",
            "title": str(x.staff),
            "amount": x.amount,
            "date": x.pay_date,
            "note": x.note,
            "pk": x.pk,
            "edit_url": "expenses:salary_edit",
            "delete_url": "expenses:salary_delete",
        })

    for x in other_qs:
        expense_rows.append({
            "type": "Other",
            "title": x.title,
            "amount": x.amount,
            "date": x.expense_date,
            "note": x.note,
            "pk": x.pk,
            "edit_url": "expenses:other_edit",
            "delete_url": "expenses:other_delete",
        })

    expense_rows.sort(key=lambda r: r["date"], reverse=True)

    return render(request, "expenses/dashboard.html", {
        "utility_total": utility_total,
        "raw_total": raw_total,
        "salary_total": salary_total,
        "other_total": other_total,
        "grand_total": grand_total,

        "from_date": from_date,
        "to_date": to_date,

        "expense_rows": expense_rows,
    })


# -------------------- Utility Bill --------------------

class UtilityBillListView(ListView):
    model = UtilityBill
    template_name = "expenses/utility_list.html"
    context_object_name = "items"
    paginate_by = 10
    ordering = ["-bill_date", "-id"]


class UtilityBillCreateView(CreateView):
    model = UtilityBill
    form_class = UtilityBillForm
    template_name = "expenses/form.html"
    success_url = reverse_lazy("expenses:utility_list")
    extra_context = {"page_title": "Add Utility Bill"}


class UtilityBillUpdateView(UpdateView):
    model = UtilityBill
    form_class = UtilityBillForm
    template_name = "expenses/form.html"
    success_url = reverse_lazy("expenses:utility_list")
    extra_context = {"page_title": "Edit Utility Bill"}


class UtilityBillDeleteView(DeleteView):
    model = UtilityBill
    template_name = "expenses/confirm_delete.html"
    success_url = reverse_lazy("expenses:utility_list")
    extra_context = {"page_title": "Delete Utility Bill"}


# -------------------- Raw Material Purchase --------------------

class RawPurchaseListView(ListView):
    model = RawMaterialPurchase
    template_name = "expenses/raw_list.html"
    context_object_name = "items"
    paginate_by = 10
    ordering = ["-purchase_date", "-id"]


class RawPurchaseCreateView(CreateView):
    model = RawMaterialPurchase
    form_class = RawMaterialPurchaseForm
    template_name = "expenses/form.html"
    success_url = reverse_lazy("expenses:raw_list")
    extra_context = {"page_title": "Add Raw Material Purchase"}


class RawPurchaseUpdateView(UpdateView):
    model = RawMaterialPurchase
    form_class = RawMaterialPurchaseForm
    template_name = "expenses/form.html"
    success_url = reverse_lazy("expenses:raw_list")
    extra_context = {"page_title": "Edit Raw Material Purchase"}


class RawPurchaseDeleteView(DeleteView):
    model = RawMaterialPurchase
    template_name = "expenses/confirm_delete.html"
    success_url = reverse_lazy("expenses:raw_list")
    extra_context = {"page_title": "Delete Raw Material Purchase"}


# -------------------- Staff Salary Payment --------------------

class SalaryPaymentListView(ListView):
    model = StaffSalaryPayment
    template_name = "expenses/salary_list.html"
    context_object_name = "items"
    paginate_by = 10
    ordering = ["-pay_date", "-id"]


class SalaryPaymentCreateView(CreateView):
    model = StaffSalaryPayment
    form_class = StaffSalaryPaymentForm
    template_name = "expenses/form.html"
    success_url = reverse_lazy("expenses:salary_list")
    extra_context = {"page_title": "Add Staff Salary Payment"}


class SalaryPaymentUpdateView(UpdateView):
    model = StaffSalaryPayment
    form_class = StaffSalaryPaymentForm
    template_name = "expenses/form.html"
    success_url = reverse_lazy("expenses:salary_list")
    extra_context = {"page_title": "Edit Staff Salary Payment"}


class SalaryPaymentDeleteView(DeleteView):
    model = StaffSalaryPayment
    template_name = "expenses/confirm_delete.html"
    success_url = reverse_lazy("expenses:salary_list")
    extra_context = {"page_title": "Delete Staff Salary Payment"}


# -------------------- Other Expense --------------------

class OtherExpenseListView(ListView):
    model = OtherExpense
    template_name = "expenses/other_list.html"
    context_object_name = "items"
    paginate_by = 10
    ordering = ["-expense_date", "-id"]


class OtherExpenseCreateView(CreateView):
    model = OtherExpense
    form_class = OtherExpenseForm
    template_name = "expenses/form.html"
    success_url = reverse_lazy("expenses:other_list")
    extra_context = {"page_title": "Add Other Expense"}


class OtherExpenseUpdateView(UpdateView):
    model = OtherExpense
    form_class = OtherExpenseForm
    template_name = "expenses/form.html"
    success_url = reverse_lazy("expenses:other_list")
    extra_context = {"page_title": "Edit Other Expense"}


class OtherExpenseDeleteView(DeleteView):
    model = OtherExpense
    template_name = "expenses/confirm_delete.html"
    success_url = reverse_lazy("expenses:other_list")
    extra_context = {"page_title": "Delete Other Expense"}


# -------------------- API: Staff Salary Auto Fill --------------------

@require_GET
def staff_salary_api(request):
    staff_id = request.GET.get("staff_id")
    if not staff_id:
        return JsonResponse({"error": "staff_id is required"}, status=400)

    try:
        s = Staff.objects.get(pk=staff_id)
    except Staff.DoesNotExist:
        return JsonResponse({"error": "Staff not found"}, status=404)

    return JsonResponse({"salary": str(s.monthly_salary)})
