"""Parquet Storage - Historical analytical storage with partitioning."""

import logging
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Optional
from typing import TYPE_CHECKING
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.dataset as ds
import pyarrow.compute as pc
import pandas as pd

if TYPE_CHECKING:
    import pyarrow as pa
    import pyarrow.parquet as pq

logger = logging.getLogger(__name__)


class ParquetStorage:
    """Parquet-based historical storage with partitioning and predicate pushdown."""
    
    def __init__(self, base_path: str = "~/.erin/data/parquet"):
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._dataset_cache: Dict[str, ds.Dataset] = {}
    
    def _get_dataset(self, table_name: str) -> ds.Dataset:
        """Get or create Arrow dataset for a table."""
        if table_name not in self._dataset_cache:
            table_path = self.base_path / table_name
            if table_path.exists():
                self._dataset_cache[table_name] = ds.dataset(
                    str(table_path),
                    format="parquet",
                    partitioning="hive"
                )
            else:
                # Create empty dataset
                self._dataset_cache[table_name] = None
        return self._dataset_cache[table_name]
    
    def write_table(
        self,
        table_name: str,
        data: List[Dict],
        partition_cols: Optional[List[str]] = None,
        compression: str = "snappy",
        row_group_size: int = 128 * 1024 * 1024  # 128MB
    ) -> str:
        """Write data to Parquet with partitioning."""
        import pandas as pd
        
        if not data:
            logger.warning(f"No data to write for {table_name}")
            return ""
        
        df = pd.DataFrame(data)
        table = pa.Table.from_pandas(df)
        
        # Partitioning
        if partition_cols:
            for col in partition_cols:
                if col not in df.columns:
                    logger.warning(f"Partition column {col} not in data, skipping partition")
                    partition_cols = None
                    break
        
        # Create output path
        table_path = self.base_path / table_name
        table_path.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        file_name = f"{table_name}_{timestamp}.parquet"
        file_path = table_path / file_name
        
        # Write with partitioning
        if partition_cols:
            pq.write_to_dataset(
                table,
                root_path=str(self.base_path / table_name),
                partition_cols=partition_cols,
                compression=compression,
                row_group_size=row_group_size,
                write_statistics=True,
                use_dictionary=True,
                existing_data_behavior="overwrite_or_ignore"
            )
            return str(self.base_path / table_name)
        else:
            pq.write_table(
                table,
                str(file_path),
                compression=compression,
                row_group_size=row_group_size,
                write_statistics=True,
                use_dictionary=True
            )
            return str(file_path)
    
    def append_partition(
        self,
        table_name: str,
        data: List[Dict],
        partition_cols: List[str],
        compression: str = "snappy"
    ) -> str:
        """Append data to existing partitioned dataset."""
        import pandas as pd
        
        df = pd.DataFrame(data)
        table = pa.Table.from_pandas(df)
        
        table_path = self.base_path / table_name
        
        pq.write_to_dataset(
            table,
            root_path=str(self.base_path / table_name),
            partition_cols=partition_cols,
            compression=compression,
            existing_data_behavior="overwrite_or_ignore"
        )
        
        return str(self.base_path / table_name)
    
    def read_table(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        filters: Optional[List[tuple]] = None,
        limit: Optional[int] = None
    ) -> 'pd.DataFrame':
        """Read data from Parquet with predicate pushdown."""
        import pandas as pd
        
        dataset = self._get_dataset(table_name)
        if dataset is None:
            return pd.DataFrame()
        
        # Build scanner with filters
        scanner = ds.Scanner.from_dataset(
            dataset,
            columns=columns,
            filter=ds.Expression(filters) if filters else None,
            limit=limit
        )
        
        return scanner.to_table().to_pandas()
    
    def query(
        self,
        table_name: str,
        query: str,
        params: tuple = ()
    ) -> 'pd.DataFrame':
        """Execute SQL query on Parquet data using DuckDB."""
        import duckdb
        import pandas as pd
        
        conn = duckdb.connect()
        
        # Register dataset as view
        table_path = self.base_path / table_name
        if table_path.exists():
            conn.execute(f"CREATE VIEW {table_name} AS SELECT * FROM read_parquet('{self.base_path}/{table_name}/**/*.parquet')")
        else:
            return pd.DataFrame()
        
        result = duckdb.execute(query).df()
        return result
    
    def scan_partitions(
        self,
        table_name: str,
        partition_values: Dict[str, Any]
    ) -> 'pd.DataFrame':
        """Read specific partitions efficiently."""
        import pandas as pd
        
        dataset = self._get_dataset(table_name)
        if dataset is None:
            return pd.DataFrame()
        
        # Build partition filter
        filters = []
        for col, val in partition_values.items():
            if isinstance(val, list):
                filters.append((col, 'in', val))
            else:
                filters.append((col, '=', val))
        
        scanner = ds.Scanner.from_dataset(
            dataset,
            filter=ds.Expression(filters) if filters else None
        )
        
        return scanner.to_table().to_pandas()
    
    def list_partitions(self, table_name: str) -> List[Dict[str, Any]]:
        """List all partitions for a table."""
        dataset = self._get_dataset(table_name)
        if dataset is None:
            return []
        
        partitions = []
        for fragment in dataset.get_fragments():
            partition = fragment.partition_expression
            if partition:
                partitions.append(partition)
        return partitions
    
    def get_partition_stats(self, table_name: str) -> Dict[str, Any]:
        """Get statistics about partitions."""
        import pandas as pd
        
        dataset = self._get_dataset(table_name)
        if dataset is None:
            return {"partitions": 0, "total_rows": 0, "size_bytes": 0}
        
        total_rows = 0
        total_size = 0
        partition_count = 0
        
        for fragment in dataset.get_fragments():
            partition_count += 1
            total_rows += fragment.num_rows
            total_size += sum(f.metadata.serialized_size for f in fragment.files)
        
        return {
            "partitions": partition_count,
            "total_rows": total_rows,
            "size_bytes": total_size,
            "size_mb": round(total_size / (1024 * 1024), 2)
        }
    
    def compact_partitions(
        self,
        table_name: str,
        target_row_group_size: int = 128 * 1024 * 1024
    ) -> str:
        """Compact small partitions into larger row groups."""
        import pandas as pd
        
        # Read entire table
        df = self.read_table(table_name)
        if df.empty:
            return ""
        
        # Rewrite with larger row groups
        output_path = self.base_path / table_name / f"compacted_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.parquet"
        
        table = pa.Table.from_pandas(pd.DataFrame(self.read_table(table_name)))
        pq.write_table(
            table,
            str(output_path),
            compression='snappy',
            row_group_size=128 * 1024 * 1024,  # 128MB
            write_statistics=True
        )
        
        return str(output_path)
    
    def delete_partition(
        self,
        table_name: str,
        partition_values: Dict[str, Any]
    ) -> bool:
        """Delete a specific partition."""
        # With Parquet, we need to rewrite the dataset without the partition
        # This is a heavy operation - mark as deprecated instead
        logger.warning("Partition deletion not fully implemented - consider marking as deprecated")
        return False
    
    def get_schema(self, table_name: str) -> Optional[pa.Schema]:
        """Get the schema of a Parquet table."""
        dataset = self._get_dataset(table_name)
        if dataset is None:
            return None
        return dataset.schema
    
    def get_metadata(self, table_name: str) -> Dict[str, Any]:
        """Get table metadata."""
        schema = self.get_schema(table_name)
        stats = self.get_partition_stats(table_name)
        
        return {
            "schema": str(schema) if schema else None,
            **stats
        }
    
    def vacuum(self, table_name: str) -> str:
        """Vacuum/clean up old files (placeholder for Delta Lake style)."""
        # In Parquet, we'd need to rewrite - for now just compact
        return self.compact_partitions(table_name)
    
    def get_table_size(self, table_name: str) -> int:
        """Get total size of table in bytes."""
        table_path = self.base_path / table_name
        if not table_path.exists():
            return 0
        
        total = 0
        for file_path in table_path.rglob("*.parquet"):
            total += file_path.stat().st_size
        return total


# Global instance
_parquet_storage = None

def get_parquet_storage() -> ParquetStorage:
    global _parquet_storage
    if _parquet_storage is None:
        _parquet_storage = ParquetStorage()
    return _parquet_storage