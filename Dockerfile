# 1. Build the React frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

# Copy dependencies first for better caching
COPY norn-dashboard/package*.json ./
RUN npm install

# Copy source and build
COPY norn-dashboard/ ./
RUN npm run build

# 2. Build the Python backend and final image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NORN_ENV=production \
    NORN_PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# First copy only files needed for pip install
COPY pyproject.toml README.md ./
COPY norn/ __init__.py norn/
# Install norn with api dependencies
RUN pip install --no-cache-dir -e ".[api]"

# Copy the rest of the backend source code
COPY norn/ norn/

# Copy the built frontend static files from the builder stage
# We'll place them where FastAPI expects them (or configure FastAPI to serve them)
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Expose the API port
EXPOSE 8000

# Run the FastAPI server
# We use uvicorn directly and bind to 0.0.0.0 so it's accessible outside the container
CMD ["uvicorn", "norn.api:app", "--host", "0.0.0.0", "--port", "8000"]
