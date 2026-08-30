from django.db import models
from django.utils import timezone


class ServiceCache(models.Model):
    antrian_service_id = models.IntegerField(primary_key=True)
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    synced_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "service_cache"


class DailyQuota(models.Model):
    antrian_service = models.ForeignKey(
        ServiceCache,
        on_delete=models.RESTRICT,
        db_column="antrian_service_id",
        related_name="quotas",
    )
    day = models.DateField()
    capacity = models.PositiveIntegerField()
    booked_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "daily_quota"
        constraints = [
            models.UniqueConstraint(
                fields=["antrian_service", "day"],
                name="uq_daily_quota_service_day",
            ),
            models.CheckConstraint(
                condition=models.Q(capacity__gte=1),
                name="ck_daily_quota_capacity_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(booked_count__gte=0),
                name="ck_daily_quota_booked_count_nonnegative",
            ),
        ]
