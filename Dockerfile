FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Dependencies first, without the project itself, so this layer is cached
# across source-only changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY memory_service ./memory_service
COPY demo_agent ./demo_agent
RUN uv sync --frozen --no-dev

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "memory_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
