from django import forms
from .models import Staff, StaffRole


class StaffForm(forms.ModelForm):
    class Meta:
        model = Staff
        fields = ["name", "phone", "role", "monthly_salary", "is_active", "joined_at"]
        widgets = {
            "joined_at": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base = (
            "w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-white "
            "focus:outline-none focus:ring-2 focus:ring-orange-200 focus:border-orange-300"
        )
        for f in self.fields.values():
            f.widget.attrs["class"] = base


class StaffRoleForm(forms.ModelForm):
    class Meta:
        model = StaffRole
        fields = ["name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs["class"] = (
            "w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-white "
            "focus:outline-none focus:ring-2 focus:ring-orange-200 focus:border-orange-300"
        )
