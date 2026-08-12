FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

COPY . .
RUN uv sync --no-dev


FROM python:3.12-slim AS runtime

RUN groupadd --system app \
    && useradd --system --gid app --create-home --home-dir /home/app app

# без HOME/каталога падает с PermissionError на /home/app.
ENV PATH="/app/.venv/bin:$PATH" \
    HOME=/home/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

# каталог должен принадлежать app, иначе mkdir падает с PermissionError.
RUN chmod +x /app/entrypoint.sh \
    && mkdir -p /app/staticfiles \
    && chown -R app:app /app

USER app
EXPOSE 8000

CMD ["/app/entrypoint.sh"]
