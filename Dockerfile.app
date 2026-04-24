FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY packages/wttj-app ./packages/wttj-app

RUN uv sync --package wttj-app --frozen --no-dev

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["uv", "run", "streamlit", "run", \
     "packages/wttj-app/src/wttj_app/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0"]
