# FIREWISE single-container image: FastAPI serves /api/* and the built UI on one origin.
# Prerequisites on the build host (see README "Deploy"):
#   python3 -I scripts/load_db.py .        -> build/firewise.sqlite
#   (cd ui && npm ci && npm run build)     -> ui/dist/
# The image contains no NASA raw data, no .env and no API key; pass ANTHROPIC_API_KEY at run time if wanted.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ api/
COPY build/firewise.sqlite build/firewise.sqlite
COPY ui/dist/ ui/dist/

RUN useradd --create-home --uid 10001 firewise && chown -R firewise /app
USER firewise

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/health',timeout=4)"
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
