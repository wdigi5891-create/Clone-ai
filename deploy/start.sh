#!/bin/sh
# Démarre l'interface (port interne 3000) puis l'API, seule exposée (port public 7860).
# L'API relaie les pages vers l'interface et reçoit directement les vidéos.
set -e
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
# /data existe si un stockage persistant est attaché ; sinon les données sont perdues au redémarrage.
if [ -d /data ] && [ -w /data ]; then DATA=/data; else DATA="$APP_DIR/data"; fi
mkdir -p "$DATA/files" "$DATA/tmp"
export STORAGE_LOCAL_DIR="${STORAGE_LOCAL_DIR:-$DATA/files}" TEMP_DIR="${TEMP_DIR:-$DATA/tmp}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///$DATA/app.db}"
if [ -z "$SECRET_KEY" ]; then
  # Clé de session aléatoire conservée avec les données.
  [ -f "$DATA/secret_key" ] || python -c "import secrets; print(secrets.token_urlsafe(48))" > "$DATA/secret_key"
  export SECRET_KEY="$(cat "$DATA/secret_key")"
fi
cd "$APP_DIR/backend"
case "$DATABASE_URL" in postgres*) alembic upgrade head ;; esac
(cd "$APP_DIR/frontend" && PORT=3000 HOSTNAME=127.0.0.1 exec node server.js) &
export FRONTEND_PROXY_URL=http://127.0.0.1:3000
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-7860}"
