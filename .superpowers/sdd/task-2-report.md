# Task 2 Report — Domain Models, Alembic, and Staff Login

## Status

DONE_WITH_CONCERNS

## Delivered

- SQLModel tables for `service_cache`, `daily_quota`, `appointment`, `check_in`,
  and `staff_user`, with appointment and staff-role enums.
- Database constraints for daily quota uniqueness, positive capacity, and
  non-negative booked counts.
- Async Alembic configuration at `backend/alembic.ini` and initial migration
  `3af89261b339_init_temujanji_models.py`.
- `POST /api/v1/auth/login`, BCrypt password hashing, HS256 JWTs containing
  `sub` and `role`, agent API-key protection, and staff/admin dependencies.
- Race-safe PostgreSQL bootstrap of `admin` using
  `ADMIN_BOOTSTRAP_PASSWORD` (default `admin123`).

## Tests and verification

- `uv run pytest -v`: 3 passed.
- `uv run ruff check backend`: passed.
- `uv run alembic -c backend/alembic.ini upgrade head --sql`: rendered valid
  PostgreSQL DDL for all tables, constraints, indexes, UUIDs, and enums.
- `uv run alembic -c backend/alembic.ini downgrade head:base --sql`: rendered
  the expected table and enum cleanup.

Authentication tests override `get_session` with a small async fake session.
This keeps login HTTP/password/JWT behavior testable without a live database;
production continues to use asyncpg/PostgreSQL.

## Concern

Docker was unavailable (`Cannot connect to the Docker daemon`), so a live
PostgreSQL `alembic upgrade head` and startup-admin insertion were not run.
The offline PostgreSQL SQL rendering succeeded, but it is not a substitute for
running the migration against an actual database.

## TDD note

The brief's initial test accepts both 401 and 404, so it passed before the
route existed. It was tightened after implementation to require 401 and a
success-path test was added for token claims.
