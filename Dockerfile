# Image tout-en-un (interface + API) pour un hébergeur à conteneur unique,
# par exemple un Space Docker Hugging Face (port 7860).
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1 NEXT_PUBLIC_API_URL="" NEXT_OUTPUT=standalone
RUN npm run build

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
COPY --from=web /usr/local/bin/node /usr/local/bin/node
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app
COPY --chown=user backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir --user -r backend/requirements.txt
COPY --chown=user backend/ backend/
COPY --chown=user --from=web /web/.next/standalone/ frontend/
COPY --chown=user --from=web /web/.next/static/ frontend/.next/static/
COPY --chown=user deploy/start.sh start.sh
ENV APP_ENV=production TASK_BACKEND=inline PUBLIC_API_URL="" CORS_ORIGINS="" \
    VISION_PROVIDER=gemini LLM_PROVIDER=gemini TRANSCRIPTION_PROVIDER=gemini \
    MAX_UPLOAD_MB=100 MAX_DURATION_SECONDS=180 AI_CONCURRENCY=1 NEXT_TELEMETRY_DISABLED=1
EXPOSE 7860
CMD ["sh", "start.sh"]
