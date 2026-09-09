import json

import pytest

pytest.importorskip("airflow")
from dags.stock_pipeline import dag
from src.transform import parse_stock_data


def test_dag_structure_and_configuration():
    assert dag.dag_id == "stock_market_pipeline"
    assert {task.task_id for task in dag.tasks} == {"fetch_stock_data", "parse_and_validate", "update_postgres"}
    tasks = {task.task_id: task for task in dag.tasks}
    assert tasks["fetch_stock_data"].downstream_task_ids == {"parse_and_validate"}
    assert tasks["parse_and_validate"].downstream_task_ids == {"update_postgres"}
    assert dag.schedule is not None
    assert dag.catchup is False
    assert tasks["fetch_stock_data"].retries == 2
    assert dag.max_active_runs == 1


def test_transformed_payload_is_json_serializable():
    payload = {"Time Series (Daily)": {"2026-09-08": {
        "1. open": "100", "2. high": "110", "3. low": "95", "4. close": "105", "5. volume": "10"
    }}}
    json.dumps(parse_stock_data(payload, "AAPL"))
