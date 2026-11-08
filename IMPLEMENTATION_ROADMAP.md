# ERIN 2.0 — IMPLEMENTATION ROADMAP

**Version:** 1.0
**Status:** DRAFT
**Classification:** INTERNAL — PROGRAM MANAGEMENT
**Owner:** Chief Orchestrator
**Phase:** 2 — Domain & System Architecture

---

## 1. Roadmap Overview

| Phase | Duration | Focus | Key Deliverable |
|-------|----------|-------|-----------------|
| **Phase 0** | Week 1 | Repository & Product Audit | ✅ Complete (this document set) |
| **Phase 1** | Weeks 1-2 | Product Requirements | PRD.md, Feature Registry, License Register |
| **Phase 2** | Weeks 2-3 | Domain & System Architecture | Architecture, Domain Model, DB Schema, API Contracts, Methodology, Security, Multi-Agent, ECP, Resource Policy, Test Strategy |
| **Phase 3** | Weeks 3-4 | Development Infrastructure | Git, Monorepo, CI/CD, ECP Scripts, Docker, Pre-commit |
| **Phase 4** | Weeks 4-6 | Terminal UI Foundation | Tauri 2 + React + TS, Design System, Command Bar, Panels, Charts |
| **Phase 5** | Weeks 6-8 | Market Data Foundation | Provider Adapters, Instrument Master, Ingestion, DuckDB/Parquet, Quality |
| **Phase 6** | Weeks 8-10 | Fundamental & Equity Research | Company Profiles, Financial Statements, Ratios, SEC Adapter |
| **Phase 7** | Weeks 10-13 | Quantitative Finance | Distributions, Monte Carlo, GBM, Factor Models, Optimization |
| **Phase 8** | Weeks 13-16 | Portfolio & Risk | Portfolio/Positions, VaR/ES, Stress Testing, Attribution |
| **Phase 9** | Weeks 16-20 | Fixed Income & Derivatives | Bond Analytics, Yield Curves, BSM, Binomial, Vol Surfaces |
| **Phase 10** | Weeks 20-24 | Trading & Backtesting | OMS, Event-driven Backtest, TCA, Walk-forward, Paper Trading |
| **Phase 11** | Weeks 24-28 | Macro & News Intelligence | FRED/IMF/OECD, Calendar, News Ingestion, NER, Sentiment |
| **Phase 12** | Weeks 28-32 | AI Research Assistant | RAG, Tool Allowlist, Sandbox, Report Generation |
| **Phase 13** | Weeks 32-34 | Security Hardening | Threat Model Review, Pen Test, Dependency Audit, Incident Response |
| **Phase 14** | Weeks 34-36 | Performance & Scalability | Load Testing, Profiling, Migration Guide, Benchmarks |
| **Phase 15** | Weeks 36-38 | Production Release | Signed Builds, Documentation, Runbooks, v1.0.0 |

**Total: ~38 weeks**

---

## 2. Phase Detail

### Phase 0: Repository & Product Audit (Week 1) ✅ COMPLETE
- [x] Repository inspection
- [x] Technology stack identification
- [x] Existing module mapping
- [x] Dependency analysis
- [x] Technical debt detection
- [x] Architecture violation identification
- [x] Security weakness identification
- [x] Financial methodology problem identification
- [x] Hardware compatibility evaluation

### Phase 1: Product Requirements (Weeks 1-2)
| Task | Owner | Deliverable |
|------|-------|-------------|
| Write detailed PRD | Product Spec Agent | `PRD.md` |
| Create Feature Registry | Product Spec Agent | `FEATURE_REGISTRY.md` |
| Populate Data License Register | Data Engineer | `DATA_LICENSE_REGISTER.md` |
| Define Phase 1 Acceptance Criteria | QA Lead | `PHASE1_ACCEPTANCE_CRITERIA.md` |
| Stakeholder Review | Chief Orchestrator | Signed PRD |

### Phase 2: Domain & System Architecture (Weeks 2-3) ✅ COMPLETE (Design Docs)
| Document | Owner | Status |
|----------|-------|--------|
| `ARCHITECTURE.md` | Principal Architect | ✅ Draft |
| `DOMAIN_MODEL.md` | Data Architect | ✅ Draft |
| `DATABASE_SCHEMA.md` | Data Engineer | ✅ Draft |
| `API_CONTRACTS.md` | Backend Engineer | ✅ Draft |
| `FINANCIAL_METHODOLOGY.md` | Quant Finance Engineer | ✅ Draft |
| `SECURITY_THREAT_MODEL.md` | Security Engineer | ✅ Draft |
| `MULTI_AGENT_EXECUTION.md` | Chief Orchestrator | ✅ Draft |
| `ECP_SPECIFICATION.md` | Chief Orchestrator | ✅ Draft |
| `RESOURCE_POLICY.md` | SRE | ✅ Draft |
| `TEST_STRATEGY.md` | QA Lead | ✅ Draft |
| `FEATURE_DEPENDENCY_GRAPH.md` | Principal Architect | ✅ Draft |
| `IMPLEMENTATION_ROADMAP.md` | Chief Orchestrator | ✅ Draft |
| `PHASE1_ACCEPTANCE_CRITERIA.md` | QA Lead | 🔄 This doc |

### Phase 3: Development Infrastructure (Weeks 3-4)
| Task | Owner | Acceptance Criteria |
|------|-------|---------------------|
| Initialize Git monorepo | Chief Orchestrator | `git init`, conventional commits, signed tags |
| Create `pyproject.toml` (uv workspaces) | Backend Engineer | All packages build, deps pinned |
| Create `Cargo.toml` (workspace) | Frontend Engineer | `cargo build` passes |
| Create `package.json` (pnpm workspaces) | Frontend Engineer | `pnpm install` passes |
| Setup GitHub Actions CI | SRE | Lint, typecheck, test, security, SBOM |
| Implement ECP Scripts | Chief Orchestrator | All 12 scripts functional |
| Configure Pre-commit Hooks | SRE | Runs on every commit |
| Docker Multi-stage Build | SRE | Produces < 500MB image |
| SBOM Generation (Syft) | Security Engineer | CycloneDX JSON on every build |
| Dependency Pinning Policy | Chief Orchestrator | Documented in `DECISIONS.md` |

### Phase 4: Terminal UI Foundation (Weeks 4-6)
| Sprint | Focus | Deliverables |
|--------|-------|--------------|
| **4.1** | Tauri 2 + React + TS + Vite Scaffold | `apps/desktop` builds, runs, hot reload |
| **4.2** | Design System (Tailwind + Radix) | Dark-first theme, tokens, components |
| **4.3** | Global Command Bar (Cmd/Ctrl+K) | Fuzzy search, history, keyboard nav |
| **4.4** | Keyboard Shortcuts Registry | Declarative, configurable, no conflicts |
| **4.5** | Multi-panel Layout (Dock/Resize/Persist) | Grid/Tabs, localStorage, restore |
| **4.6** | Watchlist Panel | CRUD, 500 symbol limit, persist |
| **4.7** | Chart Panel (Lightweight Charts) | Line/Candle, timeframes, sync crosshair |
| **4.8** | Settings/Config UI | Provider keys, theme, shortcuts |

**UI Acceptance Criteria:**
- [ ] Cold start < 3 seconds
- [ ] 60fps chart rendering
- [ ] 100% keyboard navigable
- [ ] WCAG AA contrast
- [ ] Layout persists across sessions

### Phase 5: Market Data Foundation (Weeks 6-8)
| Task | Owner | Acceptance Criteria |
|------|-------|---------------------|
| Provider Adapter Protocol | Data Engineer | `MarketDataProvider` interface, 3 adapters |
| OpenBB Adapter | Data Engineer | Quotes, fundamentals, options, news |
| yfinance Adapter | Data Engineer | Quotes, basic fundamentals |
| FRED Adapter | Data Engineer | Macro indicators, yield curves |
| Instrument Master | Data Engineer | FIGI primary, 50k+ instruments |
| Ingestion Pipeline | Data Engineer | Scheduled, incremental, idempotent |
| DuckDB Schema | Data Engineer | Normalized/Adjusted/Derived layers |
| Parquet Partitioning | Data Engineer | Date/Symbol, 128MB row groups |
| Data Quality Checks | Data Engineer | Completeness, staleness, outliers |
| Quote WebSocket | Backend Engineer | < 500ms latency, 1000 concurrent |

### Phase 6: Fundamental & Equity Research (Weeks 8-10)
| Task | Owner | Acceptance Criteria |
|------|-------|---------------------|
| Company Profile Domain | Backend Engineer | CRUD, CIK unique, ticker mappings |
| SEC EDGAR Adapter | Data Engineer | 10-K, 10-Q, 8-K parsing |
| Financial Statement Storage | Backend Engineer | GAAP/IFRS tags, period validation |
| Ratio Engine | Quant Engineer | Profitability, Liquidity, Solvency, Efficiency |
| Peer Group Identification | Quant Engineer | GICS + custom, configurable |
| Research Notebook | Frontend Engineer | Jupyter kernel, .ipynb save/load |

### Phase 7: Quantitative Finance (Weeks 10-13)
| Model | Verification Target | Status |
|-------|---------------------|--------|
| `ERIN-FM-DIST-001` | Distribution library (Normal, LogNormal, Student-t, GED) | PLANNED |
| `ERIN-FM-MC-001` | Monte Carlo framework (antithetic, control variates) | PLANNED |
| `ERIN-FM-GBM-001` | GBM paths (moment matching, log-normal property) | PLANNED |
| `ERIN-FM-FACTOR-001` | PCA, Regression factor models | PLANNED |
| `ERIN-FM-OPT-001` | CVXPY optimization (mean-variance, constraints) | PLANNED |

### Phase 8: Portfolio & Risk (Weeks 13-16)
| Model | Verification Target | Status |
|-------|---------------------|--------|
| `ERIN-FM-VAR-HIST-001` | Historical VaR (Kupiec/Christoffersen backtest) | PLANNED |
| `ERIN-FM-VAR-PARAM-001` | Parametric VaR (Delta-Normal, analytical) | PLANNED |
| `ERIN-FM-ES-001` | Expected Shortfall (Acerbi-Szekely) | PLANNED |
| `ERIN-FM-STRESS-001` | Historical + Hypothetical scenarios | PLANNED |
| `ERIN-FM-ATTRIB-001` | Brinson attribution | PLANNED |

### Phase 9: Fixed Income & Derivatives (Weeks 16-20)
| Model | Verification Target | Status |
|-------|---------------------|--------|
| `ERIN-FM-BOND-001` | Price, YTM, Duration, Convexity (Fabozzi) | PLANNED |
| `ERIN-FM-CURVE-001` | Nelson-Siegel-Svensson (R² > 0.999) | PLANNED |
| `ERIN-FM-BSM-001` | BSM European (Put-call parity, Greeks) | PLANNED |
| `ERIN-FM-BINOM-001` | CRR Binomial (Convergence, Early exercise) | PLANNED |
| `ERIN-FM-VOLSURF-001` | SVI Calibration (No arbitrage) | PLANNED |

### Phase 10: Trading & Backtesting (Weeks 20-24)
| Feature | Acceptance Criteria |
|---------|---------------------|
| Order Management | Order ticket, lifecycle, audit trail |
| Event-driven Backtest | Vectorized + iterative, no look-ahead |
| Transaction Cost Model | Spread + Slippage + Commission |
| Walk-forward/OOS | Temporal validation, leakage prevention |
| Paper Trading | Simulated broker, P&L tracking |

### Phase 11: Macro & News Intelligence (Weeks 24-28)
| Feature | Acceptance Criteria |
|---------|---------------------|
| FRED/IMF/OECD Adapters | 1000+ indicators, automated ingestion |
| Economic Calendar | Central bank dates, releases, forecasts |
| News Ingestion | RSS + NewsAPI, deduplication |
| NER + Entity Linking | Company/Instrument mapping > 90% precision |
| Sentiment (FinBERT) | -1 to 1 score, per entity |

### Phase 12: AI Research Assistant (Weeks 28-32)
| Feature | Acceptance Criteria |
|---------|---------------------|
| RAG Pipeline | LanceDB, Hybrid search, Citations |
| Tool Allowlist | Schema validation, Sandbox, Audit |
| Code Execution | Python, seccomp, 128MB, 60s |
| Report Generation | Template + Evidence → Markdown/PDF |

### Phase 13: Security Hardening (Weeks 32-34)
| Activity | Acceptance Criteria |
|----------|---------------------|
| Threat Model Review | All STRIDE mitigated |
| Penetration Test | 0 Critical/High findings |
| Dependency Audit | 0 Critical/High vulns |
| SBOM Signing | Cosign verified |
| Incident Response Runbook | Tested drill |

### Phase 14: Performance & Scalability (Weeks 34-36)
| Benchmark | Target |
|-----------|--------|
| Cold Start | < 3s |
| Quote Latency | < 500ms |
| DCF (100 scenarios) | < 2s |
| VaR (5yr, 1000 assets) | < 5s |
| Peak RSS (Standard) | ≤ 6 GB |
| Test Suite | < 5 min |

### Phase 15: Production Release (Weeks 36-38)
| Deliverable | Status |
|-------------|--------|
| Signed Builds (Windows/Linux/macOS) | PLANNED |
| Complete Documentation | PLANNED |
| Known Limitations Published | PLANNED |
| Deployment Runbooks | PLANNED |
| v1.0.0 Tag | PLANNED |

---

## 3. Milestone Gates

| Gate | Criteria | Authority |
|------|----------|-----------|
| **Phase 1→2** | PRD signed, License register populated | Product Spec + Chief Orchestrator |
| **Phase 2→3** | All 12 design docs reviewed, ADRs for key decisions | Principal Architect + Security |
| **Phase 3→4** | CI green, ECP scripts functional, Docker builds | SRE + Chief Orchestrator |
| **Phase 4→5** | UI launches, command bar works, panels dock | Frontend Engineer + QA |
| **Phase 5→6** | Real quotes via WebSocket, 1000 symbols | Data Engineer + Backend |
| **Phase 6→7** | DCF runs with real fundamentals | Quant Engineer + QA |
| **Phase 7→8** | VaR calculates on real portfolio | Quant Engineer + Risk |
| **Phase 8→9** | Bond analytics match Fabozzi | Quant Engineer + QA |
| **Phase 9→10** | Backtest runs without look-ahead | Quant Engineer + QA |
| **Phase 10→11** | Macro indicators update automatically | Data Engineer + QA |
| **Phase 11→12** | RAG answers with citations | AI Engineer + QA |
| **Phase 12→13** | All security gates pass | Security Engineer |
| **Phase 13→14** | Performance benchmarks met | SRE + QA |
| **Phase 14→15** | Release gate 100% pass | Chief Orchestrator + Integration Reviewer |

---

## 4. Resource Allocation (Agent Weeks)

| Role | Phase 3 | Phase 4 | Phase 5 | Phase 6 | Phase 7 | Phase 8 | Phase 9 | Phase 10 | Phase 11 | Phase 12 | Phase 13 | Phase 14 | Phase 15 | Total |
|------|---------|---------|---------|---------|---------|---------|---------|----------|----------|----------|----------|----------|----------|-------|
| Chief Orchestrator | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 16 |
| Principal Architect | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 15 |
| Product Spec Agent | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 4 |
| Backend Engineer | 2 | 1 | 3 | 3 | 2 | 3 | 2 | 2 | 2 | 1 | 1 | 1 | 1 | 24 |
| Frontend Engineer | 1 | 4 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | 1 | 1 | 16 |
| Quant Finance Engineer | 0 | 0 | 0 | 1 | 4 | 3 | 3 | 2 | 1 | 1 | 0 | 1 | 0 | 16 |
| Data Engineer | 1 | 0 | 4 | 2 | 1 | 1 | 1 | 1 | 3 | 1 | 0 | 1 | 0 | 16 |
| Security Engineer | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 3 | 1 | 1 | 7 |
| QA Lead | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 1 | 1 | 1 | 2 | 2 | 18 |
| Integration Reviewer | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 2 | 7 |
| **Total** | **11** | **8** | **11** | **11** | **11** | **14** | **10** | **11** | **11** | **9** | **8** | **10** | **11** | **139** |

---

## 5. Risk Register (Top 10)

| ID | Risk | Probability | Impact | Mitigation | Owner |
|----|------|-------------|--------|------------|-------|
| R1 | OpenBB API breaking changes | High | Medium | Adapter isolation, version pin, fallback providers | Data Engineer |
| R2 | 8GB RAM limit exceeded | Medium | High | Continuous profiling, lazy loading, streaming | SRE |
| R3 | Financial model numerical errors | Medium | Critical | Property-based testing, reference validation | Quant Engineer |
| R4 | Data licensing non-compliance | Medium | Critical | License register, automated checks | Data Engineer |
| R5 | AI tool sandbox escape | Low | Critical | seccomp, gVisor, strict allowlist | Security Engineer |
| R6 | Scope creep (18 domains) | Very High | High | Strict phase gates, ADR for additions | Chief Orchestrator |
| R7 | Tauri/WebView2 distribution issues | Low | High | Document install, bundle bootstrapper | Frontend Engineer |
| R8 | Python 3.14 ecosystem issues | Medium | High | Pin 3.12 LTS for production | Backend Engineer |
| R9 | Single developer bus factor | High | High | Documentation-first, ADRs, ECP automation | Chief Orchestrator |
| R10 | Dependency vulnerability cascade | Medium | High | Daily scans, lockfiles, sigstore | Security Engineer |

---

## 6. Approval

**Chief Orchestrator:** _________________ **Date:** __________

**Principal Architect:** _________________ **Date:** __________

**All Specialist Leads:** _________________ **Date:** __________