"use client";

import { useParams } from "next/navigation";
import { QRCodeSVG } from "qrcode.react";
import { useEffect, useState } from "react";
import { api, type Appointment } from "@/lib/api";

export default function MagicLinkPage() {
  const { token } = useParams<{ token: string }>();
  const [appointment, setAppointment] = useState<Appointment>();
  const [error, setError] = useState("");

  useEffect(() => {
    api.appointmentByToken(token).then(setAppointment).catch((reason: Error) => setError(reason.message));
  }, [token]);

  if (error) return <main className="p-8 text-red-700">{error}</main>;
  if (!appointment) return <main className="p-8">Loading appointment…</main>;

  return (
    <main className="mx-auto max-w-md p-6">
      <p className="text-sm font-semibold text-teal-700">KJRI APPOINTMENT</p>
      <h1 className="mt-2 text-3xl font-bold">{appointment.booking_code}</h1>
      <dl className="mt-6 space-y-3 rounded-xl bg-white p-5 shadow-sm">
        <div><dt className="text-sm text-slate-500">Name</dt><dd className="font-semibold">{appointment.full_name}</dd></div>
        <div><dt className="text-sm text-slate-500">Date</dt><dd>{appointment.appointment_date}</dd></div>
        <div><dt className="text-sm text-slate-500">Status</dt><dd className="capitalize">{appointment.status}</dd></div>
      </dl>
      <div className="mt-6 flex justify-center rounded-xl bg-white p-6 shadow-sm">
        <QRCodeSVG value={appointment.qr_payload} size={240} includeMargin />
      </div>
      <p className="mt-4 text-center text-sm text-slate-600">Show this QR code to staff at check-in.</p>
    </main>
  );
}
