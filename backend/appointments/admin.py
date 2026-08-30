from django.contrib import admin

from appointments.models import Appointment, CheckIn


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        "booking_code",
        "full_name",
        "appointment_date",
        "status",
        "antrian_service_id",
    )


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ("id", "appointment", "staff_user", "checked_in_at")
