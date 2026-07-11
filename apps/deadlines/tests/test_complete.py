from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client as HttpClient, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.calendar_sync.event_builder import (
    build_event_description,
    build_event_title,
    build_extended_properties,
)
from apps.clients.models import Client
from apps.deadlines.models import Deadline, DeadlineStatus, GoogleSyncStatus
from apps.deadlines.services import complete_deadline

User = get_user_model()


class DeadlineCompleteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="maria",
            password="test-pass-123",
            first_name="María",
            last_name="López",
            display_name="María López",
        )
        self.other = User.objects.create_user(username="otro", password="test-pass-123")
        self.client_obj = Client.objects.create(
            name="EMPRESA EJEMPLO S.A.",
            cuit="30-12345678-7",
        )
        self.deadline = Deadline.objects.create(
            client=self.client_obj,
            obligation_code="IVA",
            obligation_name="IVA",
            period="07/2026",
            due_date=date(2026, 8, 21),
            assigned_to=self.user,
            created_by=self.user,
            status=DeadlineStatus.PENDING,
            google_calendar_event_id="evt_existing_123",
            google_sync_status=GoogleSyncStatus.SYNCED,
        )

    def test_event_title_pending(self):
        self.assertEqual(
            build_event_title(self.deadline),
            "🔵 IVA – EMPRESA EJEMPLO S.A.",
        )

    def test_event_title_completed(self):
        self.deadline.status = DeadlineStatus.COMPLETED
        self.assertEqual(
            build_event_title(self.deadline),
            "✅ IVA – EMPRESA EJEMPLO S.A.",
        )

    def test_extended_properties_include_deadline_id(self):
        props = build_extended_properties(self.deadline)
        self.assertEqual(props["private"]["deadline_id"], str(self.deadline.id))
        self.assertEqual(props["private"]["obligation_code"], "IVA")
        self.assertIn("application_name", props["private"])

    def test_description_has_secure_complete_link(self):
        text = build_event_description(self.deadline)
        self.assertIn(f"/deadlines/{self.deadline.id}/complete", text)
        self.assertIn("Marcar como completado:", text)

    @patch("apps.calendar_sync.services.sync_deadline_to_google")
    def test_complete_is_idempotent(self, mock_sync):
        mock_sync.side_effect = lambda d: d
        complete_deadline(deadline=self.deadline, user=self.user, observation="OK")
        self.deadline.refresh_from_db()
        first_at = self.deadline.completed_at
        complete_deadline(deadline=self.deadline, user=self.user, observation="otra")
        self.deadline.refresh_from_db()
        self.assertEqual(self.deadline.completed_at, first_at)
        self.assertEqual(self.deadline.status, DeadlineStatus.COMPLETED)

    @override_settings(GOOGLE_CALENDAR_ENABLED=True, GOOGLE_SERVICE_ACCOUNT_FILE="/tmp/fake.json")
    @patch("apps.calendar_sync.services.calendar_sync_ready", return_value=True)
    @patch("apps.calendar_sync.services.create_or_update_event")
    def test_complete_keeps_same_event_id_on_sync_failure(self, mock_create, _ready):
        mock_create.side_effect = RuntimeError("Google down")
        complete_deadline(
            deadline=self.deadline,
            user=self.user,
            observation="Presentación realizada correctamente",
            sync_immediately=True,
        )
        self.deadline.refresh_from_db()
        self.assertEqual(self.deadline.status, DeadlineStatus.COMPLETED)
        self.assertEqual(self.deadline.google_calendar_event_id, "evt_existing_123")
        self.assertEqual(self.deadline.google_sync_status, GoogleSyncStatus.ERROR)
        self.assertTrue(self.deadline.audit_logs.filter(action="COMPLETE").exists())

    def test_complete_get_does_not_complete(self):
        http = HttpClient()
        http.login(username="maria", password="test-pass-123")
        url = reverse("deadline-complete", kwargs={"pk": self.deadline.id})
        response = http.get(url)
        self.assertEqual(response.status_code, 200)
        self.deadline.refresh_from_db()
        self.assertEqual(self.deadline.status, DeadlineStatus.PENDING)

    @patch("apps.calendar_sync.services.sync_deadline_to_google")
    def test_complete_post_web(self, mock_sync):
        def _sync(d):
            d.google_sync_status = GoogleSyncStatus.SYNCED
            d.save(update_fields=["google_sync_status", "updated_at"])
            return d

        mock_sync.side_effect = _sync
        http = HttpClient()
        http.login(username="maria", password="test-pass-123")
        url = reverse("deadline-complete", kwargs={"pk": self.deadline.id})
        response = http.post(url, {"observation": "Hecho"})
        self.assertEqual(response.status_code, 302)
        self.deadline.refresh_from_db()
        self.assertEqual(self.deadline.status, DeadlineStatus.COMPLETED)
        self.assertEqual(self.deadline.completed_by, self.user)

    @patch("apps.calendar_sync.services.sync_deadline_to_google")
    def test_api_complete_endpoint(self, mock_sync):
        def _sync(d):
            d.google_sync_status = GoogleSyncStatus.SYNCED
            d.save(update_fields=["google_sync_status", "updated_at"])
            return d

        mock_sync.side_effect = _sync
        api = APIClient()
        api.login(username="maria", password="test-pass-123")
        url = f"/api/v1/deadlines/{self.deadline.id}/complete/"
        response = api.post(url, {"observation": "Presentación OK"}, format="json")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["completed_by"]["name"], "María López")
        self.assertEqual(data["google_sync_status"], "SYNCED")
        self.assertIn("completed_at", data)

    def test_api_complete_forbidden_for_unrelated_user(self):
        api = APIClient()
        api.login(username="otro", password="test-pass-123")
        url = f"/api/v1/deadlines/{self.deadline.id}/complete/"
        response = api.post(url, {}, format="json")
        self.assertEqual(response.status_code, 403)
