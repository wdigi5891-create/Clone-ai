"use client";
import { Check, Pencil, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Spinner } from "../ui";
import type { Project } from "@/lib/types";

export interface TabProps {
  project: Project;
  setProject: React.Dispatch<React.SetStateAction<Project | null>>;
  reload: () => Promise<Project | null>;
  running: boolean;
}

/** Texte modifiable en place ; onSave doit persister côté serveur. */
export function EditableText({ value, onSave, multiline = true, placeholder = "—", className = "" }: {
  value: string; onSave: (v: string) => Promise<unknown>; multiline?: boolean; placeholder?: string; className?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { if (!editing) setDraft(value); }, [value, editing]);

  async function save() {
    setBusy(true); setError("");
    try { await onSave(draft); setEditing(false); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  if (!editing) {
    return (
      <button type="button" onClick={() => setEditing(true)} title="Modifier"
        className={`group flex w-full items-start gap-2 rounded-lg px-2 py-1 text-left transition hover:bg-white/5 ${className}`}>
        <span className={`min-w-0 flex-1 whitespace-pre-wrap break-words ${value ? "" : "text-slate-500"}`}>{value || placeholder}</span>
        <Pencil className="mt-1 h-3.5 w-3.5 shrink-0 text-slate-500 opacity-60 transition group-hover:opacity-100 sm:opacity-0" />
      </button>
    );
  }
  return (
    <div className="space-y-2">
      {multiline
        ? <textarea autoFocus className="input min-h-[90px] resize-y" rows={Math.min(10, Math.max(3, Math.ceil(draft.length / 70)))} value={draft} onChange={(e) => setDraft(e.target.value)} />
        : <input autoFocus className="input" value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === "Enter" && save()} />}
      {error && <p className="text-xs text-red-300">{error}</p>}
      <div className="flex gap-2">
        <button className="btn-primary px-3 py-1.5 text-xs" disabled={busy} onClick={save}>{busy ? <Spinner className="h-3 w-3" /> : <Check className="h-3.5 w-3.5" />}Enregistrer</button>
        <button className="btn-ghost px-3 py-1.5 text-xs" disabled={busy} onClick={() => setEditing(false)}><X className="h-3.5 w-3.5" />Annuler</button>
      </div>
    </div>
  );
}

export const SCENE_FIELDS: [string, string][] = [
  ["location", "Lieu"], ["set_design", "Décor"], ["time_of_day", "Moment de la journée"],
  ["character_positions", "Position des personnages"], ["actions", "Actions"], ["gestures", "Gestes"],
  ["expressions", "Expressions"], ["movements", "Mouvements"], ["lighting", "Éclairage"], ["mood", "Ambiance"],
  ["camera_type", "Type de caméra"], ["camera_angle", "Angle de caméra"], ["camera_movement", "Mouvement de caméra"],
  ["ambient_sounds", "Sons d'ambiance"], ["music", "Musique éventuelle"],
];
export const CHARACTER_FIELDS: [string, string][] = [
  ["physical_description", "Description physique"], ["skin_tone_appearance", "Teint et apparence visibles"],
  ["hair", "Coiffure"], ["clothing", "Vêtements"], ["accessories", "Accessoires"],
  ["apparent_age", "Âge apparent estimé"], ["facial_expressions", "Expressions faciales"],
  ["posture", "Posture"], ["distinctive_features", "Particularités visuelles distinctives"],
];
export const FRAME_KINDS: Record<string, string> = { start: "Début", middle: "Milieu", end: "Fin", key: "Image clé" };
