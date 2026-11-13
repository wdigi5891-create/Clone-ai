# AI VIDEO CLONER

Plateforme d'analyse vidéo par IA : importez une vidéo, obtenez son découpage en scènes, ses images clés, ses personnages, ses dialogues et un prompt détaillé par scène pour la recréer avec Google Flow / Veo, Kling, Runway, etc.

> Les prompts produits sont une **reconstruction** fondée sur l'analyse de l'image et du son. L'application ne prétend jamais retrouver le prompt d'origine, n'identifie aucune personne réelle et ne contourne aucune protection de plateforme.

## Fonctionnalités

| Module | Ce qu'il fait |
|---|---|
| Import | Fichier MP4 / MOV / WEBM (glisser-déposer, mobile) ou lien direct. Validation réelle par `ffprobe`, limites de taille et de durée, confirmation des droits. |
| Analyse générale | Durée, résolution, cadence, format, orientation, langue parlée, ambiance, style visuel. |
| Scènes | Découpage **intelligent** (PySceneDetect) ou **fixe** (5 / 10 / 15 / 20 / 30 s). |
| Images | Début, milieu, fin + image la plus nette de chaque scène (OpenCV), horodatages exacts, téléchargement unitaire. |
| Personnages | Fiches détaillées, image de référence recadrée, scènes d'apparition, identifiants neutres. |
| Storyboard | Une carte par scène : lieu, décor, actions, caméra, éclairage, sons, dialogues, description cinématographique. |
| Script et dialogues | Transcription horodatée, orateur, ton, émotion, intensité, rythme ; tout est modifiable. Un passage inaudible devient « Dialogue non identifiable ». |
| Prompt Engine | Prompt en 13 sections par scène, anglais par défaut, dialogues conservés dans leur langue. |
| Recréer cette vidéo | Sélection de scènes, 9 styles visuels, langue, durée cible, régénération, prompt global. |
| Export | Images, fiches, storyboard, dialogues (SRT / JSON), prompts, script, ZIP complet, rapport PDF. |
| Tableau de bord | Statistiques, dernières analyses, bibliothèque avec recherche, ouverture et suppression. |

## Architecture

```
frontend/   Next.js 15 · React 19 · TypeScript · Tailwind · Framer Motion · Lucide
backend/
  api/        routes REST FastAPI (auth, projets, édition, exports)
  core/       configuration, base de données, sécurité (JWT, URLs signées, limitation de débit)
  models/     modèles SQLAlchemy
  services/   pipeline d'analyse, prompt engine, stockage, export, import par lien, nettoyage
  video/      ffprobe, détection des scènes (PySceneDetect), images clés (FFmpeg + OpenCV)
  audio/      extraction de la piste audio
  ai/         couche d'adaptation IA + fournisseurs (Anthropic, OpenAI, Gemini, faster-whisper)
  workers/    tâches Celery (analyse, régénération, nettoyage périodique)
  alembic/    migrations
  tests/      tests pytest
database/   schéma SQL de référence     storage/  stockage local (dev)     docs/  documentation
```

Détails : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · API : [docs/API.md](docs/API.md) (et Swagger sur `/docs`).

## Prérequis

- Python 3.11+ · Node.js 20+ · **FFmpeg** (avec `ffprobe`) · PostgreSQL 14+ · Redis 6+
- Clés d'API IA (voir ci-dessous)

## Clés d'API et variables nécessaires

Copiez `.env.example` en `.env` à la racine. Variables indispensables :

| Variable | Rôle |
|---|---|
| `SECRET_KEY` | Signature des jetons et des liens de fichiers. Obligatoire en production. |
| `DATABASE_URL`, `REDIS_URL` | PostgreSQL et Redis. |
| `ANTHROPIC_API_KEY` | Vision + rédaction avec Claude (fournisseur par défaut de `VISION_PROVIDER` et `LLM_PROVIDER`). |
| `OPENAI_API_KEY` | Transcription Whisper (fournisseur par défaut de `TRANSCRIPTION_PROVIDER`), et vision / rédaction si vous choisissez `openai`. |

**Essai gratuit** : une seule clé Google Gemini (niveau gratuit) couvre vision, rédaction et transcription : `VISION_PROVIDER=gemini`, `LLM_PROVIDER=gemini`, `TRANSCRIPTION_PROVIDER=gemini`, `GEMINI_API_KEY=...`. Mise en ligne gratuite pas à pas : [docs/DEPLOY_FREE.md](docs/DEPLOY_FREE.md).

Autres combinaisons possibles : tout OpenAI (`VISION_PROVIDER=openai`, `LLM_PROVIDER=openai`) ; Claude + transcription locale (`TRANSCRIPTION_PROVIDER=faster_whisper` après `pip install faster-whisper`) ; ou `TRANSCRIPTION_PROVIDER=none` pour ignorer les dialogues.

Sans clé, l'import, l'analyse générale, le découpage et l'extraction des images fonctionnent ; les étapes IA s'arrêtent avec un message explicite et peuvent être relancées une fois la clé ajoutée. Aucun résultat factice n'est produit.

## Installation et lancement (développement)

```bash
cp .env.example .env            # puis renseigner les clés

# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head            # crée les tables PostgreSQL
uvicorn main:app --reload --port 8000

# 2. Worker (autre terminal, même venv, depuis backend/)
celery -A workers.celery_app worker -B --loglevel=info

# 3. Frontend (autre terminal)
cd frontend
npm install
npm run dev                     # http://localhost:3000
```

**Démarrage rapide sans PostgreSQL ni Redis** : laissez `DATABASE_URL` vide (SQLite dans `storage/dev.db`, tables créées automatiquement) et mettez `TASK_BACKEND=inline` ; seul `uvicorn` est alors nécessaire côté backend.

**Docker** : `docker compose up --build` démarre PostgreSQL, Redis, l'API (migrations incluses), le worker et le frontend.

## Tests

```bash
cd backend && python -m pytest tests -q
cd frontend && npm run build
```

Les tests génèrent une vraie vidéo avec FFmpeg et exécutent le pipeline complet (découpage, images, exports ZIP/PDF, édition, sécurité). Les fournisseurs IA y sont remplacés par des doubles de test ; ces doubles n'existent que dans `backend/tests/`.

## Sécurité et garde-fous

- Authentification JWT, mots de passe bcrypt, routes protégées, isolation stricte des projets par compte.
- Fichiers servis uniquement par URL signée à durée limitée (ou URL présignée S3).
- Validation des fichiers par extension **et** par analyse `ffprobe` ; limites de taille, de durée et de débit.
- Import par lien : schéma et hôte vérifiés, adresses privées refusées (anti-SSRF), redirections revalidées ; TikTok et les autres plateformes qui interdisent le téléchargement ne sont pas contournées.
- Clés d'API uniquement côté serveur ; `/api/meta` indique seulement si un fournisseur est configuré.
- Suppression d'un projet ou du compte = suppression des fichiers et des données ; fichiers temporaires purgés automatiquement.
- Consignes IA : identifiants neutres, aucune identification de personne réelle, indications de voix génériques (pas de clonage de voix).

## Limites connues

- Avec Gemini, les horodatages des répliques sont estimés par le modèle (moins précis que Whisper).
- Le modèle de vision n'entend pas l'audio : sons d'ambiance et musique ne sont décrits que s'ils sont déductibles de l'image, sinon marqués « non identifiable ». Ton et émotion des répliques sont des estimations.
- L'attribution d'une réplique à un personnage n'est faite que si elle est suffisamment certaine ; il n'y a pas de diarisation audio.
- La limitation de débit est en mémoire (un seul nœud API) ; utilisez un proxy ou Redis pour un déploiement multi-nœuds.
