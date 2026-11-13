# API REST

Base : `http://localhost:8000` · documentation interactive : `/docs` (Swagger) et `/redoc`.
Authentification : `Authorization: Bearer <token>`. Erreurs : `{"message": "..."}` avec le code HTTP adapté.

## Authentification
| Méthode | Route | Corps | Description |
|---|---|---|---|
| POST | `/api/auth/register` | `email, password (≥ 8), name, accept_terms` | Crée un compte → `{token, user}` |
| POST | `/api/auth/login` | `email, password` | → `{token, user}` |
| GET | `/api/auth/me` | | Utilisateur courant |
| DELETE | `/api/auth/me` | | Supprime le compte et toutes ses données |

## Import et projets
| Méthode | Route | Corps | Description |
|---|---|---|---|
| POST | `/api/projects/upload` | multipart : `file`, `name`, `rights_confirmed=true` | Importe une vidéo (MP4 / MOV / WEBM) |
| POST | `/api/projects/check-url` | `url` | Vérifie un lien ; 422 avec `code` (`platform_restricted`, `not_video`, …) et `suggestion` |
| POST | `/api/projects/import-url` | `url, name, rights_confirmed` | Importe un lien vidéo direct |
| GET | `/api/projects` | | Bibliothèque |
| GET | `/api/projects/{id}` | | Détail complet (étapes, scènes, images, personnages, dialogues, prompts) |
| PATCH | `/api/projects/{id}` | `name?` | Renomme |
| DELETE | `/api/projects/{id}` | | Supprime le projet et ses fichiers |
| GET | `/api/dashboard` | | Statistiques et dernières analyses |

## Analyse
| Méthode | Route | Corps | Description |
|---|---|---|---|
| POST | `/api/projects/{id}/analyze` | `split_mode: smart\|fixed`, `split_seconds: 5\|10\|15\|20\|30` | Lance l'analyse (202) |
| GET | `/api/projects/{id}/progress` | | Statut du projet et de chaque étape (`status`, `progress`, `message`, `error`) |
| POST | `/api/projects/{id}/retry` | `step?` | Relance à partir d'une étape (par défaut : la première en échec) |

Étapes : `import, metadata, scenes, frames, transcription, characters, scene_analysis, prompts`.
Statuts d'étape : `pending, running, done, failed, skipped`. Statuts de projet : `uploaded, queued, processing, completed, failed`.

## Édition et reconstruction
| Méthode | Route | Corps | Description |
|---|---|---|---|
| PATCH | `/api/projects/{id}/scenes/{sid}` | `data?, description?, target_duration?, selected?, character_indexes?, prompt_sections?` | Modifie une scène |
| PATCH | `/api/projects/{id}/characters/{cid}` | `data?, prompt_descriptor?` | Modifie une fiche personnage |
| POST | `/api/projects/{id}/dialogues` | `start, end, text, character_index?` | Ajoute une réplique |
| PATCH | `/api/projects/{id}/dialogues/{did}` | `text?, start?, end?, character_index?, tone?, emotion?, intensity?, pace?` | Modifie une réplique |
| DELETE | `/api/projects/{id}/dialogues/{did}` | | Supprime une réplique |
| POST | `/api/projects/{id}/prompts/regenerate` | `scene_ids?, language?, style?` | Régénère les prompts (202), suivi via `/progress` |
| POST | `/api/projects/{id}/prompts/global` | `only_selected` | Construit le prompt global |

Toute modification de personnage, de dialogue ou de durée réassemble immédiatement les prompts concernés.
Styles : `cinematic_realism, semi_realistic_3d, 3d_animation, nollywood, documentary, commercial, cinematic_drama, horror, comedy` (ou vide = fidèle à la source).

## Exports et fichiers
| Méthode | Route | Description |
|---|---|---|
| GET | `/api/projects/{id}/export/{kind}` | `images.zip, characters.json, characters.md, storyboard.json, storyboard.md, dialogues.json, dialogues.srt, prompts.txt, global_prompt.txt, script.md, report.pdf, all.zip` |
| GET | `/api/files/{key}?exp=&sig=` | Fichier du stockage local par URL signée (fournie dans les réponses) |
| GET | `/api/meta` | Styles, langues, limites, état de configuration des fournisseurs IA |
| GET | `/api/health` | État du service |

## Exemple
```bash
TOKEN=$(curl -s localhost:8000/api/auth/login -H 'content-type: application/json' \
  -d '{"email":"moi@example.com","password":"motdepasse123"}' | jq -r .token)
ID=$(curl -s localhost:8000/api/projects/upload -H "Authorization: Bearer $TOKEN" \
  -F file=@video.mp4 -F rights_confirmed=true | jq -r .id)
curl -s -X POST localhost:8000/api/projects/$ID/analyze -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' -d '{"split_mode":"fixed","split_seconds":10}'
curl -s localhost:8000/api/projects/$ID/progress -H "Authorization: Bearer $TOKEN"
```
