"use client";
import { ChevronDown, Download, Star } from "lucide-react";
import { useState } from "react";
import { api, downloadUrl } from "@/lib/api";
import { timecode } from "@/lib/format";
import type { Frame, Scene } from "@/lib/types";
import { Empty } from "../ui";
import { EditableText, FRAME_KINDS, SCENE_FIELDS, type TabProps } from "./shared";

export default function StoryboardTab({ project, setProject }: TabProps) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [zoom, setZoom] = useState<Frame | null>(null);
  const [dlError, setDlError] = useState("");
  const analysed = project.scenes.some((s) => Object.keys(s.data).length > 0);

  async function patch(scene: Scene, body: Record<string, unknown>) {
    const updated = await api<Scene>(`/api/projects/${project.id}/scenes/${scene.id}`, { method: "PATCH", body });
    setProject((p) => p && { ...p, scenes: p.scenes.map((s) => (s.id === updated.id ? updated : s)) });
  }
  const download = (f: Frame) => downloadUrl(f.url, f.filename).catch((e: Error) => setDlError(e.message));

  if (!project.scenes.length) return <Empty title="Le storyboard apparaîtra ici">Les scènes sont créées dès que l&apos;étape « Détection des scènes » est terminée.</Empty>;

  return (
    <div className="space-y-5">
      {dlError && <p className="text-sm text-red-300">{dlError}</p>}
      {project.scenes.map((s) => {
        const rep = s.frames.find((f) => f.is_representative) || s.frames[0];
        const lines = project.dialogues.filter((d) => d.scene_index === s.index);
        const expanded = open[s.id] ?? false;
        return (
          <article key={s.id} className="card overflow-hidden">
            <header className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 px-5 py-3.5">
              <h3 className="font-display text-lg font-bold text-white">SCÈNE {String(s.index).padStart(2, "0")}</h3>
              <span className="chip font-mono">Durée : {timecode(s.start)} – {timecode(s.end)}</span>
            </header>
            <div className="grid gap-5 p-5 lg:grid-cols-[minmax(0,340px)_1fr]">
              <div className="space-y-3">
                {rep && (
                  <button onClick={() => setZoom(rep)} className="block w-full overflow-hidden rounded-xl border border-white/10 bg-black">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={rep.url} alt={`Image de référence de la scène ${s.index}`} className="max-h-[420px] w-full object-contain" loading="lazy" />
                  </button>
                )}
                <div className="grid grid-cols-4 gap-2">
                  {s.frames.map((f) => (
                    <figure key={f.id} className="group relative overflow-hidden rounded-lg border border-white/10 bg-black">
                      <button onClick={() => setZoom(f)} className="block w-full">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={f.url} alt={`${FRAME_KINDS[f.kind]} à ${timecode(f.timestamp)}`} className="aspect-square w-full object-cover" loading="lazy" />
                      </button>
                      {f.is_representative && <Star className="absolute left-1 top-1 h-3.5 w-3.5 fill-amber-300 text-amber-300" aria-label="Image la plus représentative" />}
                      <button onClick={() => download(f)} aria-label={`Télécharger l'image ${f.filename}`} title="Télécharger"
                        className="absolute right-1 top-1 rounded-md bg-black/70 p-1 text-white opacity-100 transition hover:bg-brand-violet sm:opacity-0 sm:group-hover:opacity-100">
                        <Download className="h-3.5 w-3.5" />
                      </button>
                      <figcaption className="px-1 py-1 text-center text-[10px] leading-tight text-slate-400">{FRAME_KINDS[f.kind]}<br /><span className="font-mono">{f.timestamp.toFixed(2)} s</span></figcaption>
                    </figure>
                  ))}
                </div>
              </div>
              <div className="min-w-0 space-y-4 text-sm">
                <div>
                  <p className="label">Personnages présents</p>
                  <div className="flex flex-wrap gap-2">
                    {project.characters.length === 0 && <span className="text-slate-500">—</span>}
                    {project.characters.map((c) => {
                      const on = s.character_indexes.includes(c.index);
                      return (
                        <button key={c.id} aria-pressed={on} title={on ? "Retirer de la scène" : "Ajouter à la scène"}
                          onClick={() => patch(s, { character_indexes: on ? s.character_indexes.filter((i) => i !== c.index) : [...s.character_indexes, c.index] })}
                          className={`chip transition ${on ? "border-brand-violet/60 bg-brand-violet/15 text-white" : "opacity-50 hover:opacity-100"}`}>{c.label}</button>
                      );
                    })}
                  </div>
                </div>
                {!analysed ? (
                  <p className="text-slate-500">L&apos;analyse détaillée de cette scène n&apos;est pas encore disponible.</p>
                ) : (
                  <>
                    <div>
                      <p className="label">Description cinématographique</p>
                      <EditableText value={s.description} onSave={(v) => patch(s, { description: v })} className="leading-relaxed text-slate-200" />
                    </div>
                    <dl className="grid gap-x-5 gap-y-3 sm:grid-cols-2">
                      {SCENE_FIELDS.slice(0, expanded ? undefined : 6).map(([key, label]) => (
                        <div key={key} className="min-w-0">
                          <dt className="label mb-0.5">{label}</dt>
                          <dd><EditableText value={s.data[key] || ""} onSave={(v) => patch(s, { data: { [key]: v } })} className="text-slate-200" /></dd>
                        </div>
                      ))}
                    </dl>
                    <button className="flex items-center gap-1 text-xs font-medium text-brand-cyan hover:underline" onClick={() => setOpen({ ...open, [s.id]: !expanded })}>
                      <ChevronDown className={`h-4 w-4 transition ${expanded ? "rotate-180" : ""}`} />{expanded ? "Réduire" : "Afficher caméra, éclairage, sons…"}
                    </button>
                  </>
                )}
                <div>
                  <p className="label">Dialogues</p>
                  {lines.length === 0 ? <p className="text-slate-500">Aucun dialogue dans cette scène.</p> : (
                    <ul className="space-y-1.5">
                      {lines.map((d) => (
                        <li key={d.id} className="flex gap-2 text-slate-200">
                          <span className="shrink-0 font-mono text-xs text-slate-500">{timecode(d.start)}</span>
                          <span>{d.character_index ? <b className="text-brand-cyan">Personnage {d.character_index} : </b> : null}
                            {d.identifiable && d.text ? `« ${d.text} »` : <i className="text-slate-500">Dialogue non identifiable</i>}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          </article>
        );
      })}
      {zoom && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/85 p-4" onClick={() => setZoom(null)} role="dialog" aria-modal="true">
          <div className="max-h-full max-w-5xl" onClick={(e) => e.stopPropagation()}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={zoom.url} alt="" className="max-h-[80vh] w-auto rounded-xl" />
            <div className="mt-3 flex items-center justify-between gap-3 text-sm text-slate-300">
              <span>{FRAME_KINDS[zoom.kind]} · <span className="font-mono">{zoom.timestamp.toFixed(3)} s</span> · {zoom.width} × {zoom.height}</span>
              <div className="flex gap-2">
                <button className="btn-ghost py-1.5" onClick={() => download(zoom)}><Download className="h-4 w-4" />Télécharger</button>
                <button className="btn-ghost py-1.5" onClick={() => setZoom(null)}>Fermer</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
