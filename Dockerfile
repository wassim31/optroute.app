# ── Stage 1: build the React frontend ────────────────────────────────────────
FROM node:20-alpine AS frontend

WORKDIR /build

# Install deps first (cached layer unless package.json changes)
COPY app/frontend/web/package*.json ./app/frontend/web/
RUN cd app/frontend/web && npm ci

# Copy source and build → output lands at app/frontend/static/ (vite outDir: ../static)
COPY app/frontend/web/ ./app/frontend/web/
RUN cd app/frontend/web && npm run build


# ── Stage 2: production Python image ─────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Replace any dev-built static with the freshly built frontend from stage 1
COPY --from=frontend /build/app/frontend/static ./app/frontend/static

# Environment
ENV PORT=8000
EXPOSE 8000

CMD uvicorn app.api.main:app --host 0.0.0.0 --port $PORT
