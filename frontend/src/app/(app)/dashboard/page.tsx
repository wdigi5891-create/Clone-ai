"use client";
import { CheckCircle2, Clock, HardDrive, Loader, PlusCircle, Video } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import ProjectCard from "@/components/ProjectCard";
import { Empty, ErrorBox, PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { bytes, duration } from "@/lib/format";
import type { Dashboard } from "@/lib/types";

export default function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    const load = () => api<Dashboard>("/api/dashboard").then((d) => alive && setData(d), (e: Error) => alive && setError(e.message));
    load();
    const t = setInterval(load, 5000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  const stats = data && [
    { icon: Video, label: "Vidéos analysées", value: data.videos_analyzed },
    { icon: Loader, label: "Projets en cours", value: data.in_progress },
    { icon: CheckCircle2, label: "Projets terminés", value: data.completed },
    { icon: Clock, label: "Durée totale analysée", value: duration(data.total_duration_analyzed) },
    { icon: HardDrive, label: "Stockage utilisé", value: bytes(data.storage_bytes) },
  ];

  return (
    <>
      <PageHeader title={`Bonjour${user?.name ? `, ${user.name}` : ""}`} subtitle="Vue d'ensemble de vos analyses vidéo."
        actions={<Link href="/new" className="btn-primary"><PlusCircle className="h-4 w-4" />Nouvelle analyse</Link>} />
      {error && <ErrorBox message={error} />}
      {!data && !error && <div className="grid place-items-center py-20 text-slate-400"><Spinner className="h-6 w-6" /></div>}
      {stats && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          {stats.map((s) => (
            <div key={s.label} className="card p-4">
              <s.icon className="h-5 w-5 text-brand-cyan" />
              <p className="mt-3 font-display text-2xl font-bold text-white">{s.value}</p>
              <p className="mt-0.5 text-xs text-slate-400">{s.label}</p>
            </div>
          ))}
        </div>
      )}
      {data && (
        <section className="mt-10">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold text-white">Dernières analyses</h2>
            {data.total_projects > 0 && <Link href="/projects" className="text-sm text-brand-cyan hover:underline">Toute la bibliothèque</Link>}
          </div>
          {data.recent.length === 0 ? (
            <Empty title="Aucun projet pour le moment">
              <p>Importez une vidéo pour obtenir son découpage, ses personnages et ses prompts.</p>
              <Link href="/new" className="btn-primary mt-5">Analyser une vidéo</Link>
            </Empty>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {data.recent.map((p) => <ProjectCard key={p.id} project={p} />)}
            </div>
          )}
        </section>
      )}
    </>
  );
}
