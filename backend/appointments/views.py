from datetime import date
from uuid import UUID

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from appointments.models import Appointment
from appointments.qr import qr_payload_for
from appointments.services import (
    cancel_appointment,
    cancel_appointment_by_booking_code,
    check_in_appointment,
    create_appointment,
    get_appointment_by_token,
)
from authentication.api_auth import AgentAPIKeyAuthentication
from authentication.permissions import IsAdmin, IsAgent, IsStaff


class AdminAppointmentListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request) -> Response:
        queryset = Appointment.objects.all()
        day = request.query_params.get("date")
        service_id = request.query_params.get("service_id")
        status_value = request.query_params.get("status")
        if day:
            queryset = queryset.filter(appointment_date=day)
        if service_id:
            queryset = queryset.filter(antrian_service_id=int(service_id))
        if status_value:
            queryset = queryset.filter(status=status_value)
        return Response(
            [
                {
                    "id": str(appointment.id),
                    "booking_code": appointment.booking_code,
                    "antrian_service_id": appointment.antrian_service_id,
                    "full_name": appointment.full_name,
                    "appointment_date": appointment.appointment_date.isoformat(),
                    "status": appointment.status,
                    "qr_payload": qr_payload_for(appointment.booking_code),
                }
                for appointment in queryset
            ]
        )


class AppointmentCreateView(APIView):
    authentication_classes = [AgentAPIKeyAuthentication]
    permission_classes = [IsAgent]

    def post(self, request) -> Response:
        telegram_user_id = request.data.get("telegram_user_id")
        payload = create_appointment(
            antrian_service_id=int(request.data["antrian_service_id"]),
            full_name=str(request.data["full_name"]),
            document_number=str(request.data["document_number"]),
            appointment_date=date.fromisoformat(str(request.data["appointment_date"])),
            telegram_user_id=str(telegram_user_id) if telegram_user_id else None,
        )
        return Response(payload, status=201)


class AppointmentByTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, _request, token: str) -> Response:
        appointment = get_appointment_by_token(token)
        return Response(
            {
                "id": appointment.id,
                "booking_code": appointment.booking_code,
                "antrian_service_id": appointment.antrian_service_id,
                "full_name": appointment.full_name,
                "appointment_date": appointment.appointment_date,
                "status": appointment.status,
                "qr_payload": qr_payload_for(appointment.booking_code),
            }
        )


class AppointmentCancelView(APIView):
    authentication_classes = [AgentAPIKeyAuthentication]
    permission_classes = [IsAgent]

    def post(self, _request, appointment_id: UUID) -> Response:
        appointment = cancel_appointment(appointment_id)
        return Response(
            {
                "id": appointment.id,
                "booking_code": appointment.booking_code,
                "status": appointment.status,
            }
        )


class CheckInView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsStaff]

    def post(self, request) -> Response:
        appointment = check_in_appointment(
            qr_payload=str(request.data["qr_payload"]),
            staff_user=request.user,
        )
        return Response(
            {
                "booking_code": appointment.booking_code,
                "antrian_service_id": appointment.antrian_service_id,
                "full_name": appointment.full_name,
                "appointment_date": appointment.appointment_date,
                "status": appointment.status,
                "queue_number": appointment.queue_number,
            }
        )


class AppointmentCancelByCodeView(APIView):
    authentication_classes = [AgentAPIKeyAuthentication]
    permission_classes = [IsAgent]

    def post(self, request) -> Response:
        appointment = cancel_appointment_by_booking_code(
            str(request.data["booking_code"])
        )
        return Response(
            {
                "id": appointment.id,
                "booking_code": appointment.booking_code,
                "status": appointment.status,
            }
        )
