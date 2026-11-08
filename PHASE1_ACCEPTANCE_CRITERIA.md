# ERIN 2.0 — PHASE 1 ACCEPTANCE CRITERIA

**Version:** 1.0
**Status:** DRAFT
**Classification:** INTERNAL — RELEASE GOVERNANCE
**Owner:** QA Lead
**Phase:** 1 — Product Requirements

---

## 1. Phase 1 Scope Recap

Phase 1 delivers the **minimum viable foundation** for ERIN:
- Repository & Development Infrastructure (Phase 3)
- Terminal UI Foundation (Phase 4)
- Market Data Foundation (Phase 5)
- Core Domain Skeletons (Phases 6-9, 12, 16, 17, 18)

**Out of Scope:** Advanced features, full model implementations, production hardening, server deployment.

---

## 2. Acceptance Criteria by Category

### 2.1 Documentation (All Must Exist and Be Reviewed)

| Document | Review Status | Approver |
|----------|---------------|----------|
| `PROJECT_CHARTER.md` | ☐ Reviewed | Chief Orchestrator |
| `PRD.md` | ☐ Reviewed | Product Spec Agent |
| `ARCHITECTURE.md` | ☐ Reviewed | Principal Architect |
| `DOMAIN_MODEL.md` | ☐ Reviewed | Data Architect |
| `DATABASE_SCHEMA.md` | ☐ Reviewed | Data Engineer |
| `API_CONTRACTS.md` | ☐ Reviewed | Backend + Frontend Engineers |
| `FINANCIAL_METHODOLOGY.md` | ☐ Reviewed | Quant Finance Engineer |
| `SECURITY_THREAT_MODEL.md` | ☐ Reviewed | Security Engineer |
| `MULTI_AGENT_EXECUTION.md` | ☐ Reviewed | Chief Orchestrator |
| `ECP_SPECIFICATION.md` | ☐ Reviewed | Chief Orchestrator |
| `RESOURCE_POLICY.md` | ☐ Reviewed | SRE |
| `TEST_STRATEGY.md` | ☐ Reviewed | QA Lead |
| `DATA_LICENSE_REGISTER.md` | ☐ Reviewed | Data Engineer + Legal |
| `FEATURE_DEPENDENCY_GRAPH.md` | ☐ Reviewed | Principal Architect |
| `IMPLEMENTATION_ROADMAP.md` | ☐ Reviewed | Chief Orchestrator |
| `PHASE1_ACCEPTANCE_CRITERIA.md` | ☐ Reviewed | QA Lead |
| `DECISIONS.md` (ADR log) | ☐ ≥ 8 ADRs | Principal Architect |

---

### 2.2 Development Infrastructure (Phase 3)

| Criterion | Verification Method | Pass/Fail |
|-----------|---------------------|-----------|
| Git repository initialized with conventional commits | `git log --oneline` shows conventional format | ☐ |
| Monorepo structure exists (apps/, packages/, scripts/) | `ls -la` matches spec | ☐ |
| `pyproject.toml` with uv workspaces builds all packages | `uv sync && uv build --all` succeeds | ☐ |
| `Cargo.toml` workspace builds | `cargo build --workspace` succeeds | ☐ |
| `package.json` pnpm workspaces installs | `pnpm install` succeeds | ☐ |
| GitHub Actions CI pipeline runs | Green on `main` branch | ☐ |
| CI runs: lint (ruff, biome, cargo-fmt), typecheck (mypy, tsc), test | All pass | ☐ |
| CI runs: security scan (bandit, cargo-audit, npm audit, trivy) | 0 CRITICAL/HIGH | ☐ |
| CI runs: SBOM generation (syft) | CycloneDX JSON produced | ☐ |
| CI runs: resource profile (standard) | ≤ 6 GB peak RSS | ☐ |
| ECP Scripts (12) all functional | `python -m scripts.ecp.* --help` works | ☐ |
| Pre-commit hooks configured and running | `pre-commit run --all-files` passes | ☐ |
| Docker multi-stage build produces image | `docker build -t erin:test .` succeeds, < 500MB | ☐ |
| Dependency pinning documented in `DECISIONS.md` | ADR present | ☐ |

---

### 2.3 Terminal UI Foundation (Phase 4)

| Criterion | Verification Method | Pass/Fail |
|-----------|---------------------|-----------|
| Tauri 2 + React + TypeScript + Vite scaffold builds | `pnpm tauri build` produces binary | ☐ |
| Application launches in < 3 seconds (cold start) | Manual stopwatch / CI benchmark | ☐ |
| Dark-first theme implemented (Tailwind) | Visual inspection, WCAG AA contrast | ☐ |
| Radix UI primitives integrated | Component library docs | ☐ |
| Global Command Bar (Cmd/Ctrl+K) functional | Opens, fuzzy searches, executes commands | ☐ |
| Command history persists across sessions | Restart app, history present | ☐ |
| Keyboard shortcuts registry works | Declarative shortcuts, no conflicts | ☐ |
| Multi-panel layout: dock, resize, persist | Drag-drop, localStorage restore | ☐ |
| Watchlist Panel: CRUD operations | Add/remove/reorder, max 500, persist | ☐ |
| Chart Panel: Lightweight Charts integrated | Line/Candle, timeframes (1D,1W,1M,3M,1Y,5Y) | ☐ |
| Chart synchronization: crosshair/tooltip sync | Multiple charts, shared crosshair | ☐ |
| Settings UI: Provider config, theme, shortcuts | All editable, persist | ☐ |
| 100% keyboard navigable (no mouse required) | Accessibility audit | ☐ |
| No console errors on launch | DevTools console clean | ☐ |

---

### 2.4 Market Data Foundation (Phase 5)

| Criterion | Verification Method | Pass/Fail |
|-----------|---------------------|-----------|
| Provider Adapter Protocol defined | `MarketDataProvider` interface in shared-types | ☐ |
| OpenBB Adapter implemented | Quotes, fundamentals, options, news endpoints work | ☐ |
| yfinance Adapter implemented | Quotes, basic fundamentals work | ☐ |
| FRED Adapter implemented | Macro indicators, yield curves work | ☐ |
| Instrument Master populated | ≥ 10,000 instruments with FIGI, ticker, metadata | ☐ |
| Ingestion Pipeline: Scheduled, Incremental, Idempotent | Re-run produces no duplicates, only new data | ☐ |
| DuckDB Schema: Raw/Normalized/Adjusted/Derived layers | Tables exist, queries work | ☐ |
| Parquet Partitioning: Date/Symbol, 128MB row groups | `ls -la data/parquet/` shows structure | ☐ |
| Data Quality Checks: Completeness, Staleness, Outliers, Duplicates | Quality reports generated per ingestion job | ☐ |
| Data Provenance: Provider, Source TS, Ingestion TS, Version | Lineage query returns full chain | ☐ |
| Quote WebSocket Broadcast | Internal API pushes quotes to subscribers | ☐ |
| Real-time Quote Latency < 500ms (Provider → WebSocket → UI) | Load test with 1000 symbols | ☐ |
| 1000 concurrent WebSocket connections supported | Load test | ☐ |

---

### 2.5 Core Domain Skeletons (Phases 6-9, 12, 16, 17, 18)

| Domain | Criterion | Verification Method | Pass/Fail |
|--------|-----------|---------------------|-----------|
| **Equity Research** | Company Profile domain model + CRUD API | `POST/GET /api/v1/companies` works | ☐ |
| | Financial Statement storage schema | Tables exist, GAAP/IFRS tags enforced | ☐ |
| | SEC EDGAR Adapter skeleton | Can fetch 10-K for AAPL | ☐ |
| | Ratio Engine: 10 core formulas | Unit tests pass with known answers | ☐ |
| **Valuation** | DCF (FCFF 2-stage) model scaffold | `POST /api/v1/valuation/runs` returns 202 | ☐ |
| | WACC (CAPM + Build-up) model scaffold | Inputs validated, calculation runs | ☐ |
| | DDM (Gordon, H-model) model scaffold | Inputs validated, calculation runs | ☐ |
| **Quant Finance** | Distribution Library (Normal, LogNormal, Student-t, GED) | PDF, CDF, quantile, sampling work | ☐ |
| | Monte Carlo Framework (antithetic, control variates) | 10k paths GBM in < 5s | ☐ |
| | GBM Path Generation | Moment matching test passes | ☐ |
| **Portfolio** | Portfolio/Position/Cash domain models | CRUD API, invariants enforced | ☐ |
| | Transaction Recording | Buy/Sell with fees, audit trail | ☐ |
| | Basic Metrics (Value, P&L, Weights, HHI) | Calculated correctly on test data | ☐ |
| **Risk** | Historical VaR (95%, 99%, 1d/10d) | Kupiec backtest passes on synthetic | ☐ |
| | Parametric VaR (Delta-Normal) | Matches analytical quantile | ☐ |
| | Expected Shortfall (Historical) | Acerbi-Szekely backtest passes | ☐ |
| **Fixed Income** | Bond Pricing (Clean/Dirty, YTM, Duration, Convexity) | Matches Fabozzi examples | ☐ |
| | Yield Curve (Nelson-Siegel-Svensson) | R² > 0.999 on synthetic data | ☐ |
| **Derivatives** | BSM European (Price + Greeks) | Put-call parity, boundaries, Greeks consistency | ☐ |
| | Binomial (CRR) American | Convergence to BSM, early exercise premium | ☐ |
| **Workspace** | Research Notebook (Jupyter kernel) | Execute Python, save/load .ipynb | ☐ |
| | Saved Workspaces | Layout + watchlist + charts persist | ☐ |
| **AI Intelligence** | RAG Pipeline (LanceDB + Hybrid Search) | Query returns cited results | ☐ |
| | Tool Allowlist Framework | Schema validation, sandbox, audit log | ☐ |
| | Report Generation (Template + Evidence) | Markdown output with citations | ☐ |
| **Governance** | RBAC (Admin, Analyst, Viewer) | Middleware enforces permissions | ☐ |
| | Audit Trail (Immutable, Hash Chain) | Tamper detection works | ☐ |
| | Data License Register API | CRUD for provider/dataset licenses | ☐ |

---

### 2.6 Financial Model Verification (Minimum for Phase 1)

| Model | KAT Tests | Property Tests | Reference Validation | Boundary Tests | Status |
|-------|-----------|----------------|---------------------|----------------|--------|
| `ERIN-FM-DIST-001` | ≥ 5 | ✅ | SciPy | ✅ | ☐ |
| `ERIN-FM-MC-001` | ≥ 3 | ✅ | — | ✅ | ☐ |
| `ERIN-FM-GBM-001` | ≥ 3 | ✅ | Moment matching | ✅ | ☐ |
| `ERIN-FM-DCF-001` | ≥ 5 | ✅ | Damodaran dataset | ✅ | ☐ |
| `ERIN-FM-WACC-001` | ≥ 3 | ✅ | Textbook | ✅ | ☐ |
| `ERIN-FM-BSM-001` | ≥ 12 | ✅ | QuantLib 1.38 | ✅ | ☐ |
| `ERIN-FM-BINOM-001` | ≥ 5 | ✅ | Convergence test | ✅ | ☐ |
| `ERIN-FM-VAR-HIST-001` | ≥ 5 | ✅ | Kupiec/Christoffersen | ✅ | ☐ |
| `ERIN-FM-VAR-PARAM-001` | ≥ 3 | ✅ | Analytical | ✅ | ☐ |
| `ERIN-FM-ES-001` | ≥ 3 | ✅ | Acerbi-Szekely | ✅ | ☐ |
| `ERIN-FM-BOND-001` | ≥ 8 | ✅ | Fabozzi | ✅ | ☐ |
| `ERIN-FM-CURVE-001` | ≥ 3 | ✅ | R² > 0.999 | ✅ | ☐ |

**Verification Standard:** All models must have `test_verification.py` with passing tests.

---

### 2.7 Test Execution (All Must Pass)

| Test Suite | Command | Target |
|------------|---------|--------|
| Python Unit Tests | `pytest tests/unit -x` | 100% pass, ≥ 80% domain coverage |
| Rust Unit Tests | `cargo test --workspace` | 100% pass |
| TypeScript Unit Tests | `pnpm vitest run` | 100% pass, ≥ 80% UI coverage |
| Integration Tests | `pytest tests/integration -x` | 100% pass |
| Contract Tests | `python -m scripts.ecp.contract_test` | 0 breaking changes |
| Property Tests | `pytest tests/property -x` | 1000+ examples/model |
| Financial Verification | `pytest models/ -m verification -x` | All VERIFIED models pass |
| E2E UI Tests | `pnpm playwright test` | 10 core journeys pass |
| Security Scan | `python -m scripts.ecp.security_scan` | 0 CRITICAL/HIGH |
| Resource Profile | `python -m scripts.ecp.resource_profile --profile standard` | ≤ 6 GB peak RSS |
| Architecture Check | `python -m scripts.ecp.arch_check` | 0 violations |

---

### 2.8 Security (All Must Pass)

| Check | Tool | Threshold |
|-------|------|-----------|
| Python SAST | Bandit | 0 HIGH |
| Rust SAST | cargo-audit | 0 HIGH |
| Node SAST | npm audit | 0 HIGH |
| Container Scan | Trivy | 0 HIGH |
| Custom Rules | Semgrep | 0 CRITICAL |
| Secrets Detection | TruffleHog/GitLeaks | 0 |
| SBOM Generated | Syft | CycloneDX JSON exists |
| Dependency Licenses | pip-licenses/cargo-license | All compatible |

---

### 2.9 Performance Benchmarks (Phase 1 Targets)

| Benchmark | Target | Measured |
|-----------|--------|----------|
| App Cold Start | < 3 seconds | ☐ |
| Quote Update Latency (Local) | < 500ms | ☐ |
| Watchlist Load (100 symbols) | < 200ms | ☐ |
| Chart Render (1yr Daily) | < 100ms | ☐ |
| DCF Calculation (100 Scenarios) | < 2 seconds | ☐ |
| Historical VaR (5yr, 1000 Assets) | < 5 seconds | ☐ |
| Monte Carlo (10k Paths, 252 Steps) | < 10 seconds | ☐ |
| Bond Analytics (Yield Curve) | < 500ms | ☐ |
| BSM Price + Greeks | < 0.1 ms/option | ☐ |
| Peak RSS (Standard Profile) | ≤ 6 GB | ☐ |
| Full Test Suite | < 5 minutes | ☐ |

---

### 2.10 Data Licensing (All Phase 1 Providers)

| Provider | Commercial Use | Redistribution | Caching | Attribution | Status |
|----------|----------------|----------------|---------|-------------|--------|
| OpenBB Platform | ✅ | ⚠️ Per provider | ✅ | ✅ | ☐ Documented |
| yfinance | ⚠️ Gray area | ❌ | ⚠️ Limited | ❌ | ☐ Risk documented |
| FRED | ✅ | ✅ | ✅ | ✅ | ☐ Documented |
| Alpha Vantage | ❌ Free tier | ❌ Free tier | ✅ | ✅ | ☐ Not for prod |
| SEC EDGAR | ✅ | ✅ | ✅ | ✅ | ☐ Documented |

---

## 3. Phase 1 Gate Decision

### 3.1 Go/No-Go Criteria

**GO (Proceed to Phase 2+ Implementation):**
- [ ] All documentation reviewed and approved
- [ ] All development infrastructure criteria pass
- [ ] All UI foundation criteria pass
- [ ] All market data foundation criteria pass
- [ ] All core domain skeletons implemented with passing tests
- [ ] All financial model verification criteria pass (minimum 12 models)
- [ ] All test suites pass (unit, integration, contract, property, verification, E2E)
- [ ] All security scans clean
- [ ] All performance benchmarks met
- [ ] Data licensing documented for all Phase 1 providers
- [ ] No unresolved CRITICAL/HIGH issues

**NO-GO (Remediate Before Proceeding):**
- Any single criterion above fails
- Any CRITICAL/HIGH security finding
- Any financial model verification failure
- Resource budget exceeded
- Architecture violation detected

### 3.2 Conditional Go (With Remediation Plan)

If ≤ 3 non-criteria fail with clear remediation plan (≤ 1 week):
- Document failures in `KNOWN_LIMITATIONS.md`
- Assign owner and deadline
- Phase 2 can start but gate not fully passed

---

## 4. Evidence Package (Required for Gate Review)

| Artifact | Location | Required |
|----------|----------|----------|
| Test Run Reports (JUnit XML) | `artifacts/test-results/` | ✅ |
| Coverage Reports (HTML) | `artifacts/coverage/` | ✅ |
| Benchmark Results (JSON) | `artifacts/benchmarks/` | ✅ |
| Security Scan Reports (SARIF) | `artifacts/security/` | ✅ |
| Resource Profile Report | `artifacts/resource_profile.json` | ✅ |
| Architecture Check Report | `artifacts/arch_check.json` | ✅ |
| Contract Compatibility Report | `artifacts/contract_diff.json` | ✅ |
| Financial Verification Reports | `artifacts/model_verification/` | ✅ |
| E2E Test Screenshots/Videos | `artifacts/e2e/` | ✅ |
| SBOM (CycloneDX) | `artifacts/sbom.json` | ✅ |
| Signed Build Artifacts | `artifacts/builds/` | ✅ |
| Updated Documentation | Repository root | ✅ |
| `KNOWN_LIMITATIONS.md` | Repository root | ✅ |
| `CHANGELOG.md` | Repository root | ✅ |

---

## 5. Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| **QA Lead** | | | |
| **Principal Architect** | | | |
| **Security Engineer** | | | |
| **Chief Orchestrator** | | | |
| **Product Specification Agent** | | | |

---

## 6. Post-Gate Actions (If GO)

1. Tag `phase-1-complete` in Git
2. Update `FEATURE_REGISTRY.md` all Phase 1 features → `VERIFIED`
3. Archive Phase 1 evidence to `.erin/evidence/phase1/`
4. Begin Phase 2 implementation per `IMPLEMENTATION_ROADMAP.md`
5. Conduct Phase 1 Retrospective (blameless)
6. Update risk register based on learnings

---

**Phase 1 Status:** ☐ **NOT STARTED** | ☐ **IN PROGRESS** | ☐ **READY FOR GATE** | ☐ **PASSED** | ☐ **FAILED**