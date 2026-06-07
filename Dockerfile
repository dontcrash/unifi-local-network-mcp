FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml README.md ./
COPY scripts ./scripts
COPY src ./src
COPY skills ./skills

RUN pip install --no-cache-dir .

USER app
EXPOSE 8000

CMD ["python", "-m", "unifi_mcp"]
