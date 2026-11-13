"use client";
import { PlusCircle, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import ProjectCard from "@/components/ProjectCard";
import { Empty, ErrorBox, PageHeader, Spinner } from "@/components/ui";
import { useProjects } from "@/lib/useProjects";

const FILTERS = [
  { key: "all", label: "Tous" }, { key: "running", label: "En cours" },
  { key: "completed", label: "Terminés" }, { key: "failed", label: "À relancer" },
];

export default function LibraryPage() {
  const { projects, error, remove } = useProjects();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");

  const visible = useMemo(() => (projects || []).filter((p) => {
    const group = p.status === "queued" || p.status === "processing" ? "running" : p.status;
    return (filter === "all" || group === filter) && p.name.toLowerCase().includes(query.trim().toLowerCase());
  }), [projects, query, filter]);

  return (
    <>
      <PageHeader title="Bibliothèque" subtitle="Tous vos projets d'analyse."
        actions={<Link href="/new" className="btn-primary"><PlusCircle className="h-4 w-4" />Nouvelle analyse</Link>} />
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="relative min-w-[200px] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input className="input pl-9" placeholder="Rechercher un projet" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Rechercher un projet" />
        </div>
        <div className="flex gap-1 rounded-xl border border-white/10 bg-white/5 p-1">
          {FILTERS.map((f) => (
            <button key={f.key} onClick={() => setFilter(f.key)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${filter === f.key ? "bg-white/15 text-white" : "text-slate-400 hover:text-white"}`}>{f.label}</button>
          ))}
        </div>
      </div>
      {error && <div className="mb-4"><ErrorBox message={error} /></div>}
      {!projects && !error && <div className="grid place-items-center py-20 text-slate-400"><Spinner className="h-6 w-6" /></div>}
      {projects && projects.length === 0 && (
        <Empty title="Votre bibliothèque est vide">
          <p>Les vidéos que vous analysez apparaîtront ici.</p>
          <Link href="/new" className="btn-primary mt-5">Analyser une vidéo</Link>
        </Empty>
      )}
      {projects && projects.length > 0 && visible.length === 0 && <Empty title="Aucun projet ne correspond à ces critères" />}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {visible.map((p) => <ProjectCard key={p.id} project={p} onDelete={remove} />)}
      </div>
    </>
  );
}
