# Stockage

En développement (`STORAGE_BACKEND=local`), les fichiers sont écrits ici :

- `data/projects/<id>/source.<ext>` — vidéo importée
- `data/projects/<id>/frames/` — images clés (`s001_start.jpg`, `s001_middle.jpg`, `s001_end.jpg`, `s001_key.jpg`)
- `data/projects/<id>/characters/` — images de référence des personnages
- `tmp/` — fichiers de travail, supprimés après `TEMP_TTL_HOURS`

En production, utilisez `STORAGE_BACKEND=s3` (AWS S3, MinIO, R2…) : les mêmes clés sont utilisées dans le bucket et les fichiers sont servis par URL présignée.
Ce dossier n'est pas versionné.
