"""Storage Interfaces - Abstract interfaces for storage backends."""

from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Optional
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    async def connect(self) -> None:
        """Initialize connection."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if storage is healthy."""
        pass


class TransactionalStorage(StorageBackend):
    """Interface for transactional (OLTP) storage."""
    
    @abstractmethod
    async def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute a query."""
        pass
    
    @abstractmethod
    async def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute many queries."""
        pass
    
    @abstractmethod
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch a single row."""
        pass
    
    @abstractmethod
    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all rows."""
        pass
    
    @abstractmethod
    async def transaction(self):
        """Transaction context manager."""
        pass


class AnalyticalStorage(StorageBackend):
    """Interface for analytical (OLAP) storage."""
    
    @abstractmethod
    async def execute(self, query: str, params: tuple = ()) -> Any:
        """Execute analytical query."""
        pass
    
    @abstractmethod
    async def fetch_df(self, query: str, params: tuple = ()) -> Any:
        """Fetch as DataFrame."""
        pass
    
    @abstractmethod
    async def fetch_arrow(self, query: str, params: tuple = ()) -> Any:
        """Fetch as Arrow table."""
        pass
    
    @abstractmethod
    async def bulk_insert(self, table: str, data: List[Dict], batch_size: int = 10000) -> int:
        """Bulk insert data."""
        pass
    
    @abstractmethod
    async def upsert_from_parquet(
        self,
        table: str,
        parquet_path: str,
        key_columns: List[str],
        update_columns: Optional[List[str]] = None
    ) -> int:
        """Upsert from Parquet file."""
        pass


class HistoricalStorage(StorageBackend):
    """Interface for historical/analytical storage (Parquet)."""
    
    @abstractmethod
    def write_table(
        self,
        table_name: str,
        data: List[Dict],
        partition_cols: Optional[List[str]] = None,
        compression: str = "snappy"
    ) -> str:
        """Write data to partitioned Parquet."""
        pass
    
    @abstractmethod
    def read_table(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        filters: Optional[List[tuple]] = None,
        limit: Optional[int] = None
    ) -> Any:
        """Read data with predicate pushdown."""
        pass
    
    @abstractmethod
    def query(
        self,
        table_name: str,
        query: str,
        params: tuple = ()
    ) -> Any:
        """Execute SQL query on Parquet data."""
        pass
    
    @abstractmethod
    def scan_partitions(
        self,
        table_name: str,
        partition_values: Dict[str, Any]
    ) -> Any:
        """Read specific partitions."""
        pass
    
    @abstractmethod
    def get_partition_stats(self, table_name: str) -> Dict[str, Any]:
        """Get partition statistics."""
        pass


class VectorStorage(StorageBackend):
    """Interface for vector/embedding storage."""
    
    @abstractmethod
    async def add_documents(
        self,
        collection: str,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> List[str]:
        """Add documents with embeddings."""
        pass
    
    @abstractmethod
    async def search(
        self,
        collection: str,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        pass
    
    @abstractmethod
    async def delete(
        self,
        collection: str,
        ids: List[str]
    ) -> int:
        """Delete documents by ID."""
        pass
    
    @abstractmethod
    async def get_collection_stats(self, collection: str) -> Dict[str, Any]:
        """Get collection statistics."""
        pass


class StorageManager:
    """Unified storage manager coordinating all storage backends."""
    
    def __init__(self):
        self._transactional: Optional[TransactionalStorage] = None
        self._analytical: Optional[AnalyticalStorage] = None
        self._historical: Optional[HistoricalStorage] = None
        self._vector: Optional[VectorStorage] = None
    
    def set_transactional(self, storage: TransactionalStorage):
        self._transactional = storage
    
    def set_analytical(self, storage: AnalyticalStorage):
        self._analytical = storage
    
    def set_historical(self, storage: HistoricalStorage):
        self._historical = storage
    
    def set_vector(self, storage: VectorStorage):
        self._vector = storage
    
    @property
    def transactional(self) -> TransactionalStorage:
        if self._transactional is None:
            raise RuntimeError("Transactional storage not configured")
        return self._transactional
    
    @property
    def analytical(self) -> AnalyticalStorage:
        if self._analytical is None:
            raise RuntimeError("Analytical storage not configured")
        return self._analytical
    
    @property
    def historical(self) -> HistoricalStorage:
        if self._historical is None:
            raise RuntimeError("Historical storage not configured")
        return self._historical
    
    @property
    def vector(self) -> VectorStorage:
        if self._vector is None:
            raise RuntimeError("Vector storage not configured")
        return self._vector


# Global storage manager instance
storage_manager = StorageManager()