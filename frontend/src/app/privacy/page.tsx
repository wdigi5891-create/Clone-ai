import Link from "next/link";
import { Logo } from "@/components/ui";

const SECTIONS: [string, string[]][] = [
  ["Données traitées", [
    "Compte : adresse e-mail, nom facultatif et mot de passe (stocké sous forme d'empreinte bcrypt, jamais en clair).",
    "Projets : la vidéo importée, les images extraites, la transcription, les fiches personnages et les prompts générés.",
  ]],
  ["Utilisation de l'intelligence artificielle", [
    "Pour l'analyse, des images clés et la piste audio de votre vidéo sont transmises aux fournisseurs d'IA configurés par l'exploitant de la plateforme (vision, langage, transcription).",
    "Les prompts produits sont une reconstruction fondée sur l'analyse de l'image et du son. Ils ne sont jamais présentés comme le prompt d'origine de la vidéo.",
  ]],
  ["Vos droits sur les vidéos", [
    "Vous ne devez importer que des vidéos dont vous êtes l'auteur ou pour lesquelles vous disposez d'une autorisation. Cette confirmation est demandée et enregistrée à chaque import.",
    "L'import par lien n'utilise que des accès autorisés : aucun contournement des protections ou restrictions des plateformes n'est effectué.",
  ]],
  ["Personnes et voix", [
    "La plateforme n'identifie aucune personne réelle : les personnages reçoivent des identifiants neutres (Personnage 1, 2…) et des descriptions purement visuelles.",
    "Il est interdit d'utiliser les résultats pour usurper l'identité d'une personne réelle ou cloner sa voix sans son consentement. Les indications de voix générées décrivent un ton, jamais une voix à imiter.",
  ]],
  ["Conservation et suppression", [
    "Les fichiers temporaires de traitement sont supprimés automatiquement après expiration.",
    "Vous pouvez supprimer un projet à tout moment depuis la bibliothèque : la vidéo, les images et les analyses associées sont effacées. La suppression du compte efface l'ensemble de vos données.",
  ]],
  ["Sécurité", [
    "Accès protégé par authentification, fichiers servis par liens signés à durée limitée, clés d'API conservées côté serveur uniquement.",
  ]],
];

export default function Privacy() {
  return (
    <div className="mx-auto max-w-3xl px-5 py-10">
      <Logo />
      <h1 className="mt-10 font-display text-3xl font-bold text-white">Confidentialité, consentement et droits</h1>
      <p className="mt-2 text-sm text-slate-400">Modèle de politique à adapter par l&apos;exploitant de la plateforme (identité du responsable de traitement, durées, sous-traitants).</p>
      <div className="mt-8 space-y-4">
        {SECTIONS.map(([title, items]) => (
          <section key={title} className="card p-6">
            <h2 className="font-display text-lg font-semibold text-white">{title}</h2>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-relaxed text-slate-300">
              {items.map((t) => <li key={t}>{t}</li>)}
            </ul>
          </section>
        ))}
      </div>
      <Link href="/" className="btn-ghost mt-8">Retour à l&apos;accueil</Link>
    </div>
  );
}
