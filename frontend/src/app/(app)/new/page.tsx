"use client";
import { motion } from "framer-motion";
import { FileVideo, Link2, Play, ScissorsLineDashed, Sparkles, Trash2, UploadCloud } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ErrorBox, PageHeader, Spinner } from "@/components/ui";
import { api, ApiError, uploadVideo } from "@/lib/api";
import { bytes, duration } from "@/lib/format";
import type { Meta, Project } from "@/lib/types";

const EXT = ["mp4", "mov", "webm"];

export default function NewAnalysisPage() {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [mode, setMode] = useState<"file" | "url">("file");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [videoInfo, setVideoInfo] = useState<{ duration: number; width: number; height: number } | null>(null);
  const [url, setUrl] = useState("");
  const [urlState, setUrlState] = useState<{ ok: boolean; message: string } | null>(null);
  const [checking, setChecking] = useState(false);
  const [name, setName] = useState("");
  const [splitMode, setSplitMode] = useState<"smart" | "fixed">("smart");
  const [splitSeconds, setSplitSeconds] = useState(10);
  const [rights, setRights] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [phase, setPhase] = useState<"idle" | "upload" | "start">("idle");
  const [uploadRatio, setUploadRatio] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => { api<Meta>("/api/meta").then(setMeta).catch(() => undefined); }, []);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const maxMb = meta?.limits.max_upload_mb ?? 500;
  const maxDuration = meta?.limits.max_duration_seconds ?? 600;

  function pick(f: File | undefined | null) {
    setError("");
    if (!f) return;
    const ext = f.name.split(".").pop()?.toLowerCase() || "";
    if (!EXT.includes(ext)) return setError("Format non pris en charge. Formats acceptés : MP4, MOV, WEBM.");
    if (f.size > maxMb * 1024 * 1024) return setError(`Fichier trop volumineux (${bytes(f.size)}). Limite : ${maxMb} Mo.`);
    setFile(f);
    setVideoInfo(null);
    setPreview(URL.createObjectURL(f));
    if (!name) setName(f.name.replace(/\.[^.]+$/, ""));
  }
  function clearFile() {
    setFile(null); setPreview(""); setVideoInfo(null);
    if (input.current) input.current.value = "";
  }

  async function checkUrl() {
    setChecking(true); setUrlState(null); setError("");
    try {
      await api("/api/projects/check-url", { body: { url } });
      setUrlState({ ok: true, message: "Lien valide : la vidéo sera téléchargée au lancement de l'analyse." });
    } catch (e) {
      setUrlState({ ok: false, message: (e as Error).message });
    } finally { setChecking(false); }
  }

  const tooLong = !!videoInfo && videoInfo.duration > maxDuration;
  const ready = rights && !tooLong && (mode === "file" ? !!file : url.trim().length > 8 && urlState?.ok !== false);
  const busy = phase !== "idle";

  async function launch() {
    setError("");
    try {
      setPhase("upload");
      setUploadRatio(0);
      const project = mode === "file"
        ? await uploadVideo<Project>(file!, { name, rights_confirmed: "true" }, setUploadRatio)
        : await api<Project>("/api/projects/import-url", { body: { url, name, rights_confirmed: true } });
      setPhase("start");
      await api(`/api/projects/${project.id}/analyze`, { body: { split_mode: splitMode, split_seconds: splitSeconds } });
      router.push(`/projects/${project.id}`);
    } catch (e) {
      setPhase("idle");
      if (e instanceof ApiError && mode === "url") setUrlState({ ok: false, message: e.message });
      else setError((e as Error).message);
    }
  }

  return (
    <>
      <PageHeader title="Nouvelle analyse" subtitle="Importez une vidéo, choisissez le découpage, puis lancez l'analyse." />
      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <section className="space-y-4">
          <div className="grid grid-cols-2 gap-1 rounded-xl border border-white/10 bg-white/5 p-1">
            {([["file", "Importer une vidéo", FileVideo], ["url", "Importer par lien", Link2]] as const).map(([key, label, Icon]) => (
              <button key={key} disabled={busy} onClick={() => { setMode(key); setError(""); }}
                className={`flex items-center justify-center gap-2 rounded-lg py-2.5 text-sm font-medium transition ${mode === key ? "bg-white/15 text-white" : "text-slate-400 hover:text-white"}`}>
                <Icon className="h-4 w-4" />{label}
              </button>
            ))}
          </div>

          {mode === "file" && !file && (
            <div
              role="button" tabIndex={0}
              onClick={() => input.current?.click()}
              onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => { e.preventDefault(); setDragging(false); pick(e.dataTransfer.files[0]); }}
              className={`card grid cursor-pointer place-items-center border-2 border-dashed px-6 py-16 text-center transition ${dragging ? "border-brand-cyan bg-brand-cyan/10" : "border-white/15 hover:border-brand-violet/60"}`}>
              <span className="grid h-16 w-16 place-items-center rounded-2xl bg-brand-gradient shadow-glow"><UploadCloud className="h-8 w-8 text-white" /></span>
              <p className="mt-5 font-display text-lg font-semibold text-white">Glissez-déposez votre vidéo ici</p>
              <p className="mt-1 text-sm text-slate-400">ou touchez pour la choisir sur votre téléphone ou votre ordinateur</p>
              <p className="mt-4 text-xs text-slate-500">MP4, MOV ou WEBM · {maxMb} Mo max · {duration(maxDuration)} max</p>
            </div>
          )}
          <input ref={input} type="file" hidden accept="video/mp4,video/quicktime,video/webm,.mp4,.mov,.webm" onChange={(e) => pick(e.target.files?.[0])} />

          {mode === "file" && file && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card overflow-hidden">
              <video src={preview} controls playsInline className="max-h-[420px] w-full bg-black"
                onLoadedMetadata={(e) => setVideoInfo({ duration: e.currentTarget.duration, width: e.currentTarget.videoWidth, height: e.currentTarget.videoHeight })} />
              <div className="flex flex-wrap items-center gap-x-6 gap-y-3 p-4">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-white" title={file.name}>{file.name}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <span className="chip">Taille : {bytes(file.size)}</span>
                    <span className="chip">Durée : {videoInfo && isFinite(videoInfo.duration) ? duration(videoInfo.duration) : "—"}</span>
                    <span className="chip">Format : {(file.name.split(".").pop() || "").toUpperCase()}</span>
                    {videoInfo && videoInfo.width > 0 && <span className="chip">{videoInfo.width} × {videoInfo.height}</span>}
                  </div>
                </div>
                <button onClick={clearFile} disabled={busy} className="btn-danger"><Trash2 className="h-4 w-4" />Supprimer</button>
              </div>
              {tooLong && <div className="px-4 pb-4"><ErrorBox message={`Vidéo trop longue : la durée maximale est de ${duration(maxDuration)}.`} /></div>}
            </motion.div>
          )}

          {mode === "url" && (
            <div className="card space-y-4 p-5">
              <div>
                <label className="label" htmlFor="url">Lien de la vidéo</label>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <input id="url" className="input" inputMode="url" placeholder="https://… (lien TikTok ou URL directe MP4 / MOV / WEBM)"
                    value={url} onChange={(e) => { setUrl(e.target.value); setUrlState(null); }} />
                  <button onClick={checkUrl} disabled={checking || busy || url.trim().length < 9} className="btn-ghost shrink-0">{checking && <Spinner />}Vérifier le lien</button>
                </div>
              </div>
              {urlState?.ok && <p className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-3 text-sm text-emerald-100">{urlState.message}</p>}
              {urlState && !urlState.ok && (
                <ErrorBox message={urlState.message}>
                  <button className="btn-ghost py-1.5" onClick={() => { setMode("file"); setUrlState(null); }}><FileVideo className="h-4 w-4" />Importer le fichier original</button>
                </ErrorBox>
              )}
              <p className="text-xs leading-relaxed text-slate-500">
                Seuls les accès autorisés sont utilisés : un lien direct vers un fichier vidéo public est téléchargé tel quel. Les plateformes qui interdisent le téléchargement (dont TikTok) ne sont pas contournées ; importez alors votre fichier original.
              </p>
            </div>
          )}
          {error && <ErrorBox message={error} />}
        </section>

        <aside className="card h-fit space-y-5 p-5">
          <div>
            <label className="label" htmlFor="pname">Nom du projet</label>
            <input id="pname" className="input" placeholder="Ma vidéo" value={name} maxLength={200} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <p className="label">Découpage des scènes</p>
            <div className="space-y-2">
              {([["smart", "Découpage intelligent", "Détecte les vrais changements de plan.", Sparkles],
                 ["fixed", "Découpage personnalisé", "Séquences de durée fixe.", ScissorsLineDashed]] as const).map(([key, title, text, Icon]) => (
                <button key={key} type="button" onClick={() => setSplitMode(key)} aria-pressed={splitMode === key}
                  className={`flex w-full items-start gap-3 rounded-xl border p-3 text-left transition ${splitMode === key ? "border-brand-violet/70 bg-brand-violet/10" : "border-white/10 bg-white/5 hover:border-white/20"}`}>
                  <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${splitMode === key ? "text-brand-cyan" : "text-slate-400"}`} />
                  <span><span className="block text-sm font-medium text-white">{title}</span><span className="text-xs text-slate-400">{text}</span></span>
                </button>
              ))}
            </div>
            {splitMode === "fixed" && (
              <div className="mt-3 flex flex-wrap gap-2">
                {(meta?.split_seconds ?? [5, 10, 15, 20, 30]).map((s) => (
                  <button key={s} onClick={() => setSplitSeconds(s)} aria-pressed={splitSeconds === s}
                    className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition ${splitSeconds === s ? "border-brand-cyan/70 bg-brand-cyan/10 text-white" : "border-white/10 text-slate-300 hover:border-white/25"}`}>{s} s</button>
                ))}
              </div>
            )}
          </div>
          <label className="flex items-start gap-2.5 text-sm text-slate-300">
            <input type="checkbox" checked={rights} onChange={(e) => setRights(e.target.checked)} className="mt-1 accent-violet-500" />
            <span>Je confirme détenir les droits sur cette vidéo ou l&apos;autorisation de l&apos;utiliser, y compris pour les personnes et les voix qui y figurent.</span>
          </label>
          {meta && !meta.providers.vision.configured && (
            <p className="rounded-xl border border-amber-400/30 bg-amber-400/10 p-3 text-xs leading-relaxed text-amber-100">
              Aucune clé d&apos;API n&apos;est configurée pour le fournisseur de vision « {meta.providers.vision.name} ». Le découpage et l&apos;extraction des images fonctionneront ; l&apos;identification des personnages et les prompts échoueront tant que la clé n&apos;est pas ajoutée côté serveur.
            </p>
          )}
          <button className="btn-primary w-full py-3 text-base" disabled={!ready || busy} onClick={launch}>
            {busy ? <Spinner /> : <Play className="h-4 w-4" />}
            {phase === "upload" ? (mode === "file" ? `Envoi… ${Math.round(uploadRatio * 100)} %` : "Téléchargement du lien…") : phase === "start" ? "Démarrage…" : "Lancer l'analyse"}
          </button>
          {phase === "upload" && mode === "file" && (
            <div className="h-1.5 overflow-hidden rounded-full bg-white/10" role="progressbar" aria-valuenow={Math.round(uploadRatio * 100)} aria-valuemin={0} aria-valuemax={100}>
              <div className="h-full bg-brand-gradient transition-[width]" style={{ width: `${uploadRatio * 100}%` }} />
            </div>
          )}
        </aside>
      </div>
    </>
  );
}
