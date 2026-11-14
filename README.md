# ERIN 2.0

**Enterprise Research, Investment & Intelligence Network**

An independent, modular, scalable, secure, institutional-grade financial operating system.

---

## Overview

ERIN integrates financial market intelligence, investment research, quantitative finance, portfolio management, risk analytics, trading research, financial data infrastructure, macroeconomic intelligence, and controlled AI research assistance into a unified financial operating environment.

Inspired by the breadth and workflow capabilities of professional financial terminals such as Bloomberg Terminal, but built as an **independent implementation** with original interfaces and no proprietary dependencies.

---

## Architecture

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
│  │  Market Intel │ Data Infra │ Equity Research │ Quant/Risk │ Portfolio │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                 ▲                                           │
│                                 ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      INFRASTRUCTURE LAYER                              │  │
│  │  SQLite (OLTP) │ DuckDB (OLAP) │ Parquet (Historical) │ Providers    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Desktop Shell** | Tauri 2 (Rust + WebView2/WebKitGTK) |
| **Frontend** | React 18 + TypeScript + Vite |
| **UI Primitives** | Radix UI + Tailwind CSS |
| **Charts** | TradingView Lightweight Charts |
| **State** | TanStack Query + Zustand |
| **Backend** | FastAPI + Pydantic v2 |
| **Transactional DB** | SQLite (WAL mode) |
| **Analytical DB** | DuckDB |
| **Historical Storage** | Apache Parquet (partitioned) |
| **Columnar Exchange** | PyArrow |
| **Quant Compute** | NumPy/SciPy/Polars/statsmodels/CVXPY |
| **Vector Search** | LanceDB |
| **Task Queue** | BullMQ + Redis |
| **Observability** | OpenTelemetry + Prometheus |
| **Package Mgmt** | uv (Python) + Cargo (Rust) + pnpm (Node) |

---

## Current Implementation Status

| Phase | Name | Status | Notes |
|-------|------|--------|-------|
| **0** | Repository & Product Audit | ✅ **Complete** | Codebase inspected, tech stack identified |
| **1** | Product Requirements | ✅ **Complete** | PRD, Feature Registry (61 features), License Register |
| **2** | Domain & System Architecture | ✅ **Complete** | 12 design docs drafted (Architecture, Domain Model, DB Schema, API Contracts, Methodology, Security, Multi-Agent, ECP, Resource Policy, Test Strategy, Feature Graph, Roadmap) |
| **3** | Development Infrastructure | 🔄 **In Progress** | Monorepo structured, uv/Cargo/pnpm workspaces configured, GitHub Actions CI pipeline running (lint, typecheck, security, tests), ECP scripts scaffolded, Docker multi-stage build, pre-commit hooks |
| **4** | Terminal UI Foundation | 🔄 **In Progress** | Tauri 2 + React + TS + Vite scaffold builds, Command Bar (Cmd/Ctrl+K) functional, Chart Panel (Lightweight Charts) integrated, Watchlist Panel CRUD, Multi-panel layout with dock/resize/persist, Dark-first theme (Tailwind) |
| **5** | Market Data Foundation | 🔄 **In Progress** | Provider Adapter Protocol defined, **4 adapters implemented**: OpenBB, yfinance, FRED, Alpha Vantage (+ SEC EDGAR), Instrument Master domain model, Ingestion pipeline scaffolded, DuckDB/Parquet schema defined |
| **6** | Fundamental & Equity Research | 🟡 **Skeleton** | Company Profile, Financial Statements, Ratio Engine (10 formulas), SEC EDGAR adapter, Peer Group, Research Notebook (Jupyter kernel) — domain models + services exist, not fully verified |
| **7** | Quantitative Finance | 🟡 **Skeleton** | Distributions (Normal, LogNormal, Student-t, GED), Monte Carlo (antithetic/control variates), GBM paths, Factor Models (PCA/Regression), CVXPY Optimization — modules exist, verification tests pending |
| **8** | Portfolio & Risk | 🟡 **Skeleton** | Portfolio/Position/Cash domain, Transaction recording, Basic Metrics, Historical/Parametric VaR, Expected Shortfall, Stress Testing, Brinson Attribution — domain + engines scaffolded |
| **9** | Fixed Income & Derivatives | 🟡 **Skeleton** | Bond Pricing (YTM, Duration, Convexity), Nelson-Siegel-Svensson curves, BSM European (Greeks), CRR Binomial American, SVI Vol Surface — modules exist |
| **10** | Trading & Backtesting | 🟡 **Skeleton** | OMS domain, Event-driven backtest framework, TCA model, Walk-forward validation, Paper trading simulator — scaffolded |
| **11** | Macro & News Intelligence | 🟡 **Skeleton** | FRED/IMF/OECD adapters, Economic Calendar, News ingestion (RSS/NewsAPI), NER + Entity Linking, FinBERT Sentiment — adapters partially implemented |
| **12** | AI Research Assistant | 🟡 **Skeleton** | RAG Pipeline (LanceDB + Hybrid Search), Tool Allowlist Framework, Code Execution Sandbox, Report Generation — core modules exist |
| **13** | Security Hardening | ⏳ **Planned** | Threat model drafted, mitigation tracking in SECURITY_THREAT_MODEL.md |
| **14** | Performance & Scalability | ⏳ **Planned** | Resource profiling script (ECP), 8 GB RAM budget target |
| **15** | Production Release | ⏳ **Planned** | Signed builds, Cosign verification, SBOM, Release runbooks |

> **Legend:** ✅ Complete | 🔄 In Progress (functional code, tests passing) | 🟡 Skeleton (domain models/services exist, verification pending) | ⏳ Planned (design only)

---

## Project Structure

```
erin/
├── apps/
│   ├── desktop/          # Tauri 2 + React application (Phase 4 UI)
│   │   ├── src/components/     # ChartPanel, WatchlistPanel, CommandBar, Panel, Header, StatusBar
│   │   ├── src/services/       # API client, WebSocket
│   │   ├── src-tauri/          # Rust backend, Tauri plugins, SQLx/DuckDB
│   │   └── package.json / tauri.conf.json
│   └── api/              # FastAPI backend (internal API)
│       └── src/erin/api/routers/   # admin, ai, auth, instruments, market_data, portfolio, portfolios, risk, valuation, watchlists, workspace
├── packages/
│   ├── ui-core/          # Shared UI components (Radix + Tailwind)
│   ├── shared-types/     # Pydantic models for internal APIs
│   ├── data-core/        # Database connections, migrations
│   ├── quant-core/       # Shared quant utilities
│   ├── ai-core/          # AI/ML utilities
│   ├── market-intel/     # Domain: Market Intelligence (adapters, instrument_master, watchlist, valuation, fundamental, quant, portfolio, risk, fixed_income)
│   ├── data-infra/       # Domain: Financial Data Infrastructure (SQLite, DuckDB, Parquet, LanceDB storage)
│   ├── equity-research/  # Domain: Equity Research
│   ├── quant-finance/    # Domain: Quantitative Finance
│   ├── portfolio-risk/   # Domain: Portfolio & Risk
│   ├── fixed-income/     # Domain: Fixed Income
│   ├── derivatives/      # Domain: Derivatives
│   ├── macro-intel/      # Domain: Macro Intelligence
│   ├── news-intel/       # Domain: News Intelligence
│   ├── workspace/        # Domain: Financial Workspace
│   ├── ai-intelligence/  # Domain: AI Financial Intelligence
│   └── governance/       # Domain: Governance & Collaboration
├── models/               # Financial model implementations (ERIN-FM-XXX)
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contracts/
│   ├── property/
│   ├── benchmarks/
│   └── e2e/
├── scripts/
│   └── ecp/              # Engineering Control Plane scripts (contract_test, resource_profile, arch_check, release_gate, security_scan)
├── docs/
│   ├── design/
│   └── adr/
├── .github/workflows/    # CI/CD pipeline (ci.yml - lint, typecheck, security, unit, integration, contract, verification, property, e2e, resource, architecture, build/release)
├── pyproject.toml        # Python workspace config (uv, 200+ deps pinned)
├── Cargo.toml            # Rust workspace config
├── package.json          # Node workspace config
└── docker-compose.yml    # Local services (Redis)
```

---

## Quick Start (Development)

### Prerequisites

- **Rust** 1.82+ (`rustup install stable`)
- **Node.js** 22+ with pnpm 9+ (`corepack enable pnpm`)
- **Python** 3.12 with uv (`pip install uv`)
- **Docker** (for Redis, local services)

### Setup

```bash
# Clone and enter
git clone https://github.com/itlearningforreza-source/Erinkuuuuuuu.git erin
cd erin

# Install all dependencies
uv sync --all-extras                    # Python workspace (200+ deps)
cargo build --workspace                 # Rust workspace (Tauri + deps)
pnpm install                            # Node workspace

# Install pre-commit hooks
uv run pre-commit install

# Start development (frontend + Tauri dev)
cd apps/desktop && pnpm dev
```

### Run Tests

```bash
# Python (from repo root)
uv run pytest tests/unit -v -x          # Unit tests
uv run pytest tests/integration -v -x   # Integration tests (needs Redis)
uv run pytest tests/contracts -v -x     # Contract tests
uv run pytest tests/property -v -x      # Property-based tests (Hypothesis)
uv run pytest models/ -m "verification" -v  # Financial model verification
uv run pytest tests/benchmarks -v       # Performance benchmarks

# Rust
cargo test --workspace --lib            # Unit tests
cargo test --workspace                  # All tests

# TypeScript (from apps/desktop)
pnpm vitest run                         # Unit tests
pnpm typecheck                          # TypeScript typecheck
pnpm biome check .                      # Lint

# E2E
pnpm playwright install --with-deps chromium
pnpm playwright test                    # Playwright E2E

# Security
uv run bandit -r .                      # Python SAST
cargo audit                             # Rust SAST
pnpm audit                              # Node SAST
uv run pip-audit                        # Python dep vulnerabilities
```

---

## Documentation

| Document | Description | Status |
|----------|-------------|--------|
| `PROJECT_CHARTER.md` | Mission, scope, success criteria | ✅ Draft |
| `PRD.md` | Product requirements with user stories | ✅ Draft |
| `ARCHITECTURE.md` | System architecture, bounded contexts | ✅ Draft |
| `DOMAIN_MODEL.md` | Domain aggregates, entities, events | ✅ Draft |
| `DATABASE_SCHEMA.md` | SQLite/DuckDB/Parquet schemas | ✅ Draft |
| `API_CONTRACTS.md` | External + Internal API specs | ✅ Draft |
| `FINANCIAL_METHODOLOGY.md` | Model governance, verification standards | ✅ Draft |
| `SECURITY_THREAT_MODEL.md` | STRIDE analysis, mitigations | ✅ Draft |
| `MULTI_AGENT_EXECUTION.md` | Agent roles, task protocol | ✅ Draft |
| `ECP_SPECIFICATION.md` | Engineering Control Plane components | ✅ Draft |
| `RESOURCE_POLICY.md` | Memory/CPU/storage budgets (8 GB RAM binding) | ✅ Draft |
| `TEST_STRATEGY.md` | Test matrix, verification standards | ✅ Draft |
| `DATA_LICENSE_REGISTER.md` | Provider licensing compliance | ✅ Draft |
| `FEATURE_DEPENDENCY_GRAPH.md` | Feature dependencies, critical path | ✅ Draft |
| `IMPLEMENTATION_ROADMAP.md` | 15-phase, 38-week plan | ✅ Draft |
| `PHASE1_ACCEPTANCE_CRITERIA.md` | Phase 1 gate requirements | ✅ Draft |
| `DECISIONS.md` | Architecture Decision Records | 🔄 Building |
| `CHANGELOG.md` | Release history | 🔄 Building |
| `KNOWN_LIMITATIONS.md` | Transparency about constraints | 🟡 Started |
| `FEATURE_REGISTRY.md` | Feature tracking (61 features) | ✅ Draft |
| `TASK_REGISTRY.md` | Task tracking (53 tasks) | ✅ Draft |

---

## Development Principles

1. **Specification Before Implementation** — Never code without requirements
2. **Evidence Before Completion** — Tests must pass, not just compile
3. **Financial Correctness Before Output** — Mathematical verification required
4. **Security Before Convenience** — No bypassing controls
5. **Resource Efficiency Before Infrastructure** — 8 GB RAM binding constraint
6. **Modularity Without Fragmentation** — Strong boundaries, no premature microservices
7. **Backward Compatibility** — Contracts preserved unless explicit migration
8. **Reproducibility** — Versions pinned, seeds fixed, builds bit-for-bit identical
9. **Transparency** — Limitations documented, not hidden
10. **Original Implementation** — No unnecessary framework dependencies

---

## CI/CD Pipeline

GitHub Actions (`.github/workflows/ci.yml`) runs on every push/PR:

1. **Lint & Typecheck** — Ruff, MyPy, Biome, TypeScript, cargo fmt/clippy, ESLint, Prettier
2. **Security Scan** — Bandit, pip-audit, cargo audit, npm audit, Semgrep, TruffleHog, GitLeaks, Trivy (container), SBOM (Syft)
3. **Unit Tests** — Python, Rust, TypeScript (parallel)
4. **Integration Tests** — With Redis service
5. **Contract Tests** — ECP contract_test script
6. **Financial Verification** — Model verification tests (ERIN-FM-XXX)
7. **Property Tests** — Hypothesis-based (1000+ examples/model)
8. **E2E Tests** — Playwright + Tauri build
9. **Resource Profile** — CI memory/CPU profiling (≤ 6 GB target)
10. **Architecture Check** — ECP arch_check script
11. **Build & Release** — On version tags: multi-platform Tauri build, Cosign signing, SBOM, GitHub Release

---

## License

MIT License - see `LICENSE` file for details.

---

## Contributing

See `CONTRIBUTING.md` for development workflow, coding standards, and pull request process.

---

## Security

See `SECURITY.md` for vulnerability disclosure policy and security contact.

---

## Repository

**GitHub:** https://github.com/itlearningforreza-source/Erinkuuuuuuu

**Clone:** `git clone https://github.com/itlearningforreza-source/Erinkuuuuuuu.git`