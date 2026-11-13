"use client";
import { Clock, Film, FolderOpen, Layers, Trash2 } from "lucide-react";
import Link from "next/link";
import { dateFr, duration } from "@/lib/format";
import type { ProjectSummary } from "@/lib/types";
import { StatusBadge } from "./ui";

export default function ProjectCard({ project, onDelete }: { project: ProjectSummary; onDelete?: (p: ProjectSummary) => void }) {
  return (
    <div className="card card-hover flex flex-col overflow-hidden">
      <Link href={`/projects/${project.id}`} className="relative block aspect-video bg-ink-800">
        {project.thumbnail_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={project.thumbnail_url} alt="" className="h-full w-full object-cover" loading="lazy" />
        ) : (
          <span className="grid h-full place-items-center text-slate-600"><Film className="h-8 w-8" /></span>
        )}
        <span className="absolute left-2.5 top-2.5"><StatusBadge status={project.status} /></span>
      </Link>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="min-w-0">
          <h3 className="truncate font-semibold text-white" title={project.name}>{project.name}</h3>
          <p className="mt-0.5 text-xs text-slate-500">{dateFr(project.created_at)}</p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs text-slate-400">
          <span className="chip"><Clock className="h-3 w-3" />{duration(project.duration)}</span>
          <span className="chip"><Layers className="h-3 w-3" />{project.scene_count} scène{project.scene_count > 1 ? "s" : ""}</span>
        </div>
        <div className="mt-auto flex gap-2 pt-1">
          <Link href={`/projects/${project.id}`} className="btn-ghost flex-1 py-2"><FolderOpen className="h-4 w-4" />Ouvrir</Link>
          {onDelete && (
            <button onClick={() => onDelete(project)} className="btn-danger px-3 py-2" aria-label={`Supprimer ${project.name}`} title="Supprimer">
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
