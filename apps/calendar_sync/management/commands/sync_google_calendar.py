from django.core.management.base import BaseCommand

from apps.calendar_sync.services import (
    calendar_sync_ready,
    ensure_shared_calendar,
    sync_pending_deadlines,
)


class Command(BaseCommand):
    help = (
        "Sincroniza vencimientos pendientes/error con el calendario compartido "
        "«Vencimientos – Estudio Contable». Programar en Coolify cada 10–60 min: "
        "python manage.py sync_google_calendar"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Máximo de vencimientos a sincronizar en esta corrida.",
        )
        parser.add_argument(
            "--ensure-calendar",
            action="store_true",
            help="Crea o localiza el calendario compartido antes de sincronizar.",
        )

    def handle(self, *args, **options):
        if not calendar_sync_ready():
            self.stdout.write(
                self.style.WARNING(
                    "Google Calendar no conectado — se omitió la sincronización."
                )
            )
            return

        if options["ensure_calendar"]:
            calendar_id = ensure_shared_calendar()
            self.stdout.write(self.style.SUCCESS(f"Calendario compartido: {calendar_id}"))

        stats = sync_pending_deadlines(limit=options["limit"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Sincronización terminada: synced={stats['synced']} "
                f"errors={stats['errors']} skipped={stats['skipped']}"
            )
        )
