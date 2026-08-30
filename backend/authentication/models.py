from django.contrib.auth.models import AbstractUser
from django.db import models


class StaffUser(AbstractUser):
    class Role(models.TextChoices):
        STAFF = "staff", "Staff"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.STAFF,
    )

    class Meta:
        db_table = "staff_user"
