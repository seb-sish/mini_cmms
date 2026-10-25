FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.21 /uv /uvx /bin/

# Install dependencies
COPY pyproject.toml uv.lock* README.md ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy source
COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["/app/.venv/bin/uvicorn", "app.__main__:app", "--host", "0.0.0.0", "--port", "8000"]
