FROM python:3.12-slim AS dependencies
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN pip install --no-cache-dir uv==0.13.1 && uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=dependencies /app/.venv /app/.venv
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini backend/pyproject.toml ./
# Runtime does not install packages or run development/test tooling.
RUN python -m pip uninstall -y pip && useradd --create-home appuser
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
