from rest_framework import serializers

from apps.accounts.models import User
from apps.clients.models import Client
from apps.deadlines.models import Deadline, DeadlineAuditLog, DeadlineStatus


class UserBriefSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "name")

    def get_name(self, obj: User) -> str:
        return obj.get_full_name_or_username()


class ClientBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ("id", "name", "cuit")


class DeadlineSerializer(serializers.ModelSerializer):
    client = ClientBriefSerializer(read_only=True)
    client_id = serializers.PrimaryKeyRelatedField(
        source="client",
        queryset=Client.objects.filter(is_active=True),
        write_only=True,
    )
    assigned_to = UserBriefSerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        source="assigned_to",
        queryset=User.objects.filter(is_active=True),
        write_only=True,
        allow_null=True,
        required=False,
    )
    created_by = UserBriefSerializer(read_only=True)
    completed_by = UserBriefSerializer(read_only=True)

    class Meta:
        model = Deadline
        fields = (
            "id",
            "client",
            "client_id",
            "obligation_code",
            "obligation_name",
            "period",
            "due_date",
            "status",
            "assigned_to",
            "assigned_to_id",
            "created_by",
            "completed_by",
            "completed_at",
            "observations",
            "google_calendar_event_id",
            "google_sync_status",
            "google_sync_error",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "created_by",
            "completed_by",
            "completed_at",
            "google_calendar_event_id",
            "google_sync_status",
            "google_sync_error",
            "created_at",
            "updated_at",
        )


class DeadlineCompleteSerializer(serializers.Serializer):
    observation = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=5000,
    )


class DeadlineCompleteResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=DeadlineStatus.choices)
    completed_by = UserBriefSerializer()
    completed_at = serializers.DateTimeField()
    google_sync_status = serializers.CharField()


class DeadlineAuditLogSerializer(serializers.ModelSerializer):
    actor = UserBriefSerializer(read_only=True)

    class Meta:
        model = DeadlineAuditLog
        fields = (
            "id",
            "action",
            "actor",
            "previous_status",
            "new_status",
            "observation",
            "ip_address",
            "google_calendar_event_id",
            "google_sync_result",
            "created_at",
        )
