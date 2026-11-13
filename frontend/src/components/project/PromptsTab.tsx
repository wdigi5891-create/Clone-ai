"use client";
import { CheckSquare, Layers, RefreshCw, Square, Wand2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { timecode } from "@/lib/format";
import type { Meta, Scene } from "@/lib/types";
import { CopyButton, Empty, ErrorBox, Spinner } from "../ui";
import { EditableText, type TabProps } from "./shared";

const EDITABLE: [string, string][] = [
  ["scene_description", "1. Scene description"], ["environment", "3. Environment"], ["action_and_movement", "4. Action and movement"],
  ["camera_direction", "5. Camera direction"], ["lighting", "6. Lighting"], ["facial_expressions", "7. Facial expressions"],
  ["voice_direction", "9. Voice direction"], ["sound_design", "10. Sound design"], ["visual_style", "11. Visual style"], ["continuity", "13. Continuity"],
];

export default function PromptsTab({ project, setProject, reload, running }: TabProps) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [language, setLanguage] = useState(project.prompt_language || "en");
  const [style, setStyle] = useState(project.prompt_style || "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  useEffect(() => { api<Meta>("/api/meta").then(setMeta).catch(() => undefined); }, []);

  const analysed = project.scenes.some((s) => Object.keys(s.data).length > 0);
  const selected = project.scenes.filter((s) => s.selected);
  const promptStep = project.steps.find((s) => s.key === "prompts");
  const generating = promptStep?.status === "running";

  async function patch(scene: Scene, body: Record<string, unknown>) {
    const updated = await api<Scene>(`/api/projects/${project.id}/scenes/${scene.id}`, { method: "PATCH", body });
    setProject((p) => p && { ...p, scenes: p.scenes.map((s) => (s.id === updated.id ? updated : s)) });
  }
  async function selectAll(value: boolean) {
    setError("");
    try { await Promise.all(project.scenes.filter((s) => s.selected !== value).map((s) => patch(s, { selected: value }))); }
    catch (e) { setError((e as Error).message); }
  }
  async function regenerate(sceneIds?: string[]) {
    setBusy(true); setError("");
    try {
      await api(`/api/projects/${project.id}/prompts/regenerate`, { body: { scene_ids: sceneIds ?? null, language, style } });
      await reload();
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function buildGlobal() {
    setBusy(true); setError("");
    try {
      const r = await api<{ global_prompt: string }>(`/api/projects/${project.id}/prompts/global`, { body: { only_selected: true } });
      setProject((p) => p && { ...p, global_prompt: r.global_prompt });
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  if (!analysed) return <Empty title="Le Prompt Engine sera disponible après l'analyse des scènes">Les prompts sont générés à partir du storyboard, des fiches personnages et des dialogues.</Empty>;

  return (
    <div className="space-y-6">
      <section className="card p-5">
        <div className="flex items-center gap-2">
          <Wand2 className="h-5 w-5 text-brand-cyan" />
          <h2 className="font-display text-lg font-semibold text-white">Recréer cette vidéo</h2>
        </div>
        <p className="mt-1 text-sm text-slate-400">
          Choisissez les scènes, le style visuel et la langue, puis générez une nouvelle version des prompts. Dialogues, personnages et descriptions se modifient dans leurs onglets ; les dialogues restent dans leur langue d&apos;origine.
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_auto] lg:items-end">
          <div>
            <label className="label" htmlFor="style">Style visuel</label>
            <select id="style" className="input" value={style} onChange={(e) => setStyle(e.target.value)}>
              {(meta?.styles ?? [{ key: style, label: "…" }]).map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="lang">Langue des prompts</label>
            <select id="lang" className="input" value={language} onChange={(e) => setLanguage(e.target.value)}>
              {(meta?.languages ?? [{ code: language, label: language }]).map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
            </select>
          </div>
          <button className="btn-primary" disabled={busy || generating || running || selected.length === 0} onClick={() => regenerate()}>
            {busy || generating ? <Spinner /> : <RefreshCw className="h-4 w-4" />}
            Générer les prompts ({selected.length} scène{selected.length > 1 ? "s" : ""})
          </button>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
          <button className="btn-ghost py-1.5" onClick={() => selectAll(true)}><CheckSquare className="h-4 w-4" />Toutes les scènes</button>
          <button className="btn-ghost py-1.5" onClick={() => selectAll(false)}><Square className="h-4 w-4" />Aucune</button>
          <span className="text-slate-500">{selected.length} / {project.scenes.length} sélectionnée{selected.length > 1 ? "s" : ""}</span>
        </div>
        {generating && (
          <div className="mt-4">
            <div className="h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full bg-brand-gradient transition-[width] duration-500" style={{ width: `${Math.max(promptStep!.progress * 100, 4)}%` }} /></div>
            <p className="mt-1.5 text-xs text-slate-400">{promptStep!.message || "Génération en cours"}</p>
          </div>
        )}
        {promptStep?.status === "failed" && <div className="mt-4"><ErrorBox message={promptStep.error} /></div>}
        {error && <div className="mt-4"><ErrorBox message={error} /></div>}
      </section>

      <p className="text-xs text-slate-500">
        Ces prompts sont une reconstruction fondée sur l&apos;analyse de l&apos;image et du son de la vidéo. Ce ne sont pas les prompts d&apos;origine.
      </p>

      {project.scenes.map((s) => (
        <article key={s.id} className={`card overflow-hidden transition ${s.selected ? "" : "opacity-60"}`}>
          <header className="flex flex-wrap items-center gap-3 border-b border-white/10 px-5 py-3">
            <label className="flex cursor-pointer items-center gap-2.5">
              <input type="checkbox" className="h-4 w-4 accent-violet-500" checked={s.selected} onChange={(e) => patch(s, { selected: e.target.checked }).catch((er: Error) => setError(er.message))} />
              <span className="font-display font-bold text-white">SCÈNE {String(s.index).padStart(2, "0")}</span>
            </label>
            <span className="chip font-mono">{timecode(s.start)} – {timecode(s.end)}</span>
            <label className="flex items-center gap-2 text-xs text-slate-400">
              Durée cible
              <input type="number" min={1} max={120} step={0.5} className="input w-20 px-2 py-1 text-xs" aria-label={`Durée cible de la scène ${s.index} en secondes`}
                defaultValue={s.target_duration ?? s.duration} key={`${s.id}-${s.target_duration}`}
                onBlur={(e) => { const v = Number(e.target.value); if (v > 0 && v !== (s.target_duration ?? s.duration)) patch(s, { target_duration: v }).catch((er: Error) => setError(er.message)); }} />
              s
            </label>
            <div className="ml-auto flex flex-wrap gap-2">
              {s.prompt_text && <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setEditing(editing === s.id ? null : s.id)}>{editing === s.id ? "Fermer l'édition" : "Modifier"}</button>}
              <button className="btn-ghost px-3 py-1.5 text-xs" disabled={busy || generating || running} onClick={() => regenerate([s.id])}><RefreshCw className="h-3.5 w-3.5" />Régénérer</button>
              <CopyButton text={s.prompt_text} label="Copier le prompt" className="btn-primary px-3 py-1.5 text-xs" />
            </div>
          </header>
          {!s.prompt_text ? (
            <p className="p-5 text-sm text-slate-500">Aucun prompt généré pour cette scène.</p>
          ) : editing === s.id ? (
            <div className="grid gap-4 p-5 text-sm md:grid-cols-2">
              {EDITABLE.map(([key, label]) => (
                <div key={key} className="min-w-0">
                  <p className="label mb-0.5">{label}</p>
                  <EditableText value={s.prompt_sections[key] || ""} onSave={(v) => patch(s, { prompt_sections: { [key]: v } })} className="text-slate-200" />
                </div>
              ))}
              <p className="text-xs text-slate-500 md:col-span-2">Les sections 2 (personnages), 8 (dialogues) et 12 (durée) sont remplies automatiquement à partir des fiches, de la transcription et de la durée cible.</p>
            </div>
          ) : (
            <pre className="max-h-[460px] overflow-auto whitespace-pre-wrap break-words p-5 font-mono text-[12.5px] leading-relaxed text-slate-200">{s.prompt_text}</pre>
          )}
        </article>
      ))}

      <section className="card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2"><Layers className="h-5 w-5 text-brand-cyan" /><h2 className="font-display text-lg font-semibold text-white">Prompt global</h2></div>
          <div className="flex flex-wrap gap-2">
            <button className="btn-ghost" disabled={busy || generating || !project.scenes.some((s) => s.prompt_text && s.selected)} onClick={buildGlobal}>{busy ? <Spinner /> : <Layers className="h-4 w-4" />}Générer le prompt global</button>
            <CopyButton text={project.global_prompt} label="Copier" />
          </div>
        </div>
        <p className="mt-1 text-sm text-slate-400">Regroupe la bible des personnages et toutes les scènes sélectionnées en un seul prompt.</p>
        {project.global_prompt && <pre className="mt-4 max-h-[420px] overflow-auto whitespace-pre-wrap break-words rounded-xl border border-white/10 bg-ink-950/60 p-4 font-mono text-[12.5px] leading-relaxed text-slate-200">{project.global_prompt}</pre>}
      </section>
    </div>
  );
}
