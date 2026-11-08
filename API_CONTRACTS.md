# ERIN 2.0 — API CONTRACT SPECIFICATION

**Version:** 1.0
**Status:** DRAFT
**Classification:** INTERNAL — API CONTRACTS
**Owner:** Principal Backend Engineer
**Phase:** 2 — Domain & System Architecture

---

## 1. API Design Principles

- **Protocol:** HTTP/1.1 + WebSocket (local), HTTP/2 + gRPC (server)
- **Format:** JSON (request/response), MessagePack (high-throughput internal)
- **Versioning:** URL path `/api/v1/`, semantic versioning for contracts
- **Authentication:** Bearer JWT (local: HS256, server: RS256/JWKS)
- **Rate Limiting:** Token bucket per client/IP, configurable per endpoint
- **Error Format:** RFC 7807 Problem Details
- **Documentation:** OpenAPI 3.1 (auto-generated from FastAPI)
- **Contracts:** Pydantic v2 models (strict mode, frozen)

---

## 2. External API (Frontend ↔ Backend)

### 2.1 Authentication

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string",
  "mfa_code": "string?"  // Required if MFA enabled
}

Response 200:
{
  "access_token": "string",      // JWT, 15 min expiry
  "refresh_token": "string",     // Opaque, 30 day expiry
  "token_type": "bearer",
  "expires_in": 900,
  "user": { "id": "uuid", "username": "string", "roles": ["string"] }
}

POST /api/v1/auth/refresh
Authorization: Bearer <refresh_token>

Response 200: { "access_token": "...", "expires_in": 900 }

POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

### 2.2 Market Intelligence

```http
# Instruments
GET /api/v1/instruments?search={query}&asset_class={class}&exchange={exch}&limit=50
Response 200: { "items": [Instrument], "total": 1234, "page": 1, "page_size": 50 }

GET /api/v1/instruments/{figi}
Response 200: Instrument

# Quotes
GET /api/v1/quotes?symbols=AAPL.US,MSFT.US&fields=bid,ask,last,volume
Response 200: { "quotes": { "AAPL.US": Quote, "MSFT.US": Quote } }

GET /api/v1/quotes/{figi}/history
  ?start=2026-01-01&end=2026-12-31&interval=1d&adjustment=none|split|dividend|all
Response 200: { "symbol": "AAPL.US", "interval": "1d", "bars": [Bar] }

# WebSocket: Real-time Quotes
WS /api/v1/ws/quotes
  Subscribe: { "action": "subscribe", "symbols": ["AAPL.US", "MSFT.US"] }
  Unsubscribe: { "action": "unsubscribe", "symbols": ["AAPL.US"] }
  Message: { "type": "quote", "data": Quote }

# Watchlists
GET /api/v1/watchlists
POST /api/v1/watchlists { "name": "string", "symbols": ["AAPL.US"] }
GET /api/v1/watchlists/{id}
PUT /api/v1/watchlists/{id} { "name": "string", "symbols": ["..."] }
DELETE /api/v1/watchlists/{id}

# Market Calendar
GET /api/v1/calendar?exchange=NYSE&year=2026
Response 200: MarketCalendar
```

### 2.3 Equity Research

```http
# Companies
GET /api/v1/companies?search={query}&sector={sector}&limit=50
GET /api/v1/companies/{id}
GET /api/v1/companies/{id}/financials
  ?statement_type=income|balance_sheet|cash_flow
  &period_type=quarterly|annual
  &limit=20
Response 200: { "items": [FinancialStatement], "company": CompanySummary }

GET /api/v1/companies/{id}/ratios
  ?period_end=2026-06-30&ratio_type=profitability|liquidity|solvency|efficiency|valuation
Response 200: { "ratios": [FinancialRatio] }

GET /api/v1/companies/{id}/peers?method=gics|custom&limit=10
Response 200: { "peers": [CompanySummary] }
```

### 2.4 Valuation Engine

```http
# Models
GET /api/v1/valuation/models
Response 200: [ValuationModelSummary]

GET /api/v1/valuation/models/{id}
Response 200: ValuationModel (with parameter specs)

# Runs
POST /api/v1/valuation/runs
{
  "model_id": "uuid",
  "company_id": "uuid",
  "as_of_date": "2026-06-30",
  "inputs": { "revenue_growth": 0.12, "ebitda_margin": 0.25, ... },
  "sensitivity": { "variables": ["wacc", "terminal_growth"], "range_pct": 0.10 },
  "scenarios": [ { "name": "bear", "inputs": {...} }, { "name": "bull", "inputs": {...} } ]
}
Response 202: { "run_id": "uuid", "status": "PENDING" }

GET /api/v1/valuation/runs/{run_id}
Response 200: ValuationRun (with outputs, sensitivity, scenarios)

GET /api/v1/valuation/runs?company_id={id}&limit=20
```

### 2.5 Portfolio Management

```http
# Portfolios
GET /api/v1/portfolios
POST /api/v1/portfolios { "name": "string", "base_currency": "USD" }
GET /api/v1/portfolios/{id}
PUT /api/v1/portfolios/{id} { "name": "string" }
DELETE /api/v1/portfolios/{id}

GET /api/v1/portfolios/{id}/positions
Response 200: { "positions": [PositionWithMarketValue], "total_value": Money, "cash": Money, "pnl": Money }

POST /api/v1/portfolios/{id}/positions
{ "figi": "string", "quantity": 100, "avg_cost": 150.00, "currency": "USD" }

DELETE /api/v1/portfolios/{id}/positions/{figi}

# Transactions
GET /api/v1/portfolios/{id}/transactions?start=2026-01-01&end=2026-12-31
POST /api/v1/portfolios/{id}/transactions
{
  "figi": "string",
  "side": "BUY",
  "quantity": 100,
  "price": 150.00,
  "fees": 1.00,
  "executed_at": "2026-06-15T10:30:00Z",
  "broker": "IBKR"
}
```

### 2.6 Risk Management

```http
# VaR Models
GET /api/v1/risk/var/models
POST /api/v1/risk/var/models
{
  "name": "string",
  "method": "HISTORICAL|PARAMETRIC|MONTE_CARLO",
  "confidence_level": 0.99,
  "horizon_days": 1,
  "lookback_days": 252,
  "distribution_assumption": "NORMAL",
  "n_simulations": 10000
}

GET /api/v1/risk/var/models/{id}

# VaR Calculations
POST /api/v1/risk/var/calculate
{
  "model_id": "uuid",
  "portfolio_id": "uuid",
  "as_of_date": "2026-06-30"
}
Response 202: { "result_id": "uuid", "status": "PENDING" }

GET /api/v1/risk/var/results/{result_id}
Response 200: VaRResult

GET /api/v1/risk/var/results?portfolio_id={id}&limit=50

# Stress Tests
POST /api/v1/risk/stress-tests
{
  "name": "string",
  "scenario_type": "HISTORICAL|HYPOTHETICAL|REGULATORY",
  "shocks": {
    "EQ_US_LARGE": { "shock_type": "RELATIVE", "magnitude": -0.20 },
    "IR_US_10Y": { "shock_type": "ABSOLUTE", "magnitude": 0.02 }
  },
  "portfolio_id": "uuid"
}

GET /api/v1/risk/stress-tests/{id}
Response 200: StressTest (with results)
```

### 2.7 Fixed Income

```http
# Bonds
GET /api/v1/fixed-income/bonds?issuer=US&rating=AAA&limit=50
GET /api/v1/fixed-income/bonds/{figi}
GET /api/v1/fixed-income/bonds/{figi}/analytics
  ?settlement=2026-06-30&yield=0.045
Response 200: BondAnalytics { price, ytm, duration, convexity, dv01, ... }

# Yield Curves
GET /api/v1/fixed-income/curves?currency=USD&type=GOVERNMENT&date=2026-06-30
GET /api/v1/fixed-income/curves/{id}
GET /api/v1/fixed-income/curves/{id}/interpolate?tenors=1M,3M,6M,1Y,2Y,5Y,10Y,30Y
```

### 2.8 Derivatives

```http
# Options
GET /api/v1/derivatives/options?underlying=AAPL.US&expiration=2026-12-31
GET /api/v1/derivatives/options/{figi}
GET /api/v1/derivatives/options/{figi}/price
  ?model=BSM|BINOMIAL&spot=150&rate=0.045&vol=0.25&dividend_yield=0.005
Response 200: OptionPrice { price, greeks: { delta, gamma, vega, theta, rho } }

# Volatility Surfaces
GET /api/v1/derivatives/vol-surfaces?underlying=AAPL.US&date=2026-06-30
GET /api/v1/derivatives/vol-surfaces/{id}
GET /api/v1/derivatives/vol-surfaces/{id}/interpolate?expiry=2026-12-31&strike=160
```

### 2.9 Macro Intelligence

```http
# Economic Indicators
GET /api/v1/macro/indicators?category=INFLATION&geography=US&limit=50
GET /api/v1/macro/indicators/{id}
GET /api/v1/macro/indicators/{id}/observations
  ?start=2026-01-01&end=2026-12-31&limit=100
Response 200: { "observations": [IndicatorObservation] }

# Yield Curve Snapshots
GET /api/v1/macro/yield-curves?currency=USD&date=2026-06-30
```

### 2.10 News Intelligence

```http
# Articles
GET /api/v1/news/articles
  ?symbols=AAPL.US,MSFT.US&category=earnings&sentiment_min=-0.5&limit=50
Response 200: { "articles": [NewsArticleSummary], "total": 1234 }

GET /api/v1/news/articles/{id}
Response 200: NewsArticle (with full content if available)

# Entity Search
GET /api/v1/news/entities?query=Apple&type=COMPANY|INSTRUMENT
```

### 2.11 Financial Workspace

```http
# Notebooks
GET /api/v1/workspace/notebooks
POST /api/v1/workspace/notebooks { "title": "string", "kernel": "python3" }
GET /api/v1/workspace/notebooks/{id}
PUT /api/v1/workspace/notebooks/{id} { "cells": [...], "version": 5 }
DELETE /api/v1/workspace/notebooks/{id}

POST /api/v1/workspace/notebooks/{id}/execute
{ "cell_id": "uuid", "code": "string" }
Response 202: { "execution_id": "uuid" }

WS /api/v1/ws/notebooks/{id}
  Messages: { "type": "output", "cell_id": "...", "output": CellOutput }
            { "type": "status", "cell_id": "...", "status": "running|idle|error" }

# Workspaces
GET /api/v1/workspace/workspaces
POST /api/v1/workspace/workspaces { "name": "string", "layout": WorkspaceLayout }
GET /api/v1/workspace/workspaces/{id}
PUT /api/v1/workspace/workspaces/{id} { "layout": "...", "watchlist_ids": [...] }
```

### 2.12 AI Financial Intelligence

```http
# RAG
POST /api/v1/ai/rag/query
{
  "query": "string",
  "index_id": "uuid",
  "top_k": 10,
  "hybrid_weight": 0.5,  // 0=vector only, 1=BM25 only
  "filters": { "source": "notebook", "date_range": {...} }
}
Response 200: { "results": [RAGResult], "query_id": "uuid" }

# Tools
GET /api/v1/ai/tools
Response 200: [ToolDefinitionSummary]

POST /api/v1/ai/tools/execute
{
  "tool_name": "string",
  "tool_version": "string",
  "inputs": { ... }
}
Response 202: { "call_id": "uuid", "status": "PENDING" }

GET /api/v1/ai/tools/calls/{call_id}
Response 200: ToolCall

# Report Generation
POST /api/v1/ai/reports/generate
{
  "template": "string",
  "evidence": [ { "source": "rag", "query_id": "uuid" }, { "source": "valuation", "run_id": "uuid" } ],
  "format": "markdown|pdf|html"
}
Response 202: { "report_id": "uuid" }
```

### 2.13 Governance

```http
# Users (Admin)
GET /api/v1/admin/users
POST /api/v1/admin/users { "username": "...", "email": "...", "roles": ["ANALYST"] }
GET /api/v1/admin/users/{id}
PUT /api/v1/admin/users/{id} { "roles": [...], "locked": false }
DELETE /api/v1/admin/users/{id}

# Audit
GET /api/v1/admin/audit?user_id={id}&action=valuation.run&start=2026-01-01&limit=100

# Data Licenses
GET /api/v1/admin/licenses
PUT /api/v1/admin/licenses/{provider}/{dataset}
{ "commercial_use": true, "redistribution": false, "status": "ACTIVE" }
```

---

## 3. Internal API (Context ↔ Context)

All internal routes under `/api/v1/internal/` with service-to-service auth (mTLS in server, shared secret local).

### 3.1 Market Intel → Portfolio Risk
```http
GET /api/v1/internal/market-intel/quotes?symbols=AAPL.US,MSFT.US
Response 200: QuoteBatch { quotes: [Quote] }

GET /api/v1/internal/market-intel/history?figi={figi}&start={date}&end={date}
Response 200: { bars: [Bar] }
```

### 3.2 Data Infra → All
```http
POST /api/v1/internal/data-infra/ingest
{ "provider": "openbb", "dataset": "equity_quotes", "params": {...}, "priority": 0 }
Response 200: { "job_id": "uuid" }

GET /api/v1/internal/data-infra/jobs/{job_id}
Response 200: IngestionJobStatus

GET /api/v1/internal/data-infra/lineage?figi={figi}&dataset={dataset}
Response 200: DataLineage
```

### 3.3 Equity Research → Quant Finance
```http
GET /api/v1/internal/equity-research/fundamentals/{symbol}
  ?period_end=2026-06-30
Response 200: FundamentalsSnapshot

GET /api/v1/internal/equity-research/ratios/{symbol}
  ?period_end=2026-06-30&types=profitability,liquidity
Response 200: { ratios: [FinancialRatio] }
```

### 3.4 Quant Finance → Portfolio Risk
```http
POST /api/v1/internal/quant-finance/simulate
{
  "model": "GBM",
  "params": { "drift": 0.08, "vol": 0.20 },
  "n_paths": 10000,
  "n_steps": 252,
  "horizon_days": 252,
  "correlation_matrix": [[1.0, 0.3], [0.3, 1.0]],
  "seed": 42
}
Response 200: SimulationResponse
```

### 3.5 Fixed Income → Derivatives
```http
GET /api/v1/internal/fixed-income/curve/{currency}?date=2026-06-30
Response 200: YieldCurveSnapshot (for discounting)

GET /api/v1/internal/fixed-income/bond/{figi}/cashflows?settlement=2026-06-30
Response 200: [Cashflow]
```

---

## 4. WebSocket Protocols

### 4.1 Quote Stream
```
WS /api/v1/ws/quotes
Client → Server: { "action": "subscribe", "symbols": ["AAPL.US"] }
Server → Client: { "type": "quote", "data": { "symbol": "AAPL.US", "bid": 150.01, "ask": 150.02, "last": 150.015, "timestamp": "2026-06-15T10:30:00.123Z", "source": "openbb" } }
Client → Server: { "action": "unsubscribe", "symbols": ["AAPL.US"] }
Server → Client: { "type": "heartbeat", "timestamp": "..." }  // Every 30s
```

### 4.2 Notebook Execution
```
WS /api/v1/ws/notebooks/{notebook_id}
Server → Client: { "type": "output", "cell_id": "uuid", "output": { "output_type": "stream", "text": "Hello\n" } }
Server → Client: { "type": "status", "cell_id": "uuid", "status": "running" }
Client → Server: { "type": "interrupt", "cell_id": "uuid" }
```

### 4.3 Job Progress
```
WS /api/v1/ws/jobs/{job_id}
Server → Client: { "type": "progress", "job_id": "uuid", "stage": "DOWNLOADING", "progress": 0.45, "message": "Downloaded 450/1000 files" }
Server → Client: { "type": "completed", "job_id": "uuid", "result": {...} }
Server → Client: { "type": "failed", "job_id": "uuid", "error": "..." }
```

---

## 5. Error Handling (RFC 7807)

```json
{
  "type": "https://erin.example.com/errors/validation-error",
  "title": "Request Validation Failed",
  "status": 422,
  "detail": "Input validation failed for field 'confidence_level'",
  "instance": "/api/v1/risk/var/models",
  "errors": [
    { "field": "confidence_level", "message": "Must be between 0 and 1 exclusive" }
  ]
}
```

### Standard Error Types
| Type URI | Title | HTTP Status |
|----------|-------|-------------|
| `/errors/validation-error` | Request Validation Failed | 422 |
| `/errors/authentication-required` | Authentication Required | 401 |
| `/errors/authorization-failed` | Insufficient Permissions | 403 |
| `/errors/not-found` | Resource Not Found | 404 |
| `/errors/rate-limited` | Rate Limit Exceeded | 429 |
| `/errors/internal-error` | Internal Server Error | 500 |
| `/errors/provider-unavailable` | Data Provider Unavailable | 503 |
| `/errors/computation-failed` | Computation Failed | 500 |

---

## 6. Rate Limiting

| Tier | Requests/Minute | Burst | Applies To |
|------|-----------------|-------|------------|
| **Anonymous** | 10 | 20 | Unauthenticated endpoints |
| **Authenticated** | 100 | 200 | Standard API |
| **Heavy Compute** | 10 | 20 | Valuation, VaR, Simulation, Backtest |
| **AI Tools** | 20 | 50 | Tool execution, RAG queries |
| **Internal** | 1000 | 2000 | Service-to-service |

Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

---

## 7. Pagination

```json
{
  "items": [...],
  "page": 1,
  "page_size": 50,
  "total": 1234,
  "total_pages": 25,
  "has_next": true,
  "has_prev": false
}
```
Query params: `page` (default 1), `page_size` (default 50, max 200)

---

## 8. OpenAPI Generation

```python
# apps/api/src/erin/api/openapi.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

def custom_openapi(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="ERIN API",
        version="1.0.0",
        description="Enterprise Research, Investment & Intelligence Network",
        routes=app.routes,
    )
    # Add security schemes, examples, custom extensions
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema
```

---

## 9. Contract Testing

```python
# tests/contracts/test_api_contracts.py
import pytest
from pydantic import BaseModel

# Each endpoint has a request/response model pair
# Contract tests verify:
# 1. Serialization/deserialization round-trip
# 2. Required fields present
# 3. Enum values valid
# 4. Nested models valid
# 5. Backward compatibility (no required field removal)
```

---

## 10. Approval

**Principal Backend Engineer:** _________________ **Date:** __________

**Principal Architect:** _________________ **Date:** __________

**Principal Frontend Engineer:** _________________ **Date:** __________