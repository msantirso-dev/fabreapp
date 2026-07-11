from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.clients.models import Client
from apps.deadlines.models import Deadline, DeadlineStatus, GoogleSyncStatus

User = get_user_model()


class Command(BaseCommand):
    help = "Carga cliente y vencimientos de ejemplo para probar la UI."

    def handle(self, *args, **options):
        admin = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not admin:
            self.stderr.write("Creá un usuario primero (createsuperuser).")
            return

        Cliente creado: EMPRESA EJEMPLO S.A.

        client, created = Client.objects.get_or_create(
            cuit="20-11111111-2",
            defaults={"name": "EMPRESA EJEMPLO S.A.", "is_active": True},
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Cliente creado: {client.name}"))
        else:
            self.stdout.write(f"Cliente existente: {client.name}")

        samples = [
            {
                "obligation_code": "IVA",
                "obligation_name": "IVA",
                "period": "07/2026",
                "due_date": date(2026, 8, 21),
                "status": DeadlineStatus.PENDING,
            },
            {
                "obligation_code": "IIBB",
                "obligation_name": "Ingresos Brutos",
                "period": "07/2026",
                "due_date": date(2026, 8, 15),
                "status": DeadlineStatus.IN_PROGRESS,
            },
            {
                "obligation_code": "SUSS",
                "obligation_name": "Sueldos / SUSS",
                "period": "06/2026",
                "due_date": date.today() - timedelta(days=2),
                "status": DeadlineStatus.OVERDUE,
            },
        ]

        created_count = 0
        for sample in samples:
            exists = Deadline.objects.filter(
                client=client,
                obligation_code=sample["obligation_code"],
                period=sample["period"],
            ).exists()
            if exists:
                continue
            Deadline.objects.create(
                client=client,
                created_by=admin,
                assigned_to=admin,
                google_sync_status=GoogleSyncStatus.PENDING,
                **sample,
            )
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Listo. Vencimientos nuevos: {created_count}. "
                f"Total cliente: {Deadline.objects.filter(client=client).count()}"
            )
        )
