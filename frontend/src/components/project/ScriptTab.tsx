"use client";
import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { timecode } from "@/lib/format";
import type { Dialogue } from "@/lib/types";
import { Empty, ErrorBox, Spinner } from "../ui";
import { EditableText, type TabProps } from "./shared";

const META: [keyof Dialogue & string, string][] = [["tone", "Ton de la voix"], ["emotion", "Émotion"], ["intensity", "Intensité"], ["pace", "Rythme de parole"]];

export default function ScriptTab({ project, reload }: TabProps) {
  const [error, setError] = useState("");
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState({ start: "0", end: "2", text: "" });
  const [busy, setBusy] = useState(false);
  const step = project.steps.find((s) => s.key === "transcription");

  async function patch(d: Dialogue, body: Record<string, unknown>) {
    await api(`/api/projects/${project.id}/dialogues/${d.id}`, { method: "PATCH", body });
    await reload();
  }
  async function remove(d: Dialogue) {
    if (!window.confirm("Supprimer cette réplique ?")) return;
    try { await api(`/api/projects/${project.id}/dialogues/${d.id}`, { method: "DELETE" }); await reload(); }
    catch (e) { setError((e as Error).message); }
  }
  async function add() {
    setBusy(true); setError("");
    try {
      await api(`/api/projects/${project.id}/dialogues`, { body: { start: Number(draft.start), end: Number(draft.end), text: draft.text } });
      setAdding(false); setDraft({ start: "0", end: "2", text: "" });
      await reload();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-sm text-slate-400">
          Texte réellement transcrit depuis la piste audio{project.language ? ` (langue détectée : ${project.language})` : ""}. Les passages inaudibles sont signalés, jamais inventés. Ton, émotion, intensité et rythme sont des estimations ; l&apos;orateur n&apos;est attribué que s&apos;il est suffisamment certain. Tout est modifiable.
        </p>
        <button className="btn-ghost" onClick={() => setAdding(!adding)} disabled={!project.scenes.length}><Plus className="h-4 w-4" />Ajouter une réplique</button>
      </div>
      {error && <ErrorBox message={error} />}
      {adding && (
        <div className="card grid gap-3 p-4 sm:grid-cols-[110px_110px_1fr_auto] sm:items-end">
          <div><label className="label" htmlFor="ds">Début (s)</label><input id="ds" type="number" min={0} step={0.1} className="input" value={draft.start} onChange={(e) => setDraft({ ...draft, start: e.target.value })} /></div>
          <div><label className="label" htmlFor="de">Fin (s)</label><input id="de" type="number" min={0} step={0.1} className="input" value={draft.end} onChange={(e) => setDraft({ ...draft, end: e.target.value })} /></div>
          <div><label className="label" htmlFor="dt">Texte</label><input id="dt" className="input" value={draft.text} onChange={(e) => setDraft({ ...draft, text: e.target.value })} /></div>
          <button className="btn-primary" disabled={busy || !draft.text.trim()} onClick={add}>{busy && <Spinner />}Ajouter</button>
        </div>
      )}
      {project.dialogues.length === 0 ? (
        <Empty title={step?.status === "skipped" ? "Pas de transcription" : step?.status === "done" ? "Aucune parole détectée" : "Les dialogues apparaîtront ici"}>
          {step?.status === "skipped" ? step.message : step?.status === "done" ? "La piste audio ne contient pas de parole reconnaissable." : "La transcription est produite par l'étape « Transcription audio »."}
        </Empty>
      ) : (
        <ol className="space-y-3">
          {project.dialogues.map((d) => (
            <li key={d.id} className="card p-4">
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="chip font-mono">{timecode(d.start)} → {timecode(d.end)}</span>
                {d.scene_index && <span className="chip">Scène {d.scene_index}</span>}
                {d.language && <span className="chip">Langue : {d.language}</span>}
                {d.edited && <span className="chip border-brand-cyan/40 text-cyan-200">Modifié</span>}
                <label className="sr-only" htmlFor={`sp-${d.id}`}>Personnage qui parle</label>
                <select id={`sp-${d.id}`} className="input ml-auto w-auto py-1.5 text-xs" value={d.character_index ?? ""}
                  onChange={(e) => patch(d, { character_index: e.target.value ? Number(e.target.value) : null }).catch((er: Error) => setError(er.message))}>
                  <option value="">Orateur non attribué</option>
                  {project.characters.map((c) => <option key={c.id} value={c.index}>{c.label}</option>)}
                </select>
                <button onClick={() => remove(d)} aria-label="Supprimer la réplique" title="Supprimer" className="rounded-lg p-1.5 text-slate-500 hover:bg-red-500/15 hover:text-red-300"><Trash2 className="h-4 w-4" /></button>
              </div>
              <div className="mt-3 text-base text-white">
                <EditableText value={d.text} placeholder="Dialogue non identifiable — cliquez pour saisir le texte si vous le connaissez" onSave={(v) => patch(d, { text: v })} />
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-4">
                {META.map(([key, label]) => (
                  <div key={key} className="min-w-0">
                    <dt className="label mb-0">{label}</dt>
                    <dd><EditableText multiline={false} value={String(d[key] || "")} onSave={(v) => patch(d, { [key]: v })} className="text-slate-300" /></dd>
                  </div>
                ))}
              </dl>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
