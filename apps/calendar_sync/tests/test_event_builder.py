from django.test import SimpleTestCase

from apps.calendar_sync.event_builder import STATUS_EMOJI, build_event_title
from apps.deadlines.models import DeadlineStatus


class EventBuilderUnitTests(SimpleTestCase):
    def test_all_statuses_have_emoji(self):
        for status, _ in DeadlineStatus.choices:
            self.assertIn(status, STATUS_EMOJI)

    def test_overdue_title_emoji(self):
        class FakeClient:
            name = "EMPRESA EJEMPLO S.A."

        class FakeDeadline:
            status = DeadlineStatus.OVERDUE
            obligation_name = "IVA"
            client = FakeClient()

        self.assertTrue(build_event_title(FakeDeadline()).startswith("🔴"))
