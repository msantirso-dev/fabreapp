from django.apps import AppConfig


class DeadlinesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.deadlines"
    label = "deadlines"
    verbose_name = "Vencimientos"

    def ready(self) -> None:
        from . import signals  # noqa: F401
