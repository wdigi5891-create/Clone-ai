"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { Progress, Project } from "./types";

const isRunning = (p: Pick<Project, "status" | "steps">) =>
  p.status === "queued" || p.status === "processing" || p.steps.some((s) => s.status === "running");

/** Charge un projet et suit la progression réelle de l'analyse (interrogation de l'API). */
export function useProject(id: string) {
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const doneCount = useRef(-1);

  const reload = useCallback(async () => {
    try {
      const p = await api<Project>(`/api/projects/${id}`);
      setProject(p);
      setError("");
      return p;
    } catch (e) {
      setError((e as Error).message);
      return null;
    }
  }, [id]);

  useEffect(() => { reload(); }, [reload]);

  const running = project ? isRunning(project) : false;
  useEffect(() => {
    if (!running) return;
    let stop = false;
    const tick = async () => {
      try {
        const pr = await api<Progress>(`/api/projects/${id}/progress`);
        if (stop) return;
        const done = pr.steps.filter((s) => s.status === "done" || s.status === "skipped").length;
        // Recharge le détail à chaque étape franchie (les résultats apparaissent au fil de l'eau) et à la fin.
        if (!isRunning(pr) || done !== doneCount.current) {
          doneCount.current = done;
          await reload();
        } else {
          setProject((p) => (p ? { ...p, status: pr.status, error: pr.error, steps: pr.steps } : p));
        }
      } catch { /* erreur réseau passagère : on réessaie au prochain passage */ }
    };
    const t = setInterval(tick, 1500);
    return () => { stop = true; clearInterval(t); };
  }, [running, id, reload]);

  return { project, setProject, error, reload, running };
}
