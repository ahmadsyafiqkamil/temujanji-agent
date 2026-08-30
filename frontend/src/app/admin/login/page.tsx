"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function AdminLoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      const login = await api.login(String(form.get("username")), String(form.get("password")));
      if (login.role !== "admin") throw new Error("This account is not an administrator.");
      sessionStorage.setItem("adminToken", login.access_token);
      router.push("/admin/quotas");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Login failed");
    }
  }
  return <main className="mx-auto max-w-md p-6"><h1 className="text-3xl font-bold">Admin login</h1><form className="mt-6 space-y-4 rounded-xl bg-white p-5 shadow-sm" onSubmit={submit}><input className="w-full rounded border p-3" name="username" placeholder="Username" required /><input className="w-full rounded border p-3" name="password" type="password" placeholder="Password" required />{error && <p className="text-sm text-red-700">{error}</p>}<button className="w-full rounded bg-teal-700 p-3 font-semibold text-white">Log in</button></form></main>;
}
