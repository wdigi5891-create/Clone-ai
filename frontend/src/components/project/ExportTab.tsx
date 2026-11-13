"use client";
import { Archive, Download, FileJson, FileText, Images, MessageSquareText, ScrollText, Users, Wand2 } from "lucide-react";
import { useState } from "react";
import { downloadExport } from "@/lib/api";
import { Empty, ErrorBox, Spinner } from "../ui";
import type { TabProps } from "./shared";

const ITEMS = [
  { icon: Images, title: "Toutes les images extraites", text: "Images clés de chaque scène et références des personnages.", files: [["images.zip", "ZIP"]] },
  { icon: Users, title: "Fiches des personnages", text: "Descriptions complètes et blocs prompt.", files: [["characters.md", "Markdown"], ["characters.json", "JSON"]] },
  { icon: FileJson, title: "Storyboard complet", text: "Scènes, horodatages, analyse et dialogues.", files: [["storyboard.md", "Markdown"], ["storyboard.json", "JSON"]] },
  { icon: MessageSquareText, title: "Dialogues", text: "Transcription horodatée.", files: [["dialogues.srt", "SRT"], ["dialogues.json", "JSON"]] },
  { icon: Wand2, title: "Prompts scène par scène", text: "Un prompt en 13 sections par scène, et le prompt global.", files: [["prompts.txt", "Scènes"], ["global_prompt.txt", "Global"]] },
  { icon: ScrollText, title: "Script global", text: "Scènes, descriptions et répliques attribuées.", files: [["script.md", "Markdown"]] },
] as const;

export default function ExportTab({ project }: TabProps) {
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  async function get(kind: string) {
    setBusy(kind); setError("");
    try { await downloadExport(project.id, kind); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(""); }
  }
  if (!project.scenes.length) return <Empty title="Rien à exporter pour le moment">Les exports sont disponibles dès que les scènes ont été détectées.</Empty>;

  const Btn = ({ kind, label, primary = false }: { kind: string; label: string; primary?: boolean }) => (
    <button className={`${primary ? "btn-primary" : "btn-ghost"} py-2`} disabled={!!busy} onClick={() => get(kind)}>
      {busy === kind ? <Spinner /> : <Download className="h-4 w-4" />}{label}
    </button>
  );
  return (
    <div className="space-y-5">
      {error && <ErrorBox message={error} />}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card relative overflow-hidden p-6">
          <div className="absolute inset-x-0 top-0 h-px bg-brand-gradient" />
          <Archive className="h-6 w-6 text-brand-cyan" />
          <h3 className="mt-3 font-display text-lg font-semibold text-white">Archive ZIP complète</h3>
          <p className="mt-1 text-sm text-slate-400">Images, fiches, storyboard, dialogues, prompts, script et rapport PDF dans un seul fichier.</p>
          <div className="mt-4"><Btn kind="all.zip" label="Télécharger le ZIP" primary /></div>
        </div>
        <div className="card relative overflow-hidden p-6">
          <div className="absolute inset-x-0 top-0 h-px bg-brand-gradient" />
          <FileText className="h-6 w-6 text-brand-cyan" />
          <h3 className="mt-3 font-display text-lg font-semibold text-white">Rapport PDF professionnel</h3>
          <p className="mt-1 text-sm text-slate-400">Analyse générale, personnages, storyboard illustré et prompts, prêt à partager.</p>
          <div className="mt-4"><Btn kind="report.pdf" label="Télécharger le PDF" primary /></div>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {ITEMS.map((it) => (
          <div key={it.title} className="card flex flex-col p-5">
            <it.icon className="h-5 w-5 text-brand-violet" />
            <h3 className="mt-3 font-semibold text-white">{it.title}</h3>
            <p className="mt-1 flex-1 text-sm text-slate-400">{it.text}</p>
            <div className="mt-4 flex flex-wrap gap-2">{it.files.map(([kind, label]) => <Btn key={kind} kind={kind} label={label} />)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
