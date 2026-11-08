# ERIN 2.0 — TASK REGISTRY

**Version:** 1.0
**Status:** ACTIVE
**Classification:** INTERNAL — TASK TRACKING
**Owner:** Chief Orchestrator

---

## Task Status Definitions

| Status | Definition |
|--------|------------|
| `NOT_STARTED` | No work begun; dependencies not met |
| `IN_PROGRESS` | Active work; agent assigned |
| `IMPLEMENTED` | Code complete; tests not run |
| `TESTED` | All tests passing (unit, integration, contract, property) |
| `REVIEWED` | Architecture/Security/Financial review passed |
| `VERIFIED` | **All acceptance criteria demonstrated**; evidence in registry |
| `BLOCKED` | Explicit blocker; cannot proceed |

---

## Phase 1 Tasks

### Phase 3: Development Infrastructure (Weeks 3-4)

| Task ID | Title | Agent | Status | Dependencies | Files | Acceptance Criteria | Evidence |
|---------|-------|-------|--------|--------------|-------|---------------------|----------|
| TASK-001 | Initialize Git Monorepo | Chief Orchestrator | NOT_STARTED | — | `.git/`, `README.md` | Conventional commits, signed tags | Git log |
| TASK-002 | Create Python Workspace (uv) | Backend Engineer | NOT_STARTED | TASK-001 | `pyproject.toml`, `uv.lock` | `uv sync && uv build --all` passes | Build log |
| TASK-003 | Create Rust Workspace (Cargo) | Frontend Engineer | NOT_STARTED | TASK-001 | `Cargo.toml`, `Cargo.lock` | `cargo build --workspace` passes | Build log |
| TASK-004 | Create Node Workspace (pnpm) | Frontend Engineer | NOT_STARTED | TASK-001 | `package.json`, `pnpm-lock.yaml` | `pnpm install` passes | Install log |
| TASK-005 | GitHub Actions CI Pipeline | SRE | NOT_STARTED | TASK-002,003,004 | `.github/workflows/ci.yml` | Lint, typecheck, test, security, SBOM all pass | CI run |
| TASK-006 | ECP Scripts Implementation (12) | Chief Orchestrator | NOT_STARTED | TASK-001 | `scripts/ecp/*.py` | All `python -m scripts.ecp.* --help` work | Script output |
| TASK-007 | Pre-commit Hooks Configuration | SRE | NOT_STARTED | TASK-005 | `.pre-commit-config.yaml` | `pre-commit run --all-files` passes | Hook output |
| TASK-008 | Docker Multi-stage Build | SRE | NOT_STARTED | TASK-002,003 | `Dockerfile`, `.dockerignore` | `docker build -t erin:test .` < 500MB | Image size |
| TASK-009 | SBOM Generation (Syft) | Security Engineer | NOT_STARTED | TASK-005 | `.github/workflows/sbom.yml` | CycloneDX JSON on every build | SBOM artifact |
| TASK-010 | Dependency Pinning ADR | Chief Orchestrator | NOT_STARTED | TASK-002,003,004 | `DECISIONS.md` (ADR) | Exact versions in lockfiles | ADR-016 |

### Phase 4: Terminal UI Foundation (Weeks 4-6)

| Task ID | Title | Agent | Status | Dependencies | Files | Acceptance Criteria | Evidence |
|---------|-------|-------|--------|--------------|-------|---------------------|----------|
| TASK-011 | Tauri 2 + React + TS + Vite Scaffold | Frontend Engineer | NOT_STARTED | TASK-003,004 | `apps/desktop/` | `pnpm tauri build` produces binary | Binary |
| TASK-012 | Design System (Tailwind + Radix) | Frontend Engineer | NOT_STARTED | TASK-011 | `packages/ui-core/` | Dark-first, tokens, components | Storybook |
| TASK-013 | Global Command Bar (Cmd/Ctrl+K) | Frontend Engineer | NOT_STARTED | TASK-012 | `apps/desktop/src/command-bar/` | Opens, fuzzy search, executes | Demo video |
| TASK-014 | Keyboard Shortcuts Registry | Frontend Engineer | NOT_STARTED | TASK-012 | `packages/ui-core/src/shortcuts/` | Declarative, no conflicts | Test |
| TASK-015 | Multi-panel Layout (Dock/Resize/Persist) | Frontend Engineer | NOT_STARTED | TASK-012 | `apps/desktop/src/layout/` | Grid/tabs, localStorage restore | Demo video |
| TASK-016 | Watchlist Panel | Frontend Engineer | NOT_STARTED | TASK-015 | `apps/desktop/src/watchlist/` | CRUD, 500 limit, persist | E2E test |
| TASK-017 | Chart Panel (Lightweight Charts) | Frontend Engineer | NOT_STARTED | TASK-012, TASK-015 | `apps/desktop/src/charts/` | Line/Candle, timeframes, sync | E2E test |
| TASK-018 | Settings/Config UI | Frontend Engineer | NOT_STARTED | TASK-012 | `apps/desktop/src/settings/` | Provider keys, theme, shortcuts | E2E test |

### Phase 5: Market Data Foundation (Weeks 6-8)

| Task ID | Title | Agent | Status | Dependencies | Files | Acceptance Criteria | Evidence |
|---------|-------|-------|--------|--------------|-------|---------------------|----------|
| TASK-019 | Provider Adapter Protocol | Data Engineer | NOT_STARTED | TASK-002 | `packages/data-infra/src/providers/` | `MarketDataProvider` interface | Code |
| TASK-020 | OpenBB Adapter | Data Engineer | NOT_STARTED | TASK-019 | `packages/market-intel/src/adapters/openbb/` | Quotes, fundamentals, options, news | Integration test |
| TASK-021 | yfinance Adapter | Data Engineer | NOT_STARTED | TASK-019 | `packages/market-intel/src/adapters/yfinance/` | Quotes, basic fundamentals | Integration test |
| TASK-022 | FRED Adapter | Data Engineer | NOT_STARTED | TASK-019 | `packages/macro-intel/src/adapters/fred/` | Macro indicators, yield curves | Integration test |
| TASK-023 | Instrument Master (FIGI) | Data Engineer | NOT_STARTED | TASK-019 | `packages/market-intel/src/domain/instrument.py` | 10k+ instruments, FIGI primary | DB query |
| TASK-024 | Ingestion Pipeline | Data Engineer | NOT_STARTED | TASK-019,023 | `packages/data-infra/src/ingestion/` | Scheduled, incremental, idempotent | Job logs |
| TASK-025 | DuckDB Schema (Raw/Norm/Adj/Derived) | Data Engineer | NOT_STARTED | TASK-023 | `packages/data-infra/src/schema/duckdb.sql` | Tables exist, queries work | SQL test |
| TASK-026 | Parquet Partitioning (Date/Symbol) | Data Engineer | NOT_STARTED | TASK-025 | `packages/data-infra/src/parquet/` | 128MB row groups, stats enabled | File check |
| TASK-027 | Data Quality Checks | Data Engineer | NOT_STARTED | TASK-024 | `packages/data-infra/src/quality/` | Completeness, staleness, outliers | Quality report |
| TASK-028 | Data Provenance/Lineage | Data Engineer | NOT_STARTED | TASK-024 | `packages/data-infra/src/lineage/` | Provider, timestamps, version | Lineage query |
| TASK-029 | Quote WebSocket Broadcast | Backend Engineer | NOT_STARTED | TASK-020,021 | `apps/api/src/ws/quotes.py` | < 500ms latency, 1000 conn | Load test |

### Phase 6: Fundamental & Equity Research (Weeks 8-10)

| Task ID | Title | Agent | Status | Dependencies | Files | Acceptance Criteria | Evidence |
|---------|-------|-------|--------|--------------|-------|---------------------|----------|
| TASK-030 | Company Profile Domain | Backend Engineer | NOT_STARTED | TASK-023 | `packages/equity-research/src/domain/company.py` | CRUD, CIK unique, ticker mappings | Unit test |
| TASK-031 | SEC EDGAR Adapter | Data Engineer | NOT_STARTED | TASK-019 | `packages/equity-research/src/adapters/sec_edgar/` | 10-K, 10-Q, 8-K parsing | Integration test |
| TASK-032 | Financial Statement Storage | Backend Engineer | NOT_STARTED | TASK-030 | `packages/equity-research/src/domain/financials.py` | GAAP/IFRS tags, period validation | Unit test |
| TASK-033 | Ratio Engine (10 Core) | Quant Engineer | NOT_STARTED | TASK-032 | `packages/equity-research/src/ratios/` | Profitability, Liquidity, Solvency, Efficiency | Verification test |
| TASK-034 | Research Notebook (Jupyter Kernel) | Frontend Engineer | NOT_STARTED | TASK-012 | `apps/desktop/src/notebook/` | Execute Python, save/load .ipynb | E2E test |

### Phase 7: Quantitative Finance (Weeks 10-13)

| Task ID | Title | Agent | Status | Dependencies | Files | Acceptance Criteria | Evidence |
|---------|-------|-------|--------|--------------|-------|---------------------|----------|
| TASK-035 | Distribution Library | Quant Engineer | NOT_STARTED | TASK-002 | `packages/quant-finance/src/distributions/` | Normal, LogNormal, Student-t, GED | Verification test |
| TASK-036 | Monte Carlo Framework | Quant Engineer | NOT_STARTED | TASK-035 | `packages/quant-finance/src/monte_carlo/` | Antithetic, control variates, convergence | Verification test |
| TASK-037 | GBM Path Generation | Quant Engineer | NOT_STARTED | TASK-035 | `packages/quant-finance/src/gbm/` | Moment matching, log-normal property | Verification test |

### Phase 8: Portfolio & Risk (Weeks 13-16)

| Task ID | Title | Agent | Status | Dependencies | Files | Acceptance Criteria | Evidence |
|---------|-------|-------|--------|--------------|-------|---------------------|----------|
| TASK-038 | Portfolio/Position Domain | Backend Engineer | NOT_STARTED | TASK-023 | `packages/portfolio-risk/src/domain/portfolio.py` | CRUD, invariants, cash handling | Unit test |
| TASK-039 | Transaction Recording | Backend Engineer | NOT_STARTED | TASK-038 | `packages/portfolio-risk/src/domain/transaction.py` | Buy/Sell, fees, audit trail | Unit test |
| TASK-040 | Portfolio Metrics | Backend Engineer | NOT_STARTED | TASK-038 | `packages/portfolio-risk/src/application/metrics.py` | Value, P&L, weights, HHI | Unit test |
| TASK-041 | Historical VaR | Quant Engineer | NOT_STARTED | TASK-035,038 | `packages/portfolio-risk/src/var/historical.py` | Kupiec/Christoffersen backtest | Verification test |
| TASK-042 | Parametric VaR | Quant Engineer | NOT_STARTED | TASK-035,038 | `packages/portfolio-risk/src/var/parametric.py` | Matches analytical quantile | Verification test |
| TASK-043 | Expected Shortfall | Quant Engineer | NOT_STARTED | TASK-041,042 | `packages/portfolio-risk/src/var/expected_shortfall.py` | Acerbi-Szekely backtest | Verification test |

### Phase 9: Fixed Income & Derivatives (Weeks 16-20)

| Task ID | Title | Agent | Status | Dependencies | Files | Acceptance Criteria | Evidence |
|---------|-------|-------|--------|--------------|-------|---------------------|----------|
| TASK-044 | Bond Analytics | Quant Engineer | NOT_STARTED | TASK-023 | `packages/fixed-income/src/bond/analytics.py` | Price, YTM, Duration, Convexity | Verification test |
| TASK-045 | Yield Curve (NSS) | Quant Engineer | NOT_STARTED | TASK-044 | `packages/fixed-income/src/curve/nss.py` | R² > 0.999 synthetic | Verification test |
| TASK-046 | BSM European Options | Quant Engineer | NOT_STARTED | TASK-035 | `packages/derivatives/src/bsm/` | Put-call parity, Greeks, boundaries | Verification test |
| TASK-047 | Binomial (CRR) American | Quant Engineer | NOT_STARTED | TASK-046 | `packages/derivatives/src/binomial/` | Convergence, early exercise | Verification test |

### Phase 12: AI Financial Intelligence (Weeks 28-32)

| Task ID | Title | Agent | Status | Dependencies | Files | Acceptance Criteria | Evidence |
|---------|-------|-------|--------|--------------|-------|---------------------|----------|
| TASK-048 | RAG Pipeline (LanceDB) | AI Engineer | NOT_STARTED | TASK-034,031 | `packages/ai-intelligence/src/rag/` | Hybrid search, citations | Integration test |
| TASK-049 | Tool Allowlist Framework | AI Engineer | NOT_STARTED | TASK-048 | `packages/ai-intelligence/src/tools/` | Schema validation, sandbox, audit | Security test |
| TASK-050 | Report Generation | AI Engineer | NOT_STARTED | TASK-048,049 | `packages/ai-intelligence/src/reports/` | Template + Evidence → Markdown/PDF | Demo |

### Phase 16: Governance (Weeks 1-2, ongoing)

| Task ID | Title | Agent | Status | Dependencies | Files | Acceptance Criteria | Evidence |
|---------|-------|-------|--------|--------------|-------|---------------------|----------|
| TASK-051 | RBAC (Admin, Analyst, Viewer) | Backend Engineer | NOT_STARTED | TASK-002 | `packages/governance/src/rbac/` | Middleware enforces permissions | Integration test |
| TASK-052 | Audit Trail (Hash Chain) | Backend Engineer | NOT_STARTED | TASK-051 | `packages/governance/src/audit/` | Tamper detection works | Security test |
| TASK-053 | Data License Register API | Data Engineer | NOT_STARTED | TASK-020 | `packages/governance/src/licenses/` | CRUD for provider/dataset licenses | Integration test |

---

## Task Dependency Graph (Critical Path)

```
TASK-001
  └─ TASK-002,003,004 (parallel)
      └─ TASK-005 (CI)
          └─ TASK-006,007,008,009,010 (parallel)
              └─ TASK-011 (Tauri)
                  └─ TASK-012 (Design System)
                      ├─ TASK-013 (Command Bar)
                      ├─ TASK-014 (Shortcuts)
                      └─ TASK-015 (Layout)
                          ├─ TASK-016 (Watchlist)
                          └─ TASK-017 (Charts)
                  └─ TASK-018 (Settings)
  └─ TASK-019 (Provider Protocol)
      ├─ TASK-020 (OpenBB)
      ├─ TASK-021 (yfinance)
      └─ TASK-022 (FRED)
          └─ TASK-023 (Instrument Master)
              ├─ TASK-024 (Ingestion)
              │   ├─ TASK-025 (DuckDB Schema)
              │   │   └─ TASK-026 (Parquet)
              │   ├─ TASK-027 (Quality)
              │   └─ TASK-028 (Lineage)
              └─ TASK-029 (WebSocket)
                  └─ TASK-016,017 (UI consumes)
```

---

## Summary Statistics

| Status | Count |
|--------|-------|
| NOT_STARTED | 53 |
| IN_PROGRESS | 0 |
| IMPLEMENTED | 0 |
| TESTED | 0 |
| REVIEWED | 0 |
| VERIFIED | 0 |
| BLOCKED | 0 |
| **TOTAL** | **53** |

---

## Update Protocol

- Updated by **Chief Orchestrator** on every status change
- `VERIFIED` requires: All acceptance criteria demonstrated + evidence recorded
- Evidence linked in `EVIDENCE_REGISTRY.json` with hash
- Blockers documented with owner and resolution plan
- Status changes reflected in `FEATURE_REGISTRY.md` and `CHANGELOG.md`

---

## Current Blockers

| Task | Blocker | Owner | Since |
|------|---------|-------|-------|
| — | — | — | — |

---

*Last Updated: 2026-11-02 — Phase 1 Design Complete*