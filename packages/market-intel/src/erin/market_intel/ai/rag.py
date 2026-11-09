"""RAG Pipeline - Retrieval-Augmented Generation for financial research."""

import asyncio
import logging
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Any, Callable, Tuple
from enum import Enum
from typing import TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    pass

from erin.market_intel.macro.news import NewsArticle, NewsCategory
from erin.market_intel.macro.news import NLPProcessor

logger = logging.getLogger(__name__)


class RetrievalStrategy(str, Enum):
    VECTOR_SIMILARITY = "VECTOR_SIMILARITY"
    HYBRID = "HYBRID"  # Vector + keyword
    KEYWORD = "KEYWORD"
    SEMANTIC = "SEMANTIC"


class GenerationMode(str, Enum):
    SUMMARY = "SUMMARY"
    ANALYSIS = "ANALYSIS"
    REPORT = "REPORT"
    QA = "QA"
    FORECAST = "FORECAST"


@dataclass
class DocumentChunk:
    """Document chunk for retrieval."""
    id: str = ""
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    source_document_id: str = ""
    chunk_index: int = 0
    token_count: int = 0
    
    @property
    def preview(self) -> str:
        return self.content[:200] + "..." if len(self.content) > 200 else self.content


@dataclass
class RetrievalResult:
    """Result of document retrieval."""
    chunks: List[DocumentChunk] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    query: str = ""
    retrieval_time_ms: float = 0
    strategy: RetrievalStrategy = RetrievalStrategy.VECTOR_SIMILARITY
    
    @property
    def context(self) -> str:
        return "\n\n---\n\n".join([c.content for c in self.chunks])


@dataclass
class GenerationResult:
    """Result of text generation."""
    text: str = ""
    citations: List[Dict[str, Any]] = field(default_factory=list)
    confidence: Decimal = Decimal('0')
    generation_time_ms: float = 0
    tokens_used: int = 0
    model: str = ""
    
    def add_citation(self, chunk_id: str, text: str, relevance: float):
        self.citations.append({
            "chunk_id": chunk_id,
            "text": text[:200],
            "relevance": relevance
        })


@dataclass
class RAGConfig:
    """RAG pipeline configuration."""
    # Retrieval
    retrieval_strategy: RetrievalStrategy = RetrievalStrategy.HYBRID
    top_k: int = 10
    similarity_threshold: float = 0.7
    max_context_tokens: int = 4000
    
    # Generation
    generation_model: str = "gpt-4"
    generation_mode: GenerationMode = GenerationMode.ANALYSIS
    temperature: float = 0.3
    max_tokens: int = 2000
    system_prompt: str = ""
    
    # Retrieval weights (for hybrid)
    vector_weight: float = 0.7
    keyword_weight: float = 0.3
    
    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 50
    min_chunk_size: int = 100


class DocumentChunker:
    """Split documents into chunks for retrieval."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
    
    def chunk_text(self, text: str, metadata: Dict = None) -> List[DocumentChunk]:
        """Split text into overlapping chunks."""
        chunks = []
        words = text.split()
        
        if len(words) <= self.config.min_chunk_size:
            return [DocumentChunk(
                id=hashlib.md5(text.encode()).hexdigest()[:16],
                content=text,
                metadata=metadata or {},
                token_count=len(words)
            )]
        
        step = self.config.chunk_size - self.config.chunk_overlap
        
        for i in range(0, len(words), step):
            chunk_words = words[i:i + self.config.chunk_size]
            if len(chunk_words) < self.config.min_chunk_size:
                break
            
            chunk_text = " ".join(chunk_words)
            chunk = DocumentChunk(
                id=hashlib.md5(chunk_text.encode()).hexdigest()[:16],
                content=chunk_text,
                metadata=metadata or {},
                chunk_index=len(chunks),
                token_count=len(chunk_words)
            )
            chunks.append(chunk)
        
        return chunks
    
    def chunk_article(self, article: 'NewsArticle') -> List[DocumentChunk]:
        """Chunk a news article into retrieval chunks."""
        # Combine title, summary, content
        full_text = f"{article.title}\n\n{article.summary}\n\n{article.content}"
        metadata = {
            "source": article.source.value,
            "published_at": article.published_at.isoformat(),
            "categories": [c.value for c in article.categories],
            "tickers": article.tickers,
            "url": article.url,
            "sentiment": article.sentiment.value,
        }
        return self.chunk_text(full_text, metadata)


class VectorStore:
    """Vector store for document embeddings."""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self._vectors: Dict[str, List[float]] = {}
        self._metadata: Dict[str, Dict] = {}
        self._documents: Dict[str, DocumentChunk] = {}
    
    def add_documents(self, chunks: List[DocumentChunk], embeddings: List[List[float]]):
        """Add documents with embeddings."""
        for chunk, embedding in zip(chunks, embeddings):
            self._vectors[chunk.id] = embedding
            self._documents[chunk.id] = chunk
            self._metadata[chunk.id] = chunk.metadata
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter_metadata: Dict = None,
        threshold: float = 0.0
    ) -> List[Tuple[DocumentChunk, float]]:
        """Search for similar vectors."""
        if not self._vectors:
            return []
        
        query_vec = np.array(query_embedding)
        query_norm = np.linalg.norm(query_vec)
        
        if query_norm == 0:
            return []
        
        results = []
        for doc_id, vec in self._vectors.items():
            # Apply metadata filter
            if filter_metadata:
                meta = self._metadata.get(doc_id, {})
                match = all(meta.get(k) == v for k, v in filter_metadata.items())
                if not match:
                    continue
            
            vec_norm = np.linalg.norm(vec)
            if vec_norm == 0:
                continue
            
            similarity = np.dot(query_vec, vec) / (query_norm * vec_norm)
            
            if similarity >= threshold:
                chunk = self._documents.get(doc_id)
                if chunk:
                    results.append((chunk, float(similarity)))
        
        # Sort by similarity descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_documents": len(self._documents),
            "dimension": self.dimension,
            "memory_estimate_mb": len(self._vectors) * self.dimension * 4 / (1024 * 1024)
        }


class EmbeddingProvider:
    """Provider for text embeddings."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        # In production, would use sentence-transformers or OpenAI embeddings
        # For now, return dummy embeddings
        embeddings = []
        for text in texts:
            # Create deterministic pseudo-embedding based on text hash
            hash_val = hashlib.md5(text.encode()).hexdigest()
            np.random.seed(int(hash_val[:8], 16))
            embedding = np.random.normal(0, 1, 384)
            embedding = embedding / np.linalg.norm(embedding)
            embeddings.append(embedding.tolist())
        return embeddings
    
    async def embed_query(self, query: str) -> List[float]:
        """Embed a single query."""
        return (await self.embed_texts([query]))[0]


class KeywordRetriever:
    """Keyword-based retrieval using BM25 or TF-IDF."""
    
    def __init__(self):
        self._documents: Dict[str, DocumentChunk] = {}
        self._term_freq: Dict[str, Dict[str, int]] = {}
        self._doc_freq: Dict[str, int] = {}
        self._total_docs = 0
    
    def add_documents(self, chunks: List[DocumentChunk]):
        """Add documents to index."""
        for chunk in chunks:
            self._documents[chunk.id] = chunk
            self._total_docs += 1
            
            # Build term frequency
            terms = chunk.content.lower().split()
            tf = {}
            for term in terms:
                tf[term] = tf.get(term, 0) + 1
            self._term_freq[chunk.id] = tf
            
            # Update document frequency
            unique_terms = set(terms)
            for term in unique_terms:
                self._doc_freq[term] = self._doc_freq.get(term, 0) + 1
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[DocumentChunk, float]]:
        """BM25 search."""
        if not self._documents:
            return []
        
        query_terms = query.lower().split()
        
        # Calculate BM25 scores
        scores = {}
        k1 = 1.5
        b = 0.75
        avgdl = sum(len(d.content.split()) for d in self._documents.values()) / max(len(self._documents), 1)
        
        for doc_id, chunk in self._documents.items():
            doc_len = len(chunk.content.split())
            score = 0.0
            
            for term in query_terms:
                if term not in self._doc_freq:
                    continue
                
                tf = self._term_freq[doc_id].get(term, 0)
                if tf == 0:
                    continue
                
                idf = np.log((self._total_docs - self._doc_freq[term] + 0.5) / (self._doc_freq[term] + 0.5))
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * doc_len / avgdl)
                score += idf * (numerator / denominator)
            
            if score > 0:
                scores[chunk.id] = score
        
        # Sort and return top-k
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for doc_id, score in sorted_results[:top_k]:
            chunk = self._documents.get(doc_id)
            if chunk:
                results.append((chunk, score))
        
        return results


class HybridRetriever:
    """Hybrid retriever combining vector and keyword search."""
    
    def __init__(
        self,
        vector_store: VectorStore,
        keyword_retriever: KeywordRetriever,
        embedding_provider: EmbeddingProvider,
        config: RAGConfig
    ):
        self.vector_store = vector_store
        self.keyword_retriever = keyword_retriever
        self.embedding_provider = embedding_provider
        self.config = config
    
    async def retrieve(self, query: str, top_k: int = None, filter_metadata: Dict = None) -> RetrievalResult:
        """Hybrid retrieval combining vector and keyword search."""
        import time
        start_time = time.time()
        
        top_k = top_k or self.config.top_k
        
        # Vector search
        query_embedding = await self.embedding_provider.embed_query(query)
        vector_results = self.vector_store.search(
            query_embedding,
            top_k=top_k * 2,  # Get more for fusion
            filter_metadata=filter_metadata,
            threshold=self.config.similarity_threshold
        )
        
        # Keyword search
        keyword_results = self.keyword_retriever.search(query, top_k=top_k * 2)
        
        # Fusion (Reciprocal Rank Fusion)
        fused_scores = {}
        
        for rank, (chunk, score) in enumerate(vector_results):
            fused_scores[chunk.id] = fused_scores.get(chunk.id, 0) + self.config.vector_weight / (rank + 1 + 60)
        
        for rank, (chunk, score) in enumerate(keyword_results):
            fused_scores[chunk.id] = fused_scores.get(chunk.id, 0) + self.config.keyword_weight / (rank + 1 + 60)
        
        # Sort by fused score
        sorted_results = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Get top-k chunks
        top_chunks = []
        final_scores = []
        for chunk_id, score in sorted_results[:top_k]:
            # Find chunk from either result set
            chunk = None
            for c, _ in vector_results:
                if c.id == chunk_id:
                    chunk = c
                    break
            if not chunk:
                for c, _ in keyword_results:
                    if c.id == chunk_id:
                        chunk = c
                        break
            
            if chunk:
                top_chunks.append(chunk)
                final_scores.append(score)
        
        retrieval_time = (time.time() - start_time) * 1000
        
        return RetrievalResult(
            chunks=top_chunks,
            scores=final_scores,
            query=query,
            retrieval_time_ms=retrieval_time,
            strategy=RetrievalStrategy.HYBRID
        )


class Generator:
    """Text generation using LLMs."""
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self._model = None
    
    async def generate(
        self,
        query: str,
        context: str,
        mode: GenerationMode = None
    ) -> GenerationResult:
        """Generate response based on query and context."""
        import time
        start_time = time.time()
        
        mode = mode or self.config.generation_mode
        
        # Build prompt based on mode
        prompt = self._build_prompt(query, context, mode)
        
        # In production, would call LLM API
        # For now, return structured response based on mode
        text = await self._mock_generate(prompt, mode)
        
        generation_time = (time.time() - start_time) * 1000
        
        return GenerationResult(
            text=text,
            citations=[],
            confidence=Decimal('0.85'),
            generation_time_ms=generation_time,
            tokens_used=len(text.split()),
            model=self.config.generation_model
        )
    
    def _build_prompt(self, query: str, context: str, mode: GenerationMode) -> str:
        """Build prompt based on generation mode."""
        
        base_prompt = self.config.system_prompt or "You are a financial research assistant."
        
        if mode == GenerationMode.SUMMARY:
            prompt = f"{base_prompt}\n\nSummarize the following financial documents:\n\n{context}\n\nQuery: {query}\n\nSummary:"
        elif mode == GenerationMode.ANALYSIS:
            prompt = f"{base_prompt}\n\nAnalyze the following financial information:\n\n{context}\n\nQuestion: {query}\n\nAnalysis:"
        elif mode == GenerationMode.REPORT:
            prompt = f"{base_prompt}\n\nGenerate a comprehensive financial report based on:\n\n{context}\n\nTopic: {query}\n\nReport:"
        elif mode == GenerationMode.QA:
            prompt = f"{base_prompt}\n\nAnswer the question based on the provided context:\n\n{context}\n\nQuestion: {query}\n\nAnswer:"
        elif mode == GenerationMode.FORECAST:
            prompt = f"{base_prompt}\n\nProvide a forecast based on the following data:\n\n{context}\n\nForecast request: {query}\n\nForecast:"
        else:
            prompt = f"{base_prompt}\n\nContext:\n{context}\n\nQuery: {query}\n\nResponse:"
        
        return prompt
    
    async def _mock_generate(self, prompt: str, mode: GenerationMode) -> str:
        """Mock generation for testing."""
        # In production, would call OpenAI, Anthropic, or local LLM
        if mode == GenerationMode.SUMMARY:
            return "Based on the provided documents, the key findings are: [summary would be generated here]"
        elif mode == GenerationMode.ANALYSIS:
            return "Analysis of the provided financial data reveals: [analysis would be generated here]"
        elif mode == GenerationMode.REPORT:
            return "# Financial Report\n\n## Executive Summary\n[report content would be generated here]"
        elif mode == GenerationMode.QA:
            return "Based on the provided context: [answer would be generated here]"
        elif mode == GenerationMode.FORECAST:
            return "Based on historical data and current trends: [forecast would be generated here]"
        return "Response generated based on context."


class RAGPipeline:
    """Main RAG pipeline orchestrating retrieval and generation."""
    
    def __init__(self, config: RAGConfig = None):
        self.config = config or RAGConfig()
        
        # Components
        self.chunker = DocumentChunker(self.config)
        self.vector_store = VectorStore()
        self.keyword_retriever = KeywordRetriever()
        self.embedding_provider = EmbeddingProvider()
        self.retriever = HybridRetriever(
            self.vector_store,
            self.keyword_retriever,
            EmbeddingProvider(),
            self.config
        )
        self.generator = Generator(self.config)
        self.nlp = NLPProcessor()
    
    async def add_documents(self, documents: List[Any]) -> int:
        """Add documents to the knowledge base."""
        all_chunks = []
        
        for doc in documents:
            if hasattr(doc, 'content'):  # NewsArticle-like
                chunks = self.chunker.chunk_text(doc.content, doc.metadata if hasattr(doc, 'metadata') else {})
            else:
                chunks = self.chunker.chunk_text(str(doc))
            all_chunks.extend(chunks)
        
        # Generate embeddings
        texts = [c.content for c in all_chunks]
        embeddings = await self.embedding_provider.embed_texts(texts)
        
        # Store in vector store and keyword retriever
        self.vector_store.add_documents(all_chunks, embeddings)
        self.keyword_retriever.add_documents(all_chunks)
        
        return len(all_chunks)
    
    async def add_news_articles(self, articles: List['NewsArticle']) -> int:
        """Add news articles to knowledge base."""
        all_chunks = []
        for article in articles:
            chunks = self.chunker.chunk_article(article)
            all_chunks.extend(chunks)
        
        texts = [c.content for c in all_chunks]
        embeddings = await self.embedding_provider.embed_texts(texts)
        
        self.vector_store.add_documents(all_chunks, embeddings)
        self.keyword_retriever.add_documents(all_chunks)
        
        return len(all_chunks)
    
    async def query(
        self,
        query: str,
        mode: GenerationMode = None,
        top_k: int = None,
        filter_metadata: Dict = None
    ) -> Dict[str, Any]:
        """Execute RAG query."""
        # Retrieve
        retrieval = await self.retriever.retrieve(query, top_k, filter_metadata)
        
        # Generate
        context = retrieval.context
        generation = await self.generator.generate(query, context, mode)
        
        # Add citations from retrieval
        for i, (chunk, score) in enumerate(zip(retrieval.chunks, retrieval.scores)):
            generation.add_citation(chunk.id, chunk.content[:200], score)
        
        return {
            "query": query,
            "answer": generation.text,
            "citations": generation.citations,
            "confidence": float(generation.confidence),
            "retrieval": {
                "chunks_found": len(retrieval.chunks),
                "retrieval_time_ms": retrieval.retrieval_time_ms,
                "strategy": retrieval.strategy.value
            },
            "generation": {
                "model": generation.model,
                "tokens_used": generation.tokens_used,
                "time_ms": generation.generation_time_ms
            }
        }
    
    async def analyze_ticker(self, ticker: str, question: str = None) -> Dict[str, Any]:
        """Analyze a specific ticker using relevant documents."""
        query = f"{ticker} {question}" if question else f"Analyze {ticker} financial performance and outlook"
        
        # Filter by ticker in metadata
        retrieval = await self.retriever.retrieve(
            query,
            filter_metadata={"tickers": ticker}
        )
        
        if not retrieval.chunks:
            return {"error": f"No documents found for {ticker}"}
        
        generation = await self.generator.generate(
            question or f"Analyze {ticker}",
            retrieval.context,
            GenerationMode.ANALYSIS
        )
        
        return {
            "ticker": ticker,
            "analysis": generation.text,
            "sources": len(retrieval.chunks),
            "confidence": float(generation.confidence)
        }
    
    async def generate_report(
        self,
        topic: str,
        tickers: List[str] = None,
        date_range: Tuple[date, date] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive report."""
        # Build query
        query_parts = [topic]
        if tickers:
            query_parts.append(f"tickers: {', '.join(tickers)}")
        query = " ".join(query_parts)
        
        # Build filter
        filter_meta = {}
        if tickers:
            filter_meta["tickers"] = tickers
        if date_range:
            filter_meta["date_range"] = date_range
        
        retrieval = await self.retriever.retrieve(query, filter_metadata=filter_meta)
        
        generation = await self.generator.generate(
            f"Generate comprehensive report on {topic}",
            retrieval.context,
            GenerationMode.REPORT
        )
        
        return {
            "topic": topic,
            "report": generation.text,
            "sources": len(retrieval.chunks),
            "citations": generation.citations,
            "confidence": float(generation.confidence)
        }


def create_rag_pipeline(config: RAGConfig = None) -> RAGPipeline:
    return RAGPipeline(config)


def create_rag_config(
    strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
    top_k: int = 10,
    model: str = "gpt-4",
    mode: GenerationMode = GenerationMode.ANALYSIS
) -> RAGConfig:
    return RAGConfig(
        retrieval_strategy=strategy,
        top_k=top_k,
        generation_model=model,
        generation_mode=mode
    )