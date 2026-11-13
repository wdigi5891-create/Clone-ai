# Dockerfile à placer dans un Space Hugging Face (SDK : Docker).
# Il récupère le code public sur GitHub et construit l'application tout-en-un.
FROM node:22-slim AS node

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH NEXT_TELEMETRY_DISABLED=1
WORKDIR /home/user

ARG REPO=https://github.com/wdigi5891-create/Clone-ai
ARG BRANCH=claude/ai-video-cloner-o1sspa
# Invalide le cache de construction dès que la branche change sur GitHub.
ADD --chown=user https://api.github.com/repos/wdigi5891-create/Clone-ai/git/refs/heads/${BRANCH} /home/user/ref.json
RUN git clone --depth 1 --branch "$BRANCH" "$REPO" src

RUN pip install --no-cache-dir --user -r src/backend/requirements.txt
RUN cd src/frontend && npm ci \
    && NEXT_PUBLIC_API_URL="" NEXT_OUTPUT=standalone npm run build \
    && mkdir -p /home/user/app \
    && cp -r .next/standalone /home/user/app/frontend \
    && cp -r .next/static /home/user/app/frontend/.next/static \
    && cp -r /home/user/src/backend /home/user/app/backend \
    && cp /home/user/src/deploy/start.sh /home/user/app/start.sh \
    && rm -rf /home/user/src

WORKDIR /home/user/app
ENV APP_ENV=production TASK_BACKEND=inline PUBLIC_API_URL="" CORS_ORIGINS="" \
    VISION_PROVIDER=gemini LLM_PROVIDER=gemini TRANSCRIPTION_PROVIDER=gemini \
    MAX_UPLOAD_MB=100 MAX_DURATION_SECONDS=180 AI_CONCURRENCY=1
EXPOSE 7860
CMD ["sh", "start.sh"]
