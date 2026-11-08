# ERIN 2.0 — FEATURE REGISTRY

**Version:** 1.0
**Status:** ACTIVE
**Classification:** INTERNAL — FEATURE TRACKING
**Owner:** Product Specification Agent

---

## Feature Status Definitions

| Status | Definition |
|--------|------------|
| `NOT_STARTED` | No work begun; may not be planned for current phase |
| `PLANNED` | Requirements defined, in backlog for current/next phase |
| `IN_PROGRESS` | Active implementation; code being written |
| `IMPLEMENTED` | Code complete; not yet tested |
| `TESTED` | Unit + integration tests passing |
| `REVIEWED` | Code reviewed; architecture/security/financial review passed |
| `VERIFIED` | **All acceptance criteria demonstrated**; evidence recorded |
| `BLOCKED` | Cannot proceed; explicit blocker documented |

**Only `VERIFIED` features count toward phase gate completion.**

---

## Phase 1 Feature Registry

### Domain 01: Market Intelligence

| Feature ID | Feature Name | Status | Owner | Acceptance Criteria Ref | Evidence |
|------------|--------------|--------|-------|------------------------|----------|
| MI-01 | Watchlist CRUD | NOT_STARTED | Frontend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.4 | — |
| MI-02 | Real-time Quotes (WebSocket) | NOT_STARTED | Backend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.4 | — |
| MI-03 | Market Calendar | NOT_STARTED | Data Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.4 | — |
| MI-04 | Basic Charting (Lightweight Charts) | NOT_STARTED | Frontend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.4 | — |

### Domain 02: Financial Data Infrastructure

| Feature ID | Feature Name | Status | Owner | Acceptance Criteria Ref | Evidence |
|------------|--------------|--------|-------|------------------------|----------|
| DI-01 | Provider Adapter Framework | NOT_STARTED | Data Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.4 | — |
| DI-02 | Instrument Master (FIGI) | NOT_STARTED | Data Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.4 | — |
| DI-03 | Ingestion Pipeline | NOT_STARTED | Data Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.4 | — |
| DI-04 | Data Quality Validation | NOT_STARTED | Data Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.4 | — |
| DI-05 | Data Provenance/Lineage | NOT_STARTED | Data Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.4 | — |

### Domain 03: Equity Research

| Feature ID | Feature Name | Status | Owner | Acceptance Criteria Ref | Evidence |
|------------|--------------|--------|-------|------------------------|----------|
| ER-01 | Company Profiles | NOT_STARTED | Backend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| ER-02 | Financial Statements Storage | NOT_STARTED | Backend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| ER-03 | Financial Ratios Engine | NOT_STARTED | Quant Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |

### Domain 05: Valuation Engine

| Feature ID | Feature Name | Status | Owner | Acceptance Criteria Ref | Evidence |
|------------|--------------|--------|-------|------------------------|----------|
| VE-01 | DCF (FCFF 2-Stage) | NOT_STARTED | Quant Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| VE-02 | WACC (CAPM + Build-up) | NOT_STARTED | Quant Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| VE-03 | DDM (Gordon, H-Model) | NOT_STARTED | Quant Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |

### Domain 06: Quantitative Finance

| Feature ID | Feature Name | Status | Owner | Acceptance Criteria Ref | Evidence |
|------------|--------------|--------|-------|------------------------|----------|
| QF-01 | Distribution Library | NOT_STARTED | Quant Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| QF-02 | Monte Carlo Framework | NOT_STARTED | Quant Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| QF-03 | GBM Path Generation | NOT_STARTED | Quant Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |

### Domain 08: Portfolio Management

| Feature ID | Feature Name | Status | Owner | Acceptance Criteria Ref | Evidence |
|------------|--------------|--------|-------|------------------------|----------|
| PM-01 | Portfolio/Positions Domain | NOT_STARTED | Backend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| PM-02 | Portfolio Metrics | NOT_STARTED | Backend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| PM-03 | Transaction Recording | NOT_STARTED | Backend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |

### Domain 09: Risk Management

| Feature ID | Feature Name | Status | Owner | Acceptance Criteria Ref | Evidence |
|------------|--------------|--------|-------|------------------------|----------|
| RM-01 | Historical VaR | NOT_STARTED | Quant Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| RM-02 | Parametric VaR | NOT_STARTED | Quant Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| RM-03 | Expected Shortfall | NOT_STARTED | Quant Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |

### Domain 12: Fixed Income

| Feature ID | Feature Name | Status | Owner | Acceptance Criteria Ref | Evidence |
|------------|--------------|--------|-------|------------------------|----------|
| FI-01 | Bond Analytics | NOT_STARTED | Quant Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| FI-02 | Yield Curve Construction | NOT_STARTED | Quant Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |

### Domain 13: Derivatives

| Feature ID | Feature Name | Status | Owner | Acceptance Criteria Ref | Evidence |
|------------|--------------|--------|-------|------------------------|----------|
| DV-01 | BSM European Options | NOT_STARTED | Quant Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| DV-02 | Binomial (CRR) American | NOT_STARTED | Quant Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |

### Domain 14: Macro Intelligence

| Feature ID | Feature Name | Status | Owner | Acceptance Criteria Ref | Evidence |
|------------|--------------|--------|-------|------------------------|----------|
| MAC-01 | Economic Indicators (FRED) | NOT_STARTED | Data Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| MAC-02 | Yield Curve Snapshots | NOT_STARTED | Data Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |

### Domain 15: News Intelligence

| Feature ID | Feature Name | Status | Owner | Acceptance Criteria Ref | Evidence |
|------------|--------------|--------|-------|------------------------|----------|
| NEWS-01 | Article Ingestion | NOT_STARTED | Data Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| NEWS-02 | Entity Extraction | NOT_STARTED | AI Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| NEWS-03 | Relevance Scoring | NOT_STARTED | AI Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |

### Domain 16: Financial Workspace

| Feature ID | Feature Name | Status | Owner | Acceptance Criteria Ref | Evidence |
|------------|--------------|--------|-------|------------------------|----------|
| FW-01 | Research Notebook (Jupyter) | NOT_STARTED | Frontend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| FW-02 | Saved Workspaces | NOT_STARTED | Frontend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |

### Domain 17: AI Financial Intelligence

| Feature ID | Feature Name | Status | Owner | Acceptance Criteria Ref | Evidence |
|------------|--------------|--------|-------|------------------------|----------|
| AI-01 | RAG Pipeline (LanceDB) | NOT_STARTED | AI Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| AI-02 | Tool Allowlist Framework | NOT_STARTED | AI Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| AI-03 | Report Generation | NOT_STARTED | AI Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |

### Domain 18: Governance

| Feature ID | Feature Name | Status | Owner | Acceptance Criteria Ref | Evidence |
|------------|--------------|--------|-------|------------------------|----------|
| GV-01 | RBAC (Admin, Analyst, Viewer) | NOT_STARTED | Backend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| GV-02 | Audit Trail (Hash Chain) | NOT_STARTED | Backend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |
| GV-03 | Data License Register API | NOT_STARTED | Data Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.5 | — |

---

## Cross-Cutting / Infrastructure

| Feature ID | Feature Name | Status | Owner | Acceptance Criteria Ref | Evidence |
|------------|--------------|--------|-------|------------------------|----------|
| INFRA-01 | Git Monorepo + Conventional Commits | NOT_STARTED | Chief Orchestrator | PHASE1_ACCEPTANCE_CRITERIA.md §2.2 | — |
| INFRA-02 | CI/CD Pipeline (GitHub Actions) | NOT_STARTED | SRE | PHASE1_ACCEPTANCE_CRITERIA.md §2.2 | — |
| INFRA-03 | ECP Scripts (12 components) | NOT_STARTED | Chief Orchestrator | PHASE1_ACCEPTANCE_CRITERIA.md §2.2 | — |
| INFRA-04 | Pre-commit Hooks | NOT_STARTED | SRE | PHASE1_ACCEPTANCE_CRITERIA.md §2.2 | — |
| INFRA-05 | Docker Multi-stage Build | NOT_STARTED | SRE | PHASE1_ACCEPTANCE_CRITERIA.md §2.2 | — |
| INFRA-06 | SBOM Generation | NOT_STARTED | Security Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.2 | — |
| UI-01 | Tauri 2 + React + TS + Vite Scaffold | NOT_STARTED | Frontend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.3 | — |
| UI-02 | Design System (Tailwind + Radix) | NOT_STARTED | Frontend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.3 | — |
| UI-03 | Global Command Bar + Shortcuts | NOT_STARTED | Frontend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.3 | — |
| UI-04 | Multi-panel Layout (Dock/Resize/Persist) | NOT_STARTED | Frontend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.3 | — |
| UI-05 | Watchlist Panel | NOT_STARTED | Frontend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.3 | — |
| UI-06 | Chart Panel (Lightweight Charts) | NOT_STARTED | Frontend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.3 | — |
| UI-07 | Settings/Config UI | NOT_STARTED | Frontend Engineer | PHASE1_ACCEPTANCE_CRITERIA.md §2.3 | — |

---

## Summary Statistics

| Status | Count | Percentage |
|--------|-------|------------|
| NOT_STARTED | 61 | 100% |
| PLANNED | 0 | 0% |
| IN_PROGRESS | 0 | 0% |
| IMPLEMENTED | 0 | 0% |
| TESTED | 0 | 0% |
| REVIEWED | 0 | 0% |
| VERIFIED | 0 | 0% |
| BLOCKED | 0 | 0% |
| **TOTAL** | **61** | **100%** |

---

## Phase 1 Gate Requirement

**All 61 features must reach `VERIFIED` status** for Phase 1 gate to pass.

---

## Update Protocol

- Updated by **Product Specification Agent** on every status change
- `VERIFIED` requires: Implementation + Tests + Review + Evidence recorded in `EVIDENCE_REGISTRY.json`
- Status changes logged in `CHANGELOG.md`
- Blocked features must have `BLOCKER` field with description and owner

---

## Blocker Tracking (Current)

| Feature | Blocker | Owner | Since |
|---------|---------|-------|-------|
| — | — | — | — |

---

*Last Updated: 2026-11-02 — Phase 1 Design Complete*