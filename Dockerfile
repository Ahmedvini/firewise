# FIREWISE single-container image: FastAPI serves /api/* and the built UI on one origin.
# Self-contained: builds the UI from source and ships the prebuilt scientific database (deploy/firewise.sqlite),
# so it builds the same way locally, in CI and on a hosting platform. Refresh the database with
# scripts/package_deploy.sh (needs the original NASA files, which are not in git).
# The image contains no raw NASA data, no .env and no API key; pass ANTHROPIC_API_KEY at run time if wanted.

# ---------- stage 1: UI (Vite + React) ----------
FROM node:20-slim AS ui
WORKDIR /ui
COPY ui/package.json ui/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY ui/ ./
RUN npm run build

# ---------- stage 2: API + data ----------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000 FIREWISE_STATE_DB=/app/state/twin_state.sqlite
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ api/
COPY deploy/firewise.sqlite build/firewise.sqlite
COPY --from=ui /ui/dist ui/dist/

# User state (Digital Twin scenarios, Copilot conversations, answer cache) lives in /app/state.
# Mount a volume there to keep it across restarts: docker run -v firewise-state:/app/state ...
RUN useradd --create-home --uid 10001 firewise && mkdir -p /app/state && chown -R firewise /app
USER firewise
VOLUME ["/app/state"]

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/health',timeout=4)"
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
