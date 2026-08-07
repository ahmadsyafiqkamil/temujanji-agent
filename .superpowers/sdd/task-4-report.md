# Task 4 Report — Appointments API

## Status

Complete. Added agent-key-protected appointment creation and cancellation plus a public magic-token lookup endpoint.

## Delivered

- `POST /api/v1/appointments`: validates Asia/Dubai date, active service, quota availability, and active-booking duplicates; locks the quota row before incrementing.
- `GET /api/v1/appointments/by-token/{token}`: returns user-safe appointment details and signed QR payload without exposing document numbers.
- `POST /api/v1/appointments/{id}/cancel`: locks the appointment and quota rows, permits only `booked` state, then decrements the quota atomically.
- High-entropy magic tokens, eight-hex booking codes, and HMAC QR payload generation.

## Verification

`uv run pytest backend/tests -v && uv run ruff check backend/app backend/tests`

Result: 17 passed; Ruff passed. Existing third-party deprecation warnings remain.

## Review notes

- PostgreSQL row locks are implemented with `SELECT ... FOR UPDATE`; the in-memory session double cannot demonstrate real concurrent locking, so a PostgreSQL integration concurrency test remains advisable.
- The design spec allows token cancellation, but this task explicitly required the agent API key for create/cancel; cancellation therefore uses the agent key only.
