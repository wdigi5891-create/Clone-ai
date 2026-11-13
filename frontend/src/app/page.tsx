"use client";
import { motion } from "framer-motion";
import { ArrowRight, Clapperboard, FileText, Film, LayoutGrid, MessageSquareText, ScanSearch, Upload, Users, Wand2 } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { Logo } from "@/components/ui";

const FEATURES = [
  { icon: ScanSearch, title: "Analyse vidéo intelligente", text: "Durée, résolution, cadence, orientation, langue parlée, ambiance et style visuel extraits automatiquement." },
  { icon: Users, title: "Extraction automatique des personnages", text: "Une fiche détaillée et une image de référence par personnage, réutilisées à l'identique dans chaque prompt." },
  { icon: Film, title: "Détection et découpage des scènes", text: "Détection réelle des changements de plan, ou séquences fixes de 5 à 30 secondes." },
  { icon: Wand2, title: "Génération de prompts professionnels", text: "Treize sections par scène : action, caméra, lumière, voix, son, style et continuité." },
  { icon: MessageSquareText, title: "Transcription des dialogues", text: "Paroles horodatées dans leur langue d'origine. Un passage inaudible n'est jamais inventé." },
  { icon: LayoutGrid, title: "Storyboard automatique", text: "Images de début, de milieu et de fin, plus l'image la plus représentative de chaque scène." },
];
const STEPS = [
  { icon: Upload, title: "Importez", text: "Déposez un fichier MP4, MOV ou WEBM, ou collez un lien vidéo direct." },
  { icon: ScanSearch, title: "Analysez", text: "Le moteur découpe les scènes, extrait les images clés et transcrit l'audio." },
  { icon: Clapperboard, title: "Ajustez", text: "Corrigez dialogues, personnages et descriptions, changez le style ou la langue." },
  { icon: FileText, title: "Exportez", text: "Copiez chaque prompt ou téléchargez le ZIP complet et le rapport PDF." },
];
const fade = { initial: { opacity: 0, y: 18 }, whileInView: { opacity: 1, y: 0 }, viewport: { once: true, margin: "-60px" }, transition: { duration: 0.5 } };

export default function Landing() {
  const { user } = useAuth();
  const cta = user ? "/new" : "/register";
  return (
    <div className="overflow-x-hidden">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <Logo />
        <div className="flex items-center gap-2">
          {user ? (
            <Link href="/dashboard" className="btn-ghost">Tableau de bord</Link>
          ) : (
            <>
              <Link href="/login" className="btn px-3 text-slate-300 hover:text-white">Connexion</Link>
              <Link href="/register" className="btn-ghost">Créer un compte</Link>
            </>
          )}
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-5 pb-20 pt-12 text-center sm:pt-20">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
          <span className="chip mb-6">Pour Google Flow · Veo · Kling · Runway</span>
          <h1 className="mx-auto max-w-4xl font-display text-4xl font-extrabold leading-[1.08] tracking-tight text-white sm:text-6xl">
            RECRÉEZ N&apos;IMPORTE QUELLE VIDÉO AVEC <span className="gradient-text">L&apos;INTELLIGENCE ARTIFICIELLE</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-base text-slate-300 sm:text-lg">
            Analysez vos vidéos, extrayez les personnages, reconstruisez chaque scène et obtenez des prompts détaillés pour donner vie à vos propres créations.
          </p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link href={cta} className="btn-primary px-6 py-3.5 text-base">ANALYSER UNE VIDÉO <ArrowRight className="h-4 w-4" /></Link>
            <a href="#plateforme" className="btn-ghost px-6 py-3.5 text-base">DÉCOUVRIR LA PLATEFORME</a>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.2 }}
          className="card relative mx-auto mt-16 max-w-4xl overflow-hidden p-5 text-left shadow-glow">
          <div className="absolute inset-x-0 top-0 h-px bg-brand-gradient" />
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-brand-cyan">Scène 01 · 00:00 – 00:10</p>
          <div className="grid gap-4 sm:grid-cols-[1fr_1.4fr]">
            <div className="grid grid-cols-3 gap-2">
              {["Début", "Milieu", "Fin"].map((k, i) => (
                <div key={k} className="aspect-[9/14] rounded-lg border border-white/10 bg-gradient-to-b from-ink-600 to-ink-800 p-1.5 text-[10px] text-slate-400" style={{ opacity: 1 - i * 0.12 }}>{k}</div>
              ))}
            </div>
            <pre className="overflow-hidden whitespace-pre-wrap rounded-xl border border-white/10 bg-ink-950/70 p-4 font-mono text-[11.5px] leading-relaxed text-slate-300">
{`1. SCENE DESCRIPTION
2. CHARACTER DESCRIPTION
3. ENVIRONMENT
4. ACTION AND MOVEMENT
5. CAMERA DIRECTION
6. LIGHTING
…
13. CONTINUITY`}
            </pre>
          </div>
          <p className="mt-3 text-xs text-slate-500">Structure du prompt généré pour chaque scène de votre vidéo.</p>
        </motion.div>
      </section>

      <section id="plateforme" className="mx-auto max-w-6xl scroll-mt-10 px-5 py-16">
        <motion.h2 {...fade} className="text-center font-display text-3xl font-bold text-white">Tout ce qu&apos;il faut pour reconstruire une vidéo</motion.h2>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <motion.div key={f.title} {...fade} transition={{ duration: 0.45, delay: i * 0.05 }} className="card card-hover p-6">
              <span className="mb-4 grid h-11 w-11 place-items-center rounded-xl border border-white/10 bg-white/5"><f.icon className="h-5 w-5 text-brand-cyan" /></span>
              <h3 className="font-display text-lg font-semibold text-white">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{f.text}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-5 py-16">
        <motion.h2 {...fade} className="text-center font-display text-3xl font-bold text-white">Comment ça marche</motion.h2>
        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <motion.div key={s.title} {...fade} transition={{ duration: 0.45, delay: i * 0.07 }} className="card relative p-6">
              <span className="font-display text-5xl font-extrabold text-white/10">0{i + 1}</span>
              <s.icon className="absolute right-6 top-6 h-6 w-6 text-brand-violet" />
              <h3 className="mt-3 font-display text-lg font-semibold text-white">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{s.text}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-4xl px-5 pb-20">
        <motion.div {...fade} className="card overflow-hidden p-8 text-center sm:p-12">
          <h2 className="font-display text-2xl font-bold text-white sm:text-3xl">Prêt à analyser votre première vidéo ?</h2>
          <p className="mx-auto mt-3 max-w-xl text-sm text-slate-400">
            Importez uniquement des vidéos dont vous détenez les droits ou l&apos;autorisation d&apos;usage. Les prompts produits sont une reconstruction issue de l&apos;analyse, jamais le prompt d&apos;origine.
          </p>
          <Link href={cta} className="btn-primary mt-7 px-6 py-3.5 text-base">ANALYSER UNE VIDÉO <ArrowRight className="h-4 w-4" /></Link>
        </motion.div>
      </section>

      <footer className="border-t border-white/10 px-5 py-8 text-center text-xs text-slate-500">
        © {new Date().getFullYear()} AI Video Cloner · <Link href="/privacy" className="underline hover:text-slate-300">Confidentialité et droits</Link>
      </footer>
    </div>
  );
}
