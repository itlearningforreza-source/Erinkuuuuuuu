# ERIN 2.0 — FINANCIAL METHODOLOGY CATALOG

**Version:** 1.0
**Status:** DRAFT
**Classification:** INTERNAL — QUANTITATIVE METHODOLOGY
**Owner:** Quantitative Finance Engineer
**Phase:** 2 — Domain & System Architecture

---

## 1. Model Governance Framework

Every financial model in ERIN must conform to **ERIN-FMS-001** specification template:

### 1.1 Specification Template (Mandatory Fields)

```markdown
# Model Specification: {MODEL_ID}

## 1. Identity
- **Name:** {Descriptive name, e.g., "Black-Scholes-Merton European Option Pricing"}
- **Version:** {Semantic version, e.g., "1.0.0"}
- **Owner:** {Quantitative Finance Engineer}
- **Status:** {DRAFT | IN_REVIEW | VERIFIED | DEPRECATED | SUPERSEDED}
- **Classification:** {PUBLIC | INTERNAL | RESTRICTED}

## 2. Theoretical Foundation
- **Primary Reference:** {Textbook/paper with edition/DOI, e.g., "Hull, Options, Futures, and Other Derivatives, 10th Ed., Ch. 15"}
- **Original Paper:** {DOI/URL if applicable}
- **Assumptions:** {Explicit list: log-normal returns, constant vol, no dividends, frictionless markets, etc.}
- **Domain of Validity:** {e.g., "European equity/index options, non-dividend paying, constant volatility"}

## 3. Mathematical Specification
### 3.1 Equations
{LaTeX-rendered equations with all variables defined}

### 3.2 Inputs
| Variable | Symbol | Type | Units | Convention | Required |
|----------|--------|------|-------|------------|----------|
| Spot Price | S | Decimal | Currency | Mid-price | Yes |
| Strike | K | Decimal | Currency | Same as S | Yes |
| Time to Expiry | T | Decimal | Years | ACT/365 | Yes |
| Risk-free Rate | r | Decimal | Annual % | Continuous compounding | Yes |
| Volatility | σ | Decimal | Annual % | Implied/historical | Yes |
| Dividend Yield | q | Decimal | Annual % | Continuous | No (default 0) |

### 3.3 Outputs
| Output | Symbol | Type | Units | Description |
|--------|--------|------|-------|-------------|
| Call Price | C | Decimal | Currency | Theoretical fair value |
| Put Price | P | Decimal | Currency | Theoretical fair value |
| Delta | Δ | Decimal | - | ∂V/∂S |
| Gamma | Γ | Decimal | 1/Currency | ∂²V/∂S² |
| Vega | ν | Decimal | Currency/% | ∂V/∂σ |
| Theta | θ | Decimal | Currency/Day | ∂V/∂t |
| Rho | ρ | Decimal | Currency/% | ∂V/∂r |

### 3.4 Conventions
- **Day Count:** ACT/365 for equities, ACT/ACT for govt bonds
- **Compounding:** Continuous for rates, discrete for dividends
- **Volatility:** Annualized, log-normal
- **Time:** T = (expiry - valuation_date) / 365

## 4. Numerical Implementation
- **Algorithm:** {Closed-form / Binomial (CRR, N=100) / Monte Carlo (N=100k, antithetic) / Finite Difference}
- **Libraries:** {SciPy `norm.cdf`, custom implementation, QuantLib reference}
- **Edge Cases:** {T→0, σ→0, deep ITM/OTM, strike=0}
- **Complexity:** {O(1) / O(N) / O(N×M)}
- **Precision Target:** Relative error < 1e-10 vs analytical (where available)

## 5. Verification Suite (MANDATORY)

### 5.1 Known-Answer Tests (KAT)
| Test ID | Description | Expected | Tolerance |
|---------|-------------|----------|-----------|
| KAT-001 | Put-Call Parity: C - P = S·e^(-qT) - K·e^(-rT) | 0 | 1e-10 |
| KAT-002 | Call Lower Bound: C ≥ max(0, S·e^(-qT) - K·e^(-rT)) | ≥ 0 | 1e-12 |
| KAT-003 | Put Lower Bound: P ≥ max(0, K·e^(-rT) - S·e^(-qT)) | ≥ 0 | 1e-12 |
| KAT-004 | Call Upper Bound: C ≤ S·e^(-qT) | ≤ S·e^(-qT) | 1e-12 |
| KAT-005 | Put Upper Bound: P ≤ K·e^(-rT) | ≤ K·e^(-rT) | 1e-12 |
| KAT-006 | Delta Call: 0 ≤ Δ_C ≤ e^(-qT) | In range | 1e-12 |
| KAT-007 | Delta Put: -e^(-qT) ≤ Δ_P ≤ 0 | In range | 1e-12 |
| KAT-008 | Gamma ≥ 0 | ≥ 0 | 1e-12 |
| KAT-009 | Vega ≥ 0 | ≥ 0 | 1e-12 |

### 5.2 Reference Validation
| Reference | Version | Test Cases | Status |
|-----------|---------|------------|--------|
| QuantLib | 1.38 | 50+ scenarios | PENDING |
| Hull Examples | 10th Ed. | Ch. 15 examples | PENDING |
| Bloomberg OVML | - | If licensed | N/A |

### 5.3 Boundary Tests
| Test | Input Range | Expected Behavior |
|------|-------------|-------------------|
| BT-001 | T ∈ [1e-6, 1e-3] | Converges to intrinsic value |
| BT-002 | σ ∈ [1e-6, 0.01] | Converges to deterministic |
| BT-003 | S/K ∈ [0.01, 100] | No overflow, monotonic |
| BT-004 | r ∈ [-0.05, 0.20] | Valid for negative rates |
| BT-005 | q ∈ [0, 0.20] | Dividend adjustment correct |

### 5.4 Property-Based Tests (Hypothesis)
```python
@given(
    S=st.floats(1, 10000),
    K=st.floats(1, 10000),
    T=st.floats(1/365, 10),
    r=st.floats(-0.05, 0.20),
    sigma=st.floats(0.001, 2.0),
    q=st.floats(0, 0.20)
)
@settings(max_examples=1000, deadline=5000)
def test_bsm_properties(S, K, T, r, sigma, q):
    result = bsm_price(S, K, T, r, sigma, q)
    # Put-call parity
    assert abs(result.call - result.put - (S*exp(-q*T) - K*exp(-r*T))) < 1e-10
    # Bounds
    assert result.call >= max(0, S*exp(-q*T) - K*exp(-r*T)) - 1e-12
    assert result.put >= max(0, K*exp(-r*T) - S*exp(-q*T)) - 1e-12
    # Greeks
    assert 0 <= result.delta_call <= exp(-q*T) + 1e-12
    assert -exp(-q*T) - 1e-12 <= result.delta_put <= 0
    assert result.gamma >= -1e-12
    assert result.vega >= -1e-12
```

### 5.5 Performance Benchmarks
| Metric | Target | Measurement |
|--------|--------|-------------|
| Single Price | < 0.1 ms | 1M iterations, median |
| Greeks (all) | < 0.2 ms | 1M iterations, median |
| Batch (1000) | < 50 ms | Vectorized NumPy |
| Memory | < 10 MB | Per 100k paths |

## 6. Limitations & Disclosures
- **Known Biases:** {Vol smile ignored, early exercise not handled, constant vol assumption}
- **Data Requirements:** {Implied vol surface or constant vol, risk-free curve, dividend schedule}
- **Regulatory:** {Not approved for regulatory capital, not a substitute for official pricing}
- **Model Risk:** {Document known failure modes: high vol, long dated, discontinuous payoffs}

## 7. Reproducibility Requirements
- **Random Seed:** Fixed for Monte Carlo (exposed as parameter)
- **Version Pinning:** All dependencies in `pyproject.toml` with exact versions
- **Environment:** Python 3.12, NumPy 2.0, SciPy 1.14
- **Output Hash:** SHA256 of result JSON for golden master comparison
```

---

## 2. Phase 1 Model Catalog

| Model ID | Name | Type | Verification Target | Status |
|----------|------|------|---------------------|--------|
| `ERIN-FM-DCF-001` | DCF (FCFF, 2-Stage) | Valuation | Damodaran dataset, known-answer | PLANNED |
| `ERIN-FM-WACC-001` | WACC (CAPM + Build-up) | Valuation | Industry benchmarks, textbook | PLANNED |
| `ERIN-FM-DDM-001` | DDM (Gordon, H-Model) | Valuation | Textbook examples, boundary | PLANNED |
| `ERIN-FM-VAR-HIST-001` | Historical VaR (HS) | Risk | Kupiec/Christoffersen backtest | PLANNED |
| `ERIN-FM-VAR-PARAM-001` | Parametric VaR (Delta-Normal) | Risk | Analytical normal quantile | PLANNED |
| `ERIN-FM-ES-001` | Expected Shortfall (Historical) | Risk | Acerbi-Szekely backtest | PLANNED |
| `ERIN-FM-BSM-001` | Black-Scholes-Merton European | Derivatives | Put-call parity, Greeks, boundaries | PLANNED |
| `ERIN-FM-BINOM-001` | Cox-Ross-Rubinstein Binomial | Derivatives | Convergence to BSM, early exercise | PLANNED |
| `ERIN-FM-GBM-001` | Geometric Brownian Motion | Quant | Moment matching, log-normal property | PLANNED |
| `ERIN-FM-BOND-001` | Bond Price/YTM/Duration/Convexity | Fixed Income | Fabozzi examples, Bloomberg compare | PLANNED |
| `ERIN-FM-CURVE-001` | Nelson-Siegel-Svensson Curve Fit | Fixed Income | R² > 0.999 on synthetic | PLANNED |
| `ERIN-FM-ARIMA-001` | ARIMA(p,d,q) Forecast | Econometrics | Statsmodels reference, Ljung-Box | PLANNED |

---

## 3. Detailed Model Specifications (Phase 1)

### 3.1 ERIN-FM-DCF-001: DCF (FCFF, Two-Stage)

**Mathematical Specification:**
```
FCFF_t = EBIT_t × (1 - tax_rate) + D&A_t - CapEx_t - ΔNWC_t
V_enterprise = Σ_{t=1}^{n} FCFF_t / (1 + WACC)^t + TV / (1 + WACC)^n
TV = FCFF_{n+1} / (WACC - g_terminal)   where FCFF_{n+1} = FCFF_n × (1 + g_terminal)
V_equity = V_enterprise - Net_Debt + Cash
Value_per_share = V_equity / Shares_Outstanding
```

**Inputs:**
| Parameter | Symbol | Default | Range |
|-----------|--------|---------|-------|
| Revenue Growth (Stage 1) | g₁ | 0.10 | [0, 0.50] |
| Revenue Growth (Stage 2) | g₂ | 0.03 | [0, 0.10] |
| EBIT Margin | m | 0.15 | [0, 0.50] |
| Tax Rate | τ | 0.25 | [0, 0.50] |
| D&A % Revenue | d | 0.04 | [0, 0.20] |
| CapEx % Revenue | c | 0.05 | [0, 0.20] |
| ΔNWC % Revenue | w | 0.02 | [-0.10, 0.10] |
| WACC | WACC | 0.08 | [0.01, 0.20] |
| Terminal Growth | g_∞ | 0.025 | [0, WACC-0.01] |
| Stage 1 Years | n | 5 | [3, 10] |
| Net Debt | D | 0 | [-∞, ∞] |
| Cash | C | 0 | [0, ∞] |
| Shares Outstanding | N | 1e9 | [1e6, ∞] |

**Verification:**
- KAT: Zero growth → perpetuity formula
- KAT: g_∞ = 0 → finite horizon sum
- Reference: Damodaran DCF spreadsheet (AAPL 2023)
- Property: Value monotonic in g₁, g_∞, m; decreasing in WACC, τ

### 3.2 ERIN-FM-WACC-001: WACC (CAPM + Build-up)

**Mathematical Specification:**
```
Cost of Equity (CAPM): r_e = r_f + β × (ERP) + α
Cost of Equity (Build-up): r_e = r_f + ERP + Size_Premium + Company_Specific_Premium
Cost of Debt: r_d = YTM_debt × (1 - τ)
WACC = (E / V) × r_e + (D / V) × r_d
```

**Inputs:**
| Parameter | Symbol | Default | Range |
|-----------|--------|---------|-------|
| Risk-Free Rate | r_f | 0.045 | [0, 0.15] |
| Equity Risk Premium | ERP | 0.055 | [0.02, 0.10] |
| Beta | β | 1.0 | [0, 3] |
| Alpha (CAPM) | α | 0.0 | [-0.05, 0.05] |
| Size Premium | SP | 0.0 | [0, 0.05] |
| Company Specific Premium | CSP | 0.0 | [0, 0.10] |
| Pre-tax Cost of Debt | r_d_pre | 0.055 | [0, 0.20] |
| Tax Rate | τ | 0.25 | [0, 0.50] |
| Market Value of Equity | E | 1e9 | [0, ∞] |
| Market Value of Debt | D | 0 | [0, ∞] |

### 3.3 ERIN-FM-VAR-HIST-001: Historical VaR

**Mathematical Specification:**
```
Given: Portfolio returns r_1, r_2, ..., r_N (historical, lookback L days)
VaR_α = -Quantile_α(r)   where α = confidence level (e.g., 0.99)
ES_α = -E[r | r ≤ -VaR_α]
```
**Convention:** Loss positive, VaR positive.

**Inputs:**
| Parameter | Symbol | Default | Range |
|-----------|--------|---------|-------|
| Confidence Level | α | 0.99 | (0.90, 0.999) |
| Horizon (days) | h | 1 | [1, 20] |
| Lookback (days) | L | 252 | [100, 1000] |
| Weighting | - | Equal | Equal / Exponential (λ=0.94) |

**Verification:**
- Kupiec POF Test: Exceptions ~ Binomial(N, 1-α)
- Christoffersen Independence Test: Exceptions not clustered
- Known-answer: Normal returns → analytical quantile

### 3.4 ERIN-FM-BSM-001: Black-Scholes-Merton

**Full specification per template in Section 1.1** — see `models/ERIN-FM-BSM-001/spec.md`

### 3.5 ERIN-FM-BOND-001: Bond Analytics

**Mathematical Specification:**
```
Price = Σ_{t=1}^{n} CF_t / (1 + y/f)^{t}   (discrete compounding)
Macaulay Duration = Σ t × PV(CF_t) / Price
Modified Duration = Macaulay Duration / (1 + y/f)
Convexity = Σ t(t+1) × PV(CF_t) / (Price × (1 + y/f)^2)
DV01 = -Modified Duration × Price × 0.0001
```
**Day Count:** Per bond specification (ACT/ACT, 30/360, etc.)
**Verification:** Fabozzi "Bond Markets" examples, Bloomberg YAS comparison

---

## 4. Model Registry Structure

```
/models/
├── ERIN-FM-DCF-001/
│   ├── spec.md              # Full specification (template)
│   ├── impl.py              # Single implementation
│   ├── test_verification.py # KAT + property + reference
│   ├── test_regression.py   # Golden master outputs
│   └── benchmarks.py        # Performance benchmarks
├── ERIN-FM-WACC-001/
│   └── ...
└── registry.json            # Catalog index with versions, status, deps
```

### registry.json Schema
```json
{
  "models": [
    {
      "id": "ERIN-FM-BSM-001",
      "name": "Black-Scholes-Merton European Option",
      "version": "1.0.0",
      "category": "DERIVATIVES",
      "status": "VERIFIED",
      "owner": "quant-finance-engineer",
      "spec_path": "models/ERIN-FM-BSM-001/spec.md",
      "impl_path": "models/ERIN-FM-BSM-001/impl.py",
      "verification": {
        "kat_count": 12,
        "property_tests": true,
        "reference": "QuantLib 1.38",
        "boundary_tests": 5,
        "performance_ms": 0.08
      },
      "dependencies": ["ERIN-FM-DIST-001"],
      "limitations": ["Constant vol", "No dividends", "European only"],
      "created": "2026-11-02",
      "verified_at": "2026-11-15"
    }
  ]
}
```

---

## 5. Numerical Standards

| Standard | Specification |
|----------|---------------|
| **Decimal Precision** | Python `decimal.Decimal` for all financial quantities (no float for money) |
| **Float for Math** | NumPy `float64` for computations, cast to Decimal for storage |
| **Random Seeds** | Explicit `seed` parameter on all stochastic functions; `SeedSequence` for parallel |
| **Date/Time** | `datetime` with timezone (UTC), `date` for business days |
| **Day Count** | Explicit convention per instrument (ACT/365, ACT/ACT, 30/360, etc.) |
| **Compounding** | Continuous for rates (`exp(r*t)`), discrete for coupons (`(1+r/f)^(f*t)`) |
| **Rounding** | Banker's rounding (ROUND_HALF_EVEN) for display; no rounding in computation |
| **Missing Data** | `None`/`NaN` propagated; never silently converted to zero |

---

## 6. Testing Standards

| Test Type | Framework | Requirements |
|-----------|-----------|--------------|
| **Known-Answer** | pytest | ≥ 5 tests per model, analytical solutions |
| **Property-Based** | Hypothesis | ≥ 1000 examples, shrink on failure |
| **Reference** | pytest | QuantLib / Statsmodels / Textbook comparison |
| **Boundary** | pytest | Edge cases: T→0, σ→0, extreme moneyness |
| **Regression** | pytest | Golden master JSON outputs (hash-verified) |
| **Performance** | pytest-benchmark | Median, P95, memory; CI threshold gates |

---

## 7. Approval

**Quantitative Finance Engineer:** _________________ **Date:** __________

**Principal Architect:** _________________ **Date:** __________

**QA Lead:** _________________ **Date:** __________