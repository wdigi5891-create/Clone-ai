"use client";
import { Play } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { bytes, duration } from "@/lib/format";
import { ErrorBox, Spinner } from "../ui";
import ProgressTracker from "./ProgressTracker";
import type { TabProps } from "./shared";

export default function OverviewTab({ project, reload }: TabProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const rows: [string, string][] = [
    ["Durée totale", duration(project.duration)],
    ["Résolution", `${project.width} × ${project.height}`],
    ["Fréquence d'images", `${project.fps} i/s`],
    ["Format", (project.original_filename.split(".").pop() || project.format.split(",")[0] || "—").toUpperCase()],
    ["Orientation", project.orientation || "—"],
    ["Nombre de scènes", project.scenes.length ? String(project.scenes.length) : "—"],
    ["Nombre de personnages", project.steps.find((s) => s.key === "characters")?.status === "done" ? String(project.characters.length) : "—"],
    ["Langue parlée", project.language || (project.has_audio ? "—" : "Pas de piste audio")],
    ["Découpage", project.split_mode === "smart" ? "Intelligent" : `Fixe · ${project.split_seconds} s`],
    ["Taille du fichier", bytes(project.file_size)],
  ];

  async function start() {
    setBusy(true); setError("");
    try {
      await api(`/api/projects/${project.id}/analyze`, { body: { split_mode: project.split_mode, split_seconds: project.split_seconds } });
      await reload();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
      <div className="space-y-6">
        {project.status === "uploaded" && (
          <div className="card flex flex-wrap items-center justify-between gap-3 p-5">
            <p className="text-sm text-slate-300">La vidéo est importée mais l&apos;analyse n&apos;a pas encore été lancée.</p>
            <button className="btn-primary" disabled={busy} onClick={start}>{busy ? <Spinner /> : <Play className="h-4 w-4" />}Lancer l&apos;analyse</button>
          </div>
        )}
        {error && <ErrorBox message={error} />}
        <ProgressTracker project={project} reload={reload} />
      </div>
      <div className="space-y-6">
        {project.video_url && (
          <div className="card overflow-hidden">
            <video src={project.video_url} controls playsInline preload="metadata" poster={project.thumbnail_url || undefined} className="max-h-[380px] w-full bg-black" />
          </div>
        )}
        <div className="card p-5">
          <h2 className="mb-3 font-display text-lg font-semibold text-white">Analyse générale</h2>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            {rows.map(([k, v]) => (
              <div key={k}><dt className="text-xs text-slate-500">{k}</dt><dd className="mt-0.5 font-medium text-slate-100">{v}</dd></div>
            ))}
          </dl>
          {(project.summary || project.mood || project.visual_style) && (
            <div className="mt-5 space-y-3 border-t border-white/10 pt-4 text-sm">
              {([["Résumé", project.summary], ["Ambiance générale", project.mood], ["Style visuel", project.visual_style]] as const).map(([k, v]) => v && (
                <div key={k}><p className="text-xs text-slate-500">{k}</p><p className="mt-0.5 leading-relaxed text-slate-200">{v}</p></div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
