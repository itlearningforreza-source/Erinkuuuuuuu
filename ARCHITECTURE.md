# ERIN 2.0 — SYSTEM ARCHITECTURE SPECIFICATION

**Version:** 1.0
**Status:** DRAFT
**Classification:** INTERNAL — ARCHITECTURE
**Owner:** Principal Architect
**Phase:** 2 — Domain & System Architecture

---

## 1. Architectural Style

**Modular Monolith** with explicit bounded contexts, dependency inversion, and stable internal contracts. Migration path to distributed services documented from inception.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ERIN APPLICATION                                │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────────┐ │
│  │   TAURI 2 SHELL  │  │   REACT FRONTEND  │  │   FASTAPI BACKEND (Python) │ │
│  │  (Rust + WebView)│◄─┤  (TypeScript)     │◄─┤  (Internal API only)       │ │
│  └──────────────────┘  └──────────────────┘  └────────────────────────────┘ │
│         ▲                       ▲                        ▲                  │
│         │                       │                        │                  │
│         ▼                       ▼                        ▼                  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    DOMAIN LAYER (Bounded Contexts)                     │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐        │  │
│  │  │ Market  │ │ Data    │ │ Equity  │ │Quant/   │ │Portfolio│        │  │
│  │  │ Intel   │ │ Infra   │ │Research │ │Risk     │ │/Risk    │  ...   │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│         ▲                       ▲                        ▲                  │
│         └───────────────────────┼────────────────────────┘                  │
│                                 ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      INFRASTRUCTURE LAYER                              │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐   │  │
│  │  │   SQLite     │ │   DuckDB     │ │   Parquet    │ │  Providers │   │  │
│  │  │ (Transactional)│ │ (Analytical) │ │ (Historical) │ │ (Adapters) │   │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Bounded Contexts & Ownership

| Context | Package | Owner | Primary Tables | Key Services |
|---------|---------|-------|----------------|--------------|
| `market_intel` | `packages/market-intel` | Market Intelligence | `instruments`, `quotes`, `watchlists`, `calendars` | Quote stream, watchlist CRUD, screener |
| `data_infra` | `packages/data-infra` | Data Engineering | `providers`, `ingestion_jobs`, `data_quality`, `lineage` | Adapter registry, ingestion pipeline, validation |
| `equity_research` | `packages/equity-research` | Fundamental Research | `companies`, `financials`, `filings`, `ratios` | Statement parser, ratio engine, peer lookup |
| `quant_finance` | `packages/quant-finance` | Quant Finance | `models`, `simulations`, `distributions` | Monte Carlo, GBM, optimization, derivatives |
| `portfolio_risk` | `packages/portfolio-risk` | Portfolio & Risk | `portfolios`, `positions`, `var_models`, `stress_tests` | Construction, VaR/ES, attribution, rebalancing |
| `fixed_income` | `packages/fixed-income` | Fixed Income | `bonds`, `curves`, `spreads` | Pricing, bootstrapping, analytics |
| `derivatives` | `packages/derivatives` | Derivatives | `options`, `futures`, `swaps`, `vol_surfaces` | BSM, binomial, Greeks, hedging |
| `macro_intel` | `packages/macro-intel` | Macro Intelligence | `indicators`, `yield_curves`, `central_bank_actions` | FRED/IMF/OECD adapters, calendar |
| `news_intel` | `packages/news-intel` | News Intelligence | `articles`, `entities`, `events`, `sentiment` | Ingestion, NER, classification, mapping |
| `workspace` | `packages/workspace` | Workspace | `notebooks`, `workspaces`, `reports`, `experiments` | Notebook kernel, versioning, export |
| `ai_intelligence` | `packages/ai-intelligence` | AI Research | `rag_index`, `tool_calls`, `audit_log` | RAG, tool executor, sandbox |
| `governance` | `packages/governance` | Security/Governance | `users`, `roles`, `permissions`, `audit_events` | AuthN/AuthZ, RBAC, audit, licensing |

---

## 3. Cross-Cutting Contracts (Stable Internal APIs)

All inter-context communication via **typed Pydantic schemas** over **internal FastAPI routes** (not direct imports).

### 3.1 Market Intel → Portfolio Risk
```python
# GET /api/v1/internal/market-intel/quotes?symbols=AAPL,MSFT
class QuoteBatch(BaseModel):
    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal
    bid_size: int
    ask_size: int
    timestamp: datetime
    source: ProviderId
    currency: CurrencyCode
```

### 3.2 Data Infra → All Contexts
```python
# POST /api/v1/internal/data-infra/ingest
class IngestionJobRequest(BaseModel):
    provider: ProviderId
    dataset: DatasetId
    params: dict[str, Any]
    priority: JobPriority = JobPriority.NORMAL

class IngestionJobResponse(BaseModel):
    job_id: JobId
    status: JobStatus
    estimated_completion: Optional[datetime]
```

### 3.3 Equity Research → Quant Finance
```python
# GET /api/v1/internal/equity-research/fundamentals/{symbol}
class FundamentalsSnapshot(BaseModel):
    symbol: str
    period: Date
    revenue: Optional[Decimal]
    ebitda: Optional[Decimal]
    net_income: Optional[Decimal]
    total_assets: Optional[Decimal]
    total_equity: Optional[Decimal]
    operating_cash_flow: Optional[Decimal]
    free_cash_flow: Optional[Decimal]
    shares_outstanding: Optional[Decimal]
    currency: CurrencyCode
    source: ProviderId
    filing_date: datetime
```

### 3.4 Quant Finance → Portfolio Risk
```python
# POST /api/v1/internal/quant-finance/simulate
class SimulationRequest(BaseModel):
    model: SimulationModel  # GBM, JUMP_DIFFUSION, HESTON
    params: dict[str, Any]
    n_paths: int
    n_steps: int
    horizon_days: int
    correlation_matrix: Optional[list[list[float]]]
    seed: Optional[int]

class SimulationResponse(BaseModel):
    paths: list[list[float]]  # [path][step]
    statistics: SimulationStatistics
    computation_time_ms: float
```

---

## 4. Layer Architecture Rules

### 4.1 Dependency Direction (STRICT)
```
UI Layer (React) → API Layer (FastAPI) → Domain Layer → Infrastructure Layer
     ↑                  ↑                    ↑                    ↑
  NEVER              NEVER               NEVER               NEVER
  imports            imports             imports             imports
  downward           downward            downward            downward
```

### 4.2 Enforcement Mechanisms
- **ECP Script:** `scripts/ecp/arch_check.py` — AST analysis of imports
- **CI Gate:** Fails build on layer violations
- **Package Boundaries:** Each context is a separate Python package with `__init__.py` exporting only public API

### 4.3 Allowed Cross-Context Communication
1. **Internal HTTP APIs** (FastAPI routes under `/api/v1/internal/`)
2. **Domain Events** (async, via internal event bus)
3. **Shared Types** (Pydantic schemas in `packages/shared-types`)

---

## 5. Technology Stack Decisions

| Layer | Technology | Version | Rationale |
|-------|------------|---------|-----------|
| **Desktop Shell** | Tauri 2 | 2.0.x | Native performance, small bundle, secure IPC |
| **Frontend Framework** | React | 18.3.x | Concurrent features, ecosystem, talent pool |
| **Language** | TypeScript | 5.6.x | Type safety, IDE support |
| **Build Tool** | Vite | 5.4.x | Fast HMR, optimized builds |
| **UI Primitives** | Radix UI | 1.1.x | Accessible, unstyled, composable |
| **Styling** | Tailwind CSS | 3.4.x | Design system, dark-first, compact |
| **Charts** | Lightweight Charts | 4.2.x | 60fps, financial types, 45KB gz |
| **State (Server)** | TanStack Query | 5.5.x | Server cache, deduplication, mutations |
| **State (Client)** | Zustand | 4.5.x | Minimal boilerplate, TypeScript-first |
| **Backend Framework** | FastAPI | 0.115.x | Native async, OpenAPI, validation, performance |
| **Validation** | Pydantic | 2.9.x | v2 performance, strict modes |
| **Transactional DB** | SQLite | 3.46.x | Zero-config, ACID, WAL mode |
| **Analytical DB** | DuckDB | 1.1.x | Columnar, Parquet-native, embedded |
| **Historical Storage** | Apache Parquet | 1.15.x | Columnar compression, predicate pushdown |
| **Columnar Exchange** | PyArrow | 17.0.x | Zero-copy between DuckDB/Polars/Pandas |
| **Quant Compute** | NumPy/SciPy | 2.0.x / 1.14.x | Mature, tested, no GPU needed |
| **DataFrames** | Polars | 1.10.x | Fast, streaming, expressions |
| **Statistics** | statsmodels | 0.14.x | Econometrics, time-series |
| **Optimization** | CVXPY | 1.6.x | DCP verification, multiple solvers |
| **ML** | scikit-learn | 1.5.x | Classical ML, preprocessing |
| **Task Queue** | Redis + BullMQ | 7.2.x / 5.2.x | Priority, retries, scheduling |
| **Vector DB** | LanceDB | 0.12.x | Embedded, Arrow-native, no server |
| **Observability** | OpenTelemetry | 1.28.x | Vendor-neutral, standard |
| **Testing (Python)** | pytest + Hypothesis | 8.3.x / 6.100.x | Property-based, fixtures |
| **Testing (JS)** | Vitest + Playwright | 2.1.x / 1.48.x | Unit + E2E |
| **Package Mgmt (Python)** | uv | 0.4.x | Fast, lockfiles, reproducible |
| **Package Mgmt (Node)** | pnpm | 9.12.x | Fast, disk-efficient, workspaces |
| **Package Mgmt (Rust)** | Cargo | 1.82.x | Standard, lockfiles |

---

## 6. Data Architecture

### 6.1 Data Layers (Strict Separation)

| Layer | Storage | Purpose | Retention |
|-------|---------|---------|-----------|
| **RAW** | Parquet (partitioned) | Provider-original data, immutable | Forever (append-only) |
| **NORMALIZED** | DuckDB | Schema-aligned, validated, deduplicated | Forever |
| **ADJUSTED** | DuckDB | Corporate actions, splits, dividends applied | Forever |
| **DERIVED** | DuckDB | Computed: ratios, factors, risk metrics | Recomputable |
| **ANALYTICAL OUTPUTS** | DuckDB + Parquet | Model results, backtests, reports | Versioned |

### 6.2 Data Flow

```
Provider Adapter → Raw Parquet (date/symbol) → Validation → Normalized DuckDB
                                                              ↓
Adjustment Engine (corporate actions) → Adjusted DuckDB
                                                              ↓
Derivation Pipeline (ratios, factors, risk) → Derived DuckDB
                                                              ↓
Analytical Consumers (Portfolio, Risk, Quant, AI)
```

### 6.3 Ingestion Guarantees
- **Idempotent:** Same provider+dataset+params → same output (deterministic)
- **Incremental:** Only new/changed data processed (watermark tracking)
- **Atomic:** Per-partition transactions (DuckDB ACID)
- **Observable:** Job status, metrics, lineage via internal API

---

## 7. Security Architecture

### 7.1 Desktop (Tauri) Capabilities — MINIMAL SET
```json
{
  "capabilities": [
    "core:app:allow-exit",
    "core:window:allow-create",
    "core:window:allow-show",
    "core:window:allow-hide",
    "core:menu:allow-create",
    "fs:allow-read-file",      // User-selected only
    "fs:allow-write-file",     // User-selected only
    "fs:allow-read-dir",       // User-selected only
    "dialog:allow-open",       // User-initiated only
    "dialog:allow-save",       // User-initiated only
    "shell:allow-open",        // External URLs only (https://)
    "http:allow-request"       // To localhost API only
  ]
}
```

### 7.2 API Security
- **Authentication:** JWT (HS256 local, RS256 server), short expiry (15min), refresh tokens
- **Authorization:** RBAC middleware on all internal routes
- **Rate Limiting:** Token bucket (100 req/min default, configurable per endpoint)
- **Input Validation:** Pydantic strict mode on all request bodies
- **Output Sanitization:** No raw SQL, no template injection

### 7.3 AI Security
- **Tool Allowlist:** Only pre-approved, schema-validated functions
- **Prompt Injection Defense:** System/user separation, input sanitization
- **Sandboxed Execution:** Subprocess with seccomp, memory/CPU limits
- **Read-Only Default:** All tools `read_only=true` unless explicit `write: true`
- **Human-in-the-Loop:** Sensitivity HIGH → explicit confirmation UI
- **Full Audit:** Every tool call → `governance.audit_events` with hash chain

---

## 8. Observability

### 8.1 Structured Logging
```json
{
  "timestamp": "2026-11-02T10:30:00.123Z",
  "level": "INFO",
  "service": "portfolio-risk",
  "trace_id": "abc123",
  "span_id": "def456",
  "message": "VaR calculation completed",
  "context": {
    "portfolio_id": "pf_001",
    "method": "historical",
    "confidence": 0.99,
    "horizon_days": 1,
    "duration_ms": 234
  }
}
```

### 8.2 Metrics (Prometheus)
- `erin_api_request_duration_seconds` (histogram)
- `erin_ingestion_job_duration_seconds` (histogram)
- `erin_var_calculation_duration_seconds` (histogram)
- `erin_memory_usage_bytes` (gauge)
- `erin_active_connections` (gauge)
- `erin_data_quality_score` (gauge, per dataset)

### 8.3 Tracing (OpenTelemetry)
- All internal API calls traced
- Database queries traced
- External provider calls traced
- Background jobs traced

---

## 9. Deployment Architecture

### 9.1 Stage 1: Local Workstation (Current)
```
┌─────────────────────────────────────┐
│         TAURI DESKTOP APP           │
│  ┌─────────┐  ┌─────────────────┐  │
│  │ React   │  │  FastAPI (uvicorn)  │
│  │ (WebView)│  │  2 workers        │
│  └─────────┘  └─────────────────┘  │
│         │             │            │
│         ▼             ▼            │
│  ┌─────────────────────────────┐  │
│  │     SQLite + DuckDB         │  │
│  │     (local files)           │  │
│  └─────────────────────────────┘  │
│         │                         │
│         ▼                         │
│  ┌─────────────────────────────┐  │
│  │     Parquet (local dir)     │  │
│  └─────────────────────────────┘  │
└─────────────────────────────────────┘
```

### 9.2 Stage 2: Centralized Server (Future)
```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Load Bal   │   │  API Pods   │   │  Worker Pods│
│  (nginx)    │───│  (FastAPI)  │───│  (BullMQ)   │
└─────────────┘   └──────┬──────┘   └──────┬──────┘
                         │                 │
              ┌──────────┴──────────┐     │
              ▼                     ▼     ▼
        ┌─────────┐           ┌─────────┐ ┌─────────┐
        │PostgreSQL│          │  DuckDB  │ │  Redis  │
        │(Primary) │          │(Analytical)│ │(Queue)  │
        └─────────┘           └─────────┘ └─────────┘
              │                     │
              ▼                     ▼
        ┌─────────────────────────────────────┐
        │         Object Storage (S3)         │
        │         Parquet Archives            │
        └─────────────────────────────────────┘
```

### 9.3 Stage 3: Enterprise (Future)
- Independently deployable domain services where justified
- Distributed workers (Kubernetes + KEDA)
- High availability (multi-AZ)
- Centralized observability (Grafana + Loki + Tempo)
- Multi-user governance (Keycloak OIDC)
- Multi-region when necessary

---

## 10. Migration Path Documentation

| Component | Local → Server | Server → Enterprise |
|-----------|----------------|---------------------|
| **Database** | SQLite → PostgreSQL (schema compatible) | Read replicas, partitioning |
| **Analytical** | DuckDB (embedded) → DuckDB (server) / ClickHouse | Distributed ClickHouse |
| **Queue** | SQLite-backed → Redis + BullMQ | Redis Cluster |
| **Storage** | Local Parquet → S3/MinIO | Tiered storage (hot/warm/cold) |
| **Auth** | Local JWT → OIDC (Keycloak) | Federation, SSO |
| **API** | Internal HTTP → Internal HTTP (same contracts) | gRPC for high-throughput paths |
| **Workers** | ThreadPool → BullMQ workers | Kubernetes Jobs + KEDA |

---

## 11. ADR Log (Architecture Decision Records)

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| ADR-001 | Modular Monolith over Microservices | ACCEPTED | 2026-11-02 |
| ADR-002 | Tauri 2 for Desktop Shell | ACCEPTED | 2026-11-02 |
| ADR-003 | DuckDB for Analytical Workloads | ACCEPTED | 2026-11-02 |
| ADR-004 | Parquet for Historical Storage | ACCEPTED | 2026-11-02 |
| ADR-005 | Internal HTTP APIs for Cross-Context Communication | ACCEPTED | 2026-11-02 |
| ADR-006 | LanceDB for Embedded Vector Search | ACCEPTED | 2026-11-02 |
| ADR-007 | Python 3.12 LTS for Production | ACCEPTED | 2026-11-02 |
| ADR-008 | Radix UI + Tailwind for Design System | ACCEPTED | 2026-11-02 |

---

## 12. Approval

**Principal Architect:** _________________ **Date:** __________

**Chief Orchestrator:** _________________ **Date:** __________

**Security Engineer:** _________________ **Date:** __________