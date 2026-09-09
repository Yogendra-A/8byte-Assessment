from types import SimpleNamespace

import pytest

import src.database as database


class FakeDatabaseError(Exception):
    pass


class FakeCursor:
    def __init__(self):
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def configure_database(monkeypatch):
    monkeypatch.setenv("POSTGRES_DB", "stock_pipeline")
    monkeypatch.setenv("POSTGRES_USER", "stock_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")


def test_empty_records_behavior():
    with pytest.raises(ValueError, match="empty"):
        database.update_postgres([])


def test_successful_upsert_commits_and_cleans_up(monkeypatch):
    configure_database(monkeypatch)
    connection = FakeConnection()
    captured = {}
    monkeypatch.setattr(database, "psycopg2", SimpleNamespace(connect=lambda **kwargs: connection, Error=FakeDatabaseError))

    def fake_execute_batch(cursor, sql, records):
        captured["sql"] = sql
        captured["records"] = records

    monkeypatch.setattr(database, "execute_batch", fake_execute_batch)
    records = [{"symbol": "AAPL", "price_date": "2026-09-08", "open": "1", "high": "2", "low": "1", "close": "2", "volume": 3}]
    assert database.update_postgres(records) == 1
    assert connection.committed is True
    assert connection.rolled_back is False
    assert connection.cursor_instance.closed is True
    assert connection.closed is True
    assert "ON CONFLICT (symbol, price_date)" in captured["sql"]


def test_database_exception_rolls_back_reraises_and_cleans_up(monkeypatch):
    configure_database(monkeypatch)
    connection = FakeConnection()
    monkeypatch.setattr(database, "psycopg2", SimpleNamespace(connect=lambda **kwargs: connection, Error=FakeDatabaseError))

    def failing_execute_batch(cursor, sql, records):
        raise FakeDatabaseError("insert failed")

    monkeypatch.setattr(database, "execute_batch", failing_execute_batch)
    with pytest.raises(FakeDatabaseError, match="insert failed"):
        database.update_postgres([{"symbol": "AAPL"}])
    assert connection.rolled_back is True
    assert connection.committed is False
    assert connection.cursor_instance.closed is True
    assert connection.closed is True
