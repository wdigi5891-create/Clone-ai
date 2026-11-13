"use client";
import { ArrowLeft, Clapperboard, Download, LayoutGrid, MessageSquareText, Trash2, Users, Wand2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import CharactersTab from "@/components/project/CharactersTab";
import ExportTab from "@/components/project/ExportTab";
import OverviewTab from "@/components/project/OverviewTab";
import PromptsTab from "@/components/project/PromptsTab";
import ScriptTab from "@/components/project/ScriptTab";
import StoryboardTab from "@/components/project/StoryboardTab";
import { EditableText } from "@/components/project/shared";
import { ErrorBox, Spinner, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";
import { dateFr, duration } from "@/lib/format";
import type { Project } from "@/lib/types";
import { useProject } from "@/lib/useProject";

const TABS = [
  { key: "overview", label: "Analyse", icon: Clapperboard, Tab: OverviewTab },
  { key: "storyboard", label: "Storyboard", icon: LayoutGrid, Tab: StoryboardTab },
  { key: "characters", label: "Personnages", icon: Users, Tab: CharactersTab },
  { key: "script", label: "Script et dialogues", icon: MessageSquareText, Tab: ScriptTab },
  { key: "prompts", label: "Prompt Engine", icon: Wand2, Tab: PromptsTab },
  { key: "export", label: "Exporter", icon: Download, Tab: ExportTab },
] as const;

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { project, setProject, error, reload, running } = useProject(id);
  const [tab, setTab] = useState<(typeof TABS)[number]["key"]>("overview");
  const [actionError, setActionError] = useState("");

  if (error && !project) {
    return <div className="space-y-4"><ErrorBox message={error} /><Link href="/projects" className="btn-ghost"><ArrowLeft className="h-4 w-4" />Retour à la bibliothèque</Link></div>;
  }
  if (!project) return <div className="grid place-items-center py-24 text-slate-400"><Spinner className="h-6 w-6" /></div>;

  async function remove() {
    if (!project || !window.confirm(`Supprimer définitivement « ${project.name} » et toutes ses données ?`)) return;
    try { await api(`/api/projects/${project.id}`, { method: "DELETE" }); router.push("/projects"); }
    catch (e) { setActionError((e as Error).message); }
  }
  async function rename(name: string) {
    const updated = await api<Project>(`/api/projects/${project!.id}`, { method: "PATCH", body: { name } });
    setProject(updated);
  }
  const counts: Record<string, number> = { storyboard: project.scenes.length, characters: project.characters.length, script: project.dialogues.length };
  const Active = TABS.find((t) => t.key === tab)!.Tab;

  return (
    <>
      <Link href="/projects" className="mb-4 inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-white"><ArrowLeft className="h-4 w-4" />Bibliothèque</Link>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="font-display text-2xl font-bold text-white sm:text-3xl"><EditableText multiline={false} value={project.name} onSave={rename} className="-ml-2" /></div>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <StatusBadge status={project.status} />
            <span>{dateFr(project.created_at)}</span><span>·</span><span>{duration(project.duration)}</span>
            <span>·</span><span>{project.width} × {project.height}</span>
          </div>
        </div>
        <button className="btn-danger" onClick={remove}><Trash2 className="h-4 w-4" />Supprimer</button>
      </div>
      {actionError && <div className="mb-4"><ErrorBox message={actionError} /></div>}

      <div className="-mx-4 mb-6 overflow-x-auto px-4 sm:mx-0 sm:px-0">
        <div role="tablist" className="flex w-max gap-1 rounded-xl border border-white/10 bg-white/5 p-1">
          {TABS.map((t) => (
            <button key={t.key} role="tab" aria-selected={tab === t.key} onClick={() => setTab(t.key)}
              className={`flex items-center gap-2 whitespace-nowrap rounded-lg px-3.5 py-2 text-sm font-medium transition ${tab === t.key ? "bg-white/15 text-white" : "text-slate-400 hover:text-white"}`}>
              <t.icon className={`h-4 w-4 ${tab === t.key ? "text-brand-cyan" : ""}`} />{t.label}
              {counts[t.key] > 0 && <span className="rounded-full bg-white/10 px-1.5 text-[11px] text-slate-300">{counts[t.key]}</span>}
            </button>
          ))}
        </div>
      </div>
      <Active project={project} setProject={setProject} reload={reload} running={running} />
    </>
  );
}
