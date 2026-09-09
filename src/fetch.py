"""Fetch raw daily stock data from Alpha Vantage."""
import logging
import os
from typing import Any
import requests

LOGGER = logging.getLogger(__name__)
API_URL = "https://www.alphavantage.co/query"

class StockAPIError(RuntimeError):
    """Raised when the provider returns an unusable response."""

def fetch_stock_data(symbol: str | None = None, api_key: str | None = None,
                     timeout: int | None = None, session: requests.Session | None = None) -> dict[str, Any]:
    symbol = (symbol or os.getenv("STOCK_SYMBOL", "AAPL")).strip().upper()
    api_key = api_key or os.getenv("STOCK_API_KEY", "").strip()
    timeout = timeout or int(os.getenv("STOCK_API_TIMEOUT_SECONDS", "15"))
    if not symbol:
        raise StockAPIError("STOCK_SYMBOL must not be empty")
    if not api_key or api_key == "replace-with-your-api-key":
        raise StockAPIError("STOCK_API_KEY is not configured")
    params = {"function": "TIME_SERIES_DAILY", "symbol": symbol, "apikey": api_key}
    client = session or requests
    try:
        response = client.get(API_URL, params=params, timeout=timeout)
        response.raise_for_status()
    except requests.Timeout as exc:
        raise StockAPIError(f"Alpha Vantage request timed out for {symbol}") from exc
    except requests.RequestException as exc:
        raise StockAPIError(f"Alpha Vantage request failed for {symbol}: {exc}") from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise StockAPIError("Alpha Vantage returned invalid JSON") from exc
    if not isinstance(payload, dict) or not payload:
        raise StockAPIError("Alpha Vantage returned an empty or unexpected JSON response")
    if payload.get("Error Message") or payload.get("Note"):
        raise StockAPIError(f"Alpha Vantage rejected the request: {payload.get('Error Message') or payload.get('Note')}")
    metadata = payload.get("Meta Data")
    response_symbol = metadata.get("2. Symbol") if isinstance(metadata, dict) else None
    if response_symbol and response_symbol.strip().upper() != symbol:
        raise StockAPIError(f"Alpha Vantage returned symbol {response_symbol!r}, expected {symbol!r}")
    if not isinstance(payload.get("Time Series (Daily)"), dict):
        raise StockAPIError("Alpha Vantage response has no daily time series")
    LOGGER.info("Fetched daily stock response for %s", symbol)
    return payload
