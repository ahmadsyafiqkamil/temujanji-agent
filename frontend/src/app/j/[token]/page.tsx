"use client";

import { useParams } from "next/navigation";
import { QRCodeSVG } from "qrcode.react";
import { useEffect, useState } from "react";
import { api, type Appointment } from "@/lib/api";

function statusLabel(status: string): string {
  switch (status) {
    case "booked":
      return "Terjadwal";
    case "cancelled":
      return "Dibatalkan";
    case "checked_in":
      return "Sudah check-in";
    default:
      return status;
  }
}

function loadErrorMessage(reason: Error): string {
  const message = reason.message;
  if (
    message === "Not found" ||
    message === "Appointment not found" ||
    /404/.test(message)
  ) {
    return "Tautan janji temu tidak valid atau sudah tidak berlaku.";
  }
  return "Gagal memuat janji temu. Silakan coba lagi.";
}

export default function MagicLinkPage() {
  const { token } = useParams<{ token: string }>();
  const [appointment, setAppointment] = useState<Appointment>();
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .appointmentByToken(token)
      .then(setAppointment)
      .catch((reason: Error) => setError(loadErrorMessage(reason)));
  }, [token]);

  if (error) return <main className="p-8 text-red-700">{error}</main>;
  if (!appointment) return <main className="p-8">Memuat janji temu…</main>;

  return (
    <main className="mx-auto max-w-md p-6">
      <p className="text-sm font-semibold text-teal-700">Janji temu KJRI</p>
      <h1 className="mt-2 text-3xl font-bold">{appointment.booking_code}</h1>
      <dl className="mt-6 space-y-3 rounded-xl bg-white p-5 shadow-sm">
        <div><dt className="text-sm text-slate-500">Nama</dt><dd className="font-semibold">{appointment.full_name}</dd></div>
        <div><dt className="text-sm text-slate-500">Tanggal</dt><dd>{appointment.appointment_date}</dd></div>
        <div><dt className="text-sm text-slate-500">Status</dt><dd>{statusLabel(appointment.status)}</dd></div>
      </dl>
      <div className="mt-6 flex justify-center rounded-xl bg-white p-6 shadow-sm">
        <QRCodeSVG value={appointment.qr_payload} size={240} includeMargin />
      </div>
      <p className="mt-4 text-center text-sm text-slate-600">
        Tunjukkan kode QR ini kepada petugas saat check-in.
      </p>
    </main>
  );
}
