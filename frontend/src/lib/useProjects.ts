"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { ProjectSummary } from "./types";

/** Liste des projets, rafraîchie automatiquement tant qu'une analyse est en cours. */
export function useProjects() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [error, setError] = useState("");

  const reload = useCallback(() => api<ProjectSummary[]>("/api/projects").then(
    (p) => { setProjects(p); setError(""); },
    (e: Error) => setError(e.message),
  ), []);

  useEffect(() => { reload(); }, [reload]);
  const busy = projects?.some((p) => p.status === "queued" || p.status === "processing");
  useEffect(() => {
    if (!busy) return;
    const t = setInterval(reload, 4000);
    return () => clearInterval(t);
  }, [busy, reload]);

  const remove = useCallback(async (p: ProjectSummary) => {
    if (!window.confirm(`Supprimer définitivement « ${p.name} » ? La vidéo, les images et l'analyse seront effacées.`)) return;
    try {
      await api(`/api/projects/${p.id}`, { method: "DELETE" });
      setProjects((list) => list?.filter((x) => x.id !== p.id) ?? null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  return { projects, error, reload, remove };
}
