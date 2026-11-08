import sqlite3
import duckdb
import os
from pathlib import Path
from contextlib import contextmanager

from erin.api.core.config import settings

# SQLite connection
def get_sqlite_connection() -> sqlite3.Connection:
    db_path = Path(settings.SQLITE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(
        db_path,
        isolation_level=None,  # Autocommit off, manual transactions
        check_same_thread=False,
        timeout=30.0,
    )
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-32768")  # 32MB cache
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def sqlite_transaction():
    conn = get_sqlite_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# DuckDB connection
def get_duckdb_connection() -> duckdb.DuckDBPyConnection:
    db_path = Path(settings.DUCKDB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = duckdb.connect(str(db_path), read_only=False)
    conn.execute("SET memory_limit='2GB'")
    conn.execute("SET threads=4")
    conn.execute("SET preserve_insertion_order=false")
    conn.execute("INSTALL parquet; LOAD parquet")
    conn.execute("INSTALL arrow; LOAD arrow")
    return conn

# Initialize databases
async def init_db():
    # Create SQLite tables
    with sqlite_transaction() as conn:
        # Users & Governance
        conn.execute("""
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
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                permissions TEXT NOT NULL,
                description TEXT,
                is_system INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_time ON audit_events(user_id, timestamp DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_events(resource_type, resource_id)")
        
        # Instrument Master
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_instruments_ticker ON instruments(composite_ticker)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_instruments_asset_class ON instruments(asset_class)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_instruments_exchange ON instruments(primary_exchange)")
        
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_aliases_provider_symbol ON instrument_aliases(provider, provider_symbol)")
        
        # Watchlists
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlists (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                symbols TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_watchlists_user ON watchlists(user_id)")
        
        # Market Calendar
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_calendars (
                exchange TEXT NOT NULL,
                year INTEGER NOT NULL,
                trading_days TEXT NOT NULL,
                holidays TEXT NOT NULL,
                early_closes TEXT NOT NULL,
                PRIMARY KEY (exchange, year)
            )
        """)
        
        # Data Providers
        conn.execute("""
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
            )
        """)
        
        # Ingestion Jobs
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_provider_dataset ON ingestion_jobs(provider, dataset)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_status ON ingestion_jobs(status)")
        
        # Data Quality Reports
        conn.execute("""
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
            )
        """)
        
        # Companies
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_companies_cik ON companies(cik)")
        
        # Financial Statements
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_financials_company_period ON financial_statements(company_id, period_end DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_financials_filing_date ON financial_statements(filing_date DESC)")
        
        # Financial Ratios
        conn.execute("""
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
            )
        """)
        
        # Portfolios
        conn.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                base_currency TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_positions_portfolio ON positions(portfolio_id)")
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cash_balances (
                id TEXT PRIMARY KEY,
                portfolio_id TEXT NOT NULL,
                currency TEXT NOT NULL,
                amount REAL NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
                UNIQUE(portfolio_id, currency)
            )
        """)
        
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_portfolio_time ON transactions(portfolio_id, executed_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_figi_time ON transactions(figi, executed_at DESC)")
        
        # VaR Models
        conn.execute("""
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
            )
        """)
        
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_var_results_portfolio_date ON var_results(portfolio_id, as_of_date DESC)")
        
        # Bonds
        conn.execute("""
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
            )
        """)
        
        # Yield Curves
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_curves_currency_date ON yield_curves(currency, reference_date DESC)")
        
        # Options
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_options_underlying ON options(underlying_figi)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_options_expiration ON options(expiration)")
        
        # Volatility Surfaces
        conn.execute("""
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
            )
        """)
        
        # Economic Indicators
        conn.execute("""
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
            )
        """)
        
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_obs_indicator_period ON indicator_observations(indicator_id, period DESC)")
        
        # News Articles
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_source ON news_articles(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_articles(sentiment_score)")
        
        # Notebooks
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notebooks_user ON notebooks(user_id)")
        
        # Workspaces
        conn.execute("""
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
            )
        """)
        
        # Tool Definitions
        conn.execute("""
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
            )
        """)
        
        # Tool Calls
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_user_time ON tool_calls(user_id, started_at DESC)")
        
        # Data Licenses
        conn.execute("""
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
            )
        """)
        
        # Insert default roles
        conn.execute("""
            INSERT OR IGNORE INTO roles (id, name, permissions, description, is_system) VALUES
            ('role_admin', 'ADMIN', '[{"resource": "*", "action": "*"}]', 'Full system access', 1),
            ('role_analyst', 'ANALYST', '[{"resource": "portfolio", "action": "*"}, {"resource": "valuation", "action": "*"}, {"resource": "risk", "action": "*"}, {"resource": "market_data", "action": "read"}, {"resource": "research", "action": "*"}]', 'Analyst with full research access', 1),
            ('role_viewer', 'VIEWER', '[{"resource": "portfolio", "action": "read"}, {"resource": "valuation", "action": "read"}, {"resource": "risk", "action": "read"}, {"resource": "market_data", "action": "read"}]', 'Read-only access', 1),
            ('role_quant', 'QUANT', '[{"resource": "quant_models", "action": "*"}, {"resource": "backtest", "action": "*"}, {"resource": "risk_models", "action": "*"}]', 'Quantitative researcher', 1),
            ('role_risk_manager', 'RISK_MANAGER', '[{"resource": "risk", "action": "*"}, {"resource": "portfolio", "action": "read"}]', 'Risk manager', 1)
        """)
    
    # Initialize DuckDB schema
    conn = duckdb.connect(str(Path(settings.DUCKDB_PATH).parent / "erin_analytics.duckdb"))
    conn.execute("SET memory_limit='2GB'")
    conn.execute("SET threads=4")
    conn.execute("INSTALL parquet; LOAD parquet")
    conn.execute("INSTALL arrow; LOAD arrow")
    
    # Raw Quotes (append-only, partitioned by date)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_quotes (
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
            raw_data VARCHAR
        )
    """)
    
    # Normalized Quotes
    conn.execute("""
        CREATE TABLE IF NOT EXISTS normalized_quotes (
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
        )
    """)
    
    # Adjusted Quotes
    conn.execute("""
        CREATE TABLE IF NOT EXISTS adjusted_quotes (
            figi VARCHAR,
            adj_open DOUBLE,
            adj_high DOUBLE,
            adj_low DOUBLE,
            adj_close DOUBLE,
            adj_volume BIGINT,
            timestamp TIMESTAMP,
            adjustment_factor DOUBLE,
            adjustment_type VARCHAR,
            corporate_action_id VARCHAR
        )
    """)
    
    # Daily Returns
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_returns (
            figi VARCHAR,
            date DATE,
            simple_return DOUBLE,
            log_return DOUBLE,
            close_price DOUBLE,
            volume BIGINT,
            currency VARCHAR
        )
    """)
    
    # Factor Exposures
    conn.execute("""
        CREATE TABLE IF NOT EXISTS factor_exposures (
            figi VARCHAR,
            date DATE,
            market_beta DOUBLE,
            size_factor DOUBLE,
            value_factor DOUBLE,
            momentum_factor DOUBLE,
            quality_factor DOUBLE,
            volatility_factor DOUBLE,
            r_squared DOUBLE
        )
    """)
    
    # Portfolio Risk Metrics
    conn.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_risk_metrics (
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
        )
    """)
    
    # Macro Observations
    conn.execute("""
        CREATE TABLE IF NOT EXISTS macro_observations (
            indicator_id VARCHAR,
            period DATE,
            value DOUBLE,
            revision INTEGER,
            published_at TIMESTAMP,
            geography VARCHAR,
            category VARCHAR
        )
    """)
    
    # Daily News Sentiment
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_news_sentiment (
            figi VARCHAR,
            date DATE,
            article_count INTEGER,
            avg_sentiment DOUBLE,
            weighted_sentiment DOUBLE,
            positive_count INTEGER,
            negative_count INTEGER,
            neutral_count INTEGER
        )
    """)
    
    # Model Results
    conn.execute("""
        CREATE TABLE IF NOT EXISTS model_results (
            model_id VARCHAR,
            run_id VARCHAR,
            timestamp TIMESTAMP,
            parameters VARCHAR,
            metrics VARCHAR,
            outputs_path VARCHAR
        )
    """)

# Database dependency for FastAPI
from fastapi import Depends
from typing import Generator

def get_sqlite_db() -> Generator[sqlite3.Connection, None, None]:
    conn = get_sqlite_connection()
    try:
        yield conn
    finally:
        conn.close()

def get_duckdb_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    conn = get_duckdb_connection()
    try:
        yield conn
    finally:
        conn.close()