from decimal import Decimal
import json
import pytest
from src.transform import StockDataError, parse_stock_data

def test_parses_all_daily_fields():
    payload = {"Time Series (Daily)": {"2026-09-08": {"1. open": "100.00", "2. high": "110.00", "3. low": "95.00", "4. close": "105.00", "5. volume": "1234"}}}
    record = parse_stock_data(payload, "aapl")[0]
    assert record["symbol"] == "AAPL" and record["open"] == "100.00" and record["volume"] == 1234
    json.dumps(parse_stock_data(payload, "AAPL"))
def test_skips_invalid_day_but_keeps_valid_day():
    valid = {"1. open": "1", "2. high": "2", "3. low": "1", "4. close": "2", "5. volume": "3"}
    assert len(parse_stock_data({"Time Series (Daily)": {"bad-date": valid, "2026-09-08": valid}}, "AAPL")) == 1
def test_empty_or_invalid_data_fails():
    with pytest.raises(StockDataError): parse_stock_data({"Time Series (Daily)": {"2026-09-08": {}}}, "AAPL")

def test_non_finite_numeric_values_are_skipped():
    invalid = {"1. open": "NaN", "2. high": "2", "3. low": "1", "4. close": "2", "5. volume": "3"}
    with pytest.raises(StockDataError):
        parse_stock_data({"Time Series (Daily)": {"2026-09-08": invalid}}, "AAPL")
