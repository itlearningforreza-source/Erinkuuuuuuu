"""ERIN Data Infrastructure Storage Module."""

from erin.data_infra.storage.interfaces import (
    StorageBackend,
    TransactionalStorage,
    AnalyticalStorage,
    HistoricalStorage,
    VectorStorage,
    StorageManager,
    storage_manager,
)

from erin.data_infra.storage.sqlite import SQLiteStorage, sqlite_storage, get_sqlite_storage
from erin.data_infra.storage.duckdb import DuckDBStorage, get_duckdb_storage
from erin.data_infra.storage.parquet import ParquetStorage, get_parquet_storage
from erin.data_infra.storage.lancedb import LanceDBVectorStorage, get_vector_storage

__all__ = [
    # Interfaces
    "StorageBackend",
    "TransactionalStorage",
    "AnalyticalStorage",
    "HistoricalStorage",
    "VectorStorage",
    "StorageManager",
    "storage_manager",
    
    # Implementations
    "SQLiteStorage",
    "sqlite_storage",
    "get_sqlite_storage",
    "DuckDBStorage",
    "get_duckdb_storage",
    "ParquetStorage",
    "get_parquet_storage",
    "LanceDBVectorStorage",
    "get_vector_storage",
]