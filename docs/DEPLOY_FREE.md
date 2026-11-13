# Mise en ligne gratuite (essai)

Objectif : une adresse web publique, sans rien payer, pour tester l'application avant de la rendre payante.

| Besoin | Solution gratuite | Limites |
|---|---|---|
| Intelligence artificielle (images, prompts, transcription) | **Google Gemini**, niveau gratuit, une seule clé | Quotas par minute et par jour ; Google peut utiliser les contenus du niveau gratuit pour améliorer ses produits |
| Hébergement | **Hugging Face Spaces** (Docker) | Le Space se met en veille sans visite ; **les comptes et les projets sont effacés à chaque redémarrage** tant qu'aucun stockage persistant n'est ajouté |

L'image tout-en-un fait tourner l'interface et l'API dans un seul conteneur, sans PostgreSQL ni Redis
(SQLite + traitement en tâche de fond locale). Les limites y sont réduites : 100 Mo et 3 minutes par vidéo,
une scène analysée à la fois, pour rester dans les quotas gratuits.

## Étapes

1. **Clé Gemini** : sur https://aistudio.google.com/apikey → « Create API key ». Copier la clé.
2. **Compte Hugging Face** : https://huggingface.co/join
3. **Créer le Space** : https://huggingface.co/new-space → nom au choix, SDK **Docker** (modèle « Blank »), matériel gratuit « CPU basic », visibilité publique.
4. **Ajouter la clé** : dans le Space → *Settings* → *Variables and secrets* → *New secret* → nom `GEMINI_API_KEY`, valeur = la clé.
5. **Ajouter les deux fichiers** : dans l'onglet *Files* du Space, remplacer `README.md` et créer `Dockerfile` avec le contenu de
   [`deploy/huggingface/README.md`](../deploy/huggingface/README.md) et [`deploy/huggingface/Dockerfile`](../deploy/huggingface/Dockerfile).
6. Le Space se construit (5 à 10 minutes) puis l'application est disponible à l'adresse du Space.

Pour mettre à jour après un changement de code : *Settings* → *Factory rebuild*.

## Variables utiles

| Variable | Rôle |
|---|---|
| `GEMINI_API_KEY` (secret) | Obligatoire |
| `GEMINI_MODEL` | Modèle utilisé (défaut `gemini-3.8-flash`) |
| `SECRET_KEY` (secret) | Facultatif : sinon une clé aléatoire est créée au démarrage |
| `DATABASE_URL` (secret) | Facultatif : une base PostgreSQL externe pour conserver comptes et projets |
| `MAX_UPLOAD_MB`, `MAX_DURATION_SECONDS` | Limites d'import |

## Passer au payant plus tard

Rien à réécrire : changer `VISION_PROVIDER` / `LLM_PROVIDER` / `TRANSCRIPTION_PROVIDER` pour un fournisseur payant,
brancher PostgreSQL (`DATABASE_URL`) et un stockage S3 (`STORAGE_BACKEND=s3`), ou déployer la pile complète avec `docker-compose.yml`.

## État de vérification

Le mode tout-en-un (script `deploy/start.sh`, relais des pages, envoi de 85 Mo, analyse) a été exécuté et testé hors Docker.
La construction de l'image Docker elle-même et les appels réels à Gemini n'ont pas pu être exécutés dans l'environnement de développement.
