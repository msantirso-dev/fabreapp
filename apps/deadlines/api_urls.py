from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.deadlines.api_views import DeadlineViewSet

router = DefaultRouter()
router.register("deadlines", DeadlineViewSet, basename="api-deadline")

urlpatterns = router.urls
