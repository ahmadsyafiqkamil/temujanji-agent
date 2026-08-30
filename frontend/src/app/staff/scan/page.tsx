"use client";

import { Html5Qrcode } from "html5-qrcode";
import { useEffect, useRef, useState } from "react";
import { api, type CheckInResponse } from "@/lib/api";

export default function StaffScanPage() {
  const scanner = useRef<Html5Qrcode | null>(null);
  const [payload, setPayload] = useState("");
  const [result, setResult] = useState<CheckInResponse>();
  const [error, setError] = useState("");

  async function checkIn(value: string) {
    try {
      const token = sessionStorage.getItem("staffToken");
      if (!token) throw new Error("Please log in as staff.");
      setResult(await api.checkIn(token, value));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Check-in failed");
    }
  }

  useEffect(() => () => { scanner.current?.clear(); }, []);

  async function startScanner() {
    if (scanner.current) return;
    const instance = new Html5Qrcode("qr-reader");
    scanner.current = instance;
    await instance.start({ facingMode: "environment" }, { fps: 10, qrbox: 250 }, async (text) => {
      await instance.stop();
      scanner.current = null;
      await checkIn(text);
    }, () => undefined);
  }

  return (
    <main className="mx-auto max-w-md p-6">
      <h1 className="text-3xl font-bold">Check-in scan</h1>
      <div id="qr-reader" className="mt-6 overflow-hidden rounded-xl bg-black" />
      <button className="mt-4 w-full rounded bg-teal-700 p-3 font-semibold text-white" onClick={startScanner}>Open camera</button>
      <form className="mt-4 flex gap-2" onSubmit={(event) => { event.preventDefault(); void checkIn(payload); }}>
        <input className="min-w-0 flex-1 rounded border p-3" value={payload} onChange={(event) => setPayload(event.target.value)} placeholder="Paste QR payload" required />
        <button className="rounded border px-4">Submit</button>
      </form>
      {error && <p className="mt-4 text-red-700">{error}</p>}
      {result && <section className="mt-6 rounded-xl bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">Queue number</p><p className="text-4xl font-bold text-teal-700">{result.queue_number}</p><p className="mt-2">{result.full_name} · {result.booking_code}</p></section>}
    </main>
  );
}
