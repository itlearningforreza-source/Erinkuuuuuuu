# ERIN 2.0 — DOMAIN-DRIVEN DESIGN DOCUMENT

**Version:** 1.0
**Status:** DRAFT
**Classification:** INTERNAL — DOMAIN MODEL
**Owner:** Financial Data Architect
**Phase:** 2 — Domain & System Architecture

---

## 1. Domain Model Overview

This document defines the **core domain aggregates, entities, value objects, domain events, and invariants** for each bounded context. All models are expressed in implementation-agnostic terms; physical schema is in `DATABASE_SCHEMA.md`.

---

## 2. Shared Kernel (Cross-Domain Value Objects)

```python
# packages/shared-types/src/erin/shared/kernel.py

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

class CurrencyCode(str, Enum):
    USD = "USD"
    EUR = "EUR"
    JPY = "JPY"
    GBP = "GBP"
    CNY = "CNY"
    IDR = "IDR"
    # ... ISO 4217 complete

class AssetClass(str, Enum):
    EQUITY = "EQUITY"
    FIXED_INCOME = "FIXED_INCOME"
    DERIVATIVE = "DERIVATIVE"
    COMMODITY = "COMMODITY"
    FX = "FX"
    CRYPTO = "CRYPTO"
    FUND = "FUND"
    CASH = "CASH"

class ProviderId(str, Enum):
    OPENBB = "openbb"
    YFINANCE = "yfinance"
    FRED = "fred"
    ALPHA_VANTAGE = "alpha_vantage"
    SEC_EDGAR = "sec_edgar"
    MANUAL = "manual"

@dataclass(frozen=True)
class InstrumentId:
    figi: str                    # Primary: OpenFIGI
    composite_ticker: str        # e.g., "AAPL.US", "7203.T"
    provider_symbol: Optional[str] = None  # Provider-specific

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: CurrencyCode

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Currency mismatch")
        return Money(self.amount + other.amount, self.currency)

@dataclass(frozen=True)
class Price:
    value: Decimal
    currency: CurrencyCode
    timestamp: datetime
    source: ProviderId

@dataclass(frozen=True)
class Percentage:
    value: Decimal  # Stored as decimal (0.05 = 5%)

@dataclass(frozen=True)
class TimestampRange:
    start: datetime
    end: datetime
    inclusive_start: bool = True
    inclusive_end: bool = True
```

---

## 3. Domain 01: Market Intelligence

### 3.1 Aggregates

#### Instrument (Aggregate Root)
```python
# packages/market-intel/src/erin/market_intel/domain/instrument.py

@dataclass
class Instrument:
    id: InstrumentId
    name: str
    asset_class: AssetClass
    primary_exchange: str
    currency: CurrencyCode
    country: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    gics_code: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Invariants
    # - FIGI globally unique
    # - composite_ticker unique per provider
    # - currency matches exchange standard
    # - is_active=False → no new quotes accepted
```

#### Watchlist (Aggregate Root)
```python
@dataclass
class Watchlist:
    id: UUID
    user_id: UUID
    name: str
    symbols: list[InstrumentId]  # Ordered
    created_at: datetime
    updated_at: datetime

    # Invariants
    # - Max 500 symbols
    # - No duplicate symbols
    # - User-scoped (user_id)
    # - Symbols must exist in Instrument master

    def add_symbol(self, symbol: InstrumentId) -> None:
        if len(self.symbols) >= 500:
            raise DomainError("Watchlist limit exceeded (500)")
        if symbol in self.symbols:
            raise DomainError("Symbol already in watchlist")
        self.symbols.append(symbol)
        self.updated_at = datetime.utcnow()
```

#### Quote (Entity — part of Instrument aggregate)
```python
@dataclass
class Quote:
    instrument_id: InstrumentId
    bid: Optional[Price]
    ask: Optional[Price]
    last: Optional[Price]
    bid_size: Optional[int]
    ask_size: Optional[int]
    volume: Optional[int]
    timestamp: datetime
    source: ProviderId

    # Invariants
    # - bid <= ask (if both present)
    # - timestamp <= now + 1s (clock skew tolerance)
    # - Currency matches instrument
```

#### MarketCalendar (Aggregate Root)
```python
@dataclass
class MarketCalendar:
    exchange: str
    year: int
    trading_days: list[date]
    holidays: list[Holiday]
    early_closes: list[EarlyClose]

    # Invariants
    # - trading_days sorted, unique
    # - holidays don't overlap trading_days
    # - Early closes have time component
```

### 3.2 Domain Events
```python
@dataclass(frozen=True)
class InstrumentCreated:
    instrument_id: InstrumentId
    timestamp: datetime

@dataclass(frozen=True)
class QuoteUpdated:
    instrument_id: InstrumentId
    quote: Quote
    timestamp: datetime

@dataclass(frozen=True)
class WatchlistCreated:
    watchlist_id: UUID
    user_id: UUID
    timestamp: datetime

@dataclass(frozen=True)
class WatchlistModified:
    watchlist_id: UUID
    added: list[InstrumentId]
    removed: list[InstrumentId]
    timestamp: datetime
```

---

## 4. Domain 02: Financial Data Infrastructure

### 4.1 Aggregates

#### Provider (Aggregate Root)
```python
@dataclass
class Provider:
    id: ProviderId
    name: str
    base_url: str
    auth_type: AuthType  # API_KEY, OAUTH, NONE
    rate_limit: RateLimitConfig
    supported_datasets: list[DatasetId]
    licensing: LicensingTerms
    is_active: bool = True

    # Invariants
    # - Rate limit enforced per provider
    # - Licensing terms validated before redistribution
```

#### IngestionJob (Aggregate Root)
```python
@dataclass
class IngestionJob:
    id: UUID
    provider: ProviderId
    dataset: DatasetId
    params: dict[str, Any]
    status: JobStatus  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    records_processed: int
    records_failed: int
    error_message: Optional[str]
    watermark: Optional[str]  # For incremental loads

    # Invariants
    # - Idempotent: same provider+dataset+params+watermark → same result
    # - Atomic per partition
    # - Lineage recorded on completion
```

#### DataQualityReport (Entity)
```python
@dataclass
class DataQualityReport:
    job_id: UUID
    dataset: DatasetId
    timestamp: datetime
    completeness_score: float  # 0-1
    timeliness_score: float
    validity_score: float
    consistency_score: float
    issues: list[DataQualityIssue]

@dataclass
class DataQualityIssue:
    severity: IssueSeverity  # INFO, WARNING, ERROR, CRITICAL
    rule: str
    description: str
    affected_records: int
    sample_values: list[Any]
```

#### DataLineage (Value Object)
```python
@dataclass(frozen=True)
class DataLineage:
    source_provider: ProviderId
    source_dataset: DatasetId
    source_timestamp: datetime
    ingestion_timestamp: datetime
    transformation_steps: list[str]
    quality_score: float
    version: int
```

### 4.2 Domain Events
```python
@dataclass(frozen=True)
class IngestionJobStarted:
    job_id: UUID
    provider: ProviderId
    dataset: DatasetId
    timestamp: datetime

@dataclass(frozen=True)
class IngestionJobCompleted:
    job_id: UUID
    records_processed: int
    records_failed: int
    quality_report: DataQualityReport
    timestamp: datetime

@dataclass(frozen=True)
class DataQualityAlert:
    dataset: DatasetId
    issue: DataQualityIssue
    timestamp: datetime
```

---

## 5. Domain 03: Equity Research

### 5.1 Aggregates

#### Company (Aggregate Root)
```python
@dataclass
class Company:
    id: UUID
    cik: str                    # SEC CIK (zero-padded 10 digits)
    name: str
    tickers: dict[str, str]     # exchange -> ticker (e.g., {"NASDAQ": "AAPL"})
    primary_exchange: str
    currency: CurrencyCode
    sector: Optional[str]
    industry: Optional[str]
    gics_code: Optional[str]
    headquarters: Optional[Address]
    description: Optional[str]
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    # Invariants
    # - CIK unique
    # - At least one ticker mapping
    # - Primary exchange in tickers
```

#### FinancialStatement (Entity — part of Company aggregate)
```python
@dataclass
class FinancialStatement:
    id: UUID
    company_id: UUID
    statement_type: StatementType  # INCOME, BALANCE_SHEET, CASH_FLOW
    period_type: PeriodType  # QUARTERLY, ANNUAL
    period_end: date
    filing_date: date
    gaap: GAAPType  # US_GAAP, IFRS
    currency: CurrencyCode
    line_items: dict[str, Decimal]  # Standardized tags → values
    source: ProviderId
    source_accession: Optional[str]  # SEC accession number
    is_restated: bool = False
    restatement_reason: Optional[str]
    created_at: datetime

    # Invariants
    # - No overlapping periods for same company+type+period_type
    # - Currency matches company currency
    # - Filing date >= period end
    # - Line items use standardized taxonomy (US-GAAP/IFRS tags)
```

#### FinancialRatio (Entity — derived)
```python
@dataclass
class FinancialRatio:
    company_id: UUID
    period_end: date
    ratio_type: RatioType
    value: Decimal
    inputs: dict[str, Decimal]  # Traceability
    calculated_at: datetime
    methodology_version: str

    # Ratio Types: PROFITABILITY, LIQUIDITY, SOLVENCY, EFFICIENCY, VALUATION
```

### 5.2 Domain Events
```python
@dataclass(frozen=True)
class CompanyCreated:
    company_id: UUID
    cik: str
    timestamp: datetime

@dataclass(frozen=True)
class FinancialsPublished:
    company_id: UUID
    statement_type: StatementType
    period_end: date
    filing_date: date
    timestamp: datetime

@dataclass(frozen=True)
class RatiosCalculated:
    company_id: UUID
    period_end: date
    ratios: list[FinancialRatio]
    timestamp: datetime
```

---

## 6. Domain 05: Valuation Engine

### 6.1 Aggregates

#### ValuationModel (Aggregate Root)
```python
@dataclass
class ValuationModel:
    id: UUID
    model_type: ValuationModelType  # DCF_FCFF, DCF_FCFE, DDM_GORDON, DDM_H_MODEL, WACC
    version: str
    methodology_spec: MethodologySpec  # Reference to FINANCIAL_METHODOLOGY.md
    parameters: dict[str, ParameterSpec]
    created_at: datetime
    created_by: UUID

    # Invariants
    # - Methodology spec exists and is VERIFIED
    # - All required parameters have specs
    # - Version follows semver
```

#### ValuationRun (Entity — part of ValuationModel aggregate)
```python
@dataclass
class ValuationRun:
    id: UUID
    model_id: UUID
    company_id: UUID
    as_of_date: date
    inputs: dict[str, Decimal]  # Parameter values used
    outputs: ValuationOutputs
    sensitivity: Optional[SensitivityAnalysis]
    scenario_results: Optional[list[ScenarioResult]]
    status: RunStatus  # COMPLETED, FAILED, PARTIAL
    computation_time_ms: int
    created_at: datetime

@dataclass
class ValuationOutputs:
    intrinsic_value: Money
    value_per_share: Money
    enterprise_value: Money
    equity_value: Money
    key_metrics: dict[str, Decimal]  # WACC, terminal value %, etc.

@dataclass
class SensitivityAnalysis:
    base_value: Money
    variables: list[SensitivityVariable]

@dataclass
class SensitivityVariable:
    name: str
    base_value: Decimal
    range_pct: float  # e.g., 0.10 = ±10%
    values: list[Decimal]  # Tested values
    results: list[Money]  # Corresponding valuations
```

### 6.2 Domain Events
```python
@dataclass(frozen=True)
class ValuationCompleted:
    run_id: UUID
    model_id: UUID
    company_id: UUID
    intrinsic_value: Money
    timestamp: datetime

@dataclass(frozen=True)
class ValuationFailed:
    run_id: UUID
    model_id: UUID
    error: str
    timestamp: datetime
```

---

## 7. Domain 06: Quantitative Finance

### 7.1 Aggregates

#### StochasticModel (Aggregate Root)
```python
@dataclass
class StochasticModel:
    id: UUID
    model_type: StochasticModelType  # GBM, JUMP_DIFFUSION, HESTON, CIR, OU
    version: str
    methodology_spec: MethodologySpec
    parameters: dict[str, ParameterSpec]
    calibration_method: Optional[CalibrationMethod]
    created_at: datetime

    # Invariants
    # - Parameters satisfy model constraints (e.g., κ>0, θ>0, σ>0 for Heston)
    # - Feller condition checked for Heston/CIR
```

#### Simulation (Entity — part of StochasticModel aggregate)
```python
@dataclass
class Simulation:
    id: UUID
    model_id: UUID
    n_paths: int
    n_steps: int
    horizon_days: int
    dt: float  # Time step in years
    correlation_matrix: Optional[np.ndarray]  # Multi-asset
    seed: Optional[int]
    paths: np.ndarray  # Shape: (n_paths, n_steps, n_assets)
    statistics: SimulationStatistics
    computation_time_ms: int
    created_at: datetime

@dataclass
class SimulationStatistics:
    mean: np.ndarray
    std: np.ndarray
    skewness: np.ndarray
    kurtosis: np.ndarray
    percentiles: dict[float, np.ndarray]  # 0.01, 0.05, 0.5, 0.95, 0.99
    autocorr_lag1: np.ndarray
```

### 7.2 Domain Events
```python
@dataclass(frozen=True)
class SimulationCompleted:
    simulation_id: UUID
    model_id: UUID
    n_paths: int
    computation_time_ms: int
    timestamp: datetime
```

---

## 8. Domain 08: Portfolio Management

### 8.1 Aggregates

#### Portfolio (Aggregate Root)
```python
@dataclass
class Portfolio:
    id: UUID
    user_id: UUID
    name: str
    base_currency: CurrencyCode
    positions: dict[InstrumentId, Position]  # instrument_id -> Position
    cash_balances: dict[CurrencyCode, Money]
    created_at: datetime
    updated_at: datetime

    # Invariants
    # - Positions: quantity >= 0 (unless margin enabled)
    # - Cash balances non-negative (unless margin)
    # - Base currency cash always present
    # - Total weight ≈ 100% (allowing cash residual)

    def add_position(self, position: Position) -> None:
        if position.instrument_id in self.positions:
            existing = self.positions[position.instrument_id]
            # Merge: weighted average cost
            total_qty = existing.quantity + position.quantity
            total_cost = existing.avg_cost * existing.quantity + position.avg_cost * position.quantity
            self.positions[position.instrument_id] = Position(
                instrument_id=position.instrument_id,
                quantity=total_qty,
                avg_cost=total_cost / total_qty if total_qty > 0 else Decimal('0'),
                currency=position.currency
            )
        else:
            self.positions[position.instrument_id] = position
        self.updated_at = datetime.utcnow()

    def total_value(self, quotes: dict[InstrumentId, Quote]) -> Money:
        # Calculate mark-to-market in base currency
        ...
```

#### Position (Entity)
```python
@dataclass
class Position:
    instrument_id: InstrumentId
    quantity: Decimal
    avg_cost: Decimal  # Per unit, in position currency
    currency: CurrencyCode
    opened_at: datetime
    last_updated: datetime

    # Invariants
    # - Quantity non-negative (short positions via separate flag)
    # - Avg cost > 0
```

#### Transaction (Entity — separate aggregate for audit)
```python
@dataclass
class Transaction:
    id: UUID
    portfolio_id: UUID
    instrument_id: InstrumentId
    side: TransactionSide  # BUY, SELL
    quantity: Decimal
    price: Money
    fees: Money
    slippage: Optional[Money]
    executed_at: datetime
    status: TransactionStatus  # PENDING, FILLED, PARTIAL, CANCELLED, REJECTED
    broker: Optional[str]
    order_id: Optional[str]

    # Invariants
    # - Quantity > 0
    # - Price > 0
    # - Fees >= 0
    # - Executed_at <= now
```

### 8.2 Domain Events
```python
@dataclass(frozen=True)
class PortfolioCreated:
    portfolio_id: UUID
    user_id: UUID
    timestamp: datetime

@dataclass(frozen=True)
class PositionOpened:
    portfolio_id: UUID
    position: Position
    timestamp: datetime

@dataclass(frozen=True)
class PositionClosed:
    portfolio_id: UUID
    instrument_id: InstrumentId
    realized_pnl: Money
    timestamp: datetime

@dataclass(frozen=True)
class TransactionExecuted:
    transaction_id: UUID
    portfolio_id: UUID
    instrument_id: InstrumentId
    side: TransactionSide
    quantity: Decimal
    price: Money
    timestamp: datetime
```

---

## 9. Domain 09: Risk Management

### 9.1 Aggregates

#### VaRModel (Aggregate Root)
```python
@dataclass
class VaRModel:
    id: UUID
    name: str
    method: VaRMethod  # HISTORICAL, PARAMETRIC, MONTE_CARLO
    confidence_level: float  # 0.95, 0.99, 0.995
    horizon_days: int  # 1, 10, 20
    lookback_days: int  # For historical/parametric
    distribution_assumption: Optional[DistributionType]  # For parametric
    n_simulations: Optional[int]  # For Monte Carlo
    created_at: datetime
    created_by: UUID
    is_active: bool = True

    # Invariants
    # - Confidence ∈ (0, 1)
    # - Horizon ≥ 1
    # - Lookback ≥ horizon * 10 (minimum)
    # - Method-specific params validated
```

#### VaRResult (Entity — part of VaRModel aggregate)
```python
@dataclass
class VaRResult:
    id: UUID
    model_id: UUID
    portfolio_id: UUID
    as_of_date: date
    var_value: Money
    es_value: Optional[Money]  # Expected Shortfall
    confidence_level: float
    horizon_days: int
    method: VaRMethod
    computation_details: dict[str, Any]  # For reproducibility
    computation_time_ms: int
    created_at: datetime

    # Invariants
    # - ES ≤ VaR (for same confidence, ES is more conservative)
    # - Currency matches portfolio base currency
    # - Computation_details includes seed, paths, lookback window
```

#### StressTest (Aggregate Root)
```python
@dataclass
class StressTest:
    id: UUID
    name: str
    scenario_type: StressScenarioType  # HISTORICAL, HYPOTHETICAL, REGULATORY
    shocks: dict[str, Shock]  # factor -> shock specification
    portfolio_id: UUID
    results: Optional[StressTestResults]
    created_at: datetime
    created_by: UUID

@dataclass
class Shock:
    factor: str  # e.g., "EQ_US_LARGE", "IR_US_10Y", "FX_USD_JPY"
    shock_type: ShockType  # ABSOLUTE, RELATIVE, CURVE_SHIFT
    magnitude: Decimal
    description: str
```

### 9.2 Domain Events
```python
@dataclass(frozen=True)
class VaRCalculated:
    result_id: UUID
    model_id: UUID
    portfolio_id: UUID
    var_value: Money
    timestamp: datetime

@dataclass(frozen=True)
class StressTestCompleted:
    test_id: UUID
    portfolio_id: UUID
    worst_case_loss: Money
    timestamp: datetime
```

---

## 10. Domain 12: Fixed Income

### 10.1 Aggregates

#### Bond (Aggregate Root)
```python
@dataclass
class Bond:
    id: InstrumentId
    issuer: str
    issuer_type: IssuerType  # GOVERNMENT, CORPORATE, MUNICIPAL, AGENCY, SUPRANATIONAL
    coupon_rate: Decimal  # Annual %
    coupon_frequency: CouponFrequency  # ANNUAL, SEMI_ANNUAL, QUARTERLY, MONTHLY
    day_count: DayCountConvention  # ACT_ACT, ACT_360, ACT_365, THIRTY_360
    issue_date: date
    maturity_date: date
    first_coupon_date: Optional[date]
    currency: CurrencyCode
    credit_rating: Optional[CreditRating]
    is_callable: bool = False
    call_schedule: Optional[list[CallDate]]
    is_putable: bool = False
    put_schedule: Optional[list[PutDate]]
    seniority: Seniority  # SENIOR, SUBORDINATED, JUNIOR
    created_at: datetime

    # Invariants
    # - Maturity > issue_date
    # - Coupon_rate >= 0
    # - Currency valid ISO 4217
    # - Day count convention matches market standard
```

#### YieldCurve (Aggregate Root)
```python
@dataclass
class YieldCurve:
    id: UUID
    curve_type: CurveType  # GOVERNMENT, SWAP, CORPORATE_AAA, CORPORATE_AA, etc.
    currency: CurrencyCode
    reference_date: date
    tenors: list[Tenor]  # e.g., 1M, 3M, 6M, 1Y, 2Y, 5Y, 10Y, 30Y
    rates: list[Decimal]  # Continuously compounded
    interpolation_method: InterpolationMethod  # LINEAR, CUBIC_SPLINE, NELSON_SIEGEL
    nelson_siegel_params: Optional[NelsonSiegelParams]
    source: ProviderId
    quality_score: float
    created_at: datetime

    # Invariants
    # - Tenors strictly increasing
    # - Rates length == tenors length
    # - All rates valid (not NaN, not extreme outliers)
    # - Reference date <= today
```

### 10.2 Domain Events
```python
@dataclass(frozen=True)
class BondPriced:
    bond_id: InstrumentId
    clean_price: Decimal
    dirty_price: Decimal
    ytm: Decimal
    duration: Decimal
    convexity: Decimal
    timestamp: datetime

@dataclass(frozen=True)
class CurveUpdated:
    curve_id: UUID
    reference_date: date
    max_rate_change_bps: float
    timestamp: datetime
```

---

## 11. Domain 13: Derivatives

### 11.1 Aggregates

#### Option (Aggregate Root)
```python
@dataclass
class Option:
    id: InstrumentId
    underlying: InstrumentId
    option_type: OptionType  # CALL, PUT
    style: OptionStyle  # EUROPEAN, AMERICAN, BERMUDAN
    strike: Decimal
    expiration: date
    settlement: SettlementType  # PHYSICAL, CASH
    contract_size: int  # Shares per contract (typically 100)
    currency: CurrencyCode
    exchange: str
    created_at: datetime

    # Invariants
    # - Strike > 0
    # - Expiration > today
    # - Underlying exists in Instrument master
```

#### VolatilitySurface (Aggregate Root)
```python
@dataclass
class VolatilitySurface:
    id: UUID
    underlying: InstrumentId
    reference_date: date
    expiries: list[date]
    strikes: list[Decimal]
    implied_vols: list[list[Decimal]]  # [expiry][strike]
    interpolation: SurfaceInterpolation  # BICUBIC, SPLINE, SVI
    sviv_params: Optional[SVIParams]  # If SVI calibrated
    source: ProviderId
    quality_score: float
    created_at: datetime

    # Invariants
    # - Expiries strictly increasing
    # - Strikes strictly increasing per expiry
    # - No arbitrage (calendar spread, butterfly) — checked on build
    # - Implied vols > 0, < 5.0 (500% cap)
```

### 11.2 Domain Events
```python
@dataclass(frozen=True)
class OptionPriced:
    option_id: InstrumentId
    model: PricingModel  # BSM, BINOMIAL, HESTON, MC
    price: Money
    greeks: Greeks
    timestamp: datetime

@dataclass(frozen=True)
class VolSurfaceCalibrated:
    surface_id: UUID
    underlying: InstrumentId
    calibration_error: float
    timestamp: datetime
```

---

## 12. Domain 14: Macro Intelligence

### 12.1 Aggregates

#### EconomicIndicator (Aggregate Root)
```python
@dataclass
class EconomicIndicator:
    id: UUID
    provider: ProviderId
    provider_series_id: str
    name: str
    description: str
    category: IndicatorCategory  # GDP, INFLATION, EMPLOYMENT, RATES, PMI, FISCAL, TRADE, MONEY
    frequency: DataFrequency  # DAILY, WEEKLY, MONTHLY, QUARTERLY, ANNUAL
    unit: str  # e.g., "Percent", "Billions USD", "Index"
    seasonal_adjustment: SeasonalAdjustment  # SA, NSA
    geography: str  # ISO country code or "GLOBAL"
    source_url: str
    license: LicenseTerms
    is_active: bool = True

    # Invariants
    # - Provider series ID unique per provider
    # - Frequency matches data
    # - License permits storage and analysis
```

#### IndicatorObservation (Entity)
```python
@dataclass
class IndicatorObservation:
    indicator_id: UUID
    period: date
    value: Decimal
    revision: int = 0
    published_at: datetime
    source: ProviderId
    created_at: datetime

    # Invariants
    # - Period aligns with frequency
    # - Revision ≥ 0
    # - Published_at >= period
```

#### YieldCurveSnapshot (Entity — macro view)
```python
@dataclass
class YieldCurveSnapshot:
    curve_type: CurveType  # GOV, SWAP, CORP
    currency: CurrencyCode
    reference_date: date
    tenors: list[Tenor]
    rates: list[Decimal]
    spread_to_benchmark: Optional[list[Decimal]]  # e.g., OIS spread
    source: ProviderId
    created_at: datetime
```

### 12.2 Domain Events
```python
@dataclass(frozen=True)
class IndicatorReleased:
    indicator_id: UUID
    period: date
    value: Decimal
    revision: int
    timestamp: datetime

@dataclass(frozen=True)
class CurveSnapshotUpdated:
    curve_type: CurveType
    currency: CurrencyCode
    reference_date: date
    timestamp: datetime
```

---

## 13. Domain 15: News Intelligence

### 13.1 Aggregates

#### NewsArticle (Aggregate Root)
```python
@dataclass
class NewsArticle:
    id: UUID
    url: str
    title: str
    summary: Optional[str]
    content: Optional[str]  # Full text (may be large, stored separately)
    published_at: datetime
    ingested_at: datetime
    source: ProviderId
    source_id: str  # Provider's article ID
    language: str  # ISO 639-1
    categories: list[str]  # e.g., "earnings", "m&a", "macro", "regulatory"
    sentiment_score: Optional[float]  # -1 to 1
    entities: list[ExtractedEntity]
    relevance_scores: dict[InstrumentId, float]  # 0-1
    created_at: datetime

    # Invariants
    # - URL unique
    # - Published_at <= ingested_at
    # - At least one entity extracted (or marked as non-financial)
```

#### ExtractedEntity (Value Object)
```python
@dataclass(frozen=True)
class ExtractedEntity:
    entity_type: EntityType  # COMPANY, PERSON, INSTRUMENT, INDEX, CURRENCY, COMMODITY, EVENT
    name: str
    identifier: Optional[str]  # FIGI, CIK, ticker, etc.
    confidence: float  # 0-1
    mentions: int  # Count in article
    sentiment: Optional[float]  # Entity-level sentiment
```

### 13.2 Domain Events
```python
@dataclass(frozen=True)
class ArticleIngested:
    article_id: UUID
    source: ProviderId
    published_at: datetime
    entities: list[ExtractedEntity]
    timestamp: datetime

@dataclass(frozen=True)
class EntityMentioned:
    article_id: UUID
    entity: ExtractedEntity
    instrument_id: Optional[InstrumentId]
    timestamp: datetime
```

---

## 14. Domain 16: Financial Workspace

### 14.1 Aggregates

#### ResearchNotebook (Aggregate Root)
```python
@dataclass
class ResearchNotebook:
    id: UUID
    user_id: UUID
    title: str
    cells: list[NotebookCell]
    kernel_spec: KernelSpec
    metadata: dict[str, Any]
    version: int  # Incremented on each save
    created_at: datetime
    updated_at: datetime
    last_executed_at: Optional[datetime]

@dataclass
class NotebookCell:
    id: UUID
    cell_type: CellType  # CODE, MARKDOWN, RAW
    source: str
    outputs: list[CellOutput]
    execution_count: Optional[int]
    metadata: dict[str, Any]

@dataclass
class CellOutput:
    output_type: OutputType  # STREAM, DISPLAY_DATA, EXECUTE_RESULT, ERROR
    data: dict[str, Any]  # MIME type -> content
    metadata: dict[str, Any]
```

#### Workspace (Aggregate Root)
```python
@dataclass
class Workspace:
    id: UUID
    user_id: UUID
    name: str
    layout: WorkspaceLayout  # Panel positions, sizes, dock state
    watchlist_ids: list[UUID]
    chart_configs: dict[str, ChartConfig]
    notebook_ids: list[UUID]
    created_at: datetime
    updated_at: datetime
```

### 14.2 Domain Events
```python
@dataclass(frozen=True)
class NotebookSaved:
    notebook_id: UUID
    user_id: UUID
    version: int
    timestamp: datetime

@dataclass(frozen=True)
class NotebookExecuted:
    notebook_id: UUID
    cell_id: UUID
    execution_count: int
    success: bool
    timestamp: datetime

@dataclass(frozen=True)
class WorkspaceSaved:
    workspace_id: UUID
    user_id: UUID
    timestamp: datetime
```

---

## 15. Domain 17: AI Financial Intelligence

### 15.1 Aggregates

#### RAGIndex (Aggregate Root)
```python
@dataclass
class RAGIndex:
    id: UUID
    name: str
    description: str
    embedding_model: str  # e.g., "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int
    chunk_overlap: int
    documents: list[RAGDocument]
    created_at: datetime
    updated_at: datetime

@dataclass
class RAGDocument:
    id: UUID
    source: str  # File path, URL, notebook ID, etc.
    title: str
    content_hash: str  # SHA256 for deduplication
    chunks: list[RAGChunk]
    metadata: dict[str, Any]
    ingested_at: datetime

@dataclass
class RAGChunk:
    id: UUID
    document_id: UUID
    content: str
    embedding: list[float]  # Vector
    token_count: int
    metadata: dict[str, Any]
```

#### ToolCall (Aggregate Root — for audit)
```python
@dataclass
class ToolCall:
    id: UUID
    session_id: UUID
    user_id: UUID
    tool_name: str
    tool_version: str
    inputs: dict[str, Any]
    outputs: Optional[dict[str, Any]]
    status: ToolCallStatus  # PENDING, EXECUTING, COMPLETED, FAILED, REJECTED
    sensitivity: SensitivityLevel  # LOW, MEDIUM, HIGH, CRITICAL
    approval_id: Optional[UUID]  # If HIGH/CRITICAL
    started_at: datetime
    completed_at: Optional[datetime]
    execution_time_ms: Optional[int]
    error: Optional[str]
    hash_chain: str  # SHA256(prev_hash + current_call_json)
```

#### ToolDefinition (Aggregate Root — allowlist)
```python
@dataclass
class ToolDefinition:
    name: str
    version: str
    description: str
    input_schema: dict[str, Any]  # JSON Schema
    output_schema: dict[str, Any]
    read_only: bool = True
    sensitivity: SensitivityLevel = SensitivityLevel.LOW
    allowed_roles: list[Role]
    rate_limit: Optional[RateLimit]
    timeout_seconds: int = 30
    sandbox_profile: str  # seccomp profile name
    is_active: bool = True
```

### 15.2 Domain Events
```python
@dataclass(frozen=True)
class ToolCallInitiated:
    call_id: UUID
    tool_name: str
    user_id: UUID
    sensitivity: SensitivityLevel
    timestamp: datetime

@dataclass(frozen=True)
class ToolCallCompleted:
    call_id: UUID
    success: bool
    execution_time_ms: int
    timestamp: datetime

@dataclass(frozen=True)
class RAGIndexUpdated:
    index_id: UUID
    documents_added: int
    documents_removed: int
    timestamp: datetime
```

---

## 16. Domain 18: Governance

### 16.1 Aggregates

#### User (Aggregate Root)
```python
@dataclass
class User:
    id: UUID
    username: str
    email: str
    password_hash: str  # Argon2id
    roles: list[Role]
    mfa_enabled: bool = False
    mfa_secret: Optional[str]
    last_login: Optional[datetime]
    failed_login_attempts: int = 0
    locked_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Invariants
    # - Username unique, email unique
    # - At least one role
    # - Failed attempts reset on successful login
    # - Locked after 5 failed attempts (15 min)
```

#### Role (Entity)
```python
@dataclass
class Role:
    id: UUID
    name: str  # ADMIN, ANALYST, VIEWER, QUANT, RISK_MANAGER
    permissions: list[Permission]
    description: str
    is_system: bool = True  # System roles cannot be deleted
```

#### Permission (Value Object)
```python
@dataclass(frozen=True)
class Permission:
    resource: str  # e.g., "portfolio", "valuation", "ai_tools", "admin"
    action: str    # e.g., "create", "read", "update", "delete", "execute"
    conditions: Optional[dict[str, Any]]  # e.g., {"own_only": true}
```

#### AuditEvent (Entity — append-only)
```python
@dataclass
class AuditEvent:
    id: UUID
    user_id: UUID
    action: str  # e.g., "portfolio.create", "valuation.run", "tool.execute"
    resource_type: str
    resource_id: Optional[UUID]
    details: dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime
    prev_hash: str  # Hash chain for tamper evidence
    hash: str       # SHA256(prev_hash + event_json)
```

#### DataLicense (Aggregate Root)
```python
@dataclass
class DataLicense:
    provider: ProviderId
    dataset: DatasetId
    commercial_use: bool
    redistribution: bool
    caching_allowed: bool
    caching_max_age_days: Optional[int]
    attribution_required: bool
    attribution_text: Optional[str]
    retention_max_days: Optional[int]
    license_url: str
    last_reviewed: date
    reviewed_by: UUID
    status: LicenseStatus  # ACTIVE, EXPIRED, RESTRICTED, UNKNOWN
```

### 16.2 Domain Events
```python
@dataclass(frozen=True)
class UserLoggedIn:
    user_id: UUID
    ip_address: str
    timestamp: datetime

@dataclass(frozen=True)
class PermissionDenied:
    user_id: UUID
    resource: str
    action: str
    timestamp: datetime

@dataclass(frozen=True)
class SensitiveActionPerformed:
    user_id: UUID
    action: str
    resource_id: UUID
    details: dict[str, Any]
    timestamp: datetime
```

---

## 17. Cross-Domain Relationships

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Instrument  │◄────│  Company     │     │  Bond        │
│  (Market)    │     │  (Equity)    │     │  (Fixed Inc) │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       ▼                    ▼                    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│    Quote     │     │ Financials   │     │ YieldCurve   │
│  (Market)    │     │ (Equity)     │     │ (Fixed Inc)  │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            ▼
                   ┌──────────────────┐
                   │ Portfolio / Risk │
                   │ (Portfolio-Risk) │
                   └────────┬─────────┘
                            │
           ┌────────────────┼────────────────┐
           ▼                ▼                ▼
    ┌────────────┐  ┌────────────┐  ┌────────────┐
    │ Valuation  │  │  Quant     │  │ Derivatives│
    │ (Valuation)│  │ (Quant)    │  │ (Deriv)    │
    └────────────┘  └────────────┘  └────────────┘
```

---

## 18. Approval

**Financial Data Architect:** _________________ **Date:** __________

**Principal Architect:** _________________ **Date:** __________

**Quantitative Finance Engineer:** _________________ **Date:** __________