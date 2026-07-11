from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.calendar_sync.services import try_sync_deadline
from apps.clients.models import Client
from apps.deadlines.forms import ClientForm, DeadlineForm
from apps.deadlines.models import Deadline, DeadlineStatus, GoogleSyncStatus
from apps.deadlines.permissions import CanCompleteDeadline
from apps.deadlines.services import complete_deadline, get_client_ip, write_audit


class DeadlineListView(LoginRequiredMixin, ListView):
    model = Deadline
    template_name = "deadlines/list.html"
    context_object_name = "deadlines"
    paginate_by = 50

    def get_queryset(self):
        return Deadline.objects.select_related("client", "assigned_to").order_by(
            "due_date"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["client_count"] = Client.objects.filter(is_active=True).count()
        return ctx


class DeadlineDetailView(LoginRequiredMixin, DetailView):
    model = Deadline
    template_name = "deadlines/detail.html"
    context_object_name = "deadline"

    def get_queryset(self):
        return Deadline.objects.select_related(
            "client",
            "assigned_to",
            "created_by",
            "completed_by",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["audit_logs"] = self.object.audit_logs.select_related("actor")[:50]
        ctx["can_complete"] = CanCompleteDeadline().has_object_permission(
            self.request, self, self.object
        )
        return ctx


class DeadlineCreateView(LoginRequiredMixin, CreateView):
    model = Deadline
    form_class = DeadlineForm
    template_name = "deadlines/form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Nuevo vencimiento"
        ctx["clients_exist"] = Client.objects.filter(is_active=True).exists()
        return ctx

    def form_valid(self, form):
        deadline = form.save(commit=False)
        deadline.created_by = self.request.user
        deadline.google_sync_status = GoogleSyncStatus.PENDING
        deadline.save()
        write_audit(
            deadline=deadline,
            actor=self.request.user,
            action="CREATE",
            new_status=deadline.status,
            ip_address=get_client_ip(self.request),
        )
        try_sync_deadline(deadline)
        messages.success(self.request, "Vencimiento creado.")
        return redirect("deadline-detail", pk=deadline.pk)


class DeadlineUpdateView(LoginRequiredMixin, UpdateView):
    model = Deadline
    form_class = DeadlineForm
    template_name = "deadlines/form.html"

    def get_queryset(self):
        return Deadline.objects.exclude(
            status__in=[DeadlineStatus.COMPLETED, DeadlineStatus.CANCELLED]
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Editar vencimiento"
        ctx["clients_exist"] = True
        return ctx

    def form_valid(self, form):
        previous_status = self.object.status
        previous_due = self.object.due_date
        previous_assigned = self.object.assigned_to_id

        deadline = form.save(commit=False)
        deadline.google_sync_status = GoogleSyncStatus.PENDING
        deadline.save()

        action_name = "UPDATE"
        if deadline.status == DeadlineStatus.CANCELLED and previous_status != DeadlineStatus.CANCELLED:
            action_name = "CANCEL"
        elif deadline.due_date != previous_due:
            action_name = "CHANGE_DUE_DATE"
        elif deadline.assigned_to_id != previous_assigned:
            action_name = "ASSIGN"

        write_audit(
            deadline=deadline,
            actor=self.request.user,
            action=action_name,
            previous_status=previous_status,
            new_status=deadline.status,
            ip_address=get_client_ip(self.request),
        )
        try_sync_deadline(deadline)
        messages.success(self.request, "Vencimiento actualizado.")
        return redirect("deadline-detail", pk=deadline.pk)


class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = "clients/list.html"
    context_object_name = "clients"
    paginate_by = 50

    def get_queryset(self):
        return Client.objects.order_by("name")


class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = "clients/form.html"
    success_url = reverse_lazy("client-list")

    def form_valid(self, form):
        messages.success(self.request, "Cliente creado.")
        return super().form_valid(form)


class DeadlineCompleteConfirmView(LoginRequiredMixin, View):
    """
    GET: muestra confirmación (nunca completa).
    POST: completa con CSRF + permisos + observación opcional.
    """

    template_name = "deadlines/complete_confirm.html"

    def get_deadline(self):
        return get_object_or_404(
            Deadline.objects.select_related("client", "assigned_to", "completed_by"),
            pk=self.kwargs["pk"],
        )

    def get(self, request, pk):
        deadline = self.get_deadline()
        can = CanCompleteDeadline().has_object_permission(request, self, deadline)
        return render(
            request,
            self.template_name,
            {
                "deadline": deadline,
                "can_complete": can,
                "already_completed": deadline.status == DeadlineStatus.COMPLETED,
            },
        )

    def post(self, request, pk):
        deadline = self.get_deadline()
        if not CanCompleteDeadline().has_object_permission(request, self, deadline):
            return HttpResponseForbidden("No tenés permiso para completar este vencimiento.")

        observation = request.POST.get("observation", "").strip()

        try:
            with transaction.atomic():
                locked = Deadline.objects.select_for_update().get(pk=deadline.pk)
                if not CanCompleteDeadline().has_object_permission(request, self, locked):
                    return HttpResponseForbidden(
                        "No tenés permiso para completar este vencimiento."
                    )
                complete_deadline(
                    deadline=locked,
                    user=request.user,
                    observation=observation,
                    request=request,
                    sync_immediately=True,
                )
        except ValueError as exc:
            return render(
                request,
                self.template_name,
                {
                    "deadline": deadline,
                    "can_complete": True,
                    "error": str(exc),
                    "already_completed": False,
                },
                status=400,
            )

        messages.success(request, "Vencimiento marcado como completado.")
        return redirect("deadline-detail", pk=pk)


@login_required
def home(request):
    return redirect("deadline-list")
