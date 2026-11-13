"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { ErrorBox, Logo, Spinner } from "./ui";

function Form({ mode }: { mode: "login" | "register" }) {
  const { user, login, register } = useAuth();
  const router = useRouter();
  const next = useSearchParams().get("next") || "/dashboard";
  const [form, setForm] = useState({ name: "", email: "", password: "", accept: false });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const isRegister = mode === "register";

  useEffect(() => { if (user) router.replace(next.startsWith("/") ? next : "/dashboard"); }, [user, router, next]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (isRegister) await register({ email: form.email, password: form.password, name: form.name, accept_terms: form.accept });
      else await login(form.email, form.password);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen place-items-center px-4 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 flex justify-center"><Logo /></div>
        <form onSubmit={submit} className="card space-y-4 p-6 sm:p-8">
          <h1 className="font-display text-2xl font-bold text-white">{isRegister ? "Créer un compte" : "Connexion"}</h1>
          {isRegister && (
            <div><label className="label" htmlFor="name">Nom</label>
              <input id="name" className="input" autoComplete="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
          )}
          <div><label className="label" htmlFor="email">E-mail</label>
            <input id="email" type="email" required className="input" autoComplete="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
          <div><label className="label" htmlFor="password">Mot de passe</label>
            <input id="password" type="password" required minLength={isRegister ? 8 : 1} className="input" autoComplete={isRegister ? "new-password" : "current-password"}
              value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            {isRegister && <p className="mt-1.5 text-xs text-slate-500">8 caractères minimum.</p>}</div>
          {isRegister && (
            <label className="flex items-start gap-2.5 text-sm text-slate-300">
              <input type="checkbox" required checked={form.accept} onChange={(e) => setForm({ ...form, accept: e.target.checked })} className="mt-1 accent-violet-500" />
              <span>J&apos;accepte la <Link href="/privacy" target="_blank" className="text-brand-cyan underline">politique de confidentialité</Link> et je m&apos;engage à n&apos;importer que des vidéos dont je détiens les droits.</span>
            </label>
          )}
          {error && <ErrorBox message={error} />}
          <button className="btn-primary w-full py-3" disabled={busy}>{busy && <Spinner />}{isRegister ? "Créer mon compte" : "Se connecter"}</button>
          <p className="text-center text-sm text-slate-400">
            {isRegister ? "Déjà inscrit ? " : "Pas encore de compte ? "}
            <Link href={isRegister ? "/login" : "/register"} className="font-medium text-brand-cyan hover:underline">{isRegister ? "Se connecter" : "Créer un compte"}</Link>
          </p>
        </form>
      </div>
    </div>
  );
}

export default function AuthForm({ mode }: { mode: "login" | "register" }) {
  return <Suspense><Form mode={mode} /></Suspense>;
}
