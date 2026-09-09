# Dockerized Stock Market Data Pipeline

This implementation addresses the 8byte assessment using Apache Airflow, Python `requests`, Alpha Vantage, PostgreSQL, and Docker Compose. The assessment allows either Airflow or Dagster; Airflow was selected here. The pipeline fetches daily stock JSON, validates OHLCV fields, and updates an existing PostgreSQL table.

## Architecture

The DAG is `fetch_stock_data` -> `parse_and_validate` -> `update_postgres`. Airflow scheduler runs it, the webserver exposes the UI, and PostgreSQL stores metadata plus `stock_prices`. The default schedule is `@daily` because Alpha Vantage's free tier is rate-limited; set `STOCK_SCHEDULE` to hourly only when the provider plan supports it. Each run processes the one symbol configured by `STOCK_SYMBOL`; the modular code can be extended to multiple symbols later.

## Stack and API

Airflow 2.10.4 with LocalExecutor, Python 3.11, `requests`, `psycopg2`, PostgreSQL 15, Docker Compose, and Alpha Vantage `TIME_SERIES_DAILY`. API keys and symbols are configurable; credentials and API results are not committed.

## Structure

`dags/stock_pipeline.py` contains orchestration. `src/fetch.py`, `src/transform.py`, and `src/database.py` contain reusable business logic. `tests/` contains mocked unit tests. `sql/init.sql` defines the target table. Docker and dependency files are at the repository root.

## Configuration

Copy `.env.example` to `.env`, then set `STOCK_API_KEY`, `POSTGRES_PASSWORD`, `AIRFLOW_ADMIN_USERNAME`, and `AIRFLOW_ADMIN_PASSWORD`. Other settings include `STOCK_SYMBOL`, `STOCK_SCHEDULE`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, and `POSTGRES_USER`. Inside Docker, the database host is the Compose service name `postgres`.

## Database schema

`stock_prices` contains `symbol`, `price_date`, `open`, `high`, `low`, `close`, `volume`, and `fetched_at`. `(symbol, price_date)` is the primary key. The database module uses `INSERT ... ON CONFLICT DO UPDATE`, so repeated runs are idempotent. `sql/init.sql` runs when a new Postgres volume is created.

## Run

Copy `.env.example` to `.env`, set the key and password, then run `docker compose up --build`.

Airflow is at http://localhost:8080 using the values configured by `AIRFLOW_ADMIN_USERNAME` and `AIRFLOW_ADMIN_PASSWORD`. Enable `stock_market_pipeline` and trigger it in the UI. Useful commands are `docker compose exec airflow-scheduler airflow dags list`, `docker compose exec airflow-scheduler airflow dags trigger stock_market_pipeline`, and `docker compose exec postgres psql -U "$env:POSTGRES_USER" -d "$env:POSTGRES_DB" -c "SELECT * FROM stock_prices ORDER BY price_date DESC LIMIT 10;"` after loading those values into your shell.

## Tests

The tests mock HTTP and database behavior and cover successful fetching, HTTP/provider failures, missing data, parsing, invalid records, JSON-safe transformation output, database commit/rollback/cleanup, UPSERT conflict SQL, and DAG structure when Airflow is installed. They do not call a live API. Run `python -m pytest -q`.

## Error handling

Fetching uses timeout, HTTP status checks, JSON validation, provider error/rate-limit detection, and contextual exceptions. Transformation validates dates, numeric values, OHLC relationships, and volume; malformed days are skipped, while an entirely invalid response fails. Database errors are logged, rolled back, re-raised, and retried by Airflow. The DAG has two retries, five-minute retry delays, no catchup, and one active run.

## Scalability and resilience

The code is modular, configuration-driven, and uses batch upserts. The current run handles the configured `STOCK_SYMBOL` only. For multiple symbols or materially larger data volumes, sensible next steps are symbol-level task mapping, incremental ingestion, connection pooling, retention/index planning, and managed PostgreSQL. Kafka, Kubernetes, Redis, Spark, and Celery are intentionally unnecessary here.

## Security, assumptions, and limitations

`.env` is ignored and only placeholders are committed. Airflow administrator credentials are supplied through environment variables. Alpha Vantage limits and availability are external dependencies; failures are surfaced rather than fabricated. The daily endpoint provides daily OHLCV, not intraday data. Remove the Postgres volume manually if initialization must be repeated. Docker runtime execution must be verified on a host with a running Docker daemon; this repository does not claim a successful runtime test unless one has actually been performed.

## PDF requirement checklist

| Requirement | Implementation | Verification |
|---|---|---|
| Docker Compose | `docker-compose.yml`, `Dockerfile` | `docker compose up --build` |
| Airflow container | init, scheduler, webserver | UI and `airflow dags list` |
| Scheduled JSON fetch | Alpha Vantage task, `STOCK_SCHEDULE` | DAG and mocked tests |
| requests API use | `src/fetch.py` | `tests/test_fetch.py` |
| Data extraction | symbol/date/OHLCV parser | `tests/test_transform.py` |
| PostgreSQL update | initialized table and upsert | SQL query above |
| Error management | validation, rollback, retries | tests and task logs |
| Security | environment variables, `.gitignore` | repository review |
| Scalability/resilience | modular code, batch upsert, retries | design notes above |

Before submission, run `docker compose config`, `docker compose build`, unit tests, and a real DAG run with a valid API key. Record any unavailable provider, Docker, or network checks rather than claiming they passed.
