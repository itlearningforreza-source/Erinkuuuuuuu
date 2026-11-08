# ERIN 2.0 — RESOURCE AND PERFORMANCE POLICY

**Version:** 1.0
**Status:** DRAFT
**Classification:** INTERNAL — RESOURCE GOVERNANCE
**Owner:** Site Reliability Engineer
**Phase:** 2 — Domain & System Architecture

---

## 1. Hardware Constraints (Binding)

**Development Workstation:** 8 GB RAM, 4+ CPU cores, SSD storage
**Binding Constraint:** ERIN must run entirely within **6 GB peak RSS** leaving 2 GB for OS.

---

## 2. Memory Budgets

### 2.1 Profile Definitions

| Profile | Use Case | Peak RSS Target | CPU Target | Services Active |
|---------|----------|-----------------|------------|-----------------|
| **minimal** | Core terminal only (watchlists, charts) | 3.5 GB | 30% | API, DB, UI |
| **standard** | Full local development (all Phase 1 domains) | 6.0 GB | 60% | API, DB, UI, Workers, RAG, Quant |
| **ci** | Headless test execution | 4.0 GB | 100% | API, DB, Workers |
| **server** | Production (no local limit) | Unlimited | Auto | All |

### 2.2 Component Memory Allocations (Standard Profile)

| Component | Budget | Strategy |
|-----------|--------|----------|
| **Tauri WebView (React)** | 800 MB | Lazy-load panels, virtualize lists, unmount hidden |
| **FastAPI (uvicorn, 2 workers)** | 400 MB | `--workers 2`, `--limit-concurrency 50` |
| **DuckDB (analytical)** | 1.5 GB | `memory_limit='2GB'`, stream Parquet, no full scans |
| **SQLite (transactional)** | 100 MB | WAL mode, connection pool (5) |
| **Python Quant Stack** | 1.2 GB | Import on demand (`importlib`), no global DataFrames |
| **LanceDB (vector)** | 500 MB | Quantized vectors (int8), disk-backed index |
| **Background Workers** | 500 MB | Max 2 concurrent, sequential for heavy tasks |
| **OS / Buffer** | 1.0 GB | — |
| **TOTAL** | **~6.0 GB** | **Within 8 GB** |

### 2.3 Memory Enforcement

```python
# scripts/ecp/resource_profile.py enforcement
import psutil
import resource

def enforce_memory_limit(limit_mb: int):
    """Set hard limit on process memory (Linux)"""
    limit_bytes = limit_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))

def monitor_memory(profile: str) -> MemoryReport:
    """Continuous monitoring with alerting"""
    budget = BUDGETS[profile]["peak_rss_mb"]
    current = psutil.Process().memory_info().rss / 1024 / 1024
    if current > budget * 0.9:
        warn(f"Memory at {current:.0f}MB > 90% of {budget}MB budget")
    if current > budget:
        error(f"MEMORY BUDGET EXCEEDED: {current:.0f}MB > {budget}MB")
    return MemoryReport(current=current, budget=budget, profile=profile)
```

---

## 3. CPU Budgets

| Component | Standard Profile | Strategy |
|-----------|------------------|----------|
| **UI Event Loop** | < 10% avg | 60fps target, idle when inactive |
| **FastAPI Workers** | < 30% avg | Async I/O, thread pool for blocking |
| **DuckDB Queries** | < 20% avg | Columnar, predicate pushdown, parallel=4 |
| **Quant Computations** | Burst to 80% | Job queue, max 2 concurrent, `nice +10` |
| **Background Ingestion** | < 15% avg | Rate limited, batched, off-peak preferred |
| **AI/RAG** | Burst to 50% | Token limits, quantized embeddings |

**Enforcement:** `cpulimit` or cgroups (Linux), job queue priorities.

---

## 4. Storage Budgets

| Data Type | Local Budget | Growth Rate | Retention | Archival |
|-----------|--------------|-------------|-----------|----------|
| **SQLite (transactional)** | 500 MB | 10 MB/month | Forever | Backup only |
| **DuckDB (analytical)** | 2 GB | 500 MB/month | Forever | Export to Parquet |
| **Parquet (historical)** | 5 GB | 1 GB/month | Forever | Tiered (hot/warm/cold) |
| **LanceDB (vectors)** | 1 GB | 200 MB/month | Forever | Rebuildable |
| **Logs/Audit** | 500 MB | 100 MB/month | 7 years | Compressed, rotated |
| **Model Artifacts** | 1 GB | 100 MB/month | Versioned | Immutable |
| **TOTAL** | **~10 GB** | **~2 GB/month** | | |

**Enforcement:** Disk quota monitoring, automatic cleanup of old Parquet partitions (configurable).

---

## 5. Worker Concurrency

| Worker Type | Max Concurrent | Queue Priority | Timeout |
|-------------|----------------|----------------|---------|
| **Ingestion** | 2 | HIGH | 30 min |
| **Quant/Simulation** | 1 | NORMAL | 1 hour |
| **Valuation/VaR** | 2 | HIGH | 10 min |
| **Backtest** | 1 | LOW | 4 hours |
| **AI/RAG** | 2 | NORMAL | 5 min |
| **Report Generation** | 1 | LOW | 10 min |

**Implementation:** BullMQ with Redis (server) / SQLite-backed queue (local)

---

## 6. Cache Limits

| Cache | Max Size | Eviction | TTL |
|-------|----------|----------|-----|
| **Quote Cache (WebSocket)** | 10,000 symbols | LRU | 5 min |
| **Instrument Master** | 50,000 | LRU | 24 hours |
| **Company Fundamentals** | 5,000 | LRU | 1 hour |
| **Valuation Results** | 1,000 | LRU | 4 hours |
| **RAG Embeddings** | 100,000 chunks | LFU | 30 days |
| **Chart Data (frontend)** | 50 charts | LRU | Session |

---

## 7. Dataset Limits (Local)

| Dataset | Max Records | Partitioning | Notes |
|---------|-------------|--------------|-------|
| **Equity Quotes (1min)** | 50M rows | Daily + Symbol | ~2 years for 500 symbols |
| **Equity Quotes (1day)** | 5M rows | Daily | 20+ years |
| **Options Chains** | 10M rows | Daily + Expiry | Active expiries only |
| **Bond Prices** | 1M rows | Daily | Government + IG corp |
| **Macro Indicators** | 500K rows | Monthly | FRED + IMF + OECD |
| **News Articles** | 1M rows | Monthly | Full text in separate store |
| **Financial Statements** | 100K rows | Quarterly | Per company |

---

## 8. Development Profiles Configuration

```yaml
# erin_resource_policy.yml
profiles:
  minimal:
    description: "Core terminal only - watchlists, charts, basic quotes"
    services:
      - api
      - sqlite
      - duckdb
      - ui
    workers: 1
    features:
      market_intel: true
      equity_research: false
      quant_finance: false
      portfolio_risk: false
      fixed_income: false
      derivatives: false
      macro_intel: false
      news_intel: false
      workspace: false
      ai_intelligence: false
    memory_limit_mb: 3500

  standard:
    description: "Full local development - all Phase 1 domains"
    services:
      - api
      - sqlite
      - duckdb
      - ui
      - workers
      - rag
      - quant
    workers: 2
    features:
      market_intel: true
      equity_research: true
      quant_finance: true
      portfolio_risk: true
      fixed_income: true
      derivatives: true
      macro_intel: true
      news_intel: true
      workspace: true
      ai_intelligence: true
    memory_limit_mb: 6000

  ci:
    description: "Headless CI - no UI, full test suite"
    services:
      - api
      - sqlite
      - duckdb
      - workers
    workers: 2
    features:
      market_intel: true
      equity_research: true
      quant_finance: true
      portfolio_risk: true
      fixed_income: true
      derivatives: true
      macro_intel: true
      news_intel: true
      workspace: false
      ai_intelligence: false
    memory_limit_mb: 4000

  server:
    description: "Production server - no local limits"
    services: [all]
    workers: auto
    features: [all]
    memory_limit_mb: unlimited
```

---

## 9. Performance Benchmarks (Phase 1 Targets)

| Operation | Target (Standard Profile) | Measurement Method |
|-----------|---------------------------|-------------------|
| **App Cold Start** | < 3 seconds | Tauri launch to interactive UI |
| **Quote Update Latency** | < 500ms end-to-end | Provider → WebSocket → UI |
| **Watchlist Load (100 symbols)** | < 200ms | SQLite query + UI render |
| **Chart Render (1yr daily)** | < 100ms | Lightweight Charts 60fps |
| **DCF Calculation (100 scenarios)** | < 2 seconds | Python quant core |
| **Historical VaR (5yr, 1000 assets)** | < 5 seconds | DuckDB + NumPy |
| **Monte Carlo (10k paths, 252 steps)** | < 10 seconds | Vectorized NumPy |
| **Bond Analytics (yield curve)** | < 500ms | QuantLib comparison |
| **BSM Price + Greeks** | < 0.1 ms/option | 1M iterations benchmark |
| **Full Test Suite** | < 5 minutes | pytest + vitest parallel |
| **Resource Profile (standard)** | ≤ 6 GB peak RSS | `resource_profile.py` |

---

## 10. Profiling & Optimization Workflow

1. **Baseline:** Run `resource_profile.py --profile standard` on clean main
2. **Identify:** `py-spy` / `perf` / `cargo flamegraph` for hot paths
3. **Optimize:** Target > 5% of total time or > 100MB allocation
4. **Verify:** Re-run benchmark, compare to baseline
5. **Gate:** CI fails if regression > 10% on any benchmark

---

## 11. Approval

**Site Reliability Engineer:** _________________ **Date:** __________

**Principal Architect:** _________________ **Date:** __________

**Chief Orchestrator:** _________________ **Date:** __________