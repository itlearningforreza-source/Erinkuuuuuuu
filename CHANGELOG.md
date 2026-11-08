# ERIN 2.0 — CHANGELOG

**Version:** 1.0.0
**Status:** ACTIVE
**Classification:** INTERNAL — RELEASE HISTORY
**Owner:** Chief Orchestrator

---

## Format

Based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### Categories
- **Added** — New features
- **Changed** — Changes in existing functionality
- **Deprecated** — Soon-to-be removed features
- **Removed** — Removed features
- **Fixed** — Bug fixes
- **Security** — Vulnerability fixes

---

## [Unreleased] — Development

### Added
- Initial project charter and governance documents (16 core docs)
- Repository structure and monorepo configuration
- Architecture Decision Records (ADR-001 through ADR-015)

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

---

## [0.1.0] — 2026-11-02 — Phase 1 Design Complete

### Added
- `PROJECT_CHARTER.md` — Mission, scope, success criteria, governance
- `PRD.md` — Product requirements with 50+ user stories and acceptance criteria
- `ARCHITECTURE.md` — System architecture, bounded contexts, tech stack, deployment
- `DOMAIN_MODEL.md` — 18 domain aggregates, entities, value objects, events
- `DATABASE_SCHEMA.md` — SQLite/DuckDB/Parquet schemas, migrations, retention
- `API_CONTRACTS.md` — External + Internal API specs (OpenAPI 3.1)
- `FINANCIAL_METHODOLOGY.md` — Model governance framework, 12 Phase 1 models
- `SECURITY_THREAT_MODEL.md` — STRIDE analysis, AI security, desktop hardening
- `MULTI_AGENT_EXECUTION.md` — 10 agent roles, task protocol, communication
- `ECP_SPECIFICATION.md` — 12 automated governance components
- `RESOURCE_POLICY.md` — Memory/CPU/storage budgets, profiles, benchmarks
- `TEST_STRATEGY.md` — 10-level test matrix, financial verification standards
- `DATA_LICENSE_REGISTER.md` — 20+ providers, compliance matrix
- `FEATURE_DEPENDENCY_GRAPH.md` — Mermaid graph, critical path, sprint plan
- `IMPLEMENTATION_ROADMAP.md` — 15 phases, 38 weeks, resource allocation
- `PHASE1_ACCEPTANCE_CRITERIA.md` — 200+ verifiable criteria for Phase 1 gate
- `DECISIONS.md` — 15 ADRs documenting all key technical decisions

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

---

## Release Template (Future)

```markdown
## [X.Y.Z] — YYYY-MM-DD — {Phase Name}

### Added
- Feature description [#task-id]

### Changed
- Change description [#task-id]

### Deprecated
- Deprecated feature [#task-id]

### Removed
- Removed feature [#task-id]

### Fixed
- Bug fix description [#task-id]

### Security
- Vulnerability fix [CVE-XXXX-XXXX] [#task-id]
```

---

## Versioning Policy

| Version | When |
|---------|------|
| **MAJOR** | Breaking API changes, architecture overhaul, security model change |
| **MINOR** | New domain, significant feature, backward-compatible API additions |
| **PATCH** | Bug fixes, performance improvements, documentation, non-breaking changes |

### Pre-release Tags
- `alpha` — Internal development, unstable
- `beta` — Feature complete, testing
- `rc` — Release candidate, release gate pending

---

## Git Tagging

```bash
# Release
git tag -s v1.0.0 -m "ERIN 1.0.0 — Production Release"

# Pre-release
git tag -s v0.5.0-alpha.1 -m "Phase 3 Complete — Dev Infrastructure"
git tag -s v0.8.0-beta.1 -m "Phase 8 Complete — Portfolio & Risk"
git tag -s v1.0.0-rc.1 -m "Release Candidate 1"
```

---

## Changelog Maintenance

- Updated by Chief Orchestrator at each phase gate
- Sourced from `TASK_REGISTRY.md` (VERIFIED tasks)
- Linked to GitHub/GitLab issues and merge requests
- Included in release artifacts