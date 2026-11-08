# ERIN 2.0 — DATA PROVIDER AND LICENSING REGISTER

**Version:** 1.0
**Status:** DRAFT
**Classification:** INTERNAL — LEGAL/COMPLIANCE
**Owner:** Data Engineer
**Phase:** 2 — Domain & System Architecture

---

## 1. Provider Licensing Framework

Each data provider must be evaluated against these criteria before integration:

| Criterion | Requirement | Verification |
|-----------|-------------|--------------|
| **Commercial Use** | Explicit permission for commercial applications | License text review |
| **Redistribution** | Can we redistribute derived data? | License text review |
| **Caching** | Local caching permitted? Max age? | License text review |
| **Attribution** | Required format and placement | License text review |
| **Retention** | Maximum data retention period | License text review |
| **Rate Limits** | Technical limits enforced by provider | Technical validation |
| **SLA** | Uptime, latency, support commitments | Contract review |
| **Cost** | Free tier limits, paid tier pricing | Commercial review |
| **Jurisdiction** | Governing law, data residency | Legal review |

---

## 2. Phase 1 Provider Register

| Provider | Data Types | License Status | Commercial Use | Redistribution | Caching | Attribution | Retention | Cost | Priority |
|----------|------------|----------------|----------------|----------------|---------|-------------|-----------|------|----------|
| **OpenBB Platform** | Equities, Options, Futures, Crypto, Macro, News, Fundamentals | MIT (platform), per-provider varies | ✅ Platform | ⚠️ Per provider | ✅ Platform | ✅ Platform | ✅ Platform | Free (core) | P0 |
| **yfinance** | Equities, ETFs, Basic Fundamentals | Unofficial (scraping) | ❓ Gray area | ❌ No | ⚠️ Limited | ❌ No | ❌ No | Free | P0 (fallback) |
| **FRED (St. Louis Fed)** | Macro indicators, Rates, Curves | Public Domain (US Gov) | ✅ Yes | ✅ Yes | ✅ Unlimited | ✅ "Source: FRED" | ✅ Unlimited | Free | P0 |
| **Alpha Vantage** | Equities, Forex, Crypto, Technical | Free tier: Non-commercial only | ❌ Free tier | ❌ Free tier | ✅ 5 req/min | ✅ Required | ⚠️ Cache only | Free tier / $50+/mo | P1 |
| **SEC EDGAR** | Company Filings (10-K, 10-Q, 8-K) | Public Domain (US Gov) | ✅ Yes | ✅ Yes | ✅ Unlimited | ✅ "Source: SEC" | ✅ Unlimited | Free | P1 |
| **Polygon.io** | Equities, Options, Forex, Crypto | Commercial license | ✅ Paid | ✅ Paid | ✅ Paid | ✅ Required | ✅ Paid | $199+/mo | P2 |
| **Refinitiv/ Eikon** | Comprehensive | Enterprise license | ✅ Enterprise | ⚠️ Restricted | ✅ Enterprise | ✅ Required | ✅ Enterprise | $$$$ | P3 |
| **Bloomberg** | Comprehensive | Enterprise license | ✅ Enterprise | ❌ No | ✅ Enterprise | ✅ Required | ✅ Enterprise | $$$$$ | P3 |
| **Twelve Data** | Equities, Forex, Crypto, Technical | Commercial license | ✅ Paid | ✅ Paid | ✅ Paid | ✅ Required | ✅ Paid | $8+/mo | P2 |
| **Finnhub** | Equities, Forex, Crypto, News | Commercial license | ✅ Paid | ✅ Paid | ✅ Paid | ✅ Required | ✅ Paid | Free tier / $50+/mo | P2 |
| **Quandl (Nasdaq)** | Futures, Commodities, Macro | Commercial license | ✅ Paid | ⚠️ Restricted | ✅ Paid | ✅ Required | ✅ Paid | $$$ | P2 |
| **IMF** | Macro, Financial Statistics | SDMX, free for non-commercial | ⚠️ Non-commercial | ⚠️ Non-commercial | ✅ Unlimited | ✅ Required | ✅ Unlimited | Free | P1 |
| **World Bank** | Development Indicators | CC BY 4.0 | ✅ Yes | ✅ Yes | ✅ Unlimited | ✅ Required | ✅ Unlimited | Free | P1 |
| **OECD** | Macro, Structural | Terms of Use | ✅ Non-commercial | ✅ Non-commercial | ✅ Unlimited | ✅ Required | ✅ Unlimited | Free | P1 |
| **BIS** | Banking, Financial Statistics | Free for research | ⚠️ Research only | ⚠️ Research only | ✅ Unlimited | ✅ Required | ✅ Unlimited | Free | P1 |
| **IDX (Indonesia)** | Indonesian Equities | License required | ❓ Requires license | ❓ Requires license | ❓ | ❓ | ❓ | License fee | P2 (ID focus) |
| **OJK (Indonesia)** | Financial Regulations, Supervision | Public | ✅ Yes | ✅ Yes | ✅ Unlimited | ✅ Required | ✅ Unlimited | Free | P2 (ID focus) |
| **Bank Indonesia** | Monetary, Payment Systems | Public | ✅ Yes | ✅ Yes | ✅ Unlimited | ✅ Required | ✅ Unlimited | Free | P2 (ID focus) |
| **BPS (Indonesia)** | Statistics Indonesia | Public | ✅ Yes | ✅ Yes | ✅ Unlimited | ✅ Required | ✅ Unlimited | Free | P2 (ID focus) |

---

## 3. License Compliance Matrix

### 3.1 OpenBB Provider Sub-Licenses (Critical)
OpenBB Platform aggregates 50+ providers. Each must be validated individually:

| OpenBB Provider | Data Type | Commercial Use | Redistribution | Caching | Notes |
|-----------------|-----------|----------------|----------------|---------|-------|
| `openbb-yfinance` | Equities | ⚠️ Scraping | ❌ | ⚠️ | Fallback only |
| `openbb-alpha-vantage` | Equities/Forex | ❌ Free tier | ❌ Free tier | ✅ 5/min | Paid tier needed for prod |
| `openbb-fred` | Macro | ✅ Public domain | ✅ | ✅ | Primary macro |
| `openbb-sec` | Filings | ✅ Public domain | ✅ | ✅ | Primary fundamentals |
| `openbb-fmp` | Fundamentals | ❌ Free tier | ❌ Free tier | ✅ 250/day | Paid for production |
| `openbb-tiingo` | EOD, Crypto | ❌ Free tier | ❌ Free tier | ✅ | Paid for production |
| `openbb-polygon` | Equities/Options | ✅ Paid | ✅ Paid | ✅ | Requires subscription |
| `openbb-intrinio` | Fundamentals | ✅ Paid | ✅ Paid | ✅ | Requires subscription |
| `openbb-benzinga` | News | ✅ Paid | ✅ Paid | ✅ | Requires subscription |
| `openbb-seeking-alpha` | Research | ❌ Free tier | ❌ Free tier | ❌ | Limited free |

### 3.2 Compliance Action Items

| Provider | Action Required | Owner | Deadline |
|----------|-----------------|-------|----------|
| OpenBB (all sub-providers) | Document each sub-provider license in `DATA_LICENSE_REGISTER.md` | Data Engineer | Phase 1 |
| yfinance | Legal opinion on scraping risk | Legal | Phase 1 |
| Alpha Vantage | Upgrade to paid tier for production | Product Owner | Phase 2 |
| Polygon.io | Evaluate cost/benefit for Phase 2 | Product Owner | Phase 2 |
| Indonesian providers (IDX, OJK, BI, BPS) | Obtain formal licenses | Legal | Phase 2 |

---

## 4. Data Lineage & License Tracking (Implementation)

### 4.1 Database Schema (from `DATABASE_SCHEMA.md`)
```sql
CREATE TABLE data_licenses (
    provider TEXT NOT NULL,
    dataset TEXT NOT NULL,
    commercial_use INTEGER NOT NULL,
    redistribution INTEGER NOT NULL,
    caching_allowed INTEGER NOT NULL,
    caching_max_age_days INTEGER,
    attribution_required INTEGER NOT NULL,
    attribution_text TEXT,
    retention_max_days INTEGER,
    license_url TEXT NOT NULL,
    last_reviewed DATE NOT NULL,
    reviewed_by TEXT NOT NULL,
    status TEXT NOT NULL,  -- ACTIVE, EXPIRED, RESTRICTED, UNKNOWN
    PRIMARY KEY (provider, dataset),
    FOREIGN KEY (provider) REFERENCES providers(id),
    FOREIGN KEY (reviewed_by) REFERENCES users(id)
);
```

### 4.2 Ingestion Pipeline License Checks
```python
# packages/data-infra/src/erin/data_infra/ingestion/license_check.py

async def validate_license_compliance(provider: ProviderId, dataset: DatasetId) -> LicenseCheckResult:
    license = await get_license(provider, dataset)
    
    if license.status != LicenseStatus.ACTIVE:
        return LicenseCheckResult(allowed=False, reason="License not active")
    
    if not license.commercial_use and is_commercial_context():
        return LicenseCheckResult(allowed=False, reason="Commercial use not permitted")
    
    # Check retention
    if license.retention_max_days:
        oldest_allowed = datetime.utcnow() - timedelta(days=license.retention_max_days)
        # Enforce in cleanup job
    
    return LicenseCheckResult(allowed=True, attribution=license.attribution_text)
```

### 4.3 Attribution Enforcement
- **UI:** Attribution badge on every data display (chart, table, quote)
- **Export:** Attribution included in CSV/PDF/Excel exports
- **API:** Attribution field in every response containing licensed data
- **Audit:** License compliance logged in `audit_events`

---

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| yfinance legal action | Medium | High | Use only as fallback; document risk; have paid alternatives ready |
| OpenBB sub-provider license change | Medium | Medium | Monitor OpenBB releases; automated license check in CI |
| Alpha Vantage free tier abuse | Low | Medium | Strict rate limiting; upgrade to paid before production |
| Indonesian provider access denied | Low | Medium | Engage early; have fallback data sources |
| Redistribution violation | Low | Critical | Automated license validation in ingestion pipeline |
| Attribution omission | Medium | Medium | Automated attribution injection in all outputs |

---

## 6. Review Process

1. **Quarterly:** Review all provider licenses for changes
2. **Per Release:** Validate license compliance for new datasets
3. **On Provider Change:** Immediate re-evaluation
4. **Legal Sign-off:** Required for any paid/commercial license

---

## 7. Approval

**Data Engineer:** _________________ **Date:** __________

**Legal Counsel:** _________________ **Date:** __________

**Chief Orchestrator:** _________________ **Date:** __________