from datetime import date

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from authentication.api_auth import AgentAPIKeyAuthentication
from authentication.permissions import IsAdmin, IsAgent
from catalog.models import DailyQuota, ServiceCache
from catalog.services import create_quota, sync_services, update_quota


def _service_payload(service: ServiceCache) -> dict[str, object]:
    return {
        "antrian_service_id": service.antrian_service_id,
        "code": service.code,
        "name": service.name,
        "is_active": service.is_active,
    }


def _quota_payload(quota: DailyQuota) -> dict[str, object]:
    return {
        "id": quota.id,
        "antrian_service_id": quota.antrian_service_id,
        "day": quota.day.isoformat(),
        "capacity": quota.capacity,
        "booked_count": quota.booked_count,
    }


class ServiceSyncView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def post(self, _request) -> Response:
        return Response({"synced": sync_services()})


class ServiceListView(APIView):
    authentication_classes = [AgentAPIKeyAuthentication]
    permission_classes = [IsAgent]

    def get(self, _request) -> Response:
        services = ServiceCache.objects.filter(is_active=True).order_by("name")
        return Response([_service_payload(service) for service in services])


class AdminServiceListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, _request) -> Response:
        services = ServiceCache.objects.order_by("name")
        return Response([_service_payload(service) for service in services])


class AvailabilityView(APIView):
    authentication_classes = [AgentAPIKeyAuthentication]
    permission_classes = [IsAgent]

    def get(self, request) -> Response:
        service_id = int(request.query_params["service_id"])
        from_day = date.fromisoformat(request.query_params["from"])
        to_day = date.fromisoformat(request.query_params["to"])
        quotas = DailyQuota.objects.filter(
            antrian_service_id=service_id,
            day__gte=from_day,
            day__lte=to_day,
        ).order_by("day")
        return Response(
            {
                "service_id": service_id,
                "availability": [
                    {
                        "day": quota.day.isoformat(),
                        "remaining": quota.capacity - quota.booked_count,
                    }
                    for quota in quotas
                ],
            }
        )


class AdminQuotaListCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, _request) -> Response:
        quotas = DailyQuota.objects.order_by("day")
        return Response([_quota_payload(quota) for quota in quotas])

    def post(self, request) -> Response:
        quota = create_quota(
            antrian_service_id=int(request.data["antrian_service_id"]),
            day=date.fromisoformat(str(request.data["day"])),
            capacity=int(request.data["capacity"]),
        )
        return Response(_quota_payload(quota), status=status.HTTP_201_CREATED)


class AdminQuotaDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def patch(self, request, quota_id: int) -> Response:
        quota = DailyQuota.objects.filter(pk=quota_id).first()
        if quota is None:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        quota = update_quota(quota, capacity=int(request.data["capacity"]))
        return Response(_quota_payload(quota))

    def delete(self, _request, quota_id: int) -> Response:
        deleted, _ = DailyQuota.objects.filter(pk=quota_id).delete()
        if not deleted:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
