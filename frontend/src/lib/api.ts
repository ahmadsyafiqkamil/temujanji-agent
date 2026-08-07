const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Appointment = {
  id: string;
  booking_code: string;
  antrian_service_id: number;
  full_name: string;
  appointment_date: string;
  status: string;
  qr_payload: string;
};

export type LoginResponse = {
  access_token: string;
  role: "admin" | "staff";
};

export type CheckInResponse = {
  booking_code: string;
  antrian_service_id: number;
  full_name: string;
  appointment_date: string;
  status: string;
  queue_number: string;
};

export type Quota = {
  id: number;
  antrian_service_id: number;
  day: string;
  capacity: number;
  booked_count: number;
};

type ApiOptions = RequestInit & { token?: string };

async function request<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { token, headers, ...init } = options;
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  appointmentByToken: (token: string) =>
    request<Appointment>(`/api/v1/appointments/by-token/${encodeURIComponent(token)}`),
  login: (username: string, password: string) =>
    request<LoginResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  checkIn: (token: string, qrPayload: string) =>
    request<CheckInResponse>("/api/v1/check-in", {
      method: "POST",
      token,
      body: JSON.stringify({ qr_payload: qrPayload }),
    }),
  quotas: (token: string) => request<Quota[]>("/api/v1/admin/quotas", { token }),
  createQuota: (token: string, quota: Omit<Quota, "id" | "booked_count">) =>
    request<Quota>("/api/v1/admin/quotas", {
      method: "POST",
      token,
      body: JSON.stringify(quota),
    }),
  updateQuota: (token: string, quotaId: number, capacity: number) =>
    request<Quota>(`/api/v1/admin/quotas/${quotaId}`, {
      method: "PATCH",
      token,
      body: JSON.stringify({ capacity }),
    }),
  syncServices: (token: string) =>
    request<{ synced: number }>("/api/v1/services/sync", {
      method: "POST",
      token,
    }),
  appointments: (token: string) =>
    request<Appointment[]>("/api/v1/admin/appointments", { token }),
};
