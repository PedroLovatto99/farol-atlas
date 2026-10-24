# Imagem única do backend: serve a API e roda o worker (o comando muda no docker-compose.yml).
# Funciona em amd64 e arm64 (imagens base multi-arquitetura, sem dependência sem wheel arm64).
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

RUN pip install --no-cache-dir uv

WORKDIR /app

# Dependências primeiro, para aproveitar o cache de camadas
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-default-groups --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
RUN uv sync --frozen --no-default-groups

EXPOSE 8000
CMD ["uvicorn", "farol.api.app:criar_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
