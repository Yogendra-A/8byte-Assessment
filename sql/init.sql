CREATE TABLE IF NOT EXISTS stock_prices (
    symbol VARCHAR(16) NOT NULL,
    price_date DATE NOT NULL,
    open NUMERIC(20, 8) NOT NULL,
    high NUMERIC(20, 8) NOT NULL,
    low NUMERIC(20, 8) NOT NULL,
    close NUMERIC(20, 8) NOT NULL,
    volume BIGINT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (symbol, price_date),
    CONSTRAINT stock_prices_ohlc_valid CHECK (high >= low AND open > 0 AND high > 0 AND low > 0 AND close > 0),
    CONSTRAINT stock_prices_volume_valid CHECK (volume >= 0)
);
