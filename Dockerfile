FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt
COPY . .
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
