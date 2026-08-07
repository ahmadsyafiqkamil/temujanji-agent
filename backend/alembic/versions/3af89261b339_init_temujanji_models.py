"""init temujanji models

Revision ID: 3af89261b339
Revises:
Create Date: 2026-08-07 10:15:03.815957

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3af89261b339"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    appointment_status = sa.Enum(
        "booked",
        "checked_in",
        "cancelled",
        name="appointment_status",
    )
    staff_role = sa.Enum("staff", "admin", name="staff_role")

    op.create_table(
        "service_cache",
        sa.Column(
            "antrian_service_id",
            sa.Integer(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("antrian_service_id"),
    )
    op.create_table(
        "daily_quota",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("antrian_service_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("booked_count", sa.Integer(), nullable=False),
        sa.CheckConstraint("capacity >= 1", name="ck_daily_quota_capacity_positive"),
        sa.CheckConstraint(
            "booked_count >= 0", name="ck_daily_quota_booked_count_nonnegative"
        ),
        sa.ForeignKeyConstraint(
            ["antrian_service_id"],
            ["service_cache.antrian_service_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "antrian_service_id",
            "day",
            name="uq_daily_quota_service_day",
        ),
    )
    op.create_table(
        "staff_user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", staff_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_staff_user_username", "staff_user", ["username"], unique=True)
    op.create_table(
        "appointment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("booking_code", sa.String(length=64), nullable=False),
        sa.Column("access_token", sa.String(length=255), nullable=False),
        sa.Column("antrian_service_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("document_number", sa.String(length=128), nullable=False),
        sa.Column("appointment_date", sa.Date(), nullable=False),
        sa.Column("status", appointment_status, nullable=False),
        sa.Column("telegram_user_id", sa.String(length=128), nullable=True),
        sa.Column("antrian_queue_id", sa.Integer(), nullable=True),
        sa.Column("queue_number", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_appointment_access_token", "appointment", ["access_token"], unique=True
    )
    op.create_index(
        "ix_appointment_antrian_service_id", "appointment", ["antrian_service_id"]
    )
    op.create_index(
        "ix_appointment_appointment_date", "appointment", ["appointment_date"]
    )
    op.create_index(
        "ix_appointment_booking_code", "appointment", ["booking_code"], unique=True
    )
    op.create_index(
        "ix_appointment_document_number", "appointment", ["document_number"]
    )
    op.create_table(
        "check_in",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=False),
        sa.Column("staff_user_id", sa.Integer(), nullable=False),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointment.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["staff_user_id"],
            ["staff_user.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("check_in")
    op.drop_index("ix_appointment_document_number", table_name="appointment")
    op.drop_index("ix_appointment_booking_code", table_name="appointment")
    op.drop_index("ix_appointment_appointment_date", table_name="appointment")
    op.drop_index("ix_appointment_antrian_service_id", table_name="appointment")
    op.drop_index("ix_appointment_access_token", table_name="appointment")
    op.drop_table("appointment")
    op.drop_index("ix_staff_user_username", table_name="staff_user")
    op.drop_table("staff_user")
    op.drop_table("daily_quota")
    op.drop_table("service_cache")
    op.execute("DROP TYPE IF EXISTS appointment_status")
    op.execute("DROP TYPE IF EXISTS staff_role")
