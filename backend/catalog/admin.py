from django.contrib import admin

from catalog.models import DailyQuota, ServiceCache


@admin.register(ServiceCache)
class ServiceCacheAdmin(admin.ModelAdmin):
    list_display = ("antrian_service_id", "code", "name", "is_active")


@admin.register(DailyQuota)
class DailyQuotaAdmin(admin.ModelAdmin):
    list_display = ("id", "antrian_service", "day", "capacity", "booked_count")
