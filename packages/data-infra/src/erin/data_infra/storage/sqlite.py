"""SQLite Storage - Transactional local persistence with WAL mode."""

import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Optional, List, Dict, Any, Generator, Union
import json

from erin.data_infra.storage.interfaces import StorageBackend

logger = logging.getLogger(__name__)


class SQLiteStorage:
    """SQLite storage backend with WAL mode for transactional workloads."""
    
    def __init__(self, db_path: str = "~/.erin/data/erin.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database with schema."""
        with self.get_connection() as conn:
            conn.executescript("""
                -- Users & Governance
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    roles TEXT NOT NULL,
                    mfa_enabled INTEGER DEFAULT 0,
                    mfa_secret TEXT,
                    last_login TIMESTAMP,
                    failed_login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS roles (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    permissions TEXT NOT NULL,
                    description TEXT,
                    is_system INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    prev_hash TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE INDEX IF NOT EXISTS idx_audit_user_time ON audit_events(user_id, timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_events(resource_type, resource_id);

                -- Instrument Master
                CREATE TABLE IF NOT EXISTS instruments (
                    figi TEXT PRIMARY KEY,
                    composite_ticker TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    primary_exchange TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    country TEXT NOT NULL,
                    sector TEXT,
                    industry TEXT,
                    gics_code TEXT,
                    is_active INTEGER DEFAULT 1,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_instruments_ticker ON instruments(composite_ticker);
                CREATE INDEX IF NOT EXISTS idx_instruments_asset_class ON instruments(asset_class);
                CREATE INDEX IF NOT EXISTS idx_instruments_exchange ON instruments(primary_exchange);

                -- Instrument Aliases (provider-specific symbols)
                CREATE TABLE IF NOT EXISTS instrument_aliases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    figi TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    provider_symbol TEXT NOT NULL,
                    is_primary INTEGER DEFAULT 0,
                    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    valid_to TIMESTAMP,
                    FOREIGN KEY (figi) REFERENCES instruments(figi),
                    UNIQUE(provider, provider_symbol, valid_from)
                );
                CREATE INDEX IF NOT EXISTS idx_aliases_provider_symbol ON instrument_aliases(provider, provider_symbol);

                -- Watchlists
                CREATE TABLE IF NOT EXISTS watchlists (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    symbols TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE INDEX IF NOT EXISTS idx_watchlists_user ON watchlists(user_id);

                -- Market Calendar
                CREATE TABLE IF NOT EXISTS market_calendars (
                    exchange TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    trading_days TEXT NOT NULL,
                    holidays TEXT NOT NULL,
                    early_closes TEXT NOT NULL,
                    PRIMARY KEY (exchange, year)
                );

                -- Data Providers
                CREATE TABLE IF NOT EXISTS providers (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    auth_type TEXT NOT NULL,
                    rate_limit_config TEXT NOT NULL,
                    supported_datasets TEXT NOT NULL,
                    licensing_terms TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Ingestion Jobs
                CREATE TABLE IF NOT EXISTS ingestion_jobs (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    dataset TEXT NOT NULL,
                    params TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    records_processed INTEGER DEFAULT 0,
                    records_failed INTEGER DEFAULT 0,
                    error_message TEXT,
                    watermark TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (provider) REFERENCES providers(id)
                );
                CREATE INDEX IF NOT EXISTS idx_ingestion_provider_dataset ON ingestion_jobs(provider, dataset);
                CREATE INDEX IF NOT EXISTS idx_ingestion_status ON ingestion_jobs(status);

                -- Data Quality Reports
                CREATE TABLE IF NOT EXISTS data_quality_reports (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    dataset TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completeness_score REAL,
                    timeliness_score REAL,
                    validity_score REAL,
                    consistency_score REAL,
                    issues TEXT,
                    FOREIGN KEY (job_id) REFERENCES ingestion_jobs(id)
                );

                -- Companies (Equity Research)
                CREATE TABLE IF NOT EXISTS companies (
                    id TEXT PRIMARY KEY,
                    cik TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    tickers TEXT NOT NULL,
                    primary_exchange TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    sector TEXT,
                    industry TEXT,
                    gics_code TEXT,
                    headquarters TEXT,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_companies_cik ON companies(cik);
                CREATE INDEX IF NOT EXISTS idx_companies_ticker ON companies(tickers);

                -- Financial Statements
                CREATE TABLE IF NOT EXISTS financial_statements (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    statement_type TEXT NOT NULL,
                    period_type TEXT NOT NULL,
                    period_end DATE NOT NULL,
                    filing_date DATE NOT NULL,
                    gaap TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    line_items TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_accession TEXT,
                    is_restated INTEGER DEFAULT 0,
                    restatement_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies(id),
                    UNIQUE(company_id, statement_type, period_type, period_end, gaap)
                );
                CREATE INDEX IF NOT EXISTS idx_financials_company_period ON financial_statements(company_id, period_end DESC);
                CREATE INDEX IF NOT EXISTS idx_financials_filing_date ON financial_statements(filing_date DESC);

                -- Financial Ratios (Derived)
                CREATE TABLE IF NOT EXISTS financial_ratios (
                    id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    period_end DATE NOT NULL,
                    ratio_type TEXT NOT NULL,
                    ratio_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    inputs TEXT NOT NULL,
                    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    methodology_version TEXT NOT NULL,
                    FOREIGN KEY (company_id) REFERENCES companies(id),
                    UNIQUE(company_id, period_end, ratio_type, ratio_name)
                );

                -- Portfolios
                CREATE TABLE IF NOT EXISTS portfolios (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    base_currency TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                -- Positions
                CREATE TABLE IF NOT EXISTS positions (
                    id TEXT PRIMARY KEY,
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
                CREATE INDEX IF NOT EXISTS idx_positions_portfolio ON positions(portfolio_id);

                -- Cash Balances
                CREATE TABLE IF NOT EXISTS cash_balances (
                    id TEXT PRIMARY KEY,
                    portfolio_id TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    amount REAL NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
                    UNIQUE(portfolio_id, currency)
                );

                -- Transactions
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    portfolio_id TEXT NOT NULL,
                    figi TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    price_currency TEXT NOT NULL,
                    fees REAL NOT NULL,
                    fees_currency TEXT NOT NULL,
                    slippage REAL,
                    slippage_currency TEXT,
                    executed_at TIMESTAMP NOT NULL,
                    status TEXT NOT NULL,
                    broker TEXT,
                    order_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
                    FOREIGN KEY (figi) REFERENCES instruments(figi)
                );
                CREATE INDEX IF NOT EXISTS idx_transactions_portfolio_time ON transactions(portfolio_id, executed_at DESC);
                CREATE INDEX IF NOT EXISTS idx_transactions_figi_time ON transactions(figi, executed_at DESC);

                -- VaR Models
                CREATE TABLE IF NOT EXISTS var_models (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    method TEXT NOT NULL,
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
                CREATE TABLE IF NOT EXISTS var_results (
                    id TEXT PRIMARY KEY,
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
                    computation_details TEXT,
                    computation_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (model_id) REFERENCES var_models(id),
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
                );
                CREATE INDEX IF NOT EXISTS idx_var_results_portfolio_date ON var_results(portfolio_id, as_of_date DESC);

                -- Bonds
                CREATE TABLE IF NOT EXISTS bonds (
                    figi TEXT PRIMARY KEY,
                    issuer TEXT NOT NULL,
                    issuer_type TEXT NOT NULL,
                    coupon_rate REAL NOT NULL,
                    coupon_frequency TEXT NOT NULL,
                    day_count TEXT NOT NULL,
                    issue_date DATE NOT NULL,
                    maturity_date DATE NOT NULL,
                    first_coupon_date DATE,
                    currency TEXT NOT NULL,
                    credit_rating TEXT,
                    is_callable INTEGER DEFAULT 0,
                    call_schedule TEXT,
                    is_putable INTEGER DEFAULT 0,
                    put_schedule TEXT,
                    seniority TEXT NOT NULL,
                    FOREIGN KEY (figi) REFERENCES instruments(figi)
                );

                -- Yield Curves
                CREATE TABLE IF NOT EXISTS yield_curves (
                    id TEXT PRIMARY KEY,
                    curve_type TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    reference_date DATE NOT NULL,
                    tenors TEXT NOT NULL,
                    rates TEXT NOT NULL,
                    interpolation_method TEXT NOT NULL,
                    nelson_siegel_params TEXT,
                    source TEXT NOT NULL,
                    quality_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(curve_type, currency, reference_date)
                );
                CREATE INDEX IF NOT EXISTS idx_curves_currency_date ON yield_curves(currency, reference_date DESC);

                -- Options
                CREATE TABLE IF NOT EXISTS options (
                    figi TEXT PRIMARY KEY,
                    underlying_figi TEXT NOT NULL,
                    option_type TEXT NOT NULL,
                    style TEXT NOT NULL,
                    strike REAL NOT NULL,
                    expiration DATE NOT NULL,
                    settlement TEXT NOT NULL,
                    contract_size INTEGER DEFAULT 100,
                    currency TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    FOREIGN KEY (figi) REFERENCES instruments(figi),
                    FOREIGN KEY (underlying_figi) REFERENCES instruments(figi)
                );
                CREATE INDEX IF NOT EXISTS idx_options_underlying ON options(underlying_figi);
                CREATE INDEX IF NOT EXISTS idx_options_expiration ON options(expiration);

                -- Volatility Surfaces
                CREATE TABLE IF NOT EXISTS volatility_surfaces (
                    id TEXT PRIMARY KEY,
                    underlying_figi TEXT NOT NULL,
                    reference_date DATE NOT NULL,
                    expiries TEXT NOT NULL,
                    strikes TEXT NOT NULL,
                    implied_vols TEXT NOT NULL,
                    interpolation TEXT NOT NULL,
                    svi_params TEXT,
                    source TEXT NOT NULL,
                    quality_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (underlying_figi) REFERENCES instruments(figi),
                    UNIQUE(underlying_figi, reference_date)
                );

                -- Economic Indicators
                CREATE TABLE IF NOT EXISTS economic_indicators (
                    id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    provider_series_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    seasonal_adjustment TEXT NOT NULL,
                    geography TEXT NOT NULL,
                    source_url TEXT,
                    license_terms TEXT,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (provider) REFERENCES providers(id),
                    UNIQUE(provider, provider_series_id)
                );

                -- Indicator Observations
                CREATE TABLE IF NOT EXISTS indicator_observations (
                    id TEXT PRIMARY KEY,
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
                CREATE INDEX IF NOT EXISTS idx_obs_indicator_period ON indicator_observations(indicator_id, period DESC);

                -- News Articles
                CREATE TABLE IF NOT EXISTS news_articles (
                    id TEXT PRIMARY KEY,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    content_path TEXT,
                    published_at TIMESTAMP NOT NULL,
                    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    language TEXT DEFAULT 'en',
                    categories TEXT,
                    sentiment_score REAL,
                    entities TEXT,
                    relevance_scores TEXT,
                    FOREIGN KEY (source) REFERENCES providers(id)
                );
                CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_at DESC);
                CREATE INDEX IF NOT EXISTS idx_news_source ON news_articles(source);
                CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_articles(sentiment_score);

                -- Research Notebooks
                CREATE TABLE IF NOT EXISTS notebooks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    cells TEXT NOT NULL,
                    kernel_spec TEXT NOT NULL,
                    metadata TEXT,
                    version INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_executed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                CREATE INDEX IF NOT EXISTS idx_notebooks_user ON notebooks(user_id);

                -- Workspaces
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    layout TEXT NOT NULL,
                    watchlist_ids TEXT,
                    chart_configs TEXT,
                    notebook_ids TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                -- AI Tool Definitions (Allowlist)
                CREATE TABLE IF NOT EXISTS tool_definitions (
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    description TEXT NOT NULL,
                    input_schema TEXT NOT NULL,
                    output_schema TEXT NOT NULL,
                    read_only INTEGER DEFAULT 1,
                    sensitivity TEXT NOT NULL,
                    allowed_roles TEXT NOT NULL,
                    rate_limit TEXT,
                    timeout_seconds INTEGER DEFAULT 30,
                    sandbox_profile TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    PRIMARY KEY (name, version)
                );

                -- AI Tool Calls (Audit)
                CREATE TABLE IF NOT EXISTS tool_calls (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    tool_version TEXT NOT NULL,
                    inputs TEXT NOT NULL,
                    outputs TEXT,
                    status TEXT NOT NULL,
                    sensitivity TEXT NOT NULL,
                    approval_id TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    execution_time_ms INTEGER,
                    error TEXT,
                    hash_chain TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (tool_name, tool_version) REFERENCES tool_definitions(name, version)
                );
                CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id);
                CREATE INDEX IF NOT EXISTS idx_tool_calls_user_time ON tool_calls(user_id, started_at DESC);

                -- Data Licenses
                CREATE TABLE IF NOT EXISTS data_licenses (
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
                    status TEXT NOT NULL,
                    PRIMARY KEY (provider, dataset),
                    FOREIGN KEY (provider) REFERENCES providers(id),
                    FOREIGN KEY (reviewed_by) REFERENCES users(id)
                );
            """)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with proper settings."""
        conn = sqlite3.connect(
            self.db_path,
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
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for transactions."""
        conn = sqlite3.connect(
            self.db_path,
            isolation_level=None,
            check_same_thread=False,
            timeout=30.0
        )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-32768")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor."""
        with self.get_connection() as conn:
            return conn.execute(query, params)

    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute many queries in a transaction."""
        with self.transaction() as conn:
            conn.executemany(query, params_list)

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Fetch a single row."""
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchone()

    def fetch_all(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Fetch all rows."""
        with self.get_connection() as conn:
            return conn.execute(query, params).fetchall()

    def insert(self, table: str, data: Dict[str, Any]) -> str:
        """Insert a row and return the ID."""
        columns = list(data.keys())
        placeholders = ", ".join(["?" for _ in columns])
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        with self.transaction() as conn:
            cursor = conn.execute(query, tuple(data.values()))
            return cursor.lastrowid

    def update(self, table: str, data: Dict[str, Any], where: str, where_params: tuple) -> int:
        """Update rows matching where clause."""
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        params = tuple(data.values()) + where_params
        
        with self.transaction() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount

    def delete(self, table: str, where: str, where_params: tuple) -> int:
        """Delete rows matching where clause."""
        query = f"DELETE FROM {table} WHERE {where}"
        
        with self.transaction() as conn:
            cursor = conn.execute(query, where_params)
            return cursor.rowcount

    # Instrument Master methods
    def upsert_instrument(self, instrument_data: dict) -> str:
        """Upsert an instrument and return FIGI."""
        with self.transaction() as conn:
            figi = instrument_data.get("figi")
            if not figi:
                import uuid
                figi = str(uuid.uuid4())
                instrument_data["figi"] = figi
            
            # Upsert instrument
            columns = [
                "figi", "composite_ticker", "name", "asset_class",
                "primary_exchange", "currency", "country", "sector",
                "industry", "gics_code", "is_active", "metadata",
                "created_at", "updated_at"
            ]
            
            placeholders = ", ".join(["?" for _ in columns])
            query = f"INSERT OR REPLACE INTO instruments ({', '.join(columns)}) VALUES ({', '.join(['?'] * len(columns))})"
            
            values = [
                instrument_data.get("figi"),
                instrument_data.get("composite_ticker"),
                instrument_data.get("name"),
                instrument_data.get("asset_class"),
                instrument_data.get("primary_exchange"),
                instrument_data.get("currency"),
                instrument_data.get("country"),
                instrument_data.get("sector"),
                instrument_data.get("industry"),
                instrument_data.get("gics_code"),
                1,  # is_active
                json.dumps(instrument_data.get("metadata", {})),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat()
            ]
            
            conn.execute(query, values)
            
            # Handle provider symbols
            if "provider_symbols" in instrument_data:
                self._upsert_provider_symbols(figi, instrument_data["provider_symbols"])
            
            return figi

    def _upsert_provider_symbols(self, figi: str, provider_symbols: Dict[str, str]):
        """Upsert provider-specific symbols."""
        with self.get_connection() as conn:
            for provider, symbol in provider_symbols.items():
                conn.execute(
                    """INSERT OR REPLACE INTO instrument_aliases 
                       (figi, provider, provider_symbol, is_primary, valid_from)
                       VALUES (?, ?, ?, 1, ?)""",
                    (figi, provider, symbol, datetime.utcnow().isoformat())
                )

    def get_instrument(self, figi: str) -> Optional[Dict]:
        """Get instrument by FIGI."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM instruments WHERE figi = ?", (figi,)
            ).fetchone()
            return dict(row) if row else None

    def get_instrument_by_ticker(self, ticker: str) -> Optional[Dict]:
        """Get instrument by composite ticker."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM instruments WHERE composite_ticker = ?", (ticker.upper(),)
            ).fetchone()
            return dict(row) if row else None

    def search_instruments(
        self,
        query: str = "",
        asset_class: str = "",
        exchange: str = "",
        limit: int = 50
    ) -> List[Dict]:
        """Search instruments."""
        query = "SELECT * FROM instruments WHERE is_active = 1"
        params = []
        
        if query:
            query += " AND (composite_ticker LIKE ? OR name LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        if asset_class:
            query += " AND asset_class = ?"
            params.append(asset_class)
        if exchange:
            query += " AND primary_exchange = ?"
            params.append(exchange)
        
        query += " ORDER BY composite_ticker LIMIT ?"
        params.append(limit)
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    # Watchlist methods
    def create_watchlist(self, user_id: str, name: str, symbols: List[str] = None) -> str:
        watchlist_id = str(uuid.uuid4())
        symbols_json = json.dumps(symbols or [])
        
        with self.transaction() as conn:
            conn.execute(
                """INSERT INTO watchlists (id, user_id, name, symbols, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (watchlist_id, user_id, name, json.dumps(symbols or []),
                 datetime.utcnow().isoformat(), datetime.utcnow().isoformat())
            )
        return watchlist_id

    def get_watchlists(self, user_id: str) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM watchlists WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,)
            )
            watchlists = []
            for row in cursor.fetchall():
                w = dict(row)
                w["symbols"] = json.loads(w["symbols"])
                watchlists.append(w)
            return watchlists

    def get_watchlist(self, watchlist_id: str, user_id: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM watchlists WHERE id = ? AND user_id = ?",
                (watchlist_id, user_id)
            ).fetchone()
            if row:
                w = dict(row)
                w["symbols"] = json.loads(w["symbols"])
                return w
            return None

    def update_watchlist(self, watchlist_id: str, user_id: str, name: str = None, symbols: List[str] = None):
        with self.transaction() as conn:
            updates = []
            params = []
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if symbols is not None:
                updates.append("symbols = ?")
                params.append(json.dumps(symbols))
            
            if updates:
                updates.append("updated_at = ?")
                params.append(datetime.utcnow().isoformat())
                params.append(watchlist_id)
                conn.execute(f"UPDATE watchlists SET {', '.join(updates)} WHERE id = ?", params)

    def delete_watchlist(self, watchlist_id: str, user_id: str):
        with self.transaction() as conn:
            conn.execute(
                "DELETE FROM watchlists WHERE id = ? AND user_id = ?",
                (watchlist_id, user_id)
            )

    def add_symbol_to_watchlist(self, watchlist_id: str, user_id: str, symbol: str):
        with self.transaction() as conn:
            # Get current symbols
            row = conn.execute(
                "SELECT symbols FROM watchlists WHERE id = ? AND user_id = ?",
                (watchlist_id, user_id)
            ).fetchone()
            if row:
                symbols = json.loads(row["symbols"])
                if symbol not in symbols:
                    symbols.append(symbol)
                    conn.execute(
                        "UPDATE watchlists SET symbols = ?, updated_at = ? WHERE id = ?",
                        (json.dumps(symbols), datetime.utcnow().isoformat(), watchlist_id)
                    )

    def remove_symbol_from_watchlist(self, watchlist_id: str, user_id: str, symbol: str):
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT symbols FROM watchlists WHERE id = ? AND user_id = ?",
                (watchlist_id, user_id)
            ).fetchone()
            if row:
                symbols = json.loads(row["symbols"])
                if symbol in symbols:
                    symbols.remove(symbol)
                    conn.execute(
                        "UPDATE watchlists SET symbols = ?, updated_at = ? WHERE id = ?",
                        (json.dumps(symbols), datetime.utcnow().isoformat(), watchlist_id)
                    )

    # Quote storage
    def store_quote(self, quote: Dict) -> None:
        """Store a quote in the quotes table."""
        # In practice, quotes would go to a time-series table or cache
        # For now, we just log
        pass

    def get_latest_quotes(self, symbols: List[str]) -> Dict:
        """Get latest quotes for symbols."""
        # Would query from quotes table or cache
        return {}

    # Watchlist with quotes
    def get_watchlist_with_quotes(self, watchlist_id: str, user_id: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM watchlists WHERE id = ? AND user_id = ?",
                (watchlist_id, user_id)
            ).fetchone()
            if not row:
                return None
            
            w = dict(row)
            w["symbols"] = json.loads(w["symbols"])
            
            # Get quotes for each symbol
            quotes = {}
            for symbol in w["symbols"]:
                # In real implementation, query quotes table
                pass
            
            return {
                **w,
                "quotes": quotes
            }

    # Company methods
    def create_company(self, company_data: dict) -> str:
        company_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        with self.transaction() as conn:
            conn.execute(
                """INSERT INTO companies (id, cik, name, tickers, primary_exchange, currency,
                   sector, industry, gics_code, headquarters, description, is_active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (company_id, company_data["cik"], company_data["name"],
                 json.dumps(company_data["tickers"]), company_data["primary_exchange"],
                 company_data["currency"], company_data.get("sector"),
                 company_data.get("industry"), company_data.get("gics_code"),
                 json.dumps(company_data.get("headquarters", {})),
                 company_data.get("description"), 1, now, now)
            )
        return company_id

    def get_company(self, company_id: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
            if row:
                c = dict(row)
                c["tickers"] = json.loads(c["tickers"])
                c["headquarters"] = json.loads(c["headquarters"]) if c["headquarters"] else {}
                return c
            return None

    def search_companies(self, query: str = "", sector: str = "", limit: int = 50) -> List[Dict]:
        with self.get_connection() as conn:
            query = "SELECT * FROM companies WHERE is_active = 1"
            params = []
            
            if query:
                query += " AND (name LIKE ? OR cik LIKE ?)"
                params.extend([f"%{query}%", f"%{query}%"])
            if sector:
                query += " AND sector = ?"
                params.append(sector)
            
            query += " ORDER BY name LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_company_financials(
        self,
        company_id: str,
        statement_type: str = None,
        period_type: str = None,
        limit: int = 20
    ) -> List[Dict]:
        with self.get_connection() as conn:
            query = "SELECT * FROM financial_statements WHERE company_id = ?"
            params = [company_id]
            
            if statement_type:
                query += " AND statement_type = ?"
                params.append(statement_type.upper())
            if period_type:
                query += " AND period_type = ?"
                params.append(period_type.upper())
            
            query += " ORDER BY period_end DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            financials = []
            for row in cursor.fetchall():
                f = dict(row)
                f["line_items"] = json.loads(f["line_items"])
                financials.append(f)
            return financials

    def get_company_ratios(self, company_id: str, period_end: date = None, ratio_type: str = None) -> List[Dict]:
        with self.get_connection() as conn:
            query = "SELECT * FROM financial_ratios WHERE company_id = ?"
            params = [company_id]
            
            if period_end:
                query += " AND period_end = ?"
                params.append(period_end)
            if ratio_type:
                query += " AND ratio_type = ?"
                params.append(ratio_type.upper())
            
            query += " ORDER BY period_end DESC"
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    # Portfolio methods
    def create_portfolio(self, user_id: str, name: str, base_currency: str = "USD") -> str:
        portfolio_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        with self.transaction() as conn:
            conn.execute(
                """INSERT INTO portfolios (id, user_id, name, base_currency, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (portfolio_id, user_id, name, base_currency, now, now)
            )
            # Add base currency cash balance
            conn.execute(
                """INSERT INTO cash_balances (id, portfolio_id, currency, amount, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), portfolio_id, base_currency, 0, now)
            )
        return portfolio_id

    def get_portfolio(self, portfolio_id: str, user_id: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM portfolios WHERE id = ? AND user_id = ?",
                (portfolio_id, user_id)
            )
            portfolio = cursor.fetchone()
            if not portfolio:
                return None
            
            p = dict(portfolio)
            # Get positions
            cursor = conn.execute(
                "SELECT * FROM positions WHERE portfolio_id = ?",
                (portfolio_id,)
            )
            p["positions"] = {row["figi"]: dict(row) for row in cursor.fetchall()}
            
            # Get cash balances
            cursor = conn.execute(
                "SELECT * FROM cash_balances WHERE portfolio_id = ?",
                (portfolio_id,)
            )
            p["cash_balances"] = {row["currency"]: row["amount"] for row in cursor.fetchall()}
            
            return p

    def add_position(self, portfolio_id: str, figi: str, quantity: float, avg_cost: float, currency: str) -> str:
        position_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        with self.transaction() as conn:
            # Check if position exists
            cursor = conn.execute(
                "SELECT * FROM positions WHERE portfolio_id = ? AND figi = ?",
                (portfolio_id, figi)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing position
                new_qty = existing["quantity"] + quantity
                new_avg = (existing["quantity"] * existing["avg_cost"] + quantity * avg_cost) / new_qty
                conn.execute(
                    "UPDATE positions SET quantity = ?, avg_cost = ?, last_updated = ? WHERE id = ?",
                    (new_qty, new_avg, datetime.utcnow().isoformat(), existing["id"])
                )
                return existing["id"]
            else:
                conn.execute(
                    """INSERT INTO positions (id, portfolio_id, figi, quantity, avg_cost, currency, opened_at, last_updated)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (position_id, portfolio_id, figi, quantity, avg_cost, currency, now, now)
                )
                return position_id

    def remove_position(self, portfolio_id: str, figi: str):
        with self.transaction() as conn:
            conn.execute(
                "DELETE FROM positions WHERE portfolio_id = ? AND figi = ?",
                (portfolio_id, figi)
            )

    def add_transaction(self, portfolio_id: str, transaction_data: dict) -> str:
        trans_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        with self.transaction() as conn:
            conn.execute(
                """INSERT INTO transactions (id, portfolio_id, figi, side, quantity, price, 
                   price_currency, fees, fees_currency, slippage, slippage_currency, 
                   executed_at, status, broker, order_id, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (trans_id, portfolio_id, transaction_data["figi"], transaction_data["side"],
                 transaction_data["quantity"], transaction_data["price"],
                 transaction_data["price_currency"], transaction_data["fees"],
                 transaction_data["fees_currency"], transaction_data.get("slippage"),
                 transaction_data.get("slippage_currency"), transaction_data["executed_at"],
                 transaction_data["status"], transaction_data.get("broker"),
                 transaction_data.get("order_id"), now)
            )
        return trans_id

    def get_portfolio_transactions(self, portfolio_id: str, start: date = None, end: date = None) -> List[Dict]:
        with self.get_connection() as conn:
            query = "SELECT * FROM transactions WHERE portfolio_id = ?"
            params = [portfolio_id]
            
            if start:
                query += " AND executed_at >= ?"
                params.append(start)
            if end:
                query += " AND executed_at <= ?"
                params.append(end)
            
            query += " ORDER BY executed_at DESC"
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]


# Singleton instance
sqlite_storage = SQLiteStorage()


# Helper functions
def get_sqlite_storage() -> SQLiteStorage:
    return sqlite_storage