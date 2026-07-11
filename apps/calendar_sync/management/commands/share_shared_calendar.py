from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.calendar_sync.services import ensure_shared_calendar, share_calendar_with_email
from django.conf import settings


class Command(BaseCommand):
    help = (
        "Comparte el calendario «Vencimientos – Estudio Contable» con usuarios del estudio "
        "(por google_email). No crea copias de eventos en calendarios personales."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            action="append",
            dest="emails",
            help="Email Google a compartir (repetible). Si se omite, usa google_email de usuarios activos.",
        )
        parser.add_argument(
            "--role",
            default="writer",
            choices=["reader", "writer", "owner"],
            help="Rol ACL de Google Calendar (default: writer).",
        )

    def handle(self, *args, **options):
        if not settings.GOOGLE_CALENDAR_ENABLED:
            raise CommandError("GOOGLE_CALENDAR_ENABLED=False")

        calendar_id = ensure_shared_calendar()
        emails = options["emails"]
        if not emails:
            emails = list(
                User.objects.exclude(google_email="")
                .filter(is_active=True)
                .values_list("google_email", flat=True)
            )

        if not emails:
            raise CommandError("No hay emails para compartir.")

        for email in emails:
            share_calendar_with_email(calendar_id, email, role=options["role"])
            self.stdout.write(self.style.SUCCESS(f"Compartido con {email} ({options['role']})"))
