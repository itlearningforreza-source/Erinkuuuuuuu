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

## Quick Start (Development)

### Prerequisites

- **Rust** 1.82+ (`rustup install stable`)
- **Node.js** 22+ with pnpm 9+ (`corepack enable pnpm`)
- **Python** 3.12 with uv (`pip install uv`)
- **Docker** (for CI/local services)

### Setup

```bash
# Clone and enter
git clone <repo-url> erin
cd erin

# Install all dependencies
uv sync                    # Python workspace
cargo build --workspace    # Rust workspace
pnpm install               # Node workspace

# Install pre-commit hooks
uv run pre-commit install

# Start development
pnpm dev                   # Frontend (Vite + Tauri dev)
```

### Run Tests

```bash
# Python
uv run pytest tests/ -v

# Rust
cargo test --workspace

# TypeScript
pnpm test

# E2E
pnpm test:e2e
```

---

## Project Structure

```
erin/
├── apps/
│   ├── desktop/          # Tauri 2 + React application
│   └── api/              # FastAPI backend
├── packages/
│   ├── ui-core/          # Shared UI components (Radix + Tailwind)
│   ├── shared-types/     # Pydantic models for internal APIs
│   ├── data-core/        # Database connections, migrations
│   ├── quant-core/       # Shared quant utilities
│   ├── ai-core/          # AI/ML utilities
│   ├── market-intel/     # Domain: Market Intelligence
│   ├── data-infra/       # Domain: Financial Data Infrastructure
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
│   └── ecp/              # Engineering Control Plane scripts
├── docs/
│   ├── design/
│   └── adr/
├── .github/workflows/    # CI/CD pipelines
├── pyproject.toml        # Python workspace config
├── Cargo.toml            # Rust workspace config
├── package.json          # Node workspace config
└── docker-compose.yml    # Local services (Redis, etc.)
```

---

## Documentation

| Document | Description |
|----------|-------------|
| `PROJECT_CHARTER.md` | Mission, scope, success criteria |
| `PRD.md` | Product requirements with user stories |
| `ARCHITECTURE.md` | System architecture, bounded contexts |
| `DOMAIN_MODEL.md` | Domain aggregates, entities, events |
| `DATABASE_SCHEMA.md` | SQLite/DuckDB/Parquet schemas |
| `API_CONTRACTS.md` | External + Internal API specs |
| `FINANCIAL_METHODOLOGY.md` | Model governance, verification standards |
| `SECURITY_THREAT_MODEL.md` | STRIDE analysis, mitigations |
| `MULTI_AGENT_EXECUTION.md` | Agent roles, task protocol |
| `ECP_SPECIFICATION.md` | Engineering Control Plane components |
| `RESOURCE_POLICY.md` | Memory/CPU/storage budgets |
| `TEST_STRATEGY.md` | Test matrix, verification standards |
| `DATA_LICENSE_REGISTER.md` | Provider licensing compliance |
| `FEATURE_DEPENDENCY_GRAPH.md` | Feature dependencies, critical path |
| `IMPLEMENTATION_ROADMAP.md` | 15-phase, 38-week plan |
| `PHASE1_ACCEPTANCE_CRITERIA.md` | Phase 1 gate requirements |
| `DECISIONS.md` | Architecture Decision Records |
| `CHANGELOG.md` | Release history |
| `KNOWN_LIMITATIONS.md` | Transparency about constraints |
| `FEATURE_REGISTRY.md` | Feature tracking (61 features) |
| `TASK_REGISTRY.md` | Task tracking (53 tasks) |

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

## Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 0 | Repository & Product Audit | ✅ Complete |
| 1 | Product Requirements | ✅ Complete |
| 2 | Domain & System Architecture | ✅ Complete |
| 3 | Development Infrastructure | 🔄 Next |
| 4 | Terminal UI Foundation | ⏳ Planned |
| 5 | Market Data Foundation | ⏳ Planned |
| 6 | Fundamental & Equity Research | ⏳ Planned |
| 7 | Quantitative Finance | ⏳ Planned |
| 8 | Portfolio & Risk | ⏳ Planned |
| 9 | Fixed Income & Derivatives | ⏳ Planned |
| 10 | Trading & Backtesting | ⏳ Planned |
| 11 | Macro & News Intelligence | ⏳ Planned |
| 12 | AI Research Assistant | ⏳ Planned |
| 13 | Security Hardening | ⏳ Planned |
| 14 | Performance & Scalability | ⏳ Planned |
| 15 | Production Release | ⏳ Planned |

---

## License

MIT License - see `LICENSE` file for details.

---

## Contributing

See `CONTRIBUTING.md` for development workflow, coding standards, and pull request process.

---

## Security

See `SECURITY.md` for vulnerability disclosure policy and security contact.