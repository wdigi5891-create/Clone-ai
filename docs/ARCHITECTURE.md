# Architecture

## Flux d'une analyse

```
Navigateur ──upload──▶ API FastAPI ──▶ stockage (local / S3) + PostgreSQL
                          │ enqueue
                          ▼
                    Redis ──▶ worker Celery ──▶ pipeline (services/pipeline.py)
Navigateur ◀─ GET /progress (1,5 s) ─ API ◀─ étapes persistées en base
```

Chaque étape est une ligne `analysis_steps` (statut, progression 0–1, message, erreur). La progression affichée vient
uniquement de ces lignes : nombre de scènes traitées / total, etc. Rien n'est simulé.

| # | Étape | Module | Résultat |
|---|---|---|---|
| 0 | `import` | `api/projects.py` | validation `ffprobe`, stockage, miniature |
| 1 | `metadata` | `video/probe.py` | durée, résolution, cadence, orientation, piste audio |
| 2 | `scenes` | `video/scenes.py` | PySceneDetect (adaptatif, puis contenu) ou découpage fixe ; fusion des plans < 0,6 s |
| 3 | `frames` | `video/frames.py` | début / milieu / fin (FFmpeg) + image la plus nette (variance du Laplacien, OpenCV) |
| 4 | `transcription` | `audio/extract.py`, `ai/` | segments horodatés ; segments incertains marqués non identifiables |
| 5 | `characters` | `ai/tasks.py` | fiches, bloc prompt canonique, image de référence recadrée, scènes d'apparition |
| 6 | `scene_analysis` | `ai/tasks.py` | storyboard par scène, personnages présents, attribution et ton des répliques |
| 7 | `prompts` | `services/prompt_engine.py` | prompt en 13 sections par scène + prompt global |

Une étape en échec arrête le pipeline, conserve les résultats précédents et peut être relancée
(`POST /projects/{id}/retry`) : l'analyse reprend à partir de cette étape.

## Couche d'adaptation IA (`backend/ai/`)

- `base.py` — interfaces `JSONModel` (`generate_json(system, prompt, schema, images)`) et `Transcriber` (`transcribe(audio)`).
- `providers/` — `anthropic_provider.py` (Claude, sortie JSON contrainte par schéma, streaming), `openai_provider.py`
  (vision / texte en JSON strict + Whisper), `faster_whisper_provider.py` (transcription locale).
- `registry.py` — choisit l'implémentation selon `VISION_PROVIDER`, `LLM_PROVIDER`, `TRANSCRIPTION_PROVIDER`.
- `tasks.py` — consignes et schémas JSON des tâches (personnages, scène, prompt, traduction), indépendants du fournisseur.

Ajouter un fournisseur : créer une classe dans `providers/` qui implémente l'interface, puis l'enregistrer dans
`registry.py`. Le pipeline et l'API ne changent pas.

### Suivi des personnages
Le modèle de vision reçoit jusqu'à 24 images clés horodatées couvrant toutes les scènes et doit regrouper les
apparitions d'un même individu sous un identifiant neutre. Les scènes d'apparition sont déduites des images citées,
puis affinées par l'analyse scène par scène (qui reçoit les images de référence recadrées).

### Cohérence des prompts
Le modèle de langage ne rédige que dix sections. Trois sont injectées par le code :
`CHARACTER DESCRIPTION` (bloc canonique de la fiche, identique dans toutes les scènes), `DIALOGUE` (texte exact de la
transcription, langue d'origine) et `DURATION`. Modifier une fiche, une réplique ou une durée met donc à jour tous les
prompts concernés immédiatement, sans nouvel appel IA.

## Stockage
`services/storage.py` expose `put_file / download / read / delete / delete_prefix / exists / url` avec deux
implémentations : locale (URL signées HMAC servies par `/api/files/...`) et S3 (URL présignées).
`services/cleanup.py` (tâche périodique Celery + au démarrage de l'API) purge `storage/tmp` et, si
`SOURCE_RETENTION_HOURS > 0`, les vidéos sources expirées.

## Frontend
Application Next.js (App Router). `src/lib/api.ts` centralise les appels, `src/lib/useProject.ts` suit la progression.
Pages : `/` (accueil), `/login`, `/register`, `/dashboard`, `/new`, `/projects`, `/projects/[id]` (onglets Analyse,
Storyboard, Personnages, Script et dialogues, Prompt Engine, Exporter), `/privacy`.
