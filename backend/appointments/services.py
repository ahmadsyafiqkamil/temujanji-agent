import secrets
from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import APIException, NotFound

from appointments.models import Appointment, CheckIn
from appointments.qr import qr_payload_for, verify_qr_payload
from catalog.antrian_client import AntrianClient
from catalog.models import DailyQuota


class BadRequest(APIException):
    status_code = 400
    default_detail = "Bad request"


class Conflict(APIException):
    status_code = 409
    default_detail = "Conflict"


class BadGateway(APIException):
    status_code = 502
    default_detail = "Bad gateway"


def dubai_today() -> date:
    return datetime.now(ZoneInfo("Asia/Dubai")).date()


def _create_response(appointment: Appointment) -> dict[str, object]:
    token = appointment.access_token
    return {
        "id": appointment.id,
        "booking_code": appointment.booking_code,
        "access_token": token,
        "appointment_date": appointment.appointment_date,
        "status": appointment.status,
        "magic_url": f"{settings.PUBLIC_WEB_BASE.rstrip('/')}/j/{token}",
        "qr_payload": qr_payload_for(appointment.booking_code),
    }


def create_appointment(
    *,
    antrian_service_id: int,
    full_name: str,
    document_number: str,
    appointment_date: date,
    telegram_user_id: str | None = None,
) -> dict[str, object]:
    if appointment_date < dubai_today():
        raise BadRequest("Appointment date cannot be in the past")

    with transaction.atomic():
        quota = (
            DailyQuota.objects.select_for_update()
            .filter(antrian_service_id=antrian_service_id, day=appointment_date)
            .first()
        )
        if quota is None:
            raise BadRequest("Quota is not open for this service and day")
        if quota.booked_count >= quota.capacity:
            raise Conflict("Quota is full")
        exists = Appointment.objects.filter(
            document_number=document_number,
            antrian_service_id=antrian_service_id,
            appointment_date=appointment_date,
            status=Appointment.Status.BOOKED,
        ).exists()
        if exists:
            raise Conflict("Active appointment already exists")

        appointment = Appointment.objects.create(
            booking_code=f"KJRI-{secrets.token_hex(2).upper()}",
            access_token=secrets.token_urlsafe(24),
            antrian_service_id=antrian_service_id,
            full_name=full_name,
            document_number=document_number,
            appointment_date=appointment_date,
            telegram_user_id=telegram_user_id,
        )
        quota.booked_count += 1
        quota.save(update_fields=["booked_count"])
    return _create_response(appointment)


def get_appointment_by_token(token: str) -> Appointment:
    appointment = Appointment.objects.filter(access_token=token).first()
    if appointment is None:
        raise NotFound("Appointment not found")
    return appointment


def cancel_appointment(appointment_id: UUID) -> Appointment:
    with transaction.atomic():
        appointment = (
            Appointment.objects.select_for_update()
            .filter(pk=appointment_id)
            .first()
        )
        if appointment is None:
            raise NotFound("Appointment not found")
        return _cancel_locked(appointment)


def cancel_appointment_by_booking_code(booking_code: str) -> Appointment:
    with transaction.atomic():
        appointment = (
            Appointment.objects.select_for_update()
            .filter(booking_code=booking_code)
            .first()
        )
        if appointment is None:
            raise NotFound("Appointment not found")
        return _cancel_locked(appointment)


def _cancel_locked(appointment: Appointment) -> Appointment:
    if appointment.status != Appointment.Status.BOOKED:
        raise Conflict("Only booked appointments can be cancelled")
    quota = (
        DailyQuota.objects.select_for_update()
        .filter(
            antrian_service_id=appointment.antrian_service_id,
            day=appointment.appointment_date,
        )
        .first()
    )
    appointment.status = Appointment.Status.CANCELLED
    appointment.save(update_fields=["status", "updated_at"])
    if quota is not None and quota.booked_count > 0:
        quota.booked_count -= 1
        quota.save(update_fields=["booked_count"])
    return appointment


def check_in_appointment(*, qr_payload: str, staff_user) -> Appointment:
    booking_code = verify_qr_payload(qr_payload, settings.QR_SIGNING_SECRET)
    if booking_code is None:
        raise BadRequest("Invalid QR payload")

    with transaction.atomic():
        appointment = (
            Appointment.objects.select_for_update()
            .filter(booking_code=booking_code)
            .first()
        )
        if appointment is None:
            raise NotFound("Appointment not found")
        if appointment.status == Appointment.Status.CHECKED_IN:
            return appointment
        if appointment.status != Appointment.Status.BOOKED:
            raise Conflict("Only booked appointments can be checked in")
        if appointment.appointment_date != dubai_today():
            raise Conflict("Check-in is only allowed on the appointment date")
        try:
            queue = AntrianClient().create_queue(
                appointment.antrian_service_id,
                appointment.booking_code,
            )
        except httpx.HTTPError as error:
            raise BadGateway("Unable to create antrian queue") from error
        appointment.antrian_queue_id = int(queue["id"])
        appointment.queue_number = str(queue["queue_number"])
        appointment.status = Appointment.Status.CHECKED_IN
        appointment.save(
            update_fields=[
                "antrian_queue_id",
                "queue_number",
                "status",
                "updated_at",
            ]
        )
        CheckIn.objects.create(appointment=appointment, staff_user=staff_user)
        return appointment
