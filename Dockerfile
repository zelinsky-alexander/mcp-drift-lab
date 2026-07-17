FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MCP_DRIFT_ROOT=/app

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY manifests ./manifests
COPY scenarios ./scenarios
COPY state ./state
COPY evidence ./evidence
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["mcp-drift-server", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
