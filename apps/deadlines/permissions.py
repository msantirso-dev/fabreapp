from rest_framework.permissions import BasePermission

from apps.deadlines.models import Deadline


class CanCompleteDeadline(BasePermission):
    """
    Permite completar si el usuario es staff, el responsable asignado,
    o el creador del vencimiento.
    """

    def has_object_permission(self, request, view, obj: Deadline) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        if obj.assigned_to_id and obj.assigned_to_id == user.id:
            return True
        if obj.created_by_id and obj.created_by_id == user.id:
            return True
        return False


class IsAuthenticatedStudioUser(BasePermission):
    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)
