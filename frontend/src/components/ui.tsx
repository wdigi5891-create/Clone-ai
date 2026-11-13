"use client";
import { AlertTriangle, Check, Copy, Loader2, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { STATUS_LABELS } from "@/lib/format";

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="flex items-center gap-2.5">
      <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-gradient shadow-glow">
        <Sparkles className="h-5 w-5 text-white" />
      </span>
      <span className="font-display text-[15px] font-bold tracking-wide text-white">
        AI VIDEO <span className="gradient-text">CLONER</span>
      </span>
    </Link>
  );
}

export function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return <Loader2 className={`${className} animate-spin`} />;
}

export function ErrorBox({ message, children }: { message: string; children?: React.ReactNode }) {
  return (
    <div role="alert" className="flex gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-3.5 text-sm text-red-100">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-300" />
      <div className="min-w-0 space-y-2"><p>{message}</p>{children}</div>
    </div>
  );
}

const STATUS_STYLE: Record<string, string> = {
  uploaded: "border-slate-500/30 bg-slate-500/10 text-slate-300",
  queued: "border-blue-400/30 bg-blue-400/10 text-blue-200",
  processing: "border-violet-400/30 bg-violet-400/10 text-violet-200",
  completed: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  failed: "border-amber-400/30 bg-amber-400/10 text-amber-200",
};
export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 text-xs font-medium ${STATUS_STYLE[status] || STATUS_STYLE.uploaded}`}>
      {(status === "processing" || status === "queued") && <Spinner className="h-3 w-3" />}
      {STATUS_LABELS[status] || status}
    </span>
  );
}

export function CopyButton({ text, label = "Copier", className = "btn-ghost" }: { text: string; label?: string; className?: string }) {
  const [state, setState] = useState<"idle" | "ok" | "error">("idle");
  useEffect(() => {
    if (state === "idle") return;
    const t = setTimeout(() => setState("idle"), 1800);
    return () => clearTimeout(t);
  }, [state]);
  return (
    <button
      type="button"
      className={className}
      disabled={!text}
      onClick={() => navigator.clipboard.writeText(text).then(() => setState("ok"), () => setState("error"))}
    >
      {state === "ok" ? <Check className="h-4 w-4 text-emerald-300" /> : <Copy className="h-4 w-4" />}
      {state === "ok" ? "Copié" : state === "error" ? "Copie impossible" : label}
    </button>
  );
}

export function Empty({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="card grid place-items-center px-6 py-14 text-center">
      <p className="font-display text-lg font-semibold text-white">{title}</p>
      {children && <div className="mt-2 max-w-md text-sm text-slate-400">{children}</div>}
    </div>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="font-display text-2xl font-bold text-white sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}
