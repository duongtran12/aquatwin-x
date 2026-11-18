FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    AQUATWIN_RUNTIME_MODE=real

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/backend/requirements.txt

COPY backend /app/backend
COPY simulation /app/simulation
COPY optimization /app/optimization
COPY experiments /app/experiments

RUN mkdir -p /app/data/benchmark /app/data/processed

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import json, urllib.request; data=json.load(urllib.request.urlopen('http://localhost:8000/api/health/runtime', timeout=3)); assert data['runtime']['effective_mode'] == 'real' and data['runtime']['wntr_available']"

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
