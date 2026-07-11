from django.db import transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.calendar_sync.services import try_sync_deadline
from apps.deadlines.models import Deadline, DeadlineStatus, GoogleSyncStatus
from apps.deadlines.permissions import CanCompleteDeadline, IsAuthenticatedStudioUser
from apps.deadlines.serializers import (
    DeadlineAuditLogSerializer,
    DeadlineCompleteResponseSerializer,
    DeadlineCompleteSerializer,
    DeadlineSerializer,
)
from apps.deadlines.services import complete_deadline, write_audit, get_client_ip


class DeadlineViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = DeadlineSerializer
    permission_classes = [IsAuthenticatedStudioUser]
    queryset = Deadline.objects.select_related(
        "client",
        "assigned_to",
        "created_by",
        "completed_by",
    )

    def perform_create(self, serializer):
        deadline = serializer.save(
            created_by=self.request.user,
            google_sync_status=GoogleSyncStatus.PENDING,
        )
        write_audit(
            deadline=deadline,
            actor=self.request.user,
            action="CREATE",
            new_status=deadline.status,
            ip_address=get_client_ip(self.request),
        )
        try_sync_deadline(deadline)

    def perform_update(self, serializer):
        previous = self.get_object()
        previous_status = previous.status
        previous_due = previous.due_date
        previous_assigned = previous.assigned_to_id

        deadline = serializer.save(google_sync_status=GoogleSyncStatus.PENDING)

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
            metadata={
                "due_date": str(deadline.due_date),
                "assigned_to_id": str(deadline.assigned_to_id or ""),
            },
        )
        try_sync_deadline(deadline)

    @action(
        detail=True,
        methods=["post"],
        url_path="complete",
        permission_classes=[IsAuthenticatedStudioUser, CanCompleteDeadline],
    )
    def complete(self, request, pk=None):
        deadline = self.get_object()
        self.check_object_permissions(request, deadline)

        input_serializer = DeadlineCompleteSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        observation = input_serializer.validated_data.get("observation", "")

        try:
            with transaction.atomic():
                # Lock row to avoid double-complete races
                locked = Deadline.objects.select_for_update().get(pk=deadline.pk)
                self.check_object_permissions(request, locked)
                locked = complete_deadline(
                    deadline=locked,
                    user=request.user,
                    observation=observation,
                    request=request,
                    sync_immediately=True,
                )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        payload = {
            "id": locked.id,
            "status": locked.status,
            "completed_by": locked.completed_by,
            "completed_at": locked.completed_at,
            "google_sync_status": locked.google_sync_status,
        }
        return Response(
            DeadlineCompleteResponseSerializer(payload).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="audit")
    def audit(self, request, pk=None):
        deadline = self.get_object()
        logs = deadline.audit_logs.select_related("actor")
        return Response(DeadlineAuditLogSerializer(logs, many=True).data)
