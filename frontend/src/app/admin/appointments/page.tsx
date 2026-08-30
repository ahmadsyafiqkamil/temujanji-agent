"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type Appointment } from "@/lib/api";

export default function AdminAppointmentsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [message, setMessage] = useState("Loading…");
  useEffect(() => {
    api.appointments(sessionStorage.getItem("adminToken") ?? "").then((items) => {
      setAppointments(items);
      setMessage("");
    }).catch((error: Error) => {
      setMessage(
        error.message.includes("(404)")
          ? "Appointments list is not available from the API yet."
          : error.message,
      );
    });
  }, []);
  return <main className="mx-auto max-w-3xl p-6"><nav className="mb-6 flex justify-between"><h1 className="text-3xl font-bold">Appointments</h1><Link className="text-teal-700 underline" href="/admin/quotas">Quotas</Link></nav>{message ? <p>{message}</p> : <table className="w-full bg-white text-left"><thead><tr><th>Code</th><th>Name</th><th>Date</th><th>Status</th></tr></thead><tbody>{appointments.map((item) => <tr className="border-t" key={item.id}><td>{item.booking_code}</td><td>{item.full_name}</td><td>{item.appointment_date}</td><td>{item.status}</td></tr>)}</tbody></table>}</main>;
}
