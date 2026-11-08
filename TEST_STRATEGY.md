# ERIN 2.0 — TESTING AND VERIFICATION STRATEGY

**Version:** 1.0
**Status:** DRAFT
**Classification:** INTERNAL — QUALITY ASSURANCE
**Owner:** QA Lead
**Phase:** 2 — Domain & System Architecture

---

## 1. Testing Philosophy

**Principle:** *Coverage is a diagnostic metric, not proof of correctness.*

**Hierarchy of Assurance:**
1. **Financial Model Verification** (Highest) — Known-answer, property-based, reference validation
2. **Contract Testing** — API schema compatibility, internal service contracts
3. **Integration Testing** — Cross-context flows, database, external providers
4. **Unit Testing** — Domain logic, pure functions, edge cases
5. **Property-Based Testing** — Mathematical invariants, boundary behavior
6. **Regression Testing** — Golden master outputs, performance benchmarks
7. **UI Workflow Testing** — Critical user journeys, accessibility
8. **Security Testing** — SAST, DAST, dependency, penetration
9. **Performance Testing** — Resource budgets, latency targets
10. **Recovery Testing** — Backup/restore, migration, failover

---

## 2. Test Matrix

| Test Type | Framework | Scope | Target Coverage | Gate |
|-----------|-----------|-------|-----------------|------|
| **Unit (Python)** | pytest | Domain logic, pure functions, models | 90% domain packages | CI |
| **Unit (Rust)** | cargo test | Tauri commands, IPC, performance | 80% Rust code | CI |
| **Unit (TypeScript)** | Vitest | React components, hooks, utilities | 80% UI packages | CI |
| **Integration** | pytest + testcontainers | DB, API, provider adapters, WebSocket | Critical paths | CI |
| **Contract** | schemathesis + custom | OpenAPI 3.1, internal Pydantic schemas | All endpoints | CI + Pre-commit |
| **Property-Based** | Hypothesis (Python), fast-check (TS) | Financial models, mathematical invariants | 1000+ examples/model | CI |
| **Financial Verification** | Custom + pytest | KAT, reference validation, boundary | 100% models VERIFIED | Release |
| **Regression** | pytest + golden masters | Model outputs, API responses, UI snapshots | Zero unintended changes | Release |
| **E2E UI** | Playwright | Critical workflows (watchlist, valuation, notebook) | 10 core journeys | Release |
| **Accessibility** | axe-core + Playwright | WCAG AA | 0 violations | Release |
| **Security (SAST)** | bandit, semgrep, cargo-audit | Code, dependencies, containers | 0 CRITICAL/HIGH | CI |
| **Security (DAST)** | OWASP ZAP | Running application | 0 CRITICAL/HIGH | Weekly |
| **Performance** | pytest-benchmark, k6 | Resource budgets, latency targets | All benchmarks pass | Release |
| **Recovery** | Custom scripts | Backup/restore, migration, failover | Documented + tested | Release |

---

## 3. Financial Model Verification (Critical)

### 3.1 Verification Levels

| Level | Name | Requirements | Models |
|-------|------|--------------|--------|
| **L1** | **Known-Answer Tests (KAT)** | Analytical solutions, textbook examples, boundary conditions | ALL |
| **L2** | **Property-Based Tests** | Mathematical invariants (monotonicity, bounds, symmetries) | ALL |
| **L3** | **Reference Validation** | Independent library (QuantLib, Statsmodels, SciPy) | CORE |
| **L4** | **Boundary/Stress Tests** | Extreme inputs, numerical stability, convergence | ALL |
| **L5** | **Empirical Validation** | Backtesting, out-of-sample, regime analysis | RISK/QUANT |

### 3.2 Verification Template (Per Model)

```python
# models/ERIN-FM-BSM-001/test_verification.py
import pytest
from hypothesis import given, settings, strategies as st
import numpy as np
from scipy.stats import norm

from erin.quant_finance.models.bsm import bsm_price, bsm_greeks

class TestBSMKnownAnswer:
    """L1: Known-Answer Tests against analytical solutions"""
    
    def test_put_call_parity(self):
        S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.2
        call = bsm_price(S, K, T, r, sigma, option_type="call")
        put = bsm_price(S, K, T, r, sigma, option_type="put")
        parity = call - put - (S - K * np.exp(-r * T))
        assert abs(parity) < 1e-10
    
    def test_call_lower_bound(self):
        S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.2
        call = bsm_price(S, K, T, r, sigma, option_type="call")
        intrinsic = max(0, S - K * np.exp(-r * T))
        assert call >= intrinsic - 1e-12
    
    def test_hull_example_ch15(self):
        """Hull 10th Ed, Example 15.1: S=42, K=40, T=0.5, r=0.1, sigma=0.2"""
        result = bsm_price(42, 40, 0.5, 0.1, 0.2, option_type="call")
        assert abs(result - 4.76) < 0.01  # Hull: 4.76

class TestBSMProperties:
    """L2: Property-Based Tests (Hypothesis)"""
    
    @given(
        S=st.floats(1, 10000),
        K=st.floats(1, 10000),
        T=st.floats(1/365, 10),
        r=st.floats(-0.05, 0.20),
        sigma=st.floats(0.001, 2.0),
        q=st.floats(0, 0.20)
    )
    @settings(max_examples=2000, deadline=10000)
    def test_monotonicity_in_volatility(self, S, K, T, r, sigma, q):
        """Option price increases with volatility"""
        price_low = bsm_price(S, K, T, r, sigma * 0.5, q=q)
        price_high = bsm_price(S, K, T, r, sigma * 1.5, q=q)
        assert price_high >= price_low - 1e-12
    
    @given(
        S=st.floats(1, 10000),
        K=st.floats(1, 10000),
        T=st.floats(1/365, 10),
        r=st.floats(-0.05, 0.20),
        sigma=st.floats(0.001, 2.0)
    )
    @settings(max_examples=1000)
    def test_greeks_consistency(self, S, K, T, r, sigma):
        """Delta = dPrice/dS (finite difference)"""
        price = bsm_price(S, K, T, r, sigma)
        price_up = bsm_price(S * 1.0001, K, T, r, sigma)
        delta_fd = (price_up - price) / (S * 0.0001)
        greeks = bsm_greeks(S, K, T, r, sigma)
        assert abs(greeks.delta - delta_fd) < 1e-4

class TestBSMReference:
    """L3: Reference Validation against QuantLib"""
    
    @pytest.mark.reference
    def test_quantlib_comparison(self):
        import QuantLib as ql
        # Compare 50 random scenarios
        for _ in range(50):
            S = np.random.uniform(10, 500)
            K = np.random.uniform(10, 500)
            T = np.random.uniform(0.01, 5)
            r = np.random.uniform(-0.02, 0.15)
            sigma = np.random.uniform(0.05, 1.0)
            
            our_price = bsm_price(S, K, T, r, sigma)
            ql_price = ql_bsm_price(S, K, T, r, sigma)  # Helper
            assert abs(our_price - ql_price) / ql_price < 1e-6

class TestBSMBoundary:
    """L4: Boundary Tests"""
    
    def test_t_near_zero(self):
        """T → 0 converges to intrinsic"""
        S, K, r, sigma = 100, 100, 0.05, 0.2
        for T in [1e-6, 1e-5, 1e-4, 1e-3]:
            call = bsm_price(S, K, T, r, sigma, option_type="call")
            intrinsic = max(0, S - K)
            assert abs(call - intrinsic) < 1e-4
    
    def test_sigma_near_zero(self):
        """σ → 0 converges to deterministic"""
        S, K, T, r = 100, 100, 1.0, 0.05
        for sigma in [1e-6, 1e-5, 1e-4, 1e-3]:
            call = bsm_price(S, K, T, r, sigma)
            forward = S * np.exp(r * T)
            intrinsic = max(0, forward - K) * np.exp(-r * T)
            assert abs(call - intrinsic) < 1e-4

class TestBSMRegression:
    """L5: Regression - Golden Master"""
    
    def test_golden_master_outputs(self):
        """Compare against stored golden master JSON"""
        import json
        with open("models/ERIN-FM-BSM-001/golden_master.json") as f:
            golden = json.load(f)
        
        for case in golden["test_cases"]:
            result = bsm_price(**case["inputs"])
            expected = case["outputs"]["price"]
            assert abs(result - expected) < 1e-10, f"Case {case['id']}: {result} != {expected}"
```

---

## 4. Test Data Management

### 4.1 Deterministic Fixtures
```python
# tests/fixtures/market_data.py
import pytest
from decimal import Decimal
from datetime import datetime, date

@pytest.fixture(scope="session")
def sample_quotes():
    """Deterministic quote fixtures for testing"""
    return [
        Quote(
            figi="BBG000B9XRY4",
            symbol="AAPL.US",
            bid=Decimal("150.01"),
            ask=Decimal("150.02"),
            last=Decimal("150.015"),
            timestamp=datetime(2026, 6, 15, 10, 30, 0),
            source=ProviderId.OPENBB
        ),
        # ... more fixtures
    ]

@pytest.fixture(scope="session")
def sample_portfolio():
    return Portfolio(
        id="pf_test_001",
        positions={
            "BBG000B9XRY4": Position(figi="BBG000B9XRY4", quantity=100, avg_cost=145.0),
            "BBG000BPH459": Position(figi="BBG000BPH459", quantity=50, avg_cost=380.0),
        },
        cash=Decimal("10000.00")
    )
```

### 4.2 Test Data Generation
- **Synthetic:** Property-based generators for mathematical tests
- **Historical Snapshots:** Versioned Parquet files in `tests/data/` (git-lfs)
- **Provider Mocks:** Recorded HTTP interactions (pytest-httpx / vcr.py)

---

## 5. CI/CD Test Pipeline

```yaml
# .github/workflows/test.yml
jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Python Unit Tests
        run: pytest tests/unit -x --tb=short -q
      - name: Rust Unit Tests
        run: cargo test --workspace
      - name: TypeScript Unit Tests
        run: pnpm vitest run
  
  integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: {POSTGRES_PASSWORD: test}
      redis:
        image: redis:7
    steps:
      - uses: actions/checkout@v4
      - name: Integration Tests
        run: pytest tests/integration -x --tb=short
  
  contracts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Contract Tests
        run: python -m scripts.ecp.contract_test
  
  property:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Property-Based Tests
        run: pytest tests/property -x --tb=short -q
  
  financial-verification:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Model Verification Suite
        run: pytest models/ -m "verification" -x --tb=long
  
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Tauri App
        run: pnpm tauri build
      - name: E2E Tests
        run: pnpm playwright test
  
  performance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Benchmarks
        run: pytest tests/benchmarks --benchmark-only
      - name: Resource Profile
        run: python -m scripts.ecp.resource_profile --profile ci
  
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Security Scan
        run: python -m scripts.ecp.security_scan
  
  release-gate:
    needs: [unit, integration, contracts, property, financial-verification, e2e, performance, security]
    if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    steps:
      - name: Release Gate
        run: python -m scripts.ecp.release_gate
```

---

## 6. Test Environment Management

| Environment | Purpose | Data | Reset |
|-------------|---------|------|-------|
| **Local Dev** | Developer iteration | Synthetic + small real | Manual |
| **CI** | Automated verification | Synthetic + fixtures | Per job |
| **Staging** | Pre-release validation | Production-like (anonymized) | Nightly |
| **Production** | Live | Real | N/A |

---

## 7. Flaky Test Policy

- **Zero Tolerance:** Flaky tests block merge
- **Quarantine:** Move to `tests/quarantine/` with issue reference
- **Fix Timeline:** 5 business days or removal
- **Root Cause:** Document in issue (timing, state, external dependency)

---

## 8. Approval

**QA Lead:** _________________ **Date:** __________

**Principal Architect:** _________________ **Date:** __________

**Chief Orchestrator:** _________________ **Date:** __________