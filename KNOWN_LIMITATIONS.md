# ERIN 2.0 — KNOWN LIMITATIONS

**Version:** 1.0
**Status:** ACTIVE
**Classification:** INTERNAL — TRANSPARENCY
**Owner:** Chief Orchestrator

---

## Purpose

This document records known limitations, constraints, and unresolved problems in ERIN. It is updated continuously and published with every release. Transparency about limitations is a core engineering principle (Part II, Principle 9).

---

## 1. Architectural Limitations

| ID | Limitation | Impact | Mitigation | Target Resolution |
|----|------------|--------|------------|-------------------|
| LIM-ARCH-001 | **Single-process failure domain** — All contexts share process; crash affects entire app | High availability not achievable locally | Documented migration path to distributed services (Phase 15) | Phase 15 |
| LIM-ARCH-002 | **No horizontal scaling locally** — Single workstation bound | Cannot handle enterprise load locally | Server deployment (Phase 15) designed for scaling | Phase 15 |
| LIM-ARCH-003 | **Internal HTTP overhead** — Localhost HTTP for cross-context calls adds ~1ms latency | Minor performance impact on chained calls | Acceptable for Phase 1; gRPC option for server | Phase 14 |
| LIM-ARCH-004 | **Bounded context enforcement via tooling only** — No language-level enforcement | Discipline required; ECP catches violations | ECP `arch_check.py` runs on every commit | Ongoing |

---

## 2. Data Limitations

| ID | Limitation | Impact | Mitigation | Target Resolution |
|----|------------|--------|------------|-------------------|
| LIM-DATA-001 | **yfinance is unofficial/scraping** — Legal risk, unreliable, no SLA | Production data quality risk | Fallback only; paid providers (Polygon, Refinitiv) for production | Phase 2 |
| LIM-DATA-002 | **OpenBB sub-provider licenses vary** — Some restrict commercial use/redistribution | Compliance risk if not tracked | License register per provider; automated ingestion checks | Phase 1 |
| LIM-DATA-003 | **No real-time Level 2 data** — Only Level 1 (top of book) via free providers | Cannot build order book visualization, VWAP/TWAP | Documented; licensed feed required for Level 2 | Phase 10 |
| LIM-DATA-004 | **Corporate action adjustments not implemented** — Raw prices not split/dividend adjusted | Historical returns inaccurate | Skeleton in data model; implementation Phase 5+ | Phase 5 |
| LIM-DATA-005 | **No data reconciliation across providers** — Single source per instrument | Potential undetected data errors | Multi-source reconciliation planned | Phase 5 |
| LIM-DATA-006 | **Limited historical depth for some providers** — yfinance ~20y, FRED varies | Long-term backtesting constrained | Document per provider; supplement with paid | Ongoing |
| LIM-DATA-007 | **No fundamental data for non-US markets (Phase 1)** — SEC EDGAR only | International equity research limited | SEDAR, Companies House adapters planned | Phase 6 |

---

## 3. Financial Model Limitations

| ID | Limitation | Impact | Mitigation | Target Resolution |
|----|------------|--------|------------|-------------------|
| LIM-FM-001 | **BSM assumes constant volatility** — No volatility smile/skew | Mispricing OTM options | Documented; Heston/surface models Phase 9 | Phase 9 |
| LIM-FM-002 | **BSM European only** — No American early exercise | Cannot price American equities correctly | Binomial CRR implemented for American | Phase 9 |
| LIM-FM-003 | **Historical VaR assumes stationary returns** — Regime changes not captured | Underestimates risk in crises | Stress testing + regime detection planned | Phase 8 |
| LIM-FM-004 | **Parametric VaR assumes normal returns** — Fat tails ignored | Underestimates tail risk | Expected Shortfall + stress testing | Phase 8 |
| LIM-FM-005 | **DCF uses constant WACC** — No term structure, no changing capital structure | Valuation drift over horizon | Multi-stage WACC, scenario analysis | Phase 6 |
| LIM-FM-006 | **No transaction cost model in backtesting (Phase 1)** — Zero-cost assumption | Overstates strategy returns | TCA framework Phase 10 | Phase 10 |
| LIM-FM-007 | **No survivorship bias handling in backtesting** — Delisted stocks excluded | Overstates historical returns | Documented; universe management Phase 10 | Phase 10 |
| LIM-FM-008 | **Monte Carlo uses GBM only** — No jump diffusion, stochastic vol | Path distribution inaccurate for tails | Jump diffusion, Heston Phase 7 | Phase 7 |
| LIM-FM-009 | **Factor models limited to PCA/Regression** — No dynamic factors, ML | Misses regime-dependent factors | ML factor models Phase 7 | Phase 7 |
| LIM-FM-010 | **No credit risk models** — Only market risk VaR | Cannot assess bond portfolio credit risk | Credit risk Phase 9 | Phase 9 |

---

## 4. UI/UX Limitations

| ID | Limitation | Impact | Mitigation | Target Resolution |
|----|------------|--------|------------|-------------------|
| LIM-UI-001 | **No multi-monitor workspace persistence** — Layout saved per window | Power users limited | Multi-window support planned | Phase 4+ |
| LIM-UI-002 | **Chart synchronization limited to crosshair** — No linked intervals, studies | Analysis workflow incomplete | Full sync engine Phase 4 | Phase 4 |
| LIM-UI-003 | **No drag-and-drop chart studies** — Studies added via menu | Slower workflow | Drag-drop Phase 4+ | Phase 4+ |
| LIM-UI-004 | **Command bar search limited to commands** — No data/entity search | Discovery slower | Global search Phase 4+ | Phase 4+ |
| LIM-UI-005 | **No collaborative workspaces (Phase 1)** — Single user only | Team workflows not supported | Multi-user Phase 15 | Phase 15 |
| LIM-UI-006 | **Accessibility: Screen reader testing incomplete** — WCAG AA target | Compliance risk | Audit Phase 13 | Phase 13 |

---

## 5. AI/ML Limitations

| ID | Limitation | Impact | Mitigation | Target Resolution |
|----|------------|--------|------------|-------------------|
| LIM-AI-001 | **No local LLM (8 GB RAM constraint)** — Requires external API | Privacy, cost, latency | Small local models (Ollama) optional; API default | Phase 12 |
| LIM-AI-002 | **RAG limited to LanceDB (no hybrid graph)** — No knowledge graph | Entity relationships not captured | Graph RAG Phase 12+ | Phase 12+ |
| LIM-AI-003 | **Tool sandbox uses seccomp (Linux only)** — Windows/macOS different | Cross-platform security inconsistency | gVisor/Firecracker for server | Phase 13 |
| LIM-AI-004 | **Prompt injection defenses basic** — Pattern matching only | Sophisticated attacks may bypass | Advanced defenses Phase 13 | Phase 13 |
| LIM-AI-005 | **No model fine-tuning pipeline** — Cannot customize embeddings/LLM | Generic performance only | Fine-tuning pipeline Phase 12+ | Phase 12+ |
| LIM-AI-006 | **FinBERT sentiment only English** — No multilingual | Non-English news not analyzed | Multilingual models Phase 11+ | Phase 11+ |

---

## 5. Performance Limitations

| ID | Limitation | Impact | Mitigation | Target Resolution |
|----|------------|--------|------------|-------------------|
| LIM-PERF-001 | **8 GB RAM hard limit** — No large in-memory datasets | Must stream/chunk all large ops | DuckDB streaming, Parquet partitioning | Ongoing |
| LIM-PERF-002 | **DuckDB single-writer** — Concurrent ingestion blocks | Ingestion pipeline serialized | Batch ingestion, off-peak scheduling | Ongoing |
| LIM-PERF-003 | **Python GIL limits CPU parallelism** — Quant compute single-threaded | Monte Carlo slower than Rust/C++ | Release GIL (NumPy), Rust for hot paths | Phase 7+ |
| LIM-PERF-004 | **WebView memory not directly controllable** — Chromium/WebKit internal | UI memory spikes possible | Lazy panels, virtualization, unmounting | Ongoing |
| LIM-PERF-005 | **No GPU acceleration (local)** — CPU-only quant compute | Large simulations slow | Optional CUDA/Metal for server | Phase 14 |

---

## 6. Security Limitations

| ID | Limitation | Impact | Mitigation | Target Resolution |
|----|------------|--------|------------|-------------------|
| LIM-SEC-001 | **Local secret storage uses OS keychain only** — No HSM | Secrets accessible if OS compromised | Documented; server uses Vault | Phase 15 |
| LIM-SEC-002 | **No hardware security module (HSM) integration** — Key signing software-only | Supply chain risk | Cosign keyless + TUF for server | Phase 15 |
| LIM-SEC-003 | **Audit log stored locally (SQLite)** — Tampering possible with file access | Hash chain detects but doesn't prevent | Immutable storage (WORM) for server | Phase 15 |
| LIM-SEC-004 | **No network segmentation locally** — All services localhost | Lateral movement if compromised | Server: mTLS, network policies | Phase 15 |
| LIM-SEC-005 | **Dependency scanning only at build time** — Runtime vulns missed | Zero-day between scans | Daily scheduled scans, runtime monitoring | Phase 13 |

---

## 7. Operational Limitations

| ID | Limitation | Impact | Mitigation | Target Resolution |
|----|------------|--------|------------|-------------------|
| LIM-OPS-001 | **No automated backup/restore (local)** — Manual `.backup` | Data loss risk on disk failure | Documented procedure; automated Phase 13 | Phase 13 |
| LIM-OPS-002 | **No disaster recovery plan (local)** — Single machine | Total loss unrecoverable | Documented; server has DR | Phase 15 |
| LIM-OPS-003 | **No log aggregation (local)** — Files only | Debugging harder | Structured JSON logs; Loki for server | Phase 13 |
| LIM-OPS-004 | **Single developer bus factor** — Knowledge concentrated | Project risk | Documentation-first, ADRs, ECP automation | Ongoing |

---

## 8. Regulatory/Compliance Limitations

| ID | Limitation | Impact | Mitigation | Target Resolution |
|----|------------|--------|------------|-------------------|
| LIM-REG-001 | **Not SOC 2 / ISO 27001 certified** — No formal audit | Enterprise sales blocked | Security controls documented; audit Phase 15 | Phase 15 |
| LIM-REG-002 | **No MiFID II / EMIR reporting** — Trade reporting missing | Regulatory use not supported | Reporting engine Phase 10+ | Phase 10+ |
| LIM-REG-003 | **No Basel III capital models** — Risk models not regulatory | Cannot use for regulatory capital | Documented; not a goal | N/A |
| LIM-REG-004 | **GDPR: Right to deletion manual** — No automated DSAR | Compliance effort high | Automated DSAR Phase 15 | Phase 15 |

---

## 9. Platform Limitations

| ID | Limitation | Impact | Mitigation | Target Resolution |
|----|------------|--------|------------|-------------------|
| LIM-PLAT-001 | **Windows: WebView2 bootstrapper required** — Extra install step | Friction for users | Bundle bootstrapper in installer | Phase 4 |
| LIM-PLAT-002 | **Linux: WebKitGTK system dependency** — Version varies by distro | Compatibility testing needed | Test on Ubuntu/Fedora/Arch; Flatpak | Phase 4 |
| LIM-PLAT-003 | **macOS: Not tested (Phase 1)** — WebView different | Unknown issues | macOS support Phase 4+ | Phase 4+ |
| LIM-PLAT-004 | **ARM64: Not tested (Phase 1)** — Apple Silicon, AWS Graviton | Performance unknown | CI on ARM64 Phase 14 | Phase 14 |

---

## 10. Maintenance

This document is reviewed at every phase gate. New limitations are added as discovered. Resolved limitations are moved to `CHANGELOG.md` with resolution version.

**Next Review:** Phase 2 Gate