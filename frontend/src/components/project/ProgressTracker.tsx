"use client";
import { motion } from "framer-motion";
import { AlertTriangle, Check, Circle, MinusCircle, RotateCcw } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";
import { ErrorBox, Spinner } from "../ui";

const LABEL: Record<string, string> = { pending: "En attente", running: "En cours", done: "Terminée", failed: "Échec", skipped: "Ignorée" };

export default function ProgressTracker({ project, reload }: { project: Project; reload: () => Promise<unknown> }) {
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const locked = project.status === "queued" || project.status === "processing";

  async function retry(step: string) {
    setBusy(step); setError("");
    try { await api(`/api/projects/${project.id}/retry`, { body: { step } }); await reload(); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(""); }
  }

  return (
    <div className="card p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-display text-lg font-semibold text-white">Progression de l&apos;analyse</h2>
        {project.status === "completed" && <span className="chip border-emerald-400/30 text-emerald-200"><Check className="h-3 w-3" />Analyse terminée</span>}
      </div>
      <ol className="space-y-1">
        {project.steps.map((s) => (
          <li key={s.key} className="rounded-xl px-2 py-2.5">
            <div className="flex items-center gap-3">
              <span className="grid h-7 w-7 shrink-0 place-items-center">
                {s.status === "done" && <span className="grid h-6 w-6 place-items-center rounded-full bg-emerald-400/15"><Check className="h-3.5 w-3.5 text-emerald-300" /></span>}
                {s.status === "running" && <Spinner className="h-5 w-5 text-brand-cyan" />}
                {s.status === "failed" && <AlertTriangle className="h-5 w-5 text-amber-300" />}
                {s.status === "skipped" && <MinusCircle className="h-5 w-5 text-slate-500" />}
                {s.status === "pending" && <Circle className="h-4 w-4 text-slate-600" />}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                  <p className={`text-sm font-medium ${s.status === "pending" ? "text-slate-500" : "text-white"}`}>{s.label}</p>
                  <p className="text-xs text-slate-400">
                    {LABEL[s.status]}{s.status === "running" && s.progress > 0 ? ` · ${Math.round(s.progress * 100)} %` : ""}
                  </p>
                </div>
                {s.status === "running" && (
                  <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/10">
                    <motion.div className="h-full bg-brand-gradient" animate={{ width: `${Math.max(s.progress * 100, 3)}%` }} transition={{ duration: 0.4 }} />
                  </div>
                )}
                {s.message && s.status !== "failed" && <p className="mt-0.5 text-xs text-slate-400">{s.message}</p>}
              </div>
              {!locked && s.key !== "import" && (s.status === "done" || s.status === "skipped") && (
                <button onClick={() => retry(s.key)} disabled={!!busy} title="Relancer à partir de cette étape" aria-label={`Relancer à partir de l'étape ${s.label}`}
                  className="rounded-lg p-1.5 text-slate-500 hover:bg-white/10 hover:text-white">
                  {busy === s.key ? <Spinner className="h-3.5 w-3.5" /> : <RotateCcw className="h-3.5 w-3.5" />}
                </button>
              )}
            </div>
            {s.status === "failed" && (
              <div className="ml-10 mt-2">
                <ErrorBox message={s.error || "Cette étape a échoué."}>
                  <button className="btn-ghost py-1.5" disabled={!!busy || locked} onClick={() => retry(s.key)}>
                    {busy === s.key ? <Spinner /> : <RotateCcw className="h-4 w-4" />}Relancer cette étape
                  </button>
                </ErrorBox>
              </div>
            )}
          </li>
        ))}
      </ol>
      {!locked && project.status !== "failed" && project.steps.some((s) => s.status === "pending") && project.status !== "uploaded" && (
        <button className="btn-ghost mt-3" disabled={!!busy} onClick={() => retry(project.steps.find((s) => s.status === "pending")!.key)}>
          <RotateCcw className="h-4 w-4" />Reprendre l&apos;analyse
        </button>
      )}
      {error && <div className="mt-3"><ErrorBox message={error} /></div>}
    </div>
  );
}
