FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m app && mkdir -p /app/storage && chown -R app /app
USER app
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
