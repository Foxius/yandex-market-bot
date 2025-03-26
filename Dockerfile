FROM python:3.10-slim AS builder

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

FROM python:3.10-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.10/site-packages/ /usr/local/lib/python3.10/site-packages/

COPY src/ ./src/
COPY locale/ ./locale/
COPY .env .

EXPOSE 8000
CMD ["python", "-m", "src.main"]