# R2P-IP reference platform — container image.
#
# The repo is a multi-root monorepo: seven `r2pip_*` packages live under
# different directories and are wired onto PYTHONPATH rather than installed
# (mirrors the pytest.ini / scripts/run_demo.py layout — no install step).
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so the layer caches across source-only changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the repo (see .dockerignore for what is excluded).
COPY . .

# Put the seven package roots on PYTHONPATH (container paths under /app).
# Order matches pytest.ini; r2pip_* package names are unique so order is moot.
ENV PYTHONPATH=/app/backend/audit:/app/backend/approval:/app/backend/gateway:/app/graph/ontology:/app/graph/focal:/app/memory:/app/platform

# Default: run the golden-mission demo (prints a report, exits 0 on success).
# docker-compose overrides this to serve the FastAPI app via uvicorn.
CMD ["python", "scripts/run_demo.py"]
