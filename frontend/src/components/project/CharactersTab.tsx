"use client";
import { Download, UserRound } from "lucide-react";
import { api, downloadUrl } from "@/lib/api";
import type { Character } from "@/lib/types";
import { CopyButton, Empty } from "../ui";
import { CHARACTER_FIELDS, EditableText, type TabProps } from "./shared";

export default function CharactersTab({ project, reload }: TabProps) {
  const step = project.steps.find((s) => s.key === "characters");

  async function patch(c: Character, body: Record<string, unknown>) {
    await api(`/api/projects/${project.id}/characters/${c.id}`, { method: "PATCH", body });
    await reload(); // les prompts des scènes sont réassemblés côté serveur
  }

  if (!project.characters.length) {
    return (
      <Empty title={step?.status === "done" ? "Aucun personnage visible dans cette vidéo" : "Les personnages apparaîtront ici"}>
        {step?.status !== "done" && "Les fiches sont créées par l'étape « Identification des personnages »."}
      </Empty>
    );
  }
  return (
    <div className="space-y-5">
      <p className="text-sm text-slate-400">
        Identifiants neutres et descriptions visuelles uniquement : aucune personne réelle n&apos;est identifiée. Le « bloc prompt » de chaque fiche est réutilisé à l&apos;identique dans toutes les scènes où le personnage apparaît.
      </p>
      {project.characters.map((c) => (
        <article key={c.id} className="card grid gap-5 p-5 md:grid-cols-[200px_1fr]">
          <div>
            <div className="overflow-hidden rounded-xl border border-white/10 bg-black">
              {c.reference_url
                // eslint-disable-next-line @next/next/no-img-element
                ? <img src={c.reference_url} alt={`Image de référence de ${c.label}`} className="max-h-72 w-full object-contain" loading="lazy" />
                : <span className="grid aspect-square place-items-center text-slate-600"><UserRound className="h-10 w-10" /></span>}
            </div>
            {c.reference_url && (
              <button className="btn-ghost mt-2 w-full py-2" onClick={() => downloadUrl(c.reference_url!, `personnage_${c.index}.jpg`).catch(() => undefined)}>
                <Download className="h-4 w-4" />Image de référence
              </button>
            )}
          </div>
          <div className="min-w-0 space-y-4 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="font-display text-xl font-bold text-white">{c.label}</h3>
              <div className="flex flex-wrap gap-1.5">
                {c.scene_indexes.length ? c.scene_indexes.map((i) => <span key={i} className="chip">Scène {i}</span>) : <span className="chip">Aucune scène</span>}
              </div>
            </div>
            <dl className="grid gap-x-5 gap-y-3 sm:grid-cols-2">
              {CHARACTER_FIELDS.map(([key, label]) => (
                <div key={key} className="min-w-0">
                  <dt className="label mb-0.5">{label}</dt>
                  <dd><EditableText value={c.data[key] || ""} onSave={(v) => patch(c, { data: { [key]: v } })} className="text-slate-200" /></dd>
                </div>
              ))}
            </dl>
            <div className="rounded-xl border border-brand-violet/30 bg-brand-violet/5 p-3">
              <div className="mb-1 flex items-center justify-between gap-2">
                <p className="label mb-0 text-violet-200">Bloc prompt (cohérence entre les scènes)</p>
                <CopyButton text={c.prompt_descriptor} className="btn-ghost px-2.5 py-1 text-xs" />
              </div>
              <EditableText value={c.prompt_descriptor} onSave={(v) => patch(c, { prompt_descriptor: v })} className="leading-relaxed text-slate-100" />
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
