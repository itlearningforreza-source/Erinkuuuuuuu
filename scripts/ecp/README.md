# ERIN Engineering Control Plane (ECP) Scripts

This directory contains the automated governance scripts for the ERIN project.

## Scripts

| Script | Purpose | CI Stage |
|--------|---------|----------|
| `arch_check.py` | Architecture layer violation detection | Pre-commit, CI |
| `contract_test.py` | API contract breaking change detection | Pre-commit, CI |
| `test_matrix.py` | Test suite orchestration | CI |
| `security_scan.py` | SAST, dependency, container, secrets scanning | CI |
| `resource_profile.py` | Memory/CPU profiling vs budgets | CI, Release |
| `evidence_reg.py` | Immutable test/benchmark evidence registry | Post-test |
| `debt_score.py` | Technical debt quantification | Weekly |
| `release_gate.py` | Release checklist verification | Pre-release |
| `dep_graph.py` | Dependency visualization | On-demand |
| `repo_intel.py` | Repository intelligence (AST, dead code) | CI |
| `task_sync.py` | Task registry sync with GitHub Projects | Scheduled |
| `context_mgr.py` | Agent context persistence | Agent transitions |

## Usage

```bash
# Run all checks locally
python -m scripts.ecp.arch_check
python -m scripts.ecp.contract_test
python -m scripts.ecp.security_scan --fast
python -m scripts.ecp.resource_profile --profile standard
python -m scripts.ecp.test_matrix --suites unit integration contract

# Full test matrix
python -m scripts.ecp.test_matrix --suites all --fail-fast

# Release gate
python -m scripts.ecp.release_gate
```

## Configuration

Scripts read configuration from:
- `scripts/ecp/configs/arch_rules.yaml`
- `scripts/ecp/configs/security_thresholds.yaml`
- `scripts/ecp/configs/resource_budgets.yaml`
- `scripts/ecp/configs/test_matrix.yaml`

## Output

All scripts produce JSON output in `artifacts/` directory:
- `arch_check.json`
- `contract_diff.json`
- `security_report.json`
- `resource_profile.json`
- `test_results.xml`
- `benchmarks.json`
- `sbom.json`