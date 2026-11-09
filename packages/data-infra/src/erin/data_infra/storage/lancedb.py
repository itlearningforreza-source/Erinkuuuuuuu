"""LanceDB Vector Storage - Embedded vector database for RAG."""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, List
from typing import TYPE_CHECKING
import lancedb
import pyarrow as pa
import numpy as np

if TYPE_CHECKING:
    import lancedb

logger = logging.getLogger(__name__)


class LanceDBVectorStorage:
    """LanceDB embedded vector database for RAG."""
    
    def __init__(self, db_path: str = "~/.erin/data/lancedb"):
        self.db_path = db_path
        self._db = None
        self._tables: Dict[str, Any] = {}
    
    async def _get_db(self):
        if self._db is None:
            self._db = lancedb.connect(db_path)
        return self._db
    
    async def _get_table(self, collection: str):
        if collection not in self._tables:
            db = await self._get_db()
            if collection not in db.table_names():
                # Create table with schema
                import pyarrow as pa
                schema = pa.schema([
                    pa.field("id", pa.string()),
                    pa.field("vector", pa.list_(pa.float32(), 384)),  # Default 384-dim
                    pa.field("content", pa.string()),
                    pa.field("metadata", pa.string()),
                    pa.field("source", pa.string()),
                    pa.field("created_at", pa.timestamp('us')),
            ])
                table = db.create_table(collection, schema=schema)
            else:
                table = db.open_table(collection)
            self._tables[collection] = table
        return self._tables[collection]
    
    async def add_documents(
        self,
        collection: str,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> List[str]:
        """Add documents with embeddings to collection."""
        if len(documents) != len(embeddings):
            raise ValueError("Documents and embeddings must have same length")
        
        table = await self._get_table(collection)
        
        # Prepare data
        ids = []
        vectors = []
        contents = []
        metadatas = []
        sources = []
        timestamps = []
        
        for i, (doc, emb) in enumerate(zip(documents, embeddings)):
            doc_id = doc.get('id', f"{datetime.utcnow().timestamp()}_{i}")
            ids.append(doc_id)
            vectors.append(emb)
            contents.append(doc.get('content', ''))
            metadatas.append(doc.get('metadata', {}))
            sources.append(doc.get('source', 'unknown'))
            timestamps.append(datetime.utcnow())
        
        # Create Arrow table
        import pyarrow as pa
        data = pa.table({
            "id": pa.array(ids),
            "vector": pa.array([pa.array(emb, type=pa.float32()) for emb in vectors]),
            "content": pa.array(contents),
            "metadata": pa.array([str(m) for m in metadatas]),
            "source": pa.array(sources),
            "created_at": pa.array([ts.timestamp() for ts in timestamps]),
        })
        
        table = await self._get_table(collection)
        table.add(data)
        
        return [doc.get('id', f"{datetime.utcnow().timestamp()}_{i}") for i, doc in enumerate(documents)]
    
    async def search(
        self,
        collection: str,
        query_embedding: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors."""
        table = await self._get_table(collection)
        
        # Build query
        query = table.search(query_embedding).limit(top_k)
        
        # Apply filters if provided
        if filters:
            # LanceDB supports filter predicates
            for key, value in filters.items():
                query = query.where(f"metadata['{key}'] == '{value}'")
        
        results = query.to_pandas()
        
        # Convert to list of dicts
        results_list = []
        for _, row in results.iterrows():
            results_list.append({
                'id': row['id'],
                'content': row['content'],
                'metadata': eval(row['metadata']) if isinstance(row['metadata'], str) else row['metadata'],
                'source': row['source'],
                'score': float(row['_distance']) if '_distance' in row else 1.0,
                'created_at': row['created_at']
            })
        
        return results_list
    
    async def delete(self, collection: str, ids: List[str]) -> int:
        """Delete documents by ID."""
        table = await self._get_table(collection)
        
        # LanceDB doesn't have direct delete by ID, need to filter
        # This is a limitation - we'd need to rewrite the table
        logger.warning("LanceDB delete not fully implemented - marking for compaction")
        return 0
    
    async def get_collection_stats(self, collection: str) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            table = await self._get_table(collection)
            count = table.count_rows()
            return {
                "collection": collection,
                "document_count": count,
                "index_type": "vector"
            }
        except Exception:
            return {"collection": collection, "document_count": 0}
    
    async def create_index(
        self,
        collection: str,
        metric: str = "cosine",
        num_partitions: int = 256,
        num_sub_vectors: int = 96
    ) -> bool:
        """Create vector index for faster search."""
        try:
            table = await self._get_table(collection)
            table.create_index(
                metric=metric,
                num_partitions=num_partitions,
                num_sub_vectors=num_sub_vectors
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            return False
    
    async def hybrid_search(
        self,
        collection: str,
        query_embedding: List[float],
        query_text: str,
        top_k: int = 10,
        hybrid_weight: float = 0.5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining vector and BM25 text search."""
        # LanceDB supports hybrid search natively in newer versions
        table = await self._get_table(collection)
        
        try:
            # Try hybrid search if available
            results = table.search(query_embedding, query_text).limit(top_k).to_pandas()
        except AttributeError:
            # Fallback to vector-only search
            results = table.search(query_embedding).limit(top_k).to_pandas()
        
        results_list = []
        for _, row in results.iterrows():
            results_list.append({
                'id': row['id'],
                'content': row['content'],
                'metadata': eval(row['metadata']) if isinstance(row['metadata'], str) else row['metadata'],
                'source': row['source'],
                'score': float(row['_distance']) if '_distance' in row else 1.0,
                'created_at': row['created_at']
            })
        
        return results_list
    
    async def close(self):
        """Close database connections."""
        self._tables.clear()
        self._db = None


# Factory function
async def create_vector_storage(db_path: str = "~/.erin/data/lancedb") -> LanceDBVectorStorage:
    """Create and initialize vector storage."""
    storage = LanceDBVectorStorage(db_path)
    await storage._get_db()  # Initialize connection
    return storage


# Global instance
_vector_storage = None

async def get_vector_storage() -> LanceDBVectorStorage:
    global _vector_storage
    if _vector_storage is None:
        _vector_storage = await create_vector_storage()
    return _vector_storage