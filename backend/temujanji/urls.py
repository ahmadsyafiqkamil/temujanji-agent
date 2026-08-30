from django.contrib import admin
from django.urls import include, path

from appointments.views import (
    AdminAppointmentListView,
    AppointmentByTokenView,
    AppointmentCancelByCodeView,
    AppointmentCancelView,
    AppointmentCreateView,
    CheckInView,
)
from catalog.views import (
    AdminQuotaDetailView,
    AdminQuotaListCreateView,
    AdminServiceListView,
    AvailabilityView,
    ServiceListView,
    ServiceSyncView,
)
from temujanji.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health", health, name="health"),
    path("api/v1/check-in", CheckInView.as_view(), name="check-in"),
    path("api/v1/auth/", include("authentication.urls")),
    path("api/v1/services/sync", ServiceSyncView.as_view(), name="services-sync"),
    path("api/v1/services", ServiceListView.as_view(), name="services-list"),
    path("api/v1/availability", AvailabilityView.as_view(), name="availability"),
    path("api/v1/admin/quotas", AdminQuotaListCreateView.as_view(), name="admin-quotas"),
    path(
        "api/v1/admin/quotas/<int:quota_id>",
        AdminQuotaDetailView.as_view(),
        name="admin-quota-detail",
    ),
    path("api/v1/admin/services", AdminServiceListView.as_view(), name="admin-services"),
    path(
        "api/v1/admin/appointments",
        AdminAppointmentListView.as_view(),
        name="admin-appointments",
    ),
    path("api/v1/appointments", AppointmentCreateView.as_view(), name="appointments"),
    path(
        "api/v1/appointments/by-token/<str:token>",
        AppointmentByTokenView.as_view(),
        name="appointment-by-token",
    ),
    path(
        "api/v1/appointments/cancel-by-code",
        AppointmentCancelByCodeView.as_view(),
        name="appointment-cancel-by-code",
    ),
    path(
        "api/v1/appointments/<uuid:appointment_id>/cancel",
        AppointmentCancelView.as_view(),
        name="appointment-cancel",
    ),
]
