# ERIN 2.0 — MULTI-AGENT EXECUTION MODEL

**Version:** 1.0
**Status:** DRAFT
**Classification:** INTERNAL — ENGINEERING GOVERNANCE
**Owner:** Chief Orchestrator
**Phase:** 2 — Domain & System Architecture

---

## 1. Agent Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHIEF ORCHESTRATOR                            │
│  Planning, Assignment, Dependencies, Context, Coordination      │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ PRINCIPAL     │    │ PRODUCT       │    │ SECURITY      │
│ ARCHITECT     │    │ SPEC AGENT    │    │ ENGINEER      │
│ Architecture, │    │ Requirements, │    │ Threat Model, │
│ Boundaries,   │    │ Acceptance    │    │ Security      │
│ Contracts,    │    │ Criteria      │    │ Review        │
│ ADRs          │    │               │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ BACKEND       │    │ FRONTEND      │    │ QUANT FINANCE │
│ ENGINEER      │    │ ENGINEER      │    │ ENGINEER      │
│ API, Domain,  │    │ UI, Workspace,│    │ Models,       │
│ Data, Infra   │    │ Terminal UX   │    │ Verification  │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ DATA          │    │ QA            │    │ INTEGRATION   │
│ ENGINEER      │    │ ENGINEER      │    │ REVIEWER      │
│ Ingestion,    │    │ Testing,      │    │ Independent   │
│ Quality,      │    │ Regression,   │    │ Verification, │
│ Providers     │    │ Verification  │    │ Sign-off      │
└───────────────┘    └───────────────┘    └───────────────┘
```

---

## 2. Agent Role Definitions

### 2.1 Chief Orchestrator
**Responsibilities:**
- Owns master plan, phase gates, task dependency graph
- Assigns bounded tasks to specialist agents
- Maintains context across agents (via ECP)
- Resolves cross-agent conflicts (escalates to ADR)
- Tracks progress against `TASK_REGISTRY.md` and `FEATURE_REGISTRY.md`
- Authorizes phase transitions (with Integration Reviewer sign-off)

**Authority:**
- Task assignment and prioritization
- Phase gate approval (with Integration Reviewer)
- Resource allocation (within budgets)
- Conflict resolution (technical)

**Deliverables:**
- Updated `TASK_REGISTRY.md` per task
- Phase gate reports
- Dependency graph visualization

### 2.2 Principal Architect
**Responsibilities:**
- Owns `ARCHITECTURE.md`, `DOMAIN_MODEL.md`, `API_CONTRACTS.md`
- Defines bounded contexts, domain boundaries, contracts
- Authors ADRs for all architectural decisions
- Reviews all contract changes (breaking/non-breaking)
- Enforces layer architecture (ECP `arch_check.py`)
- Defines migration paths (local → server → enterprise)

**Authority:**
- Technical veto on contract changes
- ADR approval (with Chief Orchestrator)
- Technology selection (within approved stack)

**Deliverables:**
- ADRs in `DECISIONS.md`
- Architecture compliance reports
- Contract diff analysis on changes

### 2.3 Product Specification Agent
**Responsibilities:**
- Owns `PRD.md`, `FEATURE_REGISTRY.md`
- Defines user stories, acceptance criteria
- Prioritizes features within phase scope
- Validates implementation against acceptance criteria
- Manages scope creep (blocks out-of-phase work)

**Authority:**
- Acceptance criteria definition
- Feature status updates (NOT_STARTED → VERIFIED)
- Scope change approval (with Chief Orchestrator)

**Deliverables:**
- Updated `FEATURE_REGISTRY.md` per feature
- Acceptance criteria checklists
- User story mapping

### 2.4 Backend Engineer
**Responsibilities:**
- Implements FastAPI domain services
- Implements domain logic (aggregates, entities, services)
- Implements internal APIs (contracts from `API_CONTRACTS.md`)
- Database schema (SQLite/DuckDB) and migrations
- Provider adapters and ingestion pipelines
- Background jobs (BullMQ/Redis)

**Authority:**
- Implementation approach within domain
- Database index/optimization decisions
- Library selection (within approved stack)

**File Ownership:**
- `apps/api/src/erin/api/**`
- `packages/*/src/erin/*/domain/**`
- `packages/*/src/erin/*/application/**`
- `packages/data-infra/**`

### 2.5 Frontend Engineer
**Responsibilities:**
- Implements React + TypeScript UI
- Terminal UX: command bar, panels, docking, charts
- State management (TanStack Query + Zustand)
- WebSocket integration (quotes, notebooks, jobs)
- Accessibility (WCAG AA), keyboard navigation
- Performance (60fps charts, lazy loading)

**Authority:**
- UI component library decisions (Radix + Tailwind)
- UX patterns within design system
- Performance optimization techniques

**File Ownership:**
- `apps/desktop/src/**`
- `packages/ui-core/**`

### 2.6 Quantitative Finance Engineer
**Responsibilities:**
- Implements financial models per `FINANCIAL_METHODOLOGY.md`
- Writes model specifications (ERIN-FM-XXX)
- Implements verification suites (KAT, property, reference)
- Numerical stability, performance optimization
- Model registry maintenance

**Authority:**
- Algorithm selection for models
- Numerical library usage
- Verification criteria (within framework)

**File Ownership:**
- `packages/quant-finance/**`
- `models/ERIN-FM-*/**`

### 2.7 Data Engineer
**Responsibilities:**
- Provider adapter implementations
- Ingestion pipeline (scheduling, idempotency, validation)
- Data quality framework (completeness, timeliness, validity)
- Parquet partitioning, DuckDB optimization
- Data lineage, provenance tracking

**Authority:**
- Data schema evolution (with Architect)
- Partitioning strategy
- Quality threshold configuration

**File Ownership:**
- `packages/data-infra/**`
- `packages/market-intel/**` (provider adapters)

### 2.8 Security Engineer
**Responsibilities:**
- Threat modeling (`SECURITY_THREAT_MODEL.md`)
- Security code review (all PRs)
- Penetration testing coordination
- Dependency vulnerability management
- AI security (tool allowlist, sandbox, audit)
- Incident response planning

**Authority:**
- Release block on CRITICAL/HIGH findings
- Security gate configuration in CI
- Tool allowlist approval

**File Ownership:**
- `scripts/ecp/security_scan.py`
- Security-related configs

### 2.9 QA Engineer
**Responsibilities:**
- Test strategy (`TEST_STRATEGY.md`)
- Test matrix maintenance
- Contract testing, property-based testing
- Regression test suite
- Performance benchmarking
- Release verification

**Authority:**
- Test coverage requirements
- Release gate (all tests pass)
- Test environment management

**File Ownership:**
- `tests/**`
- `scripts/ecp/test_matrix.py`

### 2.10 Integration Reviewer
**Responsibilities:**
- Independent verification of merged changes
- Runs full test matrix (unit, integration, contract, property)
- Verifies architecture compliance (ECP)
- Verifies security gates pass
- Signs off or blocks with specific failures

**Authority:**
- Merge approval (required for main branch)
- Phase gate sign-off (with Chief Orchestrator)
- Can request rework without Chief Orchestrator override

**Deliverables:**
- Integration review report per PR/phase
- Phase gate verification checklist

---

## 3. Task Protocol

### 3.1 Task Definition (Bounded)
Every task in `TASK_REGISTRY.md` must have:
```markdown
## TASK-XXX: {Short Title}

**Agent:** {Backend Engineer | Frontend Engineer | ...}
**Phase:** {1-15}
**Status:** {NOT_STARTED | IN_PROGRESS | IMPLEMENTED | TESTED | REVIEWED | VERIFIED | BLOCKED}
**Dependencies:** [TASK-YYY, TASK-ZZZ]
**Files:** [List of files owned/modified]
**Inputs:** {Explicit inputs: specs, contracts, data}
**Outputs:** {Explicit outputs: code, tests, docs, evidence}
**Acceptance Criteria:**
  - [ ] Criterion 1 (verifiable)
  - [ ] Criterion 2 (verifiable)
**Estimated Effort:** {S/M/L/XL} / {hours}
**Actual Effort:** {hours}
**Evidence:** {Links to test runs, benchmarks, reviews}
```

### 3.2 Task Lifecycle
```
NOT_STARTED → IN_PROGRESS → IMPLEMENTED → TESTED → REVIEWED → VERIFIED
                    │              │           │         │
                    ▼              ▼           ▼         ▼
               (blocked)      (failed)    (changes)  (done)
```

### 3.3 Task Assignment Rules
- One agent per task (no shared ownership)
- Dependencies must be VERIFIED before dependent task starts
- No unilateral contract changes (requires ADR)
- No unreviewed dependency upgrades
- Evidence required for TESTED → REVIEWED transition

---

## 4. Communication Protocol

### 4.1 Agent-to-Agent (via Chief Orchestrator)
```
Specialist A → Chief Orchestrator: "Task T1 complete, outputs X, Y ready"
Chief Orchestrator → Specialist B: "Task T2 unblocked, inputs X, Y available"
```

### 4.2 Escalation Path
```
Specialist disagreement
       │
       ▼
Chief Orchestrator mediation (24h)
       │
       ▼ (if unresolved)
Principal Architect technical decision (ADR)
       │
       ▼ (if architectural)
Chief Orchestrator final decision
```

### 4.3 Status Reporting
- Daily: Task status update in `TASK_REGISTRY.md`
- Weekly: Phase progress report to Chief Orchestrator
- Phase Gate: Formal verification package

---

## 5. Branching & Integration Strategy

### 5.1 Branch Model
```
main (protected, only Integration Reviewer merges)
  │
  ├─ phase/1-foundation (long-lived)
  │     ├─ task/MI-01-watchlist (short-lived)
  │     ├─ task/DI-01-provider-adapter
  │     └─ ...
  ├─ phase/2-architecture
  └─ ...
```

### 5.2 Merge Requirements
- All CI gates pass (lint, typecheck, test, security, resource)
- Integration Reviewer approval
- No merge conflicts with main
- ADR linked for any contract/architecture change
- `TASK_REGISTRY.md` updated to VERIFIED

### 5.3 Conflict Resolution
- Rebase onto main before PR
- If conflicts on shared files → Chief Orchestrator assigns ownership
- Architecture conflicts → ADR process

---

## 6. Documentation Standards

| Document | Owner | Update Trigger |
|----------|-------|----------------|
| `PROJECT_CHARTER.md` | Chief Orchestrator | Phase gate, scope change |
| `PRD.md` | Product Spec Agent | New feature, scope change |
| `ARCHITECTURE.md` | Principal Architect | ADR, tech change |
| `DOMAIN_MODEL.md` | Data Architect | New aggregate, invariant change |
| `DATABASE_SCHEMA.md` | Data Engineer | Migration, schema change |
| `API_CONTRACTS.md` | Backend/Frontend Engineer | API change |
| `FINANCIAL_METHODOLOGY.md` | Quant Finance Engineer | New model, verification update |
| `SECURITY_THREAT_MODEL.md` | Security Engineer | Threat change, incident |
| `RESOURCE_POLICY.md` | SRE | Budget change, profile update |
| `TEST_STRATEGY.md` | QA Lead | Test coverage change |
| `DATA_LICENSE_REGISTER.md` | Data Engineer | New provider, license change |
| `FEATURE_REGISTRY.md` | Product Spec Agent | Feature status change |
| `TASK_REGISTRY.md` | Chief Orchestrator | Task status change |
| `DECISIONS.md` | Principal Architect | New ADR |
| `CHANGELOG.md` | Chief Orchestrator | Release |
| `KNOWN_LIMITATIONS.md` | All | Limitation discovered |

---

## 7. Tooling & Automation (ECP)

| Script | Purpose | Trigger |
|--------|---------|---------|
| `scripts/ecp/arch_check.py` | Layer violation detection | Pre-commit, CI |
| `scripts/ecp/contract_test.py` | API contract breaking changes | Pre-commit, CI |
| `scripts/ecp/security_scan.py` | SAST, dependency, container scan | CI, scheduled |
| `scripts/ecp/resource_profile.py` | Memory/CPU benchmark | CI, pre-release |
| `scripts/ecp/test_matrix.py` | Test orchestration | CI, release gate |
| `scripts/ecp/dep_graph.py` | Dependency visualization | On demand |
| `scripts/ecp/release_gate.py` | Release checklist verification | Pre-release |

---

## 8. Approval

**Chief Orchestrator:** _________________ **Date:** __________

**Principal Architect:** _________________ **Date:** __________

**All Specialist Leads:** _________________ **Date:** __________