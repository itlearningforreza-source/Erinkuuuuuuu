# ERIN 2.0 — ARCHITECTURE DECISION RECORDS (ADR)

**Version:** 1.0
**Status:** ACTIVE
**Classification:** INTERNAL — ARCHITECTURE GOVERNANCE
**Owner:** Principal Architect

---

## ADR Format

Each ADR follows this template:
```
# ADR-XXX: {Title}

**Status:** {PROPOSED | ACCEPTED | SUPERSEDED | DEPRECATED}
**Date:** {YYYY-MM-DD}
**Deciders:** {Role names}
**Technical Story:** {Link to task/issue}

## Context
{What is the issue? What forces are at play?}

## Decision
{What was decided?}

## Consequences
{Positive, negative, risks, trade-offs}

## Alternatives Considered
{What else was evaluated? Why rejected?}

## Links
{Related ADRs, docs, issues}
```

---

## ADR Log

| ADR | Title | Status | Date | Deciders |
|-----|-------|--------|------|----------|
| ADR-001 | Modular Monolith over Microservices | ACCEPTED | 2026-11-02 | Principal Architect, Chief Orchestrator |
| ADR-002 | Tauri 2 for Desktop Shell | ACCEPTED | 2026-11-02 | Principal Architect, Frontend Engineer |
| ADR-003 | DuckDB for Analytical Workloads | ACCEPTED | 2026-11-02 | Principal Architect, Data Engineer |
| ADR-004 | Parquet for Historical Storage | ACCEPTED | 2026-11-02 | Principal Architect, Data Engineer |
| ADR-005 | Internal HTTP APIs for Cross-Context Communication | ACCEPTED | 2026-11-02 | Principal Architect, Backend Engineer |
| ADR-006 | LanceDB for Embedded Vector Search | ACCEPTED | 2026-11-02 | Principal Architect, AI Engineer |
| ADR-007 | Python 3.12 LTS for Production | ACCEPTED | 2026-11-02 | Principal Architect, Backend Engineer |
| ADR-008 | Radix UI + Tailwind for Design System | ACCEPTED | 2026-11-02 | Principal Architect, Frontend Engineer |
| ADR-009 | Lightweight Charts for Financial Charting | ACCEPTED | 2026-11-02 | Principal Architect, Frontend Engineer |
| ADR-010 | Pydantic v2 + FastAPI for API Layer | ACCEPTED | 2026-11-02 | Principal Architect, Backend Engineer |
| ADR-011 | SQLite for Transactional Local Persistence | ACCEPTED | 2026-11-02 | Principal Architect, Data Engineer |
| ADR-012 | BullMQ + Redis for Background Jobs | ACCEPTED | 2026-11-02 | Principal Architect, Backend Engineer |
| ADR-013 | OpenTelemetry for Observability | ACCEPTED | 2026-11-02 | Principal Architect, SRE |
| ADR-014 | Hypothesis for Property-Based Testing | ACCEPTED | 2026-11-02 | Principal Architect, QA Lead |
| ADR-015 | uv for Python Package Management | ACCEPTED | 2026-11-02 | Principal Architect, Backend Engineer |

---

## ADR-001: Modular Monolith over Microservices

**Status:** ACCEPTED
**Date:** 2026-11-02
**Deciders:** Principal Architect, Chief Orchestrator

### Context
ERIN must start on an 8 GB RAM workstation and scale to enterprise deployment. Microservices introduce operational complexity (service discovery, distributed tracing, network latency, data consistency) that is unjustified for a single-team, single-workstation start.

### Decision
Start with a **modular monolith** with explicit bounded contexts, dependency inversion, and stable internal contracts. Each context is a separate Python/Rust package with its own domain model. Communication between contexts is via internal HTTP APIs (FastAPI) or domain events — never direct imports.

Migration path to distributed services is documented from inception (see `ARCHITECTURE.md` Section 9).

### Consequences
**Positive:**
- Simple deployment (single binary + DB files)
- Low latency (in-process or localhost HTTP)
- Strong consistency within transaction boundary
- Easy refactoring of context boundaries
- Clear migration path when needed

**Negative:**
- Single process failure affects all domains
- Scaling requires whole-app scaling (initially)
- Team scaling limited (but team is small)

**Risks:**
- Accidental coupling across contexts → Mitigated by ECP `arch_check.py`
- Database contention → Mitigated by separate SQLite/DuckDB per context

### Alternatives Considered
- **Microservices from Day 1:** Rejected — operational overhead not justified for 8 GB workstation
- **Serverless Functions:** Rejected — cold starts, vendor lock-in, debugging difficulty
- **Modular Monolith with Shared Database:** Rejected — violates bounded context isolation

### Links
- `ARCHITECTURE.md` Sections 1, 9
- `FEATURE_DEPENDENCY_GRAPH.md`

---

## ADR-002: Tauri 2 for Desktop Shell

**Status:** ACCEPTED
**Date:** 2026-11-02
**Deciders:** Principal Architect, Frontend Engineer

### Context
ERIN requires a native desktop application with secure IPC, small bundle size, and access to native OS capabilities (file dialogs, keychain, system tray). Electron is mature but heavy (~100MB+ bundle, high memory, large attack surface). Wails is lighter but less mature ecosystem.

### Decision
Use **Tauri 2** (Rust + WebView2 on Windows, WebKitGTK on Linux, WebView on macOS) for the desktop shell. React + TypeScript runs in the WebView. Rust handles native integration, secure IPC, and performance-critical code.

### Consequences
**Positive:**
- Small bundle (~10-15MB)
- Secure by default (capability allowlist)
- Native performance for hot paths (Rust)
- WebView2/WebKitGTK are system components (no bundled Chromium)
- Strong Rust ecosystem for financial compute if needed

**Negative:**
- WebView2 bootstrapper required on Windows (can bundle)
- Linux requires WebKitGTK (system dependency)
- Smaller community than Electron
- Tauri 2 is relatively new (but stable)

**Risks:**
- WebView version differences across OS → Mitigated by testing matrix
- IPC complexity → Mitigated by strict allowlist and schema validation

### Alternatives Considered
- **Electron:** Rejected — bundle size, memory, security surface
- **Wails:** Rejected — less mature, smaller ecosystem
- **Native (Qt/GTK):** Rejected — no web UI, higher dev cost
- **PWA + Desktop Shortcut:** Rejected — no secure IPC, limited native access

### Links
- `ARCHITECTURE.md` Section 5
- `RESOURCE_POLICY.md` Section 2.2

---

## ADR-003: DuckDB for Analytical Workloads

**Status:** ACCEPTED
**Date:** 2026-11-02
**Deciders:** Principal Architect, Data Engineer

### Context
ERIN needs fast analytical queries (aggregations, window functions, joins) on historical market data. SQLite is excellent for OLTP but not optimized for columnar scans. ClickHouse/Apache Druid require separate servers. Pandas/Polars in-memory doesn't scale to multi-year datasets on 8 GB RAM.

### Decision
Use **DuckDB** as embedded analytical database. It provides:
- Columnar storage with vectorized execution
- Direct Parquet reading (zero-copy with PyArrow)
- Full SQL dialect (including window functions, lateral joins)
- Embedded (no server, runs in-process)
- `memory_limit` config for RAM budgeting

### Consequences
**Positive:**
- Zero infrastructure
- Excellent performance on analytical queries
- Seamless Parquet integration
- Python/Rust/Node bindings
- ACID transactions

**Negative:**
- Not designed for high-concurrency OLTP
- Single-writer limitation (mitigated: ingestion is batch, reads are many)
- Memory pressure on large scans → Mitigated by `memory_limit` and partitioning

### Alternatives Considered
- **ClickHouse:** Rejected — requires server, overkill for local
- **Apache Druid:** Rejected — cluster required
- **Polars DataFrames only:** Rejected — no persistence, no SQL
- **SQLite only:** Rejected — row-oriented, slow on wide scans

### Links
- `ARCHITECTURE.md` Sections 5, 6
- `DATABASE_SCHEMA.md` Section 3
- `RESOURCE_POLICY.md` Section 2.2

---

## ADR-004: Parquet for Historical Storage

**Status:** ACCEPTED
**Date:** 2026-11-02
**Deciders:** Principal Architect, Data Engineer

### Context
Historical market data (quotes, fundamentals, macro) must be stored efficiently for long-term retention, analytical queries, and interoperability. CSV lacks types and compression. Feather lacks partitioning and ecosystem. HDF5 is complex and not queryable.

### Decision
Use **Apache Parquet** with partitioning by `date` and `symbol` for all historical data. Compression: Snappy (fast, decent ratio). Row group size: 128 MB. Statistics enabled for predicate pushdown.

### Consequences
**Positive:**
- Columnar compression (5-10x vs CSV)
- Predicate pushdown (partition + row group statistics)
- Interoperable (DuckDB, Polars, Pandas, Spark, ClickHouse)
- Append-only friendly (immutable partitions)
- Schema evolution support

**Negative:**
- Not suitable for frequent updates (mitigated: historical is append-only)
- Small files problem → Mitigated by partitioning strategy and compaction job

### Alternatives Considered
- **CSV:** Rejected — no types, no compression, slow
- **Feather:** Rejected — no partitioning, limited ecosystem
- **HDF5:** Rejected — complex, not queryable by SQL engines
- **Delta Lake / Iceberg:** Rejected — overkill for local, requires catalog

### Links
- `DATABASE_SCHEMA.md` Section 4
- `ARCHITECTURE.md` Section 6

---

## ADR-005: Internal HTTP APIs for Cross-Context Communication

**Status:** ACCEPTED
**Date:** 2026-11-02
**Deciders:** Principal Architect, Backend Engineer

### Context
Bounded contexts must not import each other's domain code directly. Options for communication: direct function calls (violates boundaries), message queue (complex for local), internal HTTP (simple, testable, matches server migration), gRPC (overkill for local).

### Decision
Use **internal HTTP APIs** (FastAPI) for all cross-context communication. Routes under `/api/v1/internal/`. Contracts defined by Pydantic models in `packages/shared-types`. Local: direct function call via test client. Server: actual HTTP with mTLS.

### Consequences
**Positive:**
- Clear contracts (OpenAPI/Pydantic)
- Testable in isolation (mock HTTP)
- Matches server architecture (zero migration)
- Language agnostic (Rust/Python/TS can call)
- Observable (standard HTTP logging/tracing)

**Negative:**
- Serialization overhead (mitigated: localhost, MessagePack optional)
- Network stack latency (mitigated: < 1ms localhost)

### Alternatives Considered
- **Direct Imports:** Rejected — violates bounded contexts
- **Message Queue (NATS/RabbitMQ):** Rejected — infrastructure overhead
- **gRPC:** Rejected — complexity, HTTP/2 not needed locally
- **Shared Memory:** Rejected — unsafe, not portable

### Links
- `ARCHITECTURE.md` Section 3
- `API_CONTRACTS.md` Section 3

---

## ADR-006: LanceDB for Embedded Vector Search

**Status:** ACCEPTED
**Date:** 2026-11-02
**Deciders:** Principal Architect, AI Engineer

### Context
AI Research Assistant needs vector search for RAG (Retrieval-Augmented Generation). Options: Chroma (requires server), Pinecone (cloud, cost), pgvector (PostgreSQL only), FAISS (no persistence, no metadata), LanceDB (embedded, Arrow-native, metadata filtering).

### Decision
Use **LanceDB** as embedded vector database. It provides:
- Zero-copy Arrow integration
- Disk-backed IVF_PQ index with int8 quantization
- Metadata filtering (SQL-like)
- Embedded (no server)
- Python/Rust/Node bindings

### Consequences
**Positive:**
- No separate infrastructure
- Arrow-native (zero-copy with DuckDB/Polars)
- Efficient quantization for 8 GB RAM
- Metadata filtering without separate index

**Negative:**
- Newer project (but backed by Lance team)
- Less community than Chroma
- Index build time on large datasets

### Alternatives Considered
- **Chroma:** Rejected — requires server for persistence
- **Pinecone:** Rejected — cloud cost, data leaves machine
- **pgvector:** Rejected — PostgreSQL not in local stack
- **FAISS:** Rejected — no metadata, no persistence

### Links
- `ARCHITECTURE.md` Section 5
- `FINANCIAL_METHODOLOGY.md` (AI models)

---

## ADR-007: Python 3.12 LTS for Production

**Status:** ACCEPTED
**Date:** 2026-11-02
**Deciders:** Principal Architect, Backend Engineer

### Context
Python 3.14 is pre-release (current in OpenBB env). Production requires stability, long-term support, and ecosystem compatibility. 3.12 LTS is supported until 2028-10.

### Decision
**Pin Python 3.12** for production builds and CI. Allow 3.14 in local development for experimentation only. All dependencies must have 3.12-compatible versions.

### Consequences
**Positive:**
- Stable, supported, widely tested
- Full ecosystem compatibility
- LTS security updates until 2028
- Matches enterprise requirements

**Negative:**
- Misses 3.13/3.14 performance improvements
- Some cutting-edge libraries may require newer Python

### Alternatives Considered
- **Python 3.14:** Rejected — pre-release, unstable
- **Python 3.13:** Rejected — not LTS, shorter support
- **Multiple Python Versions:** Rejected — complexity, not needed

### Links
- `RESOURCE_POLICY.md` (Python version)
- `IMPLEMENTATION_ROADMAP.md` (Phase 3)

---

## ADR-008: Radix UI + Tailwind for Design System

**Status:** ACCEPTED
**Date:** 2026-11-02
**Deciders:** Principal Architect, Frontend Engineer

### Context
ERIN needs an institutional terminal UI: dark-first, compact, accessible, keyboard-first. Options: MUI (heavy, opinionated), shadcn/ui (Radix-based, copy-paste), Headless UI (minimal), custom (high effort).

### Decision
Use **Radix UI primitives** (accessible, unstyled, composable) + **Tailwind CSS** (utility-first, design tokens, dark mode). Build custom components on Radix primitives styled with Tailwind. This gives full control over institutional aesthetic without opinionated overrides.

### Consequences
**Positive:**
- Accessible by default (Radix)
- Full design control (Tailwind tokens)
- Small bundle (tree-shaken)
- Dark-first native support
- Keyboard navigation built-in

**Negative:**
- More initial setup than MUI
- No pre-built complex components (data grids, etc.)
- Tailwind learning curve

### Alternatives Considered
- **MUI:** Rejected — heavy, hard to customize for terminal aesthetic
- **shadcn/ui:** Acceptable alternative (Radix-based) but copy-paste model
- **Headless UI:** Rejected — fewer primitives
- **Custom from Scratch:** Rejected — accessibility burden

### Links
- `ARCHITECTURE.md` Section 5
- `API_CONTRACTS.md` (UI requirements)

---

## ADR-009: Lightweight Charts for Financial Charting

**Status:** ACCEPTED
**Date:** 2026-11-02
**Deciders:** Principal Architect, Frontend Engineer

### Context
Financial terminal requires high-performance charts: 60fps, candlestick/line, crosshair sync, overlays, studies. Options: TradingView Lightweight Charts (45KB, financial native), ECharts (heavy, general), uPlot (fast, minimal), Chart.js (not financial), Highcharts (commercial).

### Decision
Use **TradingView Lightweight Charts**. It is purpose-built for financial charts: time-scale, price-scale, series types (candle, line, area, histogram), overlays, crosshair sync, 60fps Canvas rendering, 45KB gzipped.

### Consequences
**Positive:**
- Financial chart types native
- High performance (Canvas, requestAnimationFrame)
- Small bundle
- Active maintenance (TradingView)
- TypeScript native

**Negative:**
- Less general than ECharts
- Custom studies require more code
- No 3D/WebGL

### Alternatives Considered
- **ECharts:** Rejected — heavy (200KB+), general-purpose
- **uPlot:** Rejected — excellent but less financial primitives
- **Chart.js:** Rejected — not financial, Canvas but slower
- **Highcharts:** Rejected — commercial license

### Links
- `ARCHITECTURE.md` Section 5
- `PHASE1_ACCEPTANCE_CRITERIA.md` (Chart Panel)

---

## ADR-010: Pydantic v2 + FastAPI for API Layer

**Status:** ACCEPTED
**Date:** 2026-11-02
**Deciders:** Principal Architect, Backend Engineer

### Context
ERIN needs a fast, type-safe, async API framework with automatic OpenAPI generation and request validation. FastAPI + Pydantic v2 is the industry standard. Alternatives: Django (heavy, sync), Flask (manual async), Litestar (newer, smaller ecosystem), Starlette (too low-level).

### Decision
Use **FastAPI 0.115+** with **Pydantic v2** for all API layers (external + internal). Strict mode enabled. Response models frozen. Custom validation for financial types (Decimal, Date, Enum).

### Consequences
**Positive:**
- Native async (asyncio)
- Automatic OpenAPI 3.1
- Fast validation (Pydantic v2 Rust core)
- Excellent TypeScript client generation
- Dependency injection system

**Negative:**
- Learning curve for advanced patterns
- Pydantic v2 breaking changes from v1

### Alternatives Considered
- **Django REST Framework:** Rejected — sync, heavy
- **Flask + Marshmallow:** Rejected — manual async, no OpenAPI
- **Litestar:** Rejected — newer, smaller ecosystem
- **tRPC:** Rejected — TypeScript-first, not Python

### Links
- `ARCHITECTURE.md` Section 5
- `API_CONTRACTS.md` Sections 1-3

---

## ADR-011: SQLite for Transactional Local Persistence

**Status:** ACCEPTED
**Date:** 2026-11-02
**Deciders:** Principal Architect, Data Engineer

### Context
ERIN needs ACID transactional storage for user data (portfolios, watchlists, notebooks, audit) on local workstation. PostgreSQL requires server. sql.js (WASM) is slower. IndexedDB is browser-only.

### Decision
Use **SQLite 3.46+** with WAL mode, `foreign_keys=ON`, connection pooling (5). Embedded, zero-config, ACID, single file. Migrate to PostgreSQL for server deployment (schema compatible).

### Consequences
**Positive:**
- Zero infrastructure
- ACID transactions
- WAL mode for concurrent reads
- Easy backup (`.backup` command)
- PostgreSQL migration path documented

**Negative:**
- Single writer (mitigated: low write concurrency local)
- No horizontal scaling (mitigated: server uses PostgreSQL)
- Type affinity quirks (mitigated: strict schema)

### Alternatives Considered
- **PostgreSQL (local):** Rejected — server overhead, 8 GB RAM
- **sql.js (WASM):** Rejected — slower, no native types
- **IndexedDB:** Rejected — browser only
- **DuckDB:** Rejected — OLAP optimized, not OLTP

### Links
- `ARCHITECTURE.md` Section 5
- `DATABASE_SCHEMA.md` Section 2

---

## ADR-012: BullMQ + Redis for Background Jobs

**Status:** ACCEPTED
**Date:** 2026-11-02
**Deciders:** Principal Architect, Backend Engineer

### Context
ERIN needs reliable background job processing: ingestion, VaR calculation, backtesting, report generation. Requirements: priority queues, retries, scheduling, observability, rate limiting. Local: SQLite-backed queue. Server: Redis + BullMQ.

### Decision
Use **BullMQ** with **Redis** (server) / **SQLite-backed adapter** (local). Same API, same job definitions. Priority: HIGH (quotes, VaR), NORMAL (ingestion), LOW (backtest, reports). Max concurrent: 2 (local), auto (server).

### Consequences
**Positive:**
- Priority queues, delayed jobs, cron
- Retry with exponential backoff
- Rate limiting per queue
- Dashboard (Bull Board) for monitoring
- Same code local → server

**Negative:**
- Redis dependency (server)
- Local SQLite adapter less tested

### Alternatives Considered
- **Celery:** Rejected — heavy, Redis/RabbitMQ only, complex
- **Dramatiq:** Rejected — Redis only, no priority queue
- **APScheduler:** Rejected — no persistence, no retries
- **Custom:** Rejected — reinventing wheel

### Links
- `ARCHITECTURE.md` Section 5
- `RESOURCE_POLICY.md` Section 5

---

## ADR-013: OpenTelemetry for Observability

**Status:** ACCEPTED
**Date:** 2026-11-02
**Deciders:** Principal Architect, SRE

### Context
ERIN needs structured logging, metrics, and tracing for debugging and production monitoring. Vendor lock-in (Datadog, New Relic) is undesirable. OpenTelemetry is vendor-neutral, CNCF graduated.

### Decision
Use **OpenTelemetry** (Python + Rust + TypeScript SDKs) for all observability. Export to stdout (local) / OTLP (server). Metrics: Prometheus format. Logs: JSON structured. Tracing: W3C TraceContext.

### Consequences
**Positive:**
- Vendor-neutral
- Standard instrumentation
- Auto-instrumentation for FastAPI, Redis, SQLAlchemy
- Unified context propagation

**Negative:**
- Initial setup complexity
- Cardinality management needed

### Alternatives Considered
- **Datadog Agent:** Rejected — vendor lock-in, cost
- **Custom Logging:** Rejected — inconsistent, no tracing
- **Structlog only:** Rejected — no metrics/tracing

### Links
- `ARCHITECTURE.md` Section 8
- `SECURITY_THREAT_MODEL.md` (Audit)

---

## ADR-014: Hypothesis for Property-Based Testing

**Status:** ACCEPTED
**Date:** 2026-11-02
**Deciders:** Principal Architect, QA Lead

### Context
Financial models require verification beyond example-based tests. Property-based testing (QuickCheck style) generates thousands of inputs to find edge cases. Hypothesis is the Python standard.

### Decision
Use **Hypothesis** for all financial model property tests. Minimum 1000 examples per model. Shrink on failure. Integrate with pytest.

### Consequences
**Positive:**
- Finds edge cases humans miss
- Mathematical invariant verification
- Reproducible failures (seeds)
- Integrates with pytest

**Negative:**
- Slower than example tests
- Requires careful strategy design
- Flaky if not deterministic

### Alternatives Considered
- **QuickCheck (Haskell):** Rejected — wrong language
- **fast-check (TypeScript):** Acceptable for TS, but Python is primary for quant
- **Custom Generators:** Rejected — Hypothesis is mature

### Links
- `FINANCIAL_METHODOLOGY.md` Section 6
- `TEST_STRATEGY.md` Section 3

---

## ADR-015: uv for Python Package Management

**Status:** ACCEPTED
**Date:** 2026-11-02
**Deciders:** Principal Architect, Backend Engineer

### Context
Python package management needs: fast resolution, lockfiles, workspace support, reproducible builds. pip is slow. poetry is faster but has resolver issues. pip-tools is low-level. uv (Rust-based) is 10-100x faster, supports workspaces, generates `uv.lock`.

### Decision
Use **uv** for all Python package management. Workspaces for monorepo packages. Exact version pinning in `uv.lock`. `pyproject.toml` for metadata.

### Consequences
**Positive:**
- Extremely fast (Rust resolver)
- Workspace support (monorepo)
- Lockfile for reproducibility
- Compatible with pip/poetry workflows
- Active development (Astral)

**Negative:**
- Newer tool (but stable)
- Some legacy pip features not supported

### Alternatives Considered
- **Poetry:** Rejected — slower resolver, lockfile format issues
- **pip + pip-tools:** Rejected — manual workflow
- **PDM:** Rejected — smaller community

### Links
- `IMPLEMENTATION_ROADMAP.md` Phase 3
- `RESOURCE_POLICY.md`