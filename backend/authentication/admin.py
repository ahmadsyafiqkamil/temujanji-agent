from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from authentication.models import StaffUser


@admin.register(StaffUser)
class StaffUserAdmin(UserAdmin):
    list_display = ("username", "role", "is_active")
    fieldsets = (
        *UserAdmin.fieldsets,
        ("Temujanji", {"fields": ("role",)}),
    )
