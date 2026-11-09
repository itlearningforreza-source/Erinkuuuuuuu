"""DuckDB Storage - Analytical workloads with columnar storage and Parquet integration."""

import duckdb
import logging
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Generator, Union
from contextlib import contextmanager
import pyarrow as pa
import pyarrow.parquet as pq

from erin.data_infra.storage.interfaces import StorageBackend

logger = logging.getLogger(__name__)


class DuckDBStorage:
    """DuckDB storage backend for analytical workloads."""
    
    def __init__(self, db_path: str = "~/.erin/data/erin_analytics.duckdb"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        self._init_db()
    
    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = duckdb.connect(str(self.db_path), read_only=False)
            self._conn.execute("SET memory_limit='2GB'")
            self._conn.execute("SET threads=4")
            self._conn.execute("SET preserve_insertion_order=false")
            self._conn.execute("INSTALL parquet; LOAD parquet")
            self._conn.execute("INSTALL arrow; LOAD arrow")
        return self._conn
    
    def _init_db(self):
        """Initialize DuckDB schema for analytical workloads."""
        conn = self._get_connection()
        
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
        
        # Normalized Quotes (validated, deduplicated)
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
        
        # Adjusted Quotes (corporate actions applied)
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
        
        # Factor Exposures (updated daily)
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
        
        # Portfolio Risk Metrics (per portfolio, daily)
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
        
        # Macro Indicator Observations
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
        
        # News Sentiment Aggregations (daily per instrument)
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
        
        # Model Results (backtests, simulations)
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
        
        # Create indexes for common query patterns
        self._create_indexes()
        
        logger.info("DuckDB schema initialized")
    
    def _create_indexes(self):
        """Create indexes for common query patterns."""
        conn = self._get_connection()
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_normalized_quotes_figi_time ON normalized_quotes(figi, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_daily_returns_figi_date ON daily_returns(figi, date)",
            "CREATE INDEX IF NOT EXISTS idx_factor_exposures_figi_date ON factor_exposures(figi, date)",
            "CREATE INDEX IF NOT EXISTS idx_portfolio_risk_portfolio_date ON portfolio_risk_metrics(portfolio_id, date)",
            "CREATE INDEX IF NOT EXISTS idx_macro_obs_indicator_period ON macro_observations(indicator_id, period)",
            "CREATE INDEX IF NOT EXISTS idx_daily_news_figi_date ON daily_news_sentiment(figi, date)",
            "CREATE INDEX IF NOT EXISTS idx_model_results_model_time ON model_results(model_id, timestamp)",
        ]
        
        for idx in indexes:
            try:
                self._conn.execute(idx)
            except Exception as e:
                logging.warning(f"Index creation failed (may already exist): {e}")
    
    @contextmanager
    def connection(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """Context manager for database connection."""
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            raise
    
    def execute(self, query: str, params: tuple = ()) -> duckdb.DuckDBPyRelation:
        """Execute a query and return relation."""
        conn = self._get_connection()
        return conn.execute(query, params)
    
    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute many queries in a transaction."""
        conn = self._get_connection()
        conn.executemany(query, params_list)
    
    def fetch_df(self, query: str, params: tuple = ()) -> 'pd.DataFrame':
        """Execute query and return DataFrame."""
        conn = self._get_connection()
        return conn.execute(query, params).df()
    
    def fetch_arrow(self, query: str, params: tuple = ()) -> pa.Table:
        """Execute query and return Arrow table."""
        conn = self._get_connection()
        return conn.execute(query, params).arrow()
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all rows as list of dicts."""
        conn = self._get_connection()
        result = conn.execute(query, params).fetchall()
        return [dict(row) for row in result]
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch single row as dict."""
        conn = self._get_connection()
        result = conn.execute(query, params).fetchone()
        return dict(result) if result else None
    
    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute many parameterized queries."""
        conn = self._get_connection()
        conn.executemany(query, params_list)
    
    # Parquet operations
    def write_parquet(
        self,
        table_name: str,
        data: Union[pa.Table, 'pd.DataFrame', List[Dict]],
        partition_cols: Optional[List[str]] = None,
        compression: str = "snappy",
        row_group_size: int = 128 * 1024 * 1024  # 128MB
    ) -> str:
        """Write data to Parquet file."""
        import pandas as pd
        
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, pa.Table):
            df = data.to_pandas()
        elif isinstance(data, pd.DataFrame):
            df = data
        else:
            raise ValueError("Data must be list, DataFrame, or Arrow Table")
        
        table = pa.Table.from_pandas(df)
        
        # Create output path
        output_dir = Path.home() / ".erin" / "data" / "parquet" / table_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Partition by date if specified
        if partition_cols:
            # Add partition columns to data
            pass
        
        file_path = output_dir / f"{table_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.parquet"
        
        pq.write_table(
            table,
            str(file_path),
            compression=compression,
            row_group_size=row_group_size,
            write_statistics=True
        )
        
        return str(file_path)
    
    def read_parquet(
        self,
        table_name: str,
        partitions: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        filters: Optional[List[tuple]] = None
    ) -> pa.Table:
        """Read Parquet files with optional partition pruning."""
        base_path = Path.home() / ".erin" / "data" / "parquet" / table_name
        
        if not base_path.exists():
            return pa.table({})
        
        # Use DuckDB to read with partition pruning
        conn = self._get_connection()
        
        if partitions:
            # Build partition filter
            partition_filters = []
            for col, val in partitions.items():
                if isinstance(val, list):
                    vals = ", ".join([f"'{v}'" for v in val])
                    partition_filters.append(f"{col} IN ({vals})")
                else:
                    partition_filters.append(f"{col} = '{val}'")
            partition_where = " AND ".join(partition_filters)
            
            query = f"SELECT * FROM read_parquet('{base_path}/**/*.parquet')"
            if partition_where:
                query += f" WHERE {partition_where}"
        else:
            query = f"SELECT * FROM read_parquet('{base_path}/**/*.parquet')"
        
        if filters:
            filter_strs = []
            for col, op, val in filters:
                filter_strs.append(f"{col} {op} '{val}'")
            if filter_strs:
                query += " WHERE " + " AND ".join(filter_strs)
        
        if columns:
            query = query.replace("SELECT *", f"SELECT {', '.join(columns)}")
        
        return conn.execute(query).arrow()
    
    def query_parquet(
        self,
        table_name: str,
        query: str,
        params: tuple = ()
    ) -> pa.Table:
        """Execute SQL query on Parquet data using DuckDB."""
        conn = self._get_connection()
        base_path = Path.home() / ".erin" / "data" / "parquet" / table_name
        
        # Register Parquet as a view
        conn.execute(f"""
            CREATE OR REPLACE VIEW {table_name}_view AS 
            SELECT * FROM read_parquet('{Path.home() / ".erin" / "data" / "parquet" / table_name / "*.parquet"}')
        """)
        
        result = conn.execute(query, params).arrow()
        conn.execute(f"DROP VIEW IF EXISTS {table_name}_view")
        return result
    
    # Bulk data operations
    def bulk_insert(self, table: str, data: List[Dict], batch_size: int = 10000) -> int:
        """Bulk insert data into DuckDB table."""
        import pandas as pd
        
        if not data:
            return 0
        
        df = pd.DataFrame(data)
        conn = self._get_connection()
        
        # Register DataFrame as view
        conn.register("temp_df", pd.DataFrame(df))
        
        # Insert in batches
        total = len(df)
        for i in range(0, total, batch_size):
            batch = df.iloc[i:i+batch_size]
            conn.register("batch_df", batch)
            conn.execute(f"INSERT INTO {table} SELECT * FROM batch_df")
        
        return total
    
    def upsert_from_parquet(
        self,
        table: str,
        parquet_path: str,
        key_columns: List[str],
        update_columns: Optional[List[str]] = None
    ) -> int:
        """Upsert data from Parquet file into table."""
        conn = self._get_connection()
        
        # Register Parquet as view
        conn.execute(f"""
            CREATE OR REPLACE TEMP VIEW staging_{table} AS 
            SELECT * FROM read_parquet('{parquet_path}')
        """)
        
        # Get columns
        cols = conn.execute(f"DESCRIBE staging_{table}").fetchall()
        all_cols = [row[0] for row in cols]
        
        if update_columns is None:
            update_columns = [c for c in all_cols if c not in key_columns]
        
        # Build upsert query
        key_cols = ", ".join(key_columns)
        all_cols_str = ", ".join(all_cols)
        update_cols_str = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_columns])
        
        query = f"""
            INSERT INTO {table} ({all_cols_str})
            SELECT {all_cols_str} FROM staging_{table}
            ON CONFLICT ({key_cols}) DO UPDATE SET {update_cols_str}
        """
        
        conn.execute(query)
        return conn.execute(f"SELECT COUNT(*) FROM staging_{table}").fetchone()[0]
    
    # Analytical queries
    def compute_daily_returns(self, figi: str, start_date: date, end_date: date) -> 'pd.DataFrame':
        """Compute daily returns for an instrument."""
        query = """
            SELECT 
                date,
                close_price,
                LAG(close_price) OVER (ORDER BY date) as prev_close,
                (close_price - LAG(close_price) OVER (ORDER BY date)) / LAG(close_price) OVER (ORDER BY date) as simple_return,
                LN(close_price / LAG(close_price) OVER (ORDER BY date)) as log_return
            FROM daily_returns
            WHERE figi = ? AND date BETWEEN ? AND ?
            ORDER BY date
        """
        return self._get_connection().execute(query, (figi, start_date, end_date)).df()
    
    def compute_factor_exposures(self, figis: List[str], date: date) -> 'pd.DataFrame':
        """Get factor exposures for instruments on a date."""
        placeholders = ", ".join(["?" for _ in figis])
        query = f"""
            SELECT * FROM factor_exposures
            WHERE figi IN ({placeholders}) AND date = ?
        """
        return self._get_connection().execute(query, figis + [date]).df()
    
    def get_portfolio_risk_metrics(self, portfolio_id: str, start_date: date, end_date: date) -> 'pd.DataFrame':
        """Get portfolio risk metrics over time."""
        query = """
            SELECT * FROM portfolio_risk_metrics
            WHERE portfolio_id = ? AND date BETWEEN ? AND ?
            ORDER BY date
        """
        return self._get_connection().execute(query, (portfolio_id, start_date, end_date)).df()
    
    def get_macro_observations(self, indicator_id: str, start: date, end: date) -> 'pd.DataFrame':
        """Get macro indicator observations."""
        query = """
            SELECT * FROM macro_observations
            WHERE indicator_id = ? AND period BETWEEN ? AND ?
            ORDER BY period
        """
        return self._get_connection().execute(query, (indicator_id, start, end)).df()
    
    def get_news_sentiment(self, figi: str, start_date: date, end_date: date) -> 'pd.DataFrame':
        """Get daily news sentiment for an instrument."""
        query = """
            SELECT * FROM daily_news_sentiment
            WHERE figi = ? AND date BETWEEN ? AND ?
            ORDER BY date
        """
        return self._get_connection().execute(query, (figi, start_date, end_date)).df()
    
    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Convenience functions
def get_duckdb_storage() -> DuckDBStorage:
    """Get or create DuckDB storage singleton."""
    global _duckdb_storage
    if '_duckdb_storage' not in globals():
        globals()['_duckdb_storage'] = DuckDBStorage()
    return globals()['_duckdb_storage']