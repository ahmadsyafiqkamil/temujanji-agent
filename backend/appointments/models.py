import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Appointment(models.Model):
    class Status(models.TextChoices):
        BOOKED = "booked", "Booked"
        CHECKED_IN = "checked_in", "Checked in"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_code = models.CharField(max_length=64, unique=True)
    access_token = models.CharField(max_length=255, unique=True)
    antrian_service_id = models.IntegerField(db_index=True)
    full_name = models.CharField(max_length=255)
    document_number = models.CharField(max_length=128, db_index=True)
    appointment_date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.BOOKED,
    )
    telegram_user_id = models.CharField(max_length=128, null=True, blank=True)
    antrian_queue_id = models.IntegerField(null=True, blank=True)
    queue_number = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "appointment"


class CheckIn(models.Model):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.RESTRICT,
        related_name="check_ins",
    )
    staff_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.RESTRICT,
        related_name="check_ins",
    )
    checked_in_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "check_in"
