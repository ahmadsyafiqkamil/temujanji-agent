#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000/api/v1}"
AGENT_API_KEY="${AGENT_API_KEY:-dev-agent-key}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"
ANTRIAN_HEALTH_URL="${ANTRIAN_HEALTH_URL:-http://localhost:8001/health}"

json_field() {
  uv run python -c 'import json, sys; print(json.loads(sys.stdin.read())[sys.argv[1]])' "$1"
}

tomorrow() {
  uv run python -c 'from datetime import datetime, timedelta; from zoneinfo import ZoneInfo; print((datetime.now(ZoneInfo("Asia/Dubai")).date() + timedelta(days=1)).isoformat())'
}

echo "Checking API health..."
curl --fail --silent --show-error "${API_BASE%/api/v1}/health" >/dev/null

echo "Logging in as admin..."
login_response="$(
  curl --fail --silent --show-error \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${ADMIN_USERNAME}\",\"password\":\"${ADMIN_PASSWORD}\"}" \
    "${API_BASE}/auth/login"
)"
admin_token="$(printf '%s' "$login_response" | json_field access_token)"

echo "Syncing services..."
curl --fail --silent --show-error \
  -X POST \
  -H "Authorization: Bearer ${admin_token}" \
  "${API_BASE}/services/sync" >/dev/null

echo "Loading an active service..."
services_response="$(
  curl --fail --silent --show-error \
    -H "X-API-Key: ${AGENT_API_KEY}" \
    "${API_BASE}/services"
)"
service_id="$(
  printf '%s' "$services_response" | uv run python -c \
    'import json, sys; print(next(service["antrian_service_id"] for service in json.load(sys.stdin) if service["is_active"]))'
)"
appointment_date="$(tomorrow)"
smoke_document="SMOKE-$(date +%s)"

echo "Opening quota for ${appointment_date}..."
quotas_response="$(
  curl --fail --silent --show-error \
    -H "Authorization: Bearer ${admin_token}" \
    "${API_BASE}/admin/quotas"
)"
quota_id="$(
  printf '%s' "$quotas_response" | uv run python -c \
    'import json, sys; service_id, day = sys.argv[1:]; print(next((str(quota["id"]) for quota in json.load(sys.stdin) if str(quota["antrian_service_id"]) == service_id and quota["day"] == day), ""))' \
    "$service_id" "$appointment_date"
)"
if [[ -n "$quota_id" ]]; then
  curl --fail --silent --show-error \
    -X PATCH \
    -H "Authorization: Bearer ${admin_token}" \
    -H "Content-Type: application/json" \
    -d '{"capacity":10}' \
    "${API_BASE}/admin/quotas/${quota_id}" >/dev/null
else
  curl --fail --silent --show-error \
    -X POST \
    -H "Authorization: Bearer ${admin_token}" \
    -H "Content-Type: application/json" \
    -d "{\"antrian_service_id\":${service_id},\"day\":\"${appointment_date}\",\"capacity\":10}" \
    "${API_BASE}/admin/quotas" >/dev/null
fi

echo "Creating appointment..."
appointment_response="$(
  curl --fail --silent --show-error \
    -X POST \
    -H "X-API-Key: ${AGENT_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"antrian_service_id\":${service_id},\"full_name\":\"Smoke Test\",\"document_number\":\"${smoke_document}\",\"appointment_date\":\"${appointment_date}\"}" \
    "${API_BASE}/appointments"
)"
access_token="$(printf '%s' "$appointment_response" | json_field access_token)"

echo "Reading appointment by magic token..."
token_response="$(
  curl --fail --silent --show-error \
    "${API_BASE}/appointments/by-token/${access_token}"
)"
qr_payload="$(printf '%s' "$token_response" | json_field qr_payload)"

if curl --fail --silent --show-error --max-time 3 "$ANTRIAN_HEALTH_URL" >/dev/null; then
  echo "Checking in appointment..."
  curl --fail --silent --show-error \
    -X POST \
    -H "Authorization: Bearer ${admin_token}" \
    -H "Content-Type: application/json" \
    -d "{\"qr_payload\":\"${qr_payload}\"}" \
    "${API_BASE}/check-in"
  echo
else
  echo "Skipping check-in: Antrian is unavailable at ${ANTRIAN_HEALTH_URL}."
fi

echo "Smoke E2E completed."
