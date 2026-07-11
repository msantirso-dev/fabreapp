from django import forms
from django.contrib.auth import get_user_model

from apps.clients.cuit_lookup import format_cuit, is_valid_cuit
from apps.clients.models import Client
from apps.deadlines.models import Deadline, DeadlineStatus

User = get_user_model()


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ("name", "cuit", "is_active")
        labels = {
            "name": "Razón social",
            "cuit": "CUIT",
            "is_active": "Activo",
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "EMPRESA EJEMPLO S.A.", "autocomplete": "organization"}),
            "cuit": forms.TextInput(
                attrs={
                    "placeholder": "30-12345678-9",
                    "inputmode": "numeric",
                    "autocomplete": "off",
                }
            ),
        }

    def clean_cuit(self):
        cuit = self.cleaned_data["cuit"]
        if not is_valid_cuit(cuit):
            raise forms.ValidationError("CUIT inválido. Revisá los 11 dígitos.")
        return format_cuit(cuit)


class DeadlineForm(forms.ModelForm):
    class Meta:
        model = Deadline
        fields = (
            "client",
            "obligation_code",
            "obligation_name",
            "period",
            "due_date",
            "status",
            "assigned_to",
            "observations",
        )
        labels = {
            "client": "Cliente",
            "obligation_code": "Código de obligación",
            "obligation_name": "Obligación",
            "period": "Período fiscal (MM/YYYY)",
            "due_date": "Fecha de vencimiento",
            "status": "Estado",
            "assigned_to": "Responsable",
            "observations": "Observaciones",
        }
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "period": forms.TextInput(attrs={"placeholder": "07/2026"}),
            "obligation_code": forms.TextInput(attrs={"placeholder": "IVA"}),
            "obligation_name": forms.TextInput(attrs={"placeholder": "IVA"}),
            "observations": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = Client.objects.filter(is_active=True).order_by(
            "name"
        )
        self.fields["assigned_to"].queryset = User.objects.filter(is_active=True).order_by(
            "first_name", "last_name", "username"
        )
        self.fields["assigned_to"].required = False
        self.fields["status"].choices = [
            (c.value, c.label)
            for c in DeadlineStatus
            if c
            not in {
                DeadlineStatus.COMPLETED,
            }
        ]
