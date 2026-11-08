# ERIN 2.0 — DATABASE AND DATA MODEL SPECIFICATION

**Version:** 1.0
**Status:** DRAFT
**Classification:** INTERNAL — DATABASE SCHEMA
**Owner:** Financial Data Architect
**Phase:** 2 — Domain & System Architecture

---

## 1. Database Technology Choices

| Purpose | Technology | Configuration |
|---------|------------|---------------|
| **Transactional (OLTP)** | SQLite 3.46+ | WAL mode, `foreign_keys=ON`, `journal_mode=WAL`, `synchronous=NORMAL`, 5 connection pool |
| **Analytical (OLAP)** | DuckDB 1.1+ | `memory_limit='2GB'`, `threads=4`, `preserve_insertion_order=false` |
| **Historical Archive** | Apache Parquet 1.15+ | Partitioned by `date`/`symbol`, Snappy compression, row groups 128MB |
| **Vector Search** | LanceDB 0.12+ | Embedded, IVF_PQ index, int8 quantization |
| **Columnar Exchange** | PyArrow 17+ | Zero-copy between DuckDB/Polars/Pandas/Parquet |

---

## 2. SQLite Schema (Transactional)

### 2.1 Core Tables

```sql
-- packages/data-infra/src/erin/data_infra/schema/sqlite_core.sql

-- Users & Governance
CREATE TABLE users (
    id TEXT PRIMARY KEY,                    -- UUID
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,            -- Argon2id
    roles TEXT NOT NULL,                    -- JSON array of role names
    mfa_enabled INTEGER DEFAULT 0,
    mfa_secret TEXT,
    last_login TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    permissions TEXT NOT NULL,              -- JSON array of permission objects
    description TEXT,
    is_system INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE audit_events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details TEXT,                           -- JSON
    ip_address TEXT,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    prev_hash TEXT NOT NULL,
    hash TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX idx_audit_user_time ON audit_events(user_id, timestamp DESC);
CREATE INDEX idx_audit_resource ON audit_events(resource_type, resource_id);

-- Instrument Master
CREATE TABLE instruments (
    figi TEXT PRIMARY KEY,
    composite_ticker TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    asset_class TEXT NOT NULL,              -- EQUITY, FIXED_INCOME, DERIVATIVE, etc.
    primary_exchange TEXT NOT NULL,
    currency TEXT NOT NULL,                 -- ISO 4217
    country TEXT NOT NULL,
    sector TEXT,
    industry TEXT,
    gics_code TEXT,
    is_active INTEGER DEFAULT 1,
    metadata TEXT,                          -- JSON for extensibility
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_instruments_ticker ON instruments(composite_ticker);
CREATE INDEX idx_instruments_asset_class ON instruments(asset_class);
CREATE INDEX idx_instruments_exchange ON instruments(primary_exchange);

-- Instrument Aliases (provider-specific symbols)
CREATE TABLE instrument_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    figi TEXT NOT NULL,
    provider TEXT NOT NULL,                 -- ProviderId enum
    provider_symbol TEXT NOT NULL,
    is_primary INTEGER DEFAULT 0,
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP,
    FOREIGN KEY (figi) REFERENCES instruments(figi),
    UNIQUE(provider, provider_symbol, valid_from)
);
CREATE INDEX idx_aliases_provider_symbol ON instrument_aliases(provider, provider_symbol);

-- Watchlists
CREATE TABLE watchlists (
    id TEXT PRIMARY KEY,                    -- UUID
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    symbols TEXT NOT NULL,                  -- JSON array of composite_tickers (ordered)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX idx_watchlists_user ON watchlists(user_id);

-- Market Calendar
CREATE TABLE market_calendars (
    exchange TEXT NOT NULL,
    year INTEGER NOT NULL,
    trading_days TEXT NOT NULL,             -- JSON array of ISO dates
    holidays TEXT NOT NULL,                 -- JSON array of {date, name}
    early_closes TEXT NOT NULL,             -- JSON array of {date, time, name}
    PRIMARY KEY (exchange, year)
);

-- Data Providers
CREATE TABLE providers (
    id TEXT PRIMARY KEY,                    -- ProviderId enum
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    auth_type TEXT NOT NULL,                -- API_KEY, OAUTH, NONE
    rate_limit_config TEXT NOT NULL,        -- JSON {requests_per_minute, burst}
    supported_datasets TEXT NOT NULL,       -- JSON array of DatasetId
    licensing_terms TEXT NOT NULL,          -- JSON LicensingTerms
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ingestion Jobs
CREATE TABLE ingestion_jobs (
    id TEXT PRIMARY KEY,                    -- UUID
    provider TEXT NOT NULL,
    dataset TEXT NOT NULL,
    params TEXT NOT NULL,                   -- JSON
    status TEXT NOT NULL,                   -- PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    priority INTEGER DEFAULT 0,             -- Higher = more urgent
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    records_processed INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message TEXT,
    watermark TEXT,                         -- For incremental loads
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (provider) REFERENCES providers(id)
);
CREATE INDEX idx_ingestion_provider_dataset ON ingestion_jobs(provider, dataset);
CREATE INDEX idx_ingestion_status ON ingestion_jobs(status);

-- Data Quality Reports
CREATE TABLE data_quality_reports (
    id TEXT PRIMARY KEY,                    -- UUID
    job_id TEXT NOT NULL,
    dataset TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completeness_score REAL,
    timeliness_score REAL,
    validity_score REAL,
    consistency_score REAL,
    issues TEXT,                            -- JSON array of DataQualityIssue
    FOREIGN KEY (job_id) REFERENCES ingestion_jobs(id)
);

-- Companies (Equity Research)
CREATE TABLE companies (
    id TEXT PRIMARY KEY,                    -- UUID
    cik TEXT UNIQUE NOT NULL,               -- Zero-padded 10 digits
    name TEXT NOT NULL,
    tickers TEXT NOT NULL,                  -- JSON {exchange: ticker}
    primary_exchange TEXT NOT NULL,
    currency TEXT NOT NULL,
    sector TEXT,
    industry TEXT,
    gics_code TEXT,
    headquarters TEXT,                      -- JSON Address
    description TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_companies_cik ON companies(cik);
CREATE INDEX idx_companies_ticker ON companies(tickers);

-- Financial Statements
CREATE TABLE financial_statements (
    id TEXT PRIMARY KEY,                    -- UUID
    company_id TEXT NOT NULL,
    statement_type TEXT NOT NULL,           -- INCOME, BALANCE_SHEET, CASH_FLOW
    period_type TEXT NOT NULL,              -- QUARTERLY, ANNUAL
    period_end DATE NOT NULL,
    filing_date DATE NOT NULL,
    gaap TEXT NOT NULL,                     -- US_GAAP, IFRS
    currency TEXT NOT NULL,
    line_items TEXT NOT NULL,               -- JSON {standardized_tag: value}
    source TEXT NOT NULL,                   -- ProviderId
    source_accession TEXT,                  -- SEC accession
    is_restated INTEGER DEFAULT 0,
    restatement_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, statement_type, period_type, period_end, gaap)
);
CREATE INDEX idx_financials_company_period ON financial_statements(company_id, period_end DESC);
CREATE INDEX idx_financials_filing_date ON financial_statements(filing_date DESC);

-- Financial Ratios (Derived)
CREATE TABLE financial_ratios (
    id TEXT PRIMARY KEY,                    -- UUID
    company_id TEXT NOT NULL,
    period_end DATE NOT NULL,
    ratio_type TEXT NOT NULL,               -- PROFITABILITY, LIQUIDITY, SOLVENCY, EFFICIENCY, VALUATION
    ratio_name TEXT NOT NULL,               -- e.g., "ROE", "CURRENT_RATIO", "DEBT_TO_EQUITY"
    value REAL NOT NULL,
    inputs TEXT NOT NULL,                   -- JSON {input_name: value} for traceability
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    methodology_version TEXT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, period_end, ratio_type, ratio_name)
);

-- Portfolios
CREATE TABLE portfolios (
    id TEXT PRIMARY KEY,                    -- UUID
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    base_currency TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Positions
CREATE TABLE positions (
    id TEXT PRIMARY KEY,                    -- UUID
    portfolio_id TEXT NOT NULL,
    figi TEXT NOT NULL,
    quantity REAL NOT NULL,
    avg_cost REAL NOT NULL,
    currency TEXT NOT NULL,
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
    FOREIGN KEY (figi) REFERENCES instruments(figi),
    UNIQUE(portfolio_id, figi)
);
CREATE INDEX idx_positions_portfolio ON positions(portfolio_id);

-- Cash Balances
CREATE TABLE cash_balances (
    id TEXT PRIMARY KEY,                    -- UUID
    portfolio_id TEXT NOT NULL,
    currency TEXT NOT NULL,
    amount REAL NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
    UNIQUE(portfolio_id, currency)
);

-- Transactions
CREATE TABLE transactions (
    id TEXT PRIMARY KEY,                    -- UUID
    portfolio_id TEXT NOT NULL,
    figi TEXT NOT NULL,
    side TEXT NOT NULL,                     -- BUY, SELL
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    price_currency TEXT NOT NULL,
    fees REAL NOT NULL,
    fees_currency TEXT NOT NULL,
    slippage REAL,
    slippage_currency TEXT,
    executed_at TIMESTAMP NOT NULL,
    status TEXT NOT NULL,                   -- PENDING, FILLED, PARTIAL, CANCELLED, REJECTED
    broker TEXT,
    order_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
    FOREIGN KEY (figi) REFERENCES instruments(figi)
);
CREATE INDEX idx_transactions_portfolio_time ON transactions(portfolio_id, executed_at DESC);
CREATE INDEX idx_transactions_figi_time ON transactions(figi, executed_at DESC);

-- VaR Models
CREATE TABLE var_models (
    id TEXT PRIMARY KEY,                    -- UUID
    name TEXT NOT NULL,
    method TEXT NOT NULL,                   -- HISTORICAL, PARAMETRIC, MONTE_CARLO
    confidence_level REAL NOT NULL,
    horizon_days INTEGER NOT NULL,
    lookback_days INTEGER,
    distribution_assumption TEXT,
    n_simulations INTEGER,
    created_by TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- VaR Results
CREATE TABLE var_results (
    id TEXT PRIMARY KEY,                    -- UUID
    model_id TEXT NOT NULL,
    portfolio_id TEXT NOT NULL,
    as_of_date DATE NOT NULL,
    var_value REAL NOT NULL,
    var_currency TEXT NOT NULL,
    es_value REAL,
    es_currency TEXT,
    confidence_level REAL NOT NULL,
    horizon_days INTEGER NOT NULL,
    method TEXT NOT NULL,
    computation_details TEXT,               -- JSON for reproducibility
    computation_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (model_id) REFERENCES var_models(id),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
);
CREATE INDEX idx_var_results_portfolio_date ON var_results(portfolio_id, as_of_date DESC);

-- Bonds
CREATE TABLE bonds (
    figi TEXT PRIMARY KEY,
    issuer TEXT NOT NULL,
    issuer_type TEXT NOT NULL,              -- GOVERNMENT, CORPORATE, MUNICIPAL, AGENCY, SUPRANATIONAL
    coupon_rate REAL NOT NULL,
    coupon_frequency TEXT NOT NULL,         -- ANNUAL, SEMI_ANNUAL, QUARTERLY, MONTHLY
    day_count TEXT NOT NULL,                -- ACT_ACT, ACT_360, ACT_365, THIRTY_360
    issue_date DATE NOT NULL,
    maturity_date DATE NOT NULL,
    first_coupon_date DATE,
    currency TEXT NOT NULL,
    credit_rating TEXT,
    is_callable INTEGER DEFAULT 0,
    call_schedule TEXT,                     -- JSON array
    is_putable INTEGER DEFAULT 0,
    put_schedule TEXT,                      -- JSON array
    seniority TEXT NOT NULL,                -- SENIOR, SUBORDINATED, JUNIOR
    FOREIGN KEY (figi) REFERENCES instruments(figi)
);

-- Yield Curves
CREATE TABLE yield_curves (
    id TEXT PRIMARY KEY,                    -- UUID
    curve_type TEXT NOT NULL,               -- GOVERNMENT, SWAP, CORPORATE_AAA, etc.
    currency TEXT NOT NULL,
    reference_date DATE NOT NULL,
    tenors TEXT NOT NULL,                   -- JSON array of tenor strings
    rates TEXT NOT NULL,                    -- JSON array of continuously compounded rates
    interpolation_method TEXT NOT NULL,     -- LINEAR, CUBIC_SPLINE, NELSON_SIEGEL
    nelson_siegel_params TEXT,              -- JSON {beta0, beta1, beta2, beta3, tau1, tau2}
    source TEXT NOT NULL,
    quality_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(curve_type, currency, reference_date)
);
CREATE INDEX idx_curves_currency_date ON yield_curves(currency, reference_date DESC);

-- Options
CREATE TABLE options (
    figi TEXT PRIMARY KEY,
    underlying_figi TEXT NOT NULL,
    option_type TEXT NOT NULL,              -- CALL, PUT
    style TEXT NOT NULL,                    -- EUROPEAN, AMERICAN, BERMUDAN
    strike REAL NOT NULL,
    expiration DATE NOT NULL,
    settlement TEXT NOT NULL,               -- PHYSICAL, CASH
    contract_size INTEGER DEFAULT 100,
    currency TEXT NOT NULL,
    exchange TEXT NOT NULL,
    FOREIGN KEY (figi) REFERENCES instruments(figi),
    FOREIGN KEY (underlying_figi) REFERENCES instruments(figi)
);
CREATE INDEX idx_options_underlying ON options(underlying_figi);
CREATE INDEX idx_options_expiration ON options(expiration);

-- Volatility Surfaces
CREATE TABLE volatility_surfaces (
    id TEXT PRIMARY KEY,                    -- UUID
    underlying_figi TEXT NOT NULL,
    reference_date DATE NOT NULL,
    expiries TEXT NOT NULL,                 -- JSON array of dates
    strikes TEXT NOT NULL,                  -- JSON array of strikes
    implied_vols TEXT NOT NULL,             -- JSON 2D array [expiry][strike]
    interpolation TEXT NOT NULL,            -- BICUBIC, SPLINE, SVI
    svi_params TEXT,                        -- JSON if SVI calibrated
    source TEXT NOT NULL,
    quality_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (underlying_figi) REFERENCES instruments(figi),
    UNIQUE(underlying_figi, reference_date)
);

-- Economic Indicators
CREATE TABLE economic_indicators (
    id TEXT PRIMARY KEY,                    -- UUID
    provider TEXT NOT NULL,
    provider_series_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,                 -- GDP, INFLATION, EMPLOYMENT, RATES, PMI, FISCAL, TRADE, MONEY
    frequency TEXT NOT NULL,                -- DAILY, WEEKLY, MONTHLY, QUARTERLY, ANNUAL
    unit TEXT NOT NULL,
    seasonal_adjustment TEXT NOT NULL,      -- SA, NSA
    geography TEXT NOT NULL,                -- ISO country code
    source_url TEXT,
    license_terms TEXT,                     -- JSON LicenseTerms
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (provider) REFERENCES providers(id),
    UNIQUE(provider, provider_series_id)
);

-- Indicator Observations
CREATE TABLE indicator_observations (
    id TEXT PRIMARY KEY,                    -- UUID
    indicator_id TEXT NOT NULL,
    period DATE NOT NULL,
    value REAL NOT NULL,
    revision INTEGER DEFAULT 0,
    published_at TIMESTAMP NOT NULL,
    source TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (indicator_id) REFERENCES economic_indicators(id),
    UNIQUE(indicator_id, period, revision)
);
CREATE INDEX idx_obs_indicator_period ON indicator_observations(indicator_id, period DESC);

-- News Articles
CREATE TABLE news_articles (
    id TEXT PRIMARY KEY,                    -- UUID
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    content_path TEXT,                      -- Path to full content in Parquet/blob
    published_at TIMESTAMP NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    categories TEXT,                        -- JSON array
    sentiment_score REAL,
    entities TEXT,                          -- JSON array of ExtractedEntity
    relevance_scores TEXT,                  -- JSON {composite_ticker: score}
    FOREIGN KEY (source) REFERENCES providers(id)
);
CREATE INDEX idx_news_published ON news_articles(published_at DESC);
CREATE INDEX idx_news_source ON news_articles(source);
CREATE INDEX idx_news_sentiment ON news_articles(sentiment_score);

-- Research Notebooks
CREATE TABLE notebooks (
    id TEXT PRIMARY KEY,                    -- UUID
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    cells TEXT NOT NULL,                    -- JSON array of NotebookCell
    kernel_spec TEXT NOT NULL,              -- JSON KernelSpec
    metadata TEXT,                          -- JSON
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_executed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX idx_notebooks_user ON notebooks(user_id);

-- Workspaces
CREATE TABLE workspaces (
    id TEXT PRIMARY KEY,                    -- UUID
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    layout TEXT NOT NULL,                   -- JSON WorkspaceLayout
    watchlist_ids TEXT,                     -- JSON array of UUIDs
    chart_configs TEXT,                     -- JSON {panel_id: ChartConfig}
    notebook_ids TEXT,                      -- JSON array of UUIDs
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- AI Tool Definitions (Allowlist)
CREATE TABLE tool_definitions (
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    description TEXT NOT NULL,
    input_schema TEXT NOT NULL,             -- JSON Schema
    output_schema TEXT NOT NULL,
    read_only INTEGER DEFAULT 1,
    sensitivity TEXT NOT NULL,              -- LOW, MEDIUM, HIGH, CRITICAL
    allowed_roles TEXT NOT NULL,            -- JSON array
    rate_limit TEXT,                        -- JSON RateLimit
    timeout_seconds INTEGER DEFAULT 30,
    sandbox_profile TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    PRIMARY KEY (name, version)
);

-- AI Tool Calls (Audit)
CREATE TABLE tool_calls (
    id TEXT PRIMARY KEY,                    -- UUID
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    tool_version TEXT NOT NULL,
    inputs TEXT NOT NULL,                   -- JSON
    outputs TEXT,                           -- JSON
    status TEXT NOT NULL,                   -- PENDING, EXECUTING, COMPLETED, FAILED, REJECTED
    sensitivity TEXT NOT NULL,
    approval_id TEXT,                       -- UUID if HIGH/CRITICAL
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    execution_time_ms INTEGER,
    error TEXT,
    hash_chain TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (tool_name, tool_version) REFERENCES tool_definitions(name, version)
);
CREATE INDEX idx_tool_calls_session ON tool_calls(session_id);
CREATE INDEX idx_tool_calls_user_time ON tool_calls(user_id, started_at DESC);

-- Data Licenses
CREATE TABLE data_licenses (
    provider TEXT NOT NULL,
    dataset TEXT NOT NULL,
    commercial_use INTEGER NOT NULL,
    redistribution INTEGER NOT NULL,
    caching_allowed INTEGER NOT NULL,
    caching_max_age_days INTEGER,
    attribution_required INTEGER NOT NULL,
    attribution_text TEXT,
    retention_max_days INTEGER,
    license_url TEXT NOT NULL,
    last_reviewed DATE NOT NULL,
    reviewed_by TEXT NOT NULL,
    status TEXT NOT NULL,                   -- ACTIVE, EXPIRED, RESTRICTED, UNKNOWN
    PRIMARY KEY (provider, dataset),
    FOREIGN KEY (provider) REFERENCES providers(id),
    FOREIGN KEY (reviewed_by) REFERENCES users(id)
);
```

---

## 3. DuckDB Schema (Analytical)

```sql
-- packages/data-infra/src/erin/data_infra/schema/duckdb_analytical.sql

-- Raw Quotes (append-only, partitioned by date)
CREATE TABLE raw_quotes (
    figi VARCHAR,
    provider VARCHAR,
    bid DOUBLE,
    ask DOUBLE,
    last DOUBLE,
    bid_size BIGINT,
    ask_size BIGINT,
    volume BIGINT,
    timestamp TIMESTAMP,
    source_timestamp TIMESTAMP,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_data VARCHAR  -- JSON for provider-specific fields
) PARTITION BY (date_trunc('day', timestamp));

-- Normalized Quotes (validated, deduplicated)
CREATE TABLE normalized_quotes (
    figi VARCHAR,
    bid DOUBLE,
    ask DOUBLE,
    last DOUBLE,
    bid_size BIGINT,
    ask_size BIGINT,
    volume BIGINT,
    timestamp TIMESTAMP,
    currency VARCHAR,
    source VARCHAR,
    quality_score DOUBLE,
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) PARTITION BY (date_trunc('day', timestamp));

-- Adjusted Quotes (corporate actions applied)
CREATE TABLE adjusted_quotes (
    figi VARCHAR,
    adj_open DOUBLE,
    adj_high DOUBLE,
    adj_low DOUBLE,
    adj_close DOUBLE,
    adj_volume BIGINT,
    timestamp TIMESTAMP,
    adjustment_factor DOUBLE,
    adjustment_type VARCHAR,  -- SPLIT, DIVIDEND, SPINOFF, MERGER
    corporate_action_id VARCHAR
) PARTITION BY (date_trunc('day', timestamp));

-- Derived: Daily Returns
CREATE TABLE daily_returns (
    figi VARCHAR,
    date DATE,
    simple_return DOUBLE,
    log_return DOUBLE,
    close_price DOUBLE,
    volume BIGINT,
    currency VARCHAR
) PARTITION BY date;

-- Derived: Factor Exposures (updated daily)
CREATE TABLE factor_exposures (
    figi VARCHAR,
    date DATE,
    market_beta DOUBLE,
    size_factor DOUBLE,
    value_factor DOUBLE,
    momentum_factor DOUBLE,
    quality_factor DOUBLE,
    volatility_factor DOUBLE,
    r_squared DOUBLE
) PARTITION BY date;

-- Derived: Risk Metrics (per portfolio, daily)
CREATE TABLE portfolio_risk_metrics (
    portfolio_id VARCHAR,
    date DATE,
    var_95_1d DOUBLE,
    var_99_1d DOUBLE,
    var_95_10d DOUBLE,
    var_99_10d DOUBLE,
    es_95_1d DOUBLE,
    es_99_1d DOUBLE,
    portfolio_value DOUBLE,
    currency VARCHAR
) PARTITION BY date;

-- Macro Indicator Observations (wide format for analysis)
CREATE TABLE macro_observations (
    indicator_id VARCHAR,
    period DATE,
    value DOUBLE,
    revision INTEGER,
    published_at TIMESTAMP,
    geography VARCHAR,
    category VARCHAR
) PARTITION BY period;

-- News Sentiment Aggregations (daily per instrument)
CREATE TABLE daily_news_sentiment (
    figi VARCHAR,
    date DATE,
    article_count INTEGER,
    avg_sentiment DOUBLE,
    weighted_sentiment DOUBLE,  -- Weighted by relevance
    positive_count INTEGER,
    negative_count INTEGER,
    neutral_count INTEGER
) PARTITION BY date;

-- Model Results (backtests, simulations)
CREATE TABLE model_results (
    model_id VARCHAR,
    run_id VARCHAR,
    timestamp TIMESTAMP,
    parameters VARCHAR,  -- JSON
    metrics VARCHAR,     -- JSON {metric_name: value}
    outputs_path VARCHAR -- Path to Parquet with detailed outputs
) PARTITION BY date_trunc('day', timestamp);
```

---

## 4. Parquet Partitioning Strategy

### 4.1 Directory Structure
```
/data/parquet/
├── raw_quotes/
│   ├── date=2026-01-01/
│   │   ├── symbol=AAPL.US.parquet
│   │   ├── symbol=MSFT.US.parquet
│   │   └── ...
│   ├── date=2026-01-02/
│   └── ...
├── normalized_quotes/
│   ├── date=2026-01-01/
│   └── ...
├── adjusted_quotes/
│   ├── date=2026-01-01/
│   └── ...
├── daily_returns/
│   ├── date=2026-01-01.parquet
│   └── ...
├── factor_exposures/
│   ├── date=2026-01-01.parquet
│   └── ...
├── portfolio_risk_metrics/
│   ├── date=2026-01-01.parquet
│   └── ...
├── macro_observations/
│   ├── period=2026-01-01.parquet
│   └── ...
├── daily_news_sentiment/
│   ├── date=2026-01-01.parquet
│   └── ...
└── model_results/
    ├── date=2026-01-01.parquet
    └── ...
```

### 4.2 Parquet Schema (Example: normalized_quotes)
```python
# packages/data-infra/src/erin/data_infra/schema/parquet_schemas.py

import pyarrow as pa

NORMALIZED_QUOTES_SCHEMA = pa.schema([
    pa.field('figi', pa.string(), nullable=False),
    pa.field('bid', pa.float64(), nullable=True),
    pa.field('ask', pa.float64(), nullable=True),
    pa.field('last', pa.float64(), nullable=True),
    pa.field('bid_size', pa.int64(), nullable=True),
    pa.field('ask_size', pa.int64(), nullable=True),
    pa.field('volume', pa.int64(), nullable=True),
    pa.field('timestamp', pa.timestamp('us'), nullable=False),
    pa.field('currency', pa.string(), nullable=False),
    pa.field('source', pa.string(), nullable=False),
    pa.field('quality_score', pa.float64(), nullable=True),
    pa.field('ingestion_timestamp', pa.timestamp('us'), nullable=False),
])

# Partitioning: by date (day) and symbol (for raw)
# Row group size: 128 MB
# Compression: SNAPPY
# Statistics: enabled (min/max for predicate pushdown)
```

---

## 5. Migration Strategy

### 5.1 SQLite Migrations (Alembic)
```python
# packages/data-infra/alembic/env.py
# Migration files in packages/data-infra/alembic/versions/
# Naming: YYYYMMDD_HHMMSS_description.py
# Each migration: upgrade() / downgrade() with raw SQL
# Run on application startup (blocking)
```

### 5.2 DuckDB Migrations
- Schema version stored in `duckdb_schema_version` table
- Migrations applied on startup (idempotent `CREATE TABLE IF NOT EXISTS`)
- Parquet partitioning handled by ingestion pipeline (no schema migration needed)

### 5.3 Safety Rules
- **No DROP COLUMN** in SQLite (use `ADD COLUMN` + view for removal)
- **No RENAME TABLE** without data copy verification
- **Backward compatible** changes only in minor versions
- **Breaking changes** require major version + ADR + migration script

---

## 6. Connection Configuration

### 6.1 SQLite (Local)
```python
# packages/data-infra/src/erin/data_infra/connections/sqlite.py

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path.home() / ".erin" / "data" / "erin.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(
        DB_PATH,
        isolation_level=None,  # Autocommit off, manual transactions
        check_same_thread=False,
        timeout=30.0
    )
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-32768")  # 32MB cache
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def transaction():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

### 6.2 DuckDB (Local)
```python
# packages/data-infra/src/erin/data_infra/connections/duckdb.py

import duckdb
from pathlib import Path

DB_PATH = Path.home() / ".erin" / "data" / "erin_analytics.duckdb"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_connection() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(str(DB_PATH), read_only=False)
    conn.execute("SET memory_limit='2GB'")
    conn.execute("SET threads=4")
    conn.execute("SET preserve_insertion_order=false")
    conn.execute("INSTALL parquet; LOAD parquet")
    conn.execute("INSTALL arrow; LOAD arrow")
    return conn
```

---

## 7. Data Retention & Archival

| Data Type | Hot (SSD) | Warm (HDD/Network) | Cold (Object Storage) |
|-----------|-----------|-------------------|----------------------|
| Raw Quotes | 30 days | 2 years | Forever |
| Normalized Quotes | 90 days | 5 years | Forever |
| Adjusted Quotes | 1 year | 10 years | Forever |
| Daily Returns | 1 year | Forever | Forever |
| Factor Exposures | 1 year | 5 years | Forever |
| Portfolio Risk Metrics | 1 year | 7 years | Forever |
| Macro Observations | 2 years | Forever | Forever |
| News Articles | 90 days | 2 years | 7 years (compliance) |
| Model Results | 30 days | 1 year | Forever |
| Audit Events | 1 year | 7 years | Forever (immutable) |

---

## 8. Backup & Recovery

### 8.1 Local (Development)
```bash
# SQLite: .backup command (online, consistent)
sqlite3 erin.db ".backup erin_backup_$(date +%Y%m%d).db"

# DuckDB: EXPORT DATABASE (consistent snapshot)
duckdb erin_analytics.duckdb -c "EXPORT DATABASE 'backup_$(date +%Y%m%d)' (FORMAT PARQUET);"

# Parquet: rsync to external drive
rsync -av --delete ~/.erin/data/parquet/ /mnt/backup/erin/parquet/
```

### 8.2 Server (Production)
- PostgreSQL: `pg_dump` + WAL-G for PITR
- DuckDB: Periodic `EXPORT DATABASE` to S3
- Parquet: S3 versioning + lifecycle policies
- Audit: Immutable write-once storage (S3 Object Lock)

---

## 9. Performance Indexing Strategy

### 9.1 SQLite Indexes (from schema above)
- All foreign keys indexed
- Time-series queries: composite indexes on `(entity_id, timestamp DESC)`
- Lookup queries: unique constraints create indexes automatically

### 9.2 DuckDB Indexes
```sql
-- DuckDB uses zone maps (min/max per column per row group) automatically
-- For point lookups: CREATE INDEX on high-cardinality columns
CREATE INDEX idx_normalized_quotes_figi_time ON normalized_quotes(figi, timestamp);
CREATE INDEX idx_daily_returns_figi_date ON daily_returns(figi, date);
```

### 9.3 Parquet Statistics
- Enable `write_statistics=true` (default)
- Row group size: 128 MB (balance between predicate pushdown and read amplification)
- Sort data by partition key + high-cardinality column before write

---

## 10. Approval

**Financial Data Architect:** _________________ **Date:** __________

**Principal Architect:** _________________ **Date:** __________

**SRE:** _________________ **Date:** __________