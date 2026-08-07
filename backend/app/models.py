import enum
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class AppointmentStatus(str, enum.Enum):
    BOOKED = "booked"
    CHECKED_IN = "checked_in"
    CANCELLED = "cancelled"


class StaffRole(str, enum.Enum):
    STAFF = "staff"
    ADMIN = "admin"


class ServiceCache(SQLModel, table=True):
    __tablename__ = "service_cache"

    antrian_service_id: int = Field(
        sa_column=Column(Integer, primary_key=True, autoincrement=False)
    )
    code: str = Field(max_length=64)
    name: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    synced_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class DailyQuota(SQLModel, table=True):
    __tablename__ = "daily_quota"
    __table_args__ = (
        UniqueConstraint(
            "antrian_service_id", "day", name="uq_daily_quota_service_day"
        ),
        CheckConstraint("capacity >= 1", name="ck_daily_quota_capacity_positive"),
        CheckConstraint(
            "booked_count >= 0", name="ck_daily_quota_booked_count_nonnegative"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    antrian_service_id: int = Field(
        sa_column=Column(
            ForeignKey("service_cache.antrian_service_id", ondelete="RESTRICT"),
            nullable=False,
        )
    )
    day: date
    capacity: int
    booked_count: int = Field(default=0, ge=0)


class Appointment(SQLModel, table=True):
    __tablename__ = "appointment"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    booking_code: str = Field(max_length=64, unique=True, index=True)
    access_token: str = Field(max_length=255, unique=True, index=True)
    antrian_service_id: int = Field(index=True)
    full_name: str = Field(max_length=255)
    document_number: str = Field(max_length=128, index=True)
    appointment_date: date = Field(index=True)
    status: AppointmentStatus = Field(
        default=AppointmentStatus.BOOKED,
        sa_column=Column(
            Enum(
                AppointmentStatus,
                name="appointment_status",
                values_callable=lambda statuses: [status.value for status in statuses],
            ),
            nullable=False,
        ),
    )
    telegram_user_id: str | None = Field(default=None, max_length=128)
    antrian_queue_id: int | None = Field(default=None)
    queue_number: str | None = Field(default=None, max_length=64)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=utc_now),
    )


class StaffUser(SQLModel, table=True):
    __tablename__ = "staff_user"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(max_length=128, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    role: StaffRole = Field(
        default=StaffRole.STAFF,
        sa_column=Column(
            Enum(
                StaffRole,
                name="staff_role",
                values_callable=lambda roles: [role.value for role in roles],
            ),
            nullable=False,
        ),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=utc_now),
    )


class CheckIn(SQLModel, table=True):
    __tablename__ = "check_in"

    id: int | None = Field(default=None, primary_key=True)
    appointment_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("appointment.id", ondelete="RESTRICT"), nullable=False
        )
    )
    staff_user_id: int = Field(
        sa_column=Column(
            ForeignKey("staff_user.id", ondelete="RESTRICT"), nullable=False
        )
    )
    checked_in_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
