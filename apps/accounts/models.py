from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Studio user; Google email used for calendar sharing."""

    google_email = models.EmailField(
        blank=True,
        help_text="Cuenta de Google con la que se comparte el calendario del estudio.",
    )
    display_name = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ["last_name", "first_name", "username"]

    def get_full_name_or_username(self) -> str:
        name = self.display_name or self.get_full_name()
        return name.strip() or self.username
