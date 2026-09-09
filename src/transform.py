"""Validate and normalize provider data into JSON-safe database records."""
import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

LOGGER = logging.getLogger(__name__)

class StockDataError(ValueError):
    """Raised when a response cannot produce a valid stock record."""

def parse_stock_data(payload: dict[str, Any], symbol: str) -> list[dict[str, Any]]:
    series = payload.get("Time Series (Daily)")
    if not isinstance(series, dict) or not series:
        raise StockDataError("daily time series is missing or empty")
    records: list[dict[str, Any]] = []
    skipped = 0
    for raw_date, values in series.items():
        try:
            parsed_date = date.fromisoformat(str(raw_date))
            if not isinstance(values, dict):
                raise StockDataError("record is not an object")
            record = {"symbol": symbol.upper(), "price_date": parsed_date.isoformat(),
                      "open": _positive_decimal(values, "1. open"),
                      "high": _positive_decimal(values, "2. high"),
                      "low": _positive_decimal(values, "3. low"),
                      "close": _positive_decimal(values, "4. close"),
                      "volume": _non_negative_int(values, "5. volume")}
            if record["high"] < record["low"]:
                raise StockDataError("high is below low")
            # Keep Decimal for validation/precision, then make the task result
            # safe for Airflow's JSON XCom backend.
            records.append({**record, **{key: str(record[key]) for key in ("open", "high", "low", "close")}})
        except (KeyError, TypeError, InvalidOperation, ValueError, StockDataError) as exc:
            skipped += 1
            LOGGER.warning("Skipping stock record %r: %s", raw_date, exc)
            continue
    LOGGER.info("Processed stock records: total=%d valid=%d skipped=%d", len(series), len(records), skipped)
    if not records:
        raise StockDataError("no valid stock records found in daily time series")
    return records

def _positive_decimal(values: dict[str, Any], key: str) -> Decimal:
    result = Decimal(str(values[key]))
    if not result.is_finite() or result <= 0:
        raise StockDataError(f"{key} must be positive")
    return result

def _non_negative_int(values: dict[str, Any], key: str) -> int:
    raw = str(values[key])
    result = int(raw)
    if result < 0:
        raise StockDataError(f"{key} must not be negative")
    return result
