# syntax=docker/dockerfile:1

# Build stage with uv for fast dependency installation
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Enable bytecode compilation and copy mode for mounted cache
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies first (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project --no-dev

# Copy source code and install the project
COPY src/ src/
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Runtime stage - slim image
FROM python:3.11-slim-bookworm

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY src/ src/

# Set PATH to use the virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Expose API port
EXPOSE 8000

# Run the FastAPI server
CMD ["uvicorn", "agent.services.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
