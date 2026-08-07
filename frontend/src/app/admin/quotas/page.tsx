"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api, type Quota } from "@/lib/api";

export default function QuotasPage() {
  const [quotas, setQuotas] = useState<Quota[]>([]);
  const [message, setMessage] = useState("");
  const token = () => sessionStorage.getItem("adminToken") ?? "";
  const refresh = () => api.quotas(token()).then(setQuotas).catch((error: Error) => setMessage(error.message));
  useEffect(() => {
    void refresh();
  }, []);
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try { await api.createQuota(token(), { antrian_service_id: Number(form.get("service")), day: String(form.get("day")), capacity: Number(form.get("capacity")) }); event.currentTarget.reset(); refresh(); } catch (error) { setMessage(error instanceof Error ? error.message : "Gagal"); }
  }
  return <main className="mx-auto max-w-3xl p-6"><nav className="mb-6 flex justify-between"><h1 className="text-3xl font-bold">Kuota harian</h1><Link className="text-teal-700 underline" href="/admin/appointments">Temujanji</Link></nav><div className="flex gap-2"><button className="rounded border px-3 py-2" onClick={() => api.syncServices(token()).then((r) => setMessage(`${r.synced} servis diselaraskan`)).catch((e: Error) => setMessage(e.message))}>Selaras servis</button><button className="rounded border px-3 py-2" onClick={refresh}>Muat semula</button></div><form className="mt-4 grid gap-2 rounded bg-white p-4 sm:grid-cols-4" onSubmit={create}><input className="rounded border p-2" name="service" type="number" placeholder="ID servis" required /><input className="rounded border p-2" name="day" type="date" required /><input className="rounded border p-2" name="capacity" type="number" min="1" placeholder="Kapasiti" required /><button className="rounded bg-teal-700 p-2 font-semibold text-white">Tambah</button></form>{message && <p className="mt-3 text-sm">{message}</p>}<div className="mt-6 overflow-x-auto"><table className="w-full bg-white text-left"><thead><tr><th>Tarikh</th><th>Servis</th><th>Kuota</th><th>Tempahan</th></tr></thead><tbody>{quotas.map((quota) => <tr className="border-t" key={quota.id}><td>{quota.day}</td><td>{quota.antrian_service_id}</td><td><input className="w-20 rounded border p-1" defaultValue={quota.capacity} type="number" min="1" onBlur={(event) => api.updateQuota(token(), quota.id, Number(event.target.value)).then(refresh).catch((error: Error) => setMessage(error.message))} /></td><td>{quota.booked_count}</td></tr>)}</tbody></table></div></main>;
}
