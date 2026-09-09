import pytest
import requests
from src.fetch import StockAPIError, fetch_stock_data

class FakeResponse:
    def __init__(self, payload, status=200): self.payload, self.status = payload, status
    def raise_for_status(self):
        if self.status >= 400: raise requests.HTTPError(f"status {self.status}")
    def json(self): return self.payload
class FakeSession:
    def __init__(self, response): self.response = response
    def get(self, *args, **kwargs): return self.response

def test_successful_api_response():
    payload = {"Time Series (Daily)": {"2026-09-08": {"1. open": "1"}}}
    assert fetch_stock_data("AAPL", "key", session=FakeSession(FakeResponse(payload))) == payload
def test_http_failure_is_explicit():
    with pytest.raises(StockAPIError, match="request failed"): fetch_stock_data("AAPL", "key", session=FakeSession(FakeResponse({}, 500)))
def test_provider_rate_limit_is_explicit():
    with pytest.raises(StockAPIError, match="rejected"): fetch_stock_data("AAPL", "key", session=FakeSession(FakeResponse({"Note": "rate limit"})))
def test_missing_series_is_explicit():
    with pytest.raises(StockAPIError, match="no daily time series"): fetch_stock_data("AAPL", "key", session=FakeSession(FakeResponse({"Meta Data": {}})))
