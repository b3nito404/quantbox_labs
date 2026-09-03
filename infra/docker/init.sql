-- initial database schema for QB-01.

CREATE TABLE IF NOT EXISTS ohlcv (
    id          BIGSERIAL PRIMARY KEY,
    exchange    TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    interval    TEXT NOT NULL,
    open_time   TIMESTAMPTZ NOT NULL,
    open        NUMERIC NOT NULL,
    high        NUMERIC NOT NULL,
    low         NUMERIC NOT NULL,
    close       NUMERIC NOT NULL,
    volume      NUMERIC NOT NULL,
    close_time  TIMESTAMPTZ NOT NULL,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (exchange, symbol, interval, open_time)
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_lookup
    ON ohlcv (exchange, symbol, interval, open_time);

CREATE TABLE IF NOT EXISTS backtest_runs (
    id              BIGSERIAL PRIMARY KEY,
    strategy_name   TEXT NOT NULL,
    config          JSONB NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    period_start    TIMESTAMPTZ NOT NULL,
    period_end      TIMESTAMPTZ NOT NULL,
    net_pnl         NUMERIC,
    sharpe          NUMERIC,
    max_drawdown    NUMERIC,
    win_rate        NUMERIC,
    trades_count    INTEGER,
    report_json     JSONB
);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy
    ON backtest_runs (strategy_name, started_at DESC);
