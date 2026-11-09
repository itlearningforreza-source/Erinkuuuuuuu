# Phase 12: AI Research Assistant - Design Document

## Overview
Phase 12 implements the AI Research Assistant - a conversational AI agent that serves as the primary natural-language interface to ERIN's analytical capabilities. The assistant combines Retrieval-Augmented Generation (RAG) over financial knowledge with a comprehensive tool-use framework to provide institutional-grade financial research and analysis.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    AIAssistant (Orchestrator)                 │
├─────────────────────────────────────────────────────────────┤
│  Conversation Manager  │  Mode Router  │  Tool Executor      │
├─────────────────────────────────────────────────────────────┤
│  RAG Pipeline          │  Tool Registry   │  Approval Mgr    │
├─────────────────────────────────────────────────────────────┤
│  Vector Store + Keyword  │  Tool Registry  │  Approval Queue │
│  Hybrid Retriever        │  15+ Tools      │  Audit Logger   │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. AIAssistant (Orchestrator)
**File:** `packages/market-intel/src/erin/market_intel/ai/assistant.py`

Main orchestration class managing:
- Conversation lifecycle (create, retrieve, persist)
- Mode routing (CHAT, RESEARCH, ANALYSIS, REPORT, TRADING, BACKTEST)
- Tool orchestration with approval workflows
- Callback system for UI integration

**Modes:**
- **CHAT**: General Q&A with RAG over knowledge base
- **RESEARCH**: Deep research with iterative retrieval
- **ANALYSIS**: Ticker/sector analysis with quantitative tools
- **REPORT**: Structured report generation with citations
- **TRADING**: Order placement, position management
- **BACKTEST**: Strategy backtesting with walk-forward validation

### 2. RAG Pipeline (`rag.py`)

#### DocumentChunker
- Configurable chunk size (default 512 tokens) and overlap (50 tokens)
- Article-aware chunking preserving title/summary/content structure
- Metadata propagation (source, timestamp, categories, tickers, sentiment)

#### VectorStore
- In-memory vector store with cosine similarity search
- Cosine similarity with configurable threshold
- Metadata filtering support
- In-memory storage (LanceDB integration ready)

#### EmbeddingProvider
- Pluggable embedding providers (Sentence Transformers, OpenAI, local)
- Deterministic pseudo-embeddings for testing
- Batch embedding for efficiency

#### KeywordRetriever (BM25)
- BM25 ranking with configurable k1, b parameters
- Term frequency / inverse document frequency
- Incremental index updates

#### HybridRetriever
- Reciprocal Rank Fusion (RRF) combining vector + keyword scores
- Configurable vector/keyword weights (default 0.7/0.3)
- Metadata filtering support
- Retrieval time tracking

#### Generator
- Multiple generation modes: SUMMARY, ANALYSIS, REPORT, QA, FORECAST
- Prompt templates per mode with financial domain context
- Citation tracking with relevance scores
- Mock generator for testing; pluggable LLM backend

#### RAGPipeline
- Document ingestion (chunking + embedding + indexing)
- News article ingestion with metadata extraction
- Query execution with retrieval + generation
- Ticker-specific analysis with metadata filtering
- Report generation with multi-ticker support

### 2. Tool Registry & Executor (`tools.py`)

#### ToolDefinition
- Name, version, description, I/O schemas (JSON Schema)
- Sensitivity levels: READ_ONLY, LOW, MEDIUM, HIGH, CRITICAL
- Sandbox profiles: PYTHON_BASIC, PYTHON_DATA, PYTHON_FULL, FINANCIAL_COMPUTE, SQL_READ, HTTP_GET
- Role-based access control (analyst, researcher, trader, admin)
- Rate limiting, timeout configuration

#### Registered Tools (15+)

| Tool | Category | Sensitivity | Sandbox |
|------|----------|-------------|---------|
| get_market_data | Market Data | READ_ONLY | PYTHON_DATA |
| get_fundamental_data | Fundamental | READ_ONLY | PYTHON_DATA |
| calculate_technical_indicators | Technical | READ_ONLY | PYTHON_DATA |
| calculate_var | Risk | MEDIUM | FINANCIAL_COMPUTE |
| run_stress_test | Risk | MEDIUM | FINANCIAL_COMPUTE |
| optimize_portfolio | Portfolio | MEDIUM | FINANCIAL_COMPUTE |
| run_backtest | Trading | MEDIUM | FINANCIAL_COMPUTE |
| run_monte_carlo | Quant | MEDIUM | PYTHON_DATA |
| run_factor_analysis | Quant | MEDIUM | FINANCIAL_COMPUTE |
| get_economic_calendar | Macro | READ_ONLY | PYTHON_DATA |
| search_news | News | READ_ONLY | PYTHON_DATA |
| analyze_text | NLP | READ_ONLY | PYTHON_DATA |
| execute_python | Utility | HIGH | PYTHON_FULL |
| query_database | Data | MEDIUM | SQL_READ |
| http_request | External | MEDIUM | HTTP_GET |

#### ToolExecutor
- Input validation against JSON Schema
- Sandboxed execution with timeout
- Audit trail with hash chain
- Approval workflow for HIGH/CRITICAL tools
- Error handling and structured error responses

### 3. Approval Manager (`tools.py`)

- Pending approval queue for HIGH/CRITICAL tools
- Human-in-the-loop approval/rejection
- Configurable cooldown periods
- Approval audit trail with hash chain

### 4. AIAssistant Orchestrator

#### Modes
| Mode | Description | RAG Mode | Tools |
|------|-------------|----------|-------|
| CHAT | General conversation | CHAT | Optional |
| RESEARCH | Deep research | ANALYSIS | Extensive |
| ANALYSIS | Ticker/sector analysis | ANALYSIS | Quant tools |
| REPORT | Report generation | REPORT | Research tools |
| TRADING | Order management | N/A | Trading tools |
| BACKTEST | Strategy validation | N/A | Backtest |

#### Conversation Management
- Persistent conversation history
- Tool call/result tracking in message flow
- Configurable history window (default 20 messages)
- Mode switching within conversation

### 5. Integration Points

#### RAG Pipeline Integration
- DocumentChunker for financial documents (SEC filings, research reports, news)
- VectorStore with LanceDB backend (production) / in-memory (dev)
- EmbeddingProvider: sentence-transformers (local) / OpenAI / Cohere
- HybridRetriever: RRF fusion of vector + BM25
- Generator: OpenAI GPT-4 / Anthropic Claude / Local LLM

#### Tool Integration
- ToolExecutor integrates with all quantitative engines:
  - VaREngine (risk/var.py)
  - OptimizationEngine (quant/optimization.py)
  - MonteCarloEngine (quant/monte_carlo.py)
  - FactorModelEngine (quant/factor_models.py)
  - EventDrivenBacktester (trading/backtest.py)
  - StressTestingEngine (risk/var.py)

#### Data Integration
- SQLite for transactions, positions, orders, audit
- DuckDB for analytical queries (returns, factor exposures)
- Parquet for historical market data
- LanceDB for vector embeddings
- SQLite for news articles, economic calendar

## Implementation Status

### Completed ✅
- [x] RAG Pipeline (rag.py) - Complete with hybrid retrieval
- [x] Document Chunking & Embedding (DocumentChunker, EmbeddingProvider)
- [x] Vector Store + Keyword Retrieval (VectorStore, KeywordRetriever)
- [x] Hybrid Retriever with RRF fusion
- [x] Generator with 5 modes (SUMMARY, ANALYSIS, REPORT, QA, FORECAST)
- [x] RAG Pipeline orchestration (RAGPipeline)
- [x] Tool Registry with 15+ financial tools
- [x] Tool Executor with sandboxing & audit
- [x] Approval Manager for sensitive tools
- [x] AI Assistant Orchestrator (6 modes)
- [x] Conversation Management with tool tracking
- [x] NLP Processor integration (ticker extraction, sentiment, categorization)
- [x] Tool Executor with sandboxing & approval workflows

### In Progress 🔄
- [ ] LanceDB Vector Store production backend
- [ ] OpenAI/Anthropic LLM integration in Generator
- [ ] Real-time streaming market data in tools
- [ ] WebSocket support for real-time updates

### Planned 📋
- [ ] Multi-user session isolation
- [ ] Advanced report templating
- [ ] Automated fact-checking against trusted sources
- [ ] Multi-modal (charts, tables in responses)
- [ ] Fine-tuned financial domain LLM

## Configuration

### RAGConfig
```python
RAGConfig(
    retrieval_strategy=RetrievalStrategy.HYBRID,
    top_k=10,
    similarity_threshold=0.7,
    max_context_tokens=4000,
    generation_model="gpt-4",
    generation_mode=GenerationMode.ANALYSIS,
    temperature=0.3,
    max_tokens=2000,
    system_prompt="You are a financial research assistant.",
    vector_weight=0.7,
    keyword_weight=0.3,
    chunk_size=512,
    chunk_overlap=50,
    min_chunk_size=100
)
```

### Tool Registry Configuration
```python
ToolDefinition(
    name="calculate_var",
    version="1.0",
    description="Calculate Value at Risk for a portfolio",
    input_schema={...},
    output_schema={...},
    sensitivity=ToolSensitivity.MEDIUM,
    sandbox_profile=SandboxProfile.FINANCIAL_COMPUTE,
    timeout_seconds=30,
    allowed_roles=["analyst", "researcher", "trader", "admin"]
)
```

## API Usage Examples

### Basic Chat
```python
assistant = create_ai_assistant(enable_tools=True)
session = create_assistant_session(assistant, "user_123")
response = await session.send("What's the current outlook for AAPL?")
```

### Research Mode
```python
session.set_mode(AssistantMode.RESEARCH)
response = await session.send("Analyze the impact of Fed rate cuts on tech sector")
```

### Analysis Mode
```python
session.set_mode(AssistantMode.ANALYSIS)
analysis = await session.send("Analyze AAPL's Q3 earnings and forward guidance")
```

### Report Generation
```python
session.set_mode(AssistantMode.REPORT)
report = await session.send("Generate Q3 2024 earnings report for MAG7 stocks")
```

### Tool Execution
```python
# Direct tool use
tool_executor = ToolExecutor(ToolRegistry())
result = await tool_executor.execute(
    "calculate_var",
    {"positions": {"AAPL": 100000, "MSFT": 50000}, "confidence": 0.95},
    "session_123", "user_456"
)
```

## Security Considerations

1. **Sandboxed Execution**: Python execution in restricted subprocess
2. **Approval Workflow**: HIGH/CRITICAL tools require human approval
3. **Audit Trail**: Hash-chained audit log for all tool executions
4. **Role-Based Access**: Role-based tool access control
5. **Rate Limiting**: Configurable per-tool rate limits
6. **Input Validation**: JSON Schema validation on all inputs
7. **Audit Hash Chain**: Tamper-evident execution log

## Testing

### Unit Tests
- RAG Pipeline: chunking, embedding, retrieval, generation
- Tool Executor: each tool with valid/invalid inputs
- Approval Manager: approval/rejection workflows
- Assistant Modes: each mode with sample queries

### Integration Tests
- RAG Pipeline end-to-end with sample documents
- Tool Executor with real market data
- Assistant modes with sample conversations
- Approval workflow with mock approver

## Deployment Considerations

### Production LLM Integration
```python
# Generator with OpenAI
class OpenAIGenerator(Generator):
    def __init__(self, config, api_key):
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def _mock_generate(self, prompt, mode):
        response = await self.client.chat.completions.create(
            model=self.config.generation_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        return response.choices[0].message.content
```

### LanceDB Vector Store
```python
class LanceDBVectorStore(VectorStore):
    def __init__(self, db_path, dimension=384):
        self.db = lancedb.connect(db_path)
        self.table = self.db.create_table("documents", schema=...)
    
    def add_documents(self, chunks, embeddings):
        data = [{"id": c.id, "vector": e, "text": c.content, "metadata": c.metadata} 
                for c, e in zip(chunks, embeddings)]
        self.table.add(data)
    
    def search(self, query_embedding, top_k, filter_metadata, threshold):
        query = self.table.search(query_embedding).limit(top_k)
        if filter_metadata:
            query = query.where(...filter conditions...)
        results = query.to_pandas()
        # Convert to DocumentChunk + score
```

## Dependencies

### Core Dependencies
- `sentence-transformers` - Embeddings
- `lancedb` - Vector database
- `openai` / `anthropic` - LLM APIs
- `aiohttp` - HTTP requests
- `feedparser` - RSS feeds
- `pydantic` - Schema validation
- `numpy`, `scipy` - Computations
- `pandas`, `polars` - DataFrames

### Development Dependencies
- `pytest`, `pytest-asyncio` - Testing
- `pytest-mock` - Mocking
- `black`, `ruff` - Formatting/linting
- `mypy` - Type checking

## Performance Targets

| Metric | Target |
|--------|--------|
| RAG Query Latency | < 2s (p95) |
| Tool Execution | < 5s (p95) |
| RAG Index Build | < 30s per 10K docs |
| Embedding Generation | < 100ms per 100 texts |
| Tool Approval Latency | < 1s (async) |
| Memory Usage | < 2GB (incl. vector store) |

## Monitoring & Observability

### Metrics
- RAG query latency (p50, p95, p99)
- Tool execution latency & success rate
- Approval queue depth & latency
- RAG retrieval precision/recall (eval set)
- Token usage & cost tracking

### Logging
- Structured JSON logs
- Conversation trace IDs
- Tool execution audit logs
- Error categorization & alerting

## Future Enhancements

1. **Multi-modal Responses**: Charts, tables, inline visualizations
2. **Fine-tuned Financial LLM**: Domain-adapted model for higher accuracy
3. **Automated Fact-Checking**: Cross-reference claims against trusted sources
4. **Collaborative Research**: Multi-user workspaces with shared context
5. **Automated Report Scheduling**: Recurring report generation
6. **Voice Interface**: Speech-to-text / text-to-speech
7. **Mobile Companion**: React Native companion app

---

*Document Version: 1.0*
*Last Updated: 2025*
*Author: ERIN Development Team*