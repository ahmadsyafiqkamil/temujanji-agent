"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function StaffLoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const login = await api.login(String(form.get("username")), String(form.get("password")));
      sessionStorage.setItem("staffToken", login.access_token);
      router.push("/staff/scan");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Log masuk gagal");
    }
  }

  return (
    <main className="mx-auto max-w-md p-6">
      <h1 className="text-3xl font-bold">Log masuk petugas atau pentadbir</h1>
      <form className="mt-6 space-y-4 rounded-xl bg-white p-5 shadow-sm" onSubmit={submit}>
        <input className="w-full rounded border p-3" name="username" placeholder="Nama pengguna" required />
        <input className="w-full rounded border p-3" name="password" placeholder="Kata laluan" type="password" required />
        {error && <p className="text-sm text-red-700">{error}</p>}
        <button className="w-full rounded bg-teal-700 p-3 font-semibold text-white">Log masuk</button>
      </form>
    </main>
  );
}
