# ERIN 2.0 — ENGINEERING CONTROL PLANE (ECP) SPECIFICATION

**Version:** 1.0
**Status:** DRAFT
**Classification:** INTERNAL — ENGINEERING GOVERNANCE
**Owner:** Chief Orchestrator
**Phase:** 2 — Domain & System Architecture

---

## 1. ECP Overview

The **ERIN Engineering Control Plane (ECP)** is an automated governance layer that enforces architectural compliance, security gates, resource budgets, and evidence-based verification throughout the development lifecycle. It operates as a set of CLI tools integrated into CI/CD, pre-commit hooks, and release pipelines.

**Core Principle:** *Automate what can be automated; make violations visible and blockable.*

---

## 2. ECP Components

| Component | Script | Purpose | Trigger |
|-----------|--------|---------|---------|
| **Repository Intelligence** | `repo_intel.py` | AST analysis, dead code, complexity, dependency graph | CI, on-demand |
| **Task Management** | `task_sync.py` | Sync `TASK_REGISTRY.md` ↔ GitHub Projects/Linear | Webhook, scheduled |
| **Dependency Mapping** | `dep_graph.py` | Import analysis (Python/Rust/TS), cycle detection | CI, on-demand |
| **Context Management** | `context_mgr.py` | Agent context persistence, handoff | Agent transitions |
| **Architecture Compliance** | `arch_check.py` | Layer violations, contract drift, boundary enforcement | Pre-commit, CI |
| **Contract Validation** | `contract_test.py` | OpenAPI/Pydantic schema breaking change detection | Pre-commit, CI |
| **Test Orchestration** | `test_matrix.py` | Unit/Integration/Contract/Property/Regression matrix | CI, release gate |
| **Security Gates** | `security_scan.py` | SAST, dependency, container, secrets scan | CI, scheduled |
| **Resource Monitoring** | `resource_profile.py` | Memory/CPU benchmarks vs budgets | CI, pre-release |
| **Evidence Registry** | `evidence_reg.py` | Immutable record of test runs, benchmarks, reviews | Post-test, release |
| **Technical Debt Tracking** | `debt_score.py` | Quantified debt with remediation owners | Weekly, release |
| **Release Control** | `release_gate.py` | Automated release checklist verification | Pre-release |

---

## 3. Component Specifications

### 3.1 Architecture Compliance (`arch_check.py`)

**Rules Enforced:**
1. **Layer Isolation:** No imports from higher layers
   - UI → API → Domain → Infrastructure (allowed)
   - Reverse: BLOCKED
2. **Bounded Context Boundaries:** No cross-context domain imports
   - Use internal HTTP APIs or shared-types only
3. **Public API Surface:** Only `__init__.py` exports allowed
4. **No Circular Dependencies:** Between packages

**Implementation:**
```python
# scripts/ecp/arch_check.py
import ast
import sys
from pathlib import Path

LAYER_ORDER = [
    "apps.desktop",           # UI Layer
    "apps.api",               # API Layer
    "packages.market_intel",  # Domain Layer
    "packages.data_infra",
    "packages.equity_research",
    "packages.quant_finance",
    "packages.portfolio_risk",
    "packages.fixed_income",
    "packages.derivatives",
    "packages.macro_intel",
    "packages.news_intel",
    "packages.workspace",
    "packages.ai_intelligence",
    "packages.governance",
    "packages.shared_types",  # Shared Kernel
    "packages.data_core",     # Infrastructure Layer
    "packages.quant_core",
    "packages.ai_core",
]

def check_imports(file_path: Path) -> list[Violation]:
    tree = ast.parse(file_path.read_text())
    current_layer = determine_layer(file_path)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            target_layer = determine_layer_from_module(node.module)
            if target_layer and LAYER_ORDER.index(target_layer) > LAYER_ORDER.index(current_layer):
                violations.append(Violation(
                    file=file_path,
                    line=node.lineno,
                    message=f"Illegal import: {current_layer} → {target_layer} (downward)"
                ))
    return violations
```

**CI Gate:** Fail on any violation.

### 3.2 Contract Validation (`contract_test.py`)

**Checks:**
1. **Request/Response Models:** No required field removal, no type narrowing
2. **Enum Values:** No removal, additions allowed
3. **Endpoint Signatures:** No parameter removal, no response shape breaking
4. **Internal APIs:** Same rules for `/api/v1/internal/`

**Implementation:**
```python
# scripts/ecp/contract_test.py
from pydantic import BaseModel
import json

def check_breaking_changes(old_schema: dict, new_schema: dict) -> list[BreakingChange]:
    changes = []
    # Check required fields
    old_required = set(old_schema.get("required", []))
    new_required = set(new_schema.get("required", []))
    removed_required = old_required - new_required
    if removed_required:
        changes.append(BreakingChange(
            type="REQUIRED_FIELD_REMOVED",
            fields=list(removed_required)
        ))
    # Check properties
    old_props = old_schema.get("properties", {})
    new_props = new_schema.get("properties", {})
    for prop_name, old_prop in old_props.items():
        if prop_name not in new_props:
            changes.append(BreakingChange(type="PROPERTY_REMOVED", field=prop_name))
        else:
            new_prop = new_props[prop_name]
            if not is_compatible(old_prop, new_prop):
                changes.append(BreakingChange(type="TYPE_NARROWED", field=prop_name))
    return changes
```

**CI Gate:** Fail on breaking changes without ADR.

### 3.3 Security Scan (`security_scan.py`)

**Scanners:**
| Scanner | Target | Severity Threshold |
|---------|--------|-------------------|
| `bandit` | Python code | HIGH |
| `cargo audit` | Rust dependencies | HIGH |
| `npm audit` | Node dependencies | HIGH |
| `pip-audit` | Python dependencies | HIGH |
| `trivy` | Container images | HIGH |
| `semgrep` | Custom rules (secrets, crypto) | MEDIUM |
| `syft` + `grype` | SBOM + vuln scan | CRITICAL |

**Implementation:**
```python
# scripts/ecp/security_scan.py
import subprocess
import json
from dataclasses import dataclass

@dataclass
class SecurityFinding:
    scanner: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    file: str
    line: int
    rule: str
    message: str
    cve: str | None

def run_all_scanners() -> list[SecurityFinding]:
    findings = []
    # Bandit
    result = subprocess.run(["bandit", "-r", ".", "-f", "json"], capture_output=True)
    findings.extend(parse_bandit(json.loads(result.stdout)))
    # Cargo audit
    result = subprocess.run(["cargo", "audit", "--json"], capture_output=True)
    findings.extend(parse_cargo_audit(json.loads(result.stdout)))
    # ... other scanners
    return findings

def gate(findings: list[SecurityFinding]) -> bool:
    critical_high = [f for f in findings if f.severity in ("CRITICAL", "HIGH")]
    if critical_high:
        print("SECURITY GATE FAILED:", len(critical_high), "critical/high findings")
        for f in critical_high:
            print(f"  {f.scanner}: {f.file}:{f.line} - {f.message}")
        return False
    return True
```

### 3.4 Resource Profiling (`resource_profile.py`)

**Budgets (from `RESOURCE_POLICY.md`):**
```python
# scripts/ecp/resource_profile.py
BUDGETS = {
    "minimal": {"peak_rss_mb": 3500, "cpu_percent": 50},
    "standard": {"peak_rss_mb": 6000, "cpu_percent": 80},
    "ci": {"peak_rss_mb": 4000, "cpu_percent": 100},
}

def profile_profile(profile_name: str) -> ProfileResult:
    import psutil
    import subprocess
    import time
    
    # Start application with profile config
    proc = subprocess.Popen([...], env={...})
    peak_rss = 0
    peak_cpu = 0
    
    while proc.poll() is None:
        try:
            p = psutil.Process(proc.pid)
            peak_rss = max(peak_rss, p.memory_info().rss)
            peak_cpu = max(peak_cpu, p.cpu_percent())
            time.sleep(0.1)
        except psutil.NoSuchProcess:
            break
    
    budget = BUDGETS[profile_name]
    passed = peak_rss <= budget["peak_rss_mb"] * 1024 * 1024
    
    return ProfileResult(
        profile=profile_name,
        peak_rss_mb=peak_rss / 1024 / 1024,
        peak_cpu_percent=peak_cpu,
        budget=budget,
        passed=passed
    )
```

### 3.5 Evidence Registry (`evidence_reg.py`)

**Schema:**
```json
{
  "evidence_id": "uuid",
  "timestamp": "2026-11-02T10:30:00Z",
  "type": "TEST_RUN | BENCHMARK | SECURITY_SCAN | REVIEW | DEPLOYMENT",
  "component": "package/module",
  "trigger": "CI | MANUAL | SCHEDULED",
  "status": "PASS | FAIL | PARTIAL",
  "artifacts": [
    {"name": "test_output.xml", "path": "artifacts/test_output.xml", "hash": "sha256..."},
    {"name": "benchmark.json", "path": "artifacts/benchmark.json", "hash": "..."}
  ],
  "metrics": {
    "tests_passed": 1234,
    "tests_failed": 0,
    "coverage_percent": 87.5,
    "peak_rss_mb": 5200,
    "security_findings_critical": 0
  },
  "signed_by": "agent-id",
  "signature": "ed25519..."
}
```

**Storage:** Append-only JSONL in `.erin/evidence/evidence.jsonl` + Git commit hash reference.

### 3.6 Release Gate (`release_gate.py`)

**Checklist (All Must Pass):**
```python
RELEASE_GATES = [
    ("Architecture Compliance", "arch_check.py", "zero violations"),
    ("Contract Compatibility", "contract_test.py", "zero breaking changes"),
    ("Security Scan", "security_scan.py", "zero critical/high"),
    ("Resource Profile", "resource_profile.py", "within budget"),
    ("Test Matrix", "test_matrix.py", "100% pass"),
    ("Financial Model Verification", "pytest models/", "all VERIFIED"),
    ("Documentation Complete", "docs_check.py", "all required docs exist"),
    ("SBOM Generated", "syft", "cyclonedx-json"),
    ("Signed Build", "cosign", "verified"),
    ("Changelog Updated", "changelog_check.py", "version matches"),
]
```

---

## 4. ECP Directory Structure

```
scripts/ecp/
├── __init__.py
├── repo_intel.py
├── task_sync.py
├── dep_graph.py
├── context_mgr.py
├── arch_check.py
├── contract_test.py
├── test_matrix.py
├── security_scan.py
├── resource_profile.py
├── evidence_reg.py
├── debt_score.py
├── release_gate.py
├── utils/
│   ├── git.py
│   ├── pydantic_diff.py
│   ├── ast_utils.py
│   └── hash_chain.py
└── configs/
    ├── arch_rules.yaml
    ├── security_thresholds.yaml
    ├── resource_budgets.yaml
    └── test_matrix.yaml
```

---

## 5. CI/CD Integration

### 5.1 GitHub Actions Workflow (`.github/workflows/ecp.yml`)
```yaml
name: ECP Gates
on: [push, pull_request]
jobs:
  architecture:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Architecture Check
        run: python -m scripts.ecp.arch_check
  contracts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check Contract Compatibility
        run: python -m scripts.ecp.contract_test
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Security Scan
        run: python -m scripts.ecp.security_scan
  resources:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Resource Profile (standard)
        run: python -m scripts.ecp.resource_profile --profile standard
  test-matrix:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Full Test Matrix
        run: python -m scripts.ecp.test_matrix
  release-gate:
    needs: [architecture, contracts, security, resources, test-matrix]
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Release Gate
        run: python -m scripts.ecp.release_gate
```

### 5.2 Pre-commit Hooks (`.pre-commit-config.yaml`)
```yaml
repos:
  - repo: local
    hooks:
      - id: ecp-arch-check
        name: ECP Architecture Check
        entry: python -m scripts.ecp.arch_check
        language: system
        files: \.(py|ts|rs)$
      - id: ecp-contract-check
        name: ECP Contract Check
        entry: python -m scripts.ecp.contract_test
        language: system
        files: \.(py|yaml|json)$
      - id: ecp-security-scan
        name: ECP Security Scan (fast)
        entry: python -m scripts.ecp.security_scan --fast
        language: system
        files: \.(py|rs|toml|json)$
```

---

## 6. Agent Context Management

```python
# scripts/ecp/context_mgr.py
# Each agent gets a context directory: .ecp/context/{agent_role}/
# Contains:
# - current_task.md (assigned task with acceptance criteria)
# - relevant_files.txt (file ownership)
# - decisions.md (ADRs relevant to agent)
# - blockers.md (current blockers)
# - handoff.md (for next agent)

def save_context(agent_role: str, context: AgentContext) -> None:
    ctx_dir = Path(f".ecp/context/{agent_role}")
    ctx_dir.mkdir(parents=True, exist_ok=True)
    (ctx_dir / "current_task.md").write_text(context.current_task)
    (ctx_dir / "relevant_files.txt").write_text("\n".join(context.files))
    # ...

def load_context(agent_role: str) -> AgentContext:
    # Load and return context for agent resumption
    ...
```

---

## 7. Approval

**Chief Orchestrator:** _________________ **Date:** __________

**Principal Architect:** _________________ **Date:** __________

**Security Engineer:** _________________ **Date:** __________