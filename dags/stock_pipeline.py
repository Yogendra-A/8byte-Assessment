"""Airflow DAG for fetching, validating, and upserting daily stock data."""
import os
import sys
from datetime import datetime, timedelta
from airflow import DAG
from airflow.decorators import task

sys.path.insert(0, "/opt/airflow")
from src.database import update_postgres  # noqa: E402
from src.fetch import fetch_stock_data  # noqa: E402
from src.transform import parse_stock_data  # noqa: E402

with DAG(dag_id="stock_market_pipeline", description="Fetch Alpha Vantage daily data and upsert PostgreSQL records",
         start_date=datetime(2024, 1, 1), schedule=os.getenv("STOCK_SCHEDULE", "@daily"), catchup=False,
         max_active_runs=1, default_args={"owner": "8byte-assessment", "retries": 2, "retry_delay": timedelta(minutes=5)},
         tags=["stocks", "postgres", "assessment"]) as dag:
    @task(task_id="fetch_stock_data")
    def fetch() -> dict:
        return fetch_stock_data()
    @task(task_id="parse_and_validate")
    def parse(payload: dict) -> list[dict]:
        return parse_stock_data(payload, os.getenv("STOCK_SYMBOL", "AAPL"))
    @task(task_id="update_postgres")
    def update(records: list[dict]) -> int:
        return update_postgres(records)
    update(parse(fetch()))
