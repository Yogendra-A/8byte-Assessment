"""PostgreSQL persistence for normalized stock records."""
import logging
import os
from collections.abc import Sequence
from typing import Any
LOGGER = logging.getLogger(__name__)

try:
    import psycopg2
    from psycopg2.extras import execute_batch
except ModuleNotFoundError:  # Allows unit tests that mock the driver to run locally.
    psycopg2 = None
    execute_batch = None

def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"required database configuration {name} is missing")
    return value

def update_postgres(records: Sequence[dict[str, Any]]) -> int:
    if not records:
        raise ValueError("cannot update PostgreSQL with an empty record list")
    global psycopg2, execute_batch
    if psycopg2 is None or execute_batch is None:
        import psycopg2 as psycopg2_module
        from psycopg2.extras import execute_batch as execute_batch_function
        psycopg2 = psycopg2_module
        execute_batch = execute_batch_function
    config = {"host": os.getenv("POSTGRES_HOST", "postgres"), "port": os.getenv("POSTGRES_PORT", "5432"),
              "dbname": _required_env("POSTGRES_DB"), "user": _required_env("POSTGRES_USER"),
              "password": _required_env("POSTGRES_PASSWORD")}
    sql = """INSERT INTO stock_prices (symbol, price_date, open, high, low, close, volume)
        VALUES (%(symbol)s, %(price_date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s)
        ON CONFLICT (symbol, price_date) DO UPDATE SET open=EXCLUDED.open, high=EXCLUDED.high,
        low=EXCLUDED.low, close=EXCLUDED.close, volume=EXCLUDED.volume, fetched_at=NOW()"""
    connection = None
    try:
        connection = psycopg2.connect(**config)
        with connection.cursor() as cursor:
            execute_batch(cursor, sql, records)
        connection.commit()
        LOGGER.info("Upserted %d stock records", len(records))
        return len(records)
    except psycopg2.Error:
        if connection is not None:
            connection.rollback()
        LOGGER.exception("PostgreSQL stock record update failed")
        raise
    finally:
        if connection is not None:
            connection.close()
