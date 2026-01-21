from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q, Sum
from .models import Staff, StaffRole
from .forms import StaffForm, StaffRoleForm


# -------------------------
# Staff CRUD (FBV)
# -------------------------
def staff_list(request):
    qs = Staff.objects.select_related("role").order_by("-id")

    q = request.GET.get("q", "").strip()
    active = request.GET.get("active", "").strip()  # "1" or "0"

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(phone__icontains=q) |
            Q(role__name__icontains=q)
        )

    if active in ["1", "0"]:
        qs = qs.filter(is_active=(active == "1"))

    # ✅ real totals (not affected by pagination/filter)
    base_qs = Staff.objects.all()
    total_staff = base_qs.count()
    active_staff = base_qs.filter(is_active=True).count()
    inactive_staff = base_qs.filter(is_active=False).count()
    total_salary = base_qs.filter(is_active=True).aggregate(
        total=Sum("monthly_salary")
    )["total"] or 0

    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "staff_list": page_obj.object_list,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "paginator": paginator,
        "q": q,
        "active": active,

        # ✅ for cards
        "total_staff": total_staff,
        "active_staff": active_staff,
        "inactive_staff": inactive_staff,
        "total_salary": total_salary,
    }
    return render(request, "staff/staff_list.html", context)


def staff_create(request):
    if request.method == "POST":
        form = StaffForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Staff created successfully.")
            return redirect("staff:staff_list")
    else:
        form = StaffForm()

    return render(request, "staff/staff_form.html", {"form": form})


def staff_detail(request, pk):
    staff = get_object_or_404(Staff.objects.select_related("role"), pk=pk)
    return render(request, "staff/staff_detail.html", {"staff": staff})


def staff_update(request, pk):
    staff = get_object_or_404(Staff, pk=pk)

    if request.method == "POST":
        form = StaffForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Staff updated successfully.")
            return redirect("staff:staff_list")
    else:
        form = StaffForm(instance=staff)

    return render(request, "staff/staff_form.html", {"form": form, "object": staff})


def staff_delete(request, pk):
    staff = get_object_or_404(Staff, pk=pk)

    if request.method == "POST":
        staff.delete()
        messages.success(request, "🗑️ Staff deleted successfully.")
        return redirect("staff:staff_list")

    return render(request, "staff/staff_confirm_delete.html", {"object": staff})


# -------------------------
# StaffRole CRUD (FBV)
# -------------------------
def role_list(request):
    qs = StaffRole.objects.order_by("name")

    paginator = Paginator(qs, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "roles": page_obj.object_list,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "paginator": paginator,
    }
    return render(request, "staff/role_list.html", context)


def role_create(request):
    if request.method == "POST":
        form = StaffRoleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Role created successfully.")
            return redirect("staff:role_list")
    else:
        form = StaffRoleForm()

    return render(request, "staff/role_form.html", {"form": form})


def role_update(request, pk):
    role = get_object_or_404(StaffRole, pk=pk)

    if request.method == "POST":
        form = StaffRoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Role updated successfully.")
            return redirect("staff:role_list")
    else:
        form = StaffRoleForm(instance=role)

    return render(request, "staff/role_form.html", {"form": form, "object": role})


def role_delete(request, pk):
    role = get_object_or_404(StaffRole, pk=pk)

    if request.method == "POST":
        role.delete()
        messages.success(request, "🗑️ Role deleted successfully.")
        return redirect("staff:role_list")

    return render(request, "staff/role_confirm_delete.html", {"object": role})
