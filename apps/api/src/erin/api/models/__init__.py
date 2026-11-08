from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from enum import Enum

class AssetClass(str, Enum):
    EQUITY = "EQUITY"
    FIXED_INCOME = "FIXED_INCOME"
    DERIVATIVE = "DERIVATIVE"
    COMMODITY = "COMMODITY"
    FX = "FX"
    CRYPTO = "CRYPTO"
    FUND = "FUND"
    CASH = "CASH"

class CurrencyCode(str, Enum):
    USD = "USD"
    EUR = "EUR"
    JPY = "JPY"
    GBP = "GBP"
    CNY = "CNY"
    IDR = "IDR"

class ProviderId(str, Enum):
    OPENBB = "openbb"
    YFINANCE = "yfinance"
    FRED = "fred"
    ALPHA_VANTAGE = "alpha_vantage"
    SEC_EDGAR = "sec_edgar"
    MANUAL = "manual"

class InstrumentBase(BaseModel):
    figi: str
    composite_ticker: str
    name: str
    asset_class: AssetClass
    primary_exchange: str
    currency: CurrencyCode
    country: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    gics_code: Optional[str] = None
    is_active: bool = True
    metadata: Optional[Dict[str, Any]] = None

class InstrumentCreate(InstrumentBase):
    pass

class InstrumentResponse(InstrumentBase):
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class Quote(BaseModel):
    symbol: str
    figi: str
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    last: Optional[Decimal] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    volume: Optional[int] = None
    timestamp: datetime
    source: str
    currency: CurrencyCode

class QuoteBatch(BaseModel):
    quotes: Dict[str, Quote]

class Bar(BaseModel):
    time: int  # Unix timestamp
    open: float
    high: float
    low: float
    close: float
    volume: int

class InstrumentSearch(BaseModel):
    search: Optional[str] = None
    asset_class: Optional[str] = None
    exchange: Optional[str] = None
    limit: int = 50

# Auth models
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=12)

class UserLogin(BaseModel):
    username: str
    password: str
    mfa_code: Optional[str] = None

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: "UserResponse"

class TokenData(BaseModel):
    username: str

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    roles: List[str]
    mfa_enabled: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MFASetup(BaseModel):
    secret: str
    uri: str

class MFAVerify(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)

class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=12)
    confirm_password: str

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

# Market Data models
class MarketCalendar(BaseModel):
    exchange: str
    year: int
    trading_days: List[date]
    holidays: List[Dict[str, str]]
    early_closes: List[Dict[str, Any]]

# Company models
class CompanyBase(BaseModel):
    cik: str
    name: str
    tickers: Dict[str, str]
    primary_exchange: str
    currency: CurrencyCode
    sector: Optional[str] = None
    industry: Optional[str] = None
    gics_code: Optional[str] = None
    headquarters: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    is_active: bool = True

class CompanyCreate(CompanyBase):
    pass

class CompanyResponse(CompanyBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class FinancialStatementBase(BaseModel):
    company_id: str
    statement_type: str  # INCOME, BALANCE_SHEET, CASH_FLOW
    period_type: str  # QUARTERLY, ANNUAL
    period_end: date
    filing_date: date
    gaap: str  # US_GAAP, IFRS
    currency: CurrencyCode
    line_items: Dict[str, Decimal]
    source: str
    source_accession: Optional[str] = None
    is_restated: bool = False
    restatement_reason: Optional[str] = None

class FinancialStatementResponse(FinancialStatementBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True

class FinancialRatio(BaseModel):
    company_id: str
    period_end: date
    ratio_type: str  # PROFITABILITY, LIQUIDITY, SOLVENCY, EFFICIENCY, VALUATION
    ratio_name: str
    value: Decimal
    inputs: Dict[str, Decimal]
    calculated_at: datetime
    methodology_version: str

# Valuation models
class ValuationModelType(str, Enum):
    DCF_FCFF = "DCF_FCFF"
    DCF_FCFE = "DCF_FCFE"
    DDM_GORDON = "DDM_GORDON"
    DDM_H_MODEL = "DDM_H_MODEL"
    WACC = "WACC"

class ValuationModelBase(BaseModel):
    model_type: ValuationModelType
    version: str
    methodology_spec: Dict[str, Any]
    parameters: Dict[str, Dict[str, Any]]

class ValuationModelResponse(ValuationModelBase):
    id: str
    created_at: datetime
    created_by: str

    class Config:
        from_attributes = True

class ValuationRunRequest(BaseModel):
    model_id: str
    company_id: str
    as_of_date: date
    inputs: Dict[str, Decimal]
    sensitivity: Optional[Dict[str, Any]] = None
    scenarios: Optional[List[Dict[str, Any]]] = None

class ValuationRunResponse(BaseModel):
    id: str
    model_id: str
    company_id: str
    as_of_date: date
    inputs: Dict[str, Decimal]
    outputs: Dict[str, Any]
    sensitivity: Optional[Dict[str, Any]] = None
    scenario_results: Optional[List[Dict[str, Any]]] = None
    status: str
    computation_time_ms: int
    created_at: datetime

# Portfolio models
class PositionBase(BaseModel):
    figi: str
    quantity: Decimal
    avg_cost: Decimal
    currency: CurrencyCode

class PositionResponse(PositionBase):
    instrument_name: str
    current_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    weight: Optional[Decimal] = None

class PortfolioBase(BaseModel):
    name: str
    base_currency: CurrencyCode = CurrencyCode.USD

class PortfolioCreate(PortfolioBase):
    pass

class PortfolioResponse(PortfolioBase):
    id: str
    user_id: str
    positions: Dict[str, PositionResponse] = {}
    cash_balances: Dict[str, Decimal] = {}
    total_value: Decimal = Decimal('0')
    total_pnl: Decimal = Decimal('0')
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TransactionBase(BaseModel):
    figi: str
    side: str  # BUY, SELL
    quantity: Decimal
    price: Decimal
    price_currency: CurrencyCode
    fees: Decimal
    fees_currency: CurrencyCode
    slippage: Optional[Decimal] = None
    slippage_currency: Optional[CurrencyCode] = None
    executed_at: datetime
    status: str = "FILLED"
    broker: Optional[str] = None
    order_id: Optional[str] = None

class TransactionResponse(TransactionBase):
    id: str
    portfolio_id: str
    created_at: datetime

    class Config:
        from_attributes = True

# Risk models
class VaRMethod(str, Enum):
    HISTORICAL = "HISTORICAL"
    PARAMETRIC = "PARAMETRIC"
    MONTE_CARLO = "MONTE_CARLO"

class VaRModelBase(BaseModel):
    name: str
    method: VaRMethod
    confidence_level: float = Field(..., gt=0, lt=1)
    horizon_days: int = Field(..., ge=1)
    lookback_days: Optional[int] = None
    distribution_assumption: Optional[str] = None
    n_simulations: Optional[int] = None

class VaRModelResponse(VaRModelBase):
    id: str
    created_by: str
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True

class VaRResult(BaseModel):
    id: str
    model_id: str
    portfolio_id: str
    as_of_date: date
    var_value: Decimal
    var_currency: CurrencyCode
    es_value: Optional[Decimal] = None
    es_currency: Optional[CurrencyCode] = None
    confidence_level: float
    horizon_days: int
    method: VaRMethod
    computation_details: Dict[str, Any]
    computation_time_ms: int
    created_at: datetime

    class Config:
        from_attributes = True

# Fixed Income models
class BondBase(BaseModel):
    figi: str
    issuer: str
    issuer_type: str  # GOVERNMENT, CORPORATE, MUNICIPAL, AGENCY, SUPRANATIONAL
    coupon_rate: Decimal
    coupon_frequency: str  # ANNUAL, SEMI_ANNUAL, QUARTERLY, MONTHLY
    day_count: str  # ACT_ACT, ACT_360, ACT_365, THIRTY_360
    issue_date: date
    maturity_date: date
    first_coupon_date: Optional[date] = None
    currency: CurrencyCode
    credit_rating: Optional[str] = None
    is_callable: bool = False
    call_schedule: Optional[List[Dict[str, Any]]] = None
    is_putable: bool = False
    put_schedule: Optional[List[Dict[str, Any]]] = None
    seniority: str = "SENIOR"  # SENIOR, SUBORDINATED, JUNIOR

class BondAnalytics(BaseModel):
    clean_price: Decimal
    dirty_price: Decimal
    ytm: Decimal
    duration: Decimal
    convexity: Decimal
    dv01: Decimal

# Derivatives models
class OptionType(str, Enum):
    CALL = "CALL"
    PUT = "PUT"

class OptionStyle(str, Enum):
    EUROPEAN = "EUROPEAN"
    AMERICAN = "AMERICAN"
    BERMUDAN = "BERMUDAN"

class OptionBase(BaseModel):
    figi: str
    underlying_figi: str
    option_type: OptionType
    style: OptionStyle
    strike: Decimal
    expiration: date
    settlement: str  # PHYSICAL, CASH
    contract_size: int = 100
    currency: CurrencyCode
    exchange: str

class OptionGreeks(BaseModel):
    delta: Decimal
    gamma: Decimal
    vega: Decimal
    theta: Decimal
    rho: Decimal

class OptionPrice(BaseModel):
    price: Decimal
    greeks: OptionGreeks

# Workspace models
class NotebookCell(BaseModel):
    id: str
    cell_type: str  # CODE, MARKDOWN, RAW
    source: str
    outputs: List[Dict[str, Any]] = []
    execution_count: Optional[int] = None
    metadata: Dict[str, Any] = {}

class KernelSpec(BaseModel):
    name: str
    display_name: str
    language: str

class NotebookBase(BaseModel):
    title: str
    kernel: str = "python3"

class NotebookResponse(BaseModel):
    id: str
    user_id: str
    title: str
    cells: List[NotebookCell]
    kernel_spec: KernelSpec
    metadata: Dict[str, Any] = {}
    version: int
    created_at: datetime
    updated_at: datetime
    last_executed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# AI models
class RAGQuery(BaseModel):
    query: str
    index_id: str
    top_k: int = 10
    hybrid_weight: float = 0.5
    filters: Optional[Dict[str, Any]] = None

class RAGResult(BaseModel):
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]
    source: str

class RAGQueryResponse(BaseModel):
    results: List[RAGResult]
    query_id: str

class ToolCallRequest(BaseModel):
    tool_name: str
    tool_version: str
    inputs: Dict[str, Any]

class ToolCallResponse(BaseModel):
    call_id: str
    status: str

class ToolCallStatus(BaseModel):
    id: str
    session_id: str
    user_id: str
    tool_name: str
    tool_version: str
    inputs: Dict[str, Any]
    outputs: Optional[Dict[str, Any]] = None
    status: str
    sensitivity: str
    approval_id: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_time_ms: Optional[int] = None
    error: Optional[str] = None
    hash_chain: str

# Admin models
class UserCreateAdmin(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    roles: List[str] = ["VIEWER"]

class UserUpdateAdmin(BaseModel):
    roles: Optional[List[str]] = None
    locked: Optional[bool] = None

class LicenseUpdate(BaseModel):
    commercial_use: bool
    redistribution: bool
    caching_allowed: bool
    caching_max_age_days: Optional[int] = None
    attribution_required: bool
    attribution_text: Optional[str] = None
    retention_max_days: Optional[int] = None
    status: str  # ACTIVE, EXPIRED, RESTRICTED, UNKNOWN