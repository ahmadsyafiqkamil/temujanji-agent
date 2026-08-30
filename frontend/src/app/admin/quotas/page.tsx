"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { api, type Quota, type Service } from "@/lib/api";

export default function QuotasPage() {
  const [quotas, setQuotas] = useState<Quota[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [message, setMessage] = useState("");
  const token = () => sessionStorage.getItem("adminToken") ?? "";

  const serviceName = (id: number) =>
    services.find((service) => service.antrian_service_id === id)?.name ?? `Service ${id}`;

  const refresh = async () => {
    try {
      const [nextQuotas, nextServices] = await Promise.all([
        api.quotas(token()),
        api.adminServices(token()),
      ]);
      setQuotas(nextQuotas);
      setServices(nextServices);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed to load");
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api.createQuota(token(), {
        antrian_service_id: Number(form.get("service")),
        day: String(form.get("day")),
        capacity: Number(form.get("capacity")),
      });
      event.currentTarget.reset();
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Failed");
    }
  }

  return (
    <main className="mx-auto max-w-3xl p-6">
      <nav className="mb-6 flex justify-between">
        <h1 className="text-3xl font-bold">Daily quotas</h1>
        <Link className="text-teal-700 underline" href="/admin/appointments">
          Appointments
        </Link>
      </nav>
      <div className="flex gap-2">
        <button
          className="rounded border px-3 py-2"
          onClick={() =>
            api
              .syncServices(token())
              .then(async (result) => {
                setMessage(`${result.synced} services synced`);
                await refresh();
              })
              .catch((error: Error) => setMessage(error.message))
          }
        >
          Sync services
        </button>
        <button className="rounded border px-3 py-2" onClick={() => void refresh()}>
          Refresh
        </button>
      </div>
      <form className="mt-4 grid gap-2 rounded bg-white p-4 sm:grid-cols-4" onSubmit={create}>
        <select className="rounded border p-2" name="service" required defaultValue="">
          <option value="" disabled>
            Select service
          </option>
          {services.map((service) => (
            <option key={service.antrian_service_id} value={service.antrian_service_id}>
              {service.name} (ID {service.antrian_service_id})
            </option>
          ))}
        </select>
        <input className="rounded border p-2" name="day" type="date" required />
        <input
          className="rounded border p-2"
          name="capacity"
          type="number"
          min="1"
          placeholder="Capacity"
          required
        />
        <button className="rounded bg-teal-700 p-2 font-semibold text-white">Add</button>
      </form>
      {message && <p className="mt-3 text-sm">{message}</p>}
      <div className="mt-6 overflow-x-auto">
        <table className="w-full bg-white text-left">
          <thead>
            <tr>
              <th>Date</th>
              <th>Service</th>
              <th>Quota</th>
              <th>Booked</th>
            </tr>
          </thead>
          <tbody>
            {quotas.map((quota) => (
              <tr className="border-t" key={quota.id}>
                <td>{quota.day}</td>
                <td>
                  {serviceName(quota.antrian_service_id)}{" "}
                  <span className="text-slate-500">(ID {quota.antrian_service_id})</span>
                </td>
                <td>
                  <input
                    className="w-20 rounded border p-1"
                    defaultValue={quota.capacity}
                    type="number"
                    min="1"
                    onBlur={(event) =>
                      api
                        .updateQuota(token(), quota.id, Number(event.target.value))
                        .then(() => refresh())
                        .catch((error: Error) => setMessage(error.message))
                    }
                  />
                </td>
                <td>{quota.booked_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
