# ERIN 2.0 — PRODUCT REQUIREMENTS DOCUMENT (PRD)

**Version:** 1.0
**Status:** DRAFT
**Classification:** INTERNAL — PRODUCT SPECIFICATION
**Owner:** Product Specification Agent
**Phase:** 1 — Product Requirements

---

## 1. Product Vision

ERIN is a **unified financial operating environment** that provides institutional-grade financial intelligence, research, and analytics capabilities through an original terminal interface. It serves quantitative researchers, portfolio managers, risk analysts, and equity analysts who need a reproducible, secure, and extensible platform for financial decision-making.

---

## 2. User Personas

| Persona | Primary Goals | Key Workflows |
|---------|---------------|---------------|
| **Quantitative Researcher** | Model development, backtesting, factor research | Monte Carlo simulation, factor modeling, strategy backtesting |
| **Portfolio Manager** | Portfolio construction, rebalancing, risk monitoring | Mean-variance optimization, Black-Litterman, VaR/ES monitoring |
| **Risk Analyst** | VaR/ES calculation, stress testing, risk attribution | Historical/Parametric/MC VaR, scenario analysis, backtesting |
| **Equity Analyst** | Fundamental research, valuation, peer comparison | DCF/Comps/DDM, financial statement analysis, earnings tracking |
| **Fixed Income Analyst** | Bond analytics, yield curve modeling, credit analysis | YTM/Duration/Convexity, curve bootstrapping, Z-spread/OAS |
| **Macro Strategist** | Economic indicator tracking, cross-asset analysis | FRED/IMF/OECD data, yield curve analysis, central bank monitoring |
| **AI Research Assistant User** | Document analysis, research automation, coding assistance | RAG queries, financial report generation, quant code generation |

---

## 3. Phase 1 Functional Requirements (MVP)

### 3.1 Domain 01: Market Intelligence (Core)
| ID | User Story | Acceptance Criteria |
|----|------------|---------------------|
| MI-01 | As a user, I want to create and manage watchlists so I can monitor selected instruments | Create watchlist (max 500 symbols), add/remove symbols, persist across sessions |
| MI-02 | As a user, I want real-time quote display for watchlist instruments | Bid/ask/last/size/timestamp displayed, updates via WebSocket < 500ms latency |
| MI-03 | As a user, I want a market calendar showing trading days/holidays | Major exchanges (NYSE, NASDAQ, LSE, TSE, HKEX, IDX), holiday indicators |
| MI-04 | As a user, I want basic charting (line, candlestick) for any instrument | Lightweight Charts, timeframe selection (1D, 1W, 1M, 3M, 1Y, 5Y), sync across panels |

### 3.2 Domain 02: Financial Data Infrastructure (Core)
| ID | User Story | Acceptance Criteria |
|----|------------|---------------------|
| DI-01 | As a system, I need a provider adapter framework to integrate data sources | `MarketDataProvider` protocol, OpenBB adapter implemented, yfinance adapter implemented |
| DI-02 | As a system, I need an instrument master with canonical identifiers | FIGI primary, composite ticker, exchange, currency, asset class, metadata |
| DI-03 | As a system, I need an ingestion pipeline for historical data | Scheduled, incremental, idempotent, partitioned Parquet (date/symbol) |
| DI-04 | As a system, I need data quality validation on ingestion | Completeness, staleness, outlier, duplicate, currency, timestamp checks |
| DI-05 | As a system, I need data provenance tracking | Provider, source timestamp, ingestion timestamp, version, lineage |

### 3.3 Domain 03: Equity Research (Skeleton)
| ID | User Story | Acceptance Criteria |
|----|------------|---------------------|
| ER-01 | As an analyst, I want company profiles with basic metadata | Name, CIK, ticker mappings, exchange, sector (GICS), industry, description |
| ER-02 | As an analyst, I want to store financial statements | Income statement, balance sheet, cash flow — quarterly/annual, GAAP/IFRS tagged |
| ER-03 | As an analyst, I want core financial ratios calculated | Profitability, liquidity, solvency, efficiency — on-demand from statements |

### 3.4 Domain 05: Valuation Engine (Core Framework)
| ID | User Story | Acceptance Criteria |
|----|------------|---------------------|
| VE-01 | As an analyst, I want to run a DCF (FCFF, 2-stage) valuation | Input: revenue growth, margins, WACC, terminal growth; Output: intrinsic value, sensitivity table |
| VE-02 | As an analyst, I want WACC calculation (CAPM + build-up) | Risk-free rate, equity risk premium, beta, cost of debt, tax rate, capital structure |
| VE-03 | As an analyst, I want DDM (Gordon, H-model) | Dividend inputs, growth phases, required return |

### 3.5 Domain 06: Quantitative Finance (Core Framework)
| ID | User Story | Acceptance Criteria |
|----|------------|---------------------|
| QF-01 | As a quant, I want a distribution library (Normal, LogNormal, Student-t, GED) | PDF, CDF, quantile, random sampling, parameter fitting |
| QF-02 | As a quant, I want Monte Carlo simulation framework | Path generation, antithetic variates, control variates, convergence diagnostics |
| QF-03 | As a quant, I want Geometric Brownian Motion paths | Spot, drift, vol, correlation matrix, multi-asset |

### 3.6 Domain 08: Portfolio Management (Core)
| ID | User Story | Acceptance Criteria |
|----|------------|---------------------|
| PM-01 | As a PM, I want to create multi-asset portfolios with positions | Cash, equities, bonds, options, futures — quantities, avg cost, market value |
| PM-02 | As a PM, I want basic portfolio metrics | Total value, P&L (realized/unrealized), weights, concentration (HHI) |
| PM-03 | As a PM, I want transaction recording | Buy/sell, fees, slippage, cash impact, audit trail |

### 3.7 Domain 09: Risk Management (Core)
| ID | User Story | Acceptance Criteria |
|----|------------|---------------------|
| RM-01 | As a risk analyst, I want Historical VaR (95%, 99%, 1-day/10-day) | Sorted historical returns, interpolation, Kupiec backtest |
| RM-02 | As a risk analyst, I want Parametric VaR (Delta-Normal) | Covariance matrix, portfolio weights, analytical quantile |
| RM-03 | As a risk analyst, I want Expected Shortfall (Historical) | Tail average beyond VaR, Acerbi-Szekely backtest |

### 3.8 Domain 12: Fixed Income (Core)
| ID | User Story | Acceptance Criteria |
|----|------------|---------------------|
| FI-01 | As an analyst, I want bond pricing (clean/dirty), YTM, duration, convexity | Semi-annual/annual coupons, ACT/ACT, 30/360 conventions, comparison to Fabozzi |
| FI-02 | As an analyst, I want yield curve construction (Nelson-Siegel-Svensson) | Fit to observed yields, R² > 0.999 on synthetic, extrapolation control |

### 3.9 Domain 13: Derivatives (Core)
| ID | User Story | Acceptance Criteria |
|----|------------|---------------------|
| DV-01 | As a quant, I want Black-Scholes-Merton European option pricing | Put-call parity, boundary conditions, Greeks (Δ, Γ, ν, θ, ρ) verified |
| DV-02 | As a quant, I want Binomial tree (CRR) for American options | Convergence to BSM, early exercise premium, N ≥ 100 steps |

### 3.10 Domain 16: Financial Workspace (Core)
| ID | User Story | Acceptance Criteria |
|----|------------|---------------------|
| FW-01 | As a researcher, I want a Jupyter-compatible notebook | Code/markdown cells, kernel management, output display, save/load .ipynb |
| FW-02 | As a researcher, I want saved workspaces (layout + data) | Persist panel arrangement, watchlist, chart settings, notebook references |

### 3.11 Domain 17: AI Financial Intelligence (Skeleton)
| ID | User Story | Acceptance Criteria |
|----|------------|---------------------|
| AI-01 | As a user, I want a RAG pipeline for financial documents | LanceDB vector store, hybrid search (BM25 + vector), citation tracking |
| AI-02 | As a user, I want a tool allowlist framework | Schema-validated tools, sandboxed execution, read-only default, audit log |
| AI-03 | As a user, I want basic research report generation | Template + evidence → formatted report (Markdown/PDF) |

### 3.12 Domain 18: Governance (Core)
| ID | User Story | Acceptance Criteria |
|----|------------|---------------------|
| GV-01 | As a system, I need RBAC (Admin, Analyst, Viewer) | Role assignment, permission matrix, API enforcement |
| GV-02 | As a system, I need audit trail for sensitive operations | Immutable log: user, action, resource, timestamp, hash chain |
| GV-03 | As a system, I need data licensing register per provider | Commercial use, redistribution, caching, attribution, retention terms |

---

## 4. Non-Functional Requirements

| Category | Requirement | Target |
|----------|-------------|--------|
| **Performance** | Peak RSS (8 GB workstation) | ≤ 6 GB |
| **Performance** | Quote update latency (local) | < 500ms end-to-end |
| **Performance** | DCF calculation (100 scenarios) | < 2 seconds |
| **Performance** | Historical VaR (5 years, 1000 assets) | < 5 seconds |
| **Reliability** | Uptime (local) | 99.9% (excl. maintenance) |
| **Reliability** | Data ingestion success rate | 99.5% |
| **Security** | Critical vulnerabilities at release | 0 |
| **Security** | Secret exposure in logs/code | 0 |
| **Usability** | Terminal launch time (cold) | < 3 seconds |
| **Usability** | Keyboard-only navigation | 100% core workflows |
| **Reproducibility** | Build reproducibility | Bit-for-bit identical |
| **Reproducibility** | Model verification re-run | Identical results |

---

## 5. Data Provider Requirements (Phase 1)

| Provider | Data Types | License Status | Adapter Priority |
|----------|------------|----------------|------------------|
| **OpenBB Platform** | Equities, options, futures, crypto, macro, news | MIT (platform), per-provider varies | P0 — Primary |
| **yfinance** | Equities, ETFs, basic fundamentals | Unofficial, scraping | P0 — Fallback |
| **FRED (St. Louis Fed)** | Macro indicators, rates, curves | Public domain | P0 — Macro |
| **Alpha Vantage** | Equities, forex, crypto, technical | Free tier (5 req/min) | P1 — Backup |
| **SEC EDGAR** | Company filings (10-K, 10-Q, 8-K) | Public domain | P1 — Fundamentals |

---

## 6. UI/UX Requirements (Terminal)

| Requirement | Specification |
|-------------|---------------|
| **Theme** | Dark-first, high contrast (WCAG AA), compact density |
| **Navigation** | Global command bar (Cmd/Ctrl+K), keyboard shortcuts for all core actions |
| **Layout** | Multi-panel, resizable, dockable, persistent layouts per workspace |
| **Charts** | Lightweight Charts, synchronized crosshair/tooltip across panels |
| **Data Display** | Source, units, currency, time range, freshness on every visualization |
| **Accessibility** | Focus management, ARIA labels, color-blind safe palette |
| **Responsiveness** | 60fps chart rendering, < 100ms panel switch |

---

## 7. Out of Scope (Phase 1)

- Screeners, market breadth, corporate actions, alerts (Domain 01)
- Data reconciliation, corporate action adjustments, licensing metadata (Domain 02)
- Earnings analysis, peer comparison, investment thesis, research reports (Domain 03)
- Financial forecasting, capital allocation (Domain 04)
- Comps, precedent transactions, SOTP, EVA, sensitivity/scenario (Domain 05)
- Factor models, volatility models, derivatives pricing, numerical methods (Domain 06)
- VAR, GARCH, Bayesian, Kalman, HMM, EVT, bootstrap (Domain 07)
- Optimization, Black-Litterman, risk parity, attribution, rebalancing (Domain 08)
- Monte Carlo VaR, stress testing, credit/liquidity/IR/concentration risk, Greeks, backtesting (Domain 09)
- Order book L2, VWAP/TWAP, slippage, TCA, execution quality (Domain 10)
- Walk-forward, OOS, parameter sensitivity, paper trading, journal (Domain 11)
- Credit spreads, Z-spread, OAS, bond portfolio analytics (Domain 12)
- Heston, vol surfaces, hedging analytics (Domain 13)
- Cross-asset macro, central bank policy modeling (Domain 14)
- Sentiment, event classification, PDF analysis, news-to-asset mapping (Domain 15)
- Spreadsheet integration, reproducible experiments (Domain 16)
- Research assistant, document understanding, quant coding, model explanation (Domain 17)
- Collaboration, approval workflows, COI, instrument restrictions (Domain 18)

---

## 8. Acceptance Criteria (Phase 1 Gate)

All Phase 1 functional requirements must have:
- [ ] Implementation complete
- [ ] Unit tests passing (≥ 80% coverage on domain logic)
- [ ] Integration tests passing (API contracts)
- [ ] Financial model verification tests passing (known-answer + property)
- [ ] Security scan clean (bandit, cargo-audit, npm audit)
- [ ] Resource profile within budget (≤ 6 GB peak RSS)
- [ ] Documentation updated (API contracts, model specs, ADRs)

---

## 9. Dependencies

| Requirement | Depends On |
|-------------|------------|
| MI-02 (Real-time quotes) | DI-01, DI-02 (Provider adapter, Instrument master) |
| VE-01 (DCF) | ER-02 (Financial statements), QF-01 (Distributions for sensitivity) |
| RM-01 (Historical VaR) | PM-01 (Portfolio positions), DI-03 (Historical data) |
| FI-01 (Bond pricing) | DI-02 (Instrument master for bond metadata) |
| DV-01 (BSM) | QF-01 (Normal distribution), QF-02 (Monte Carlo for verification) |
| AI-01 (RAG) | DI-04 (Document ingestion), FW-01 (Notebook for doc storage) |

---

## 10. Approval

**Product Specification Agent:** _________________ **Date:** __________

**Chief Orchestrator:** _________________ **Date:** __________