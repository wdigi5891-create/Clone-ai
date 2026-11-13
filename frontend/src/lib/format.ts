export function timecode(t: number): string {
  const m = Math.floor(t / 60);
  const s = t - m * 60;
  const whole = Math.abs(s - Math.round(s)) < 0.05;
  return `${String(m).padStart(2, "0")}:${whole ? String(Math.round(s)).padStart(2, "0") : s.toFixed(1).padStart(4, "0")}`;
}
export function duration(t: number): string {
  if (!t) return "0 s";
  if (t < 60) return `${Math.round(t * 10) / 10} s`;
  const m = Math.floor(t / 60);
  return m < 60 ? `${m} min ${Math.round(t % 60)} s` : `${Math.floor(m / 60)} h ${m % 60} min`;
}
export function bytes(n: number): string {
  if (n < 1024) return `${n} o`;
  const units = ["Ko", "Mo", "Go", "To"];
  let v = n / 1024, i = 0;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
  return `${v.toFixed(v < 10 ? 1 : 0)} ${units[i]}`;
}
export const dateFr = (iso: string) =>
  new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

export const STATUS_LABELS: Record<string, string> = {
  uploaded: "Importée", queued: "En file d'attente", processing: "Analyse en cours",
  completed: "Terminée", failed: "À relancer",
};
