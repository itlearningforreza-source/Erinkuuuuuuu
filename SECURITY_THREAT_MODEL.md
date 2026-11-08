# ERIN 2.0 — SECURITY THREAT MODEL

**Version:** 1.0
**Status:** DRAFT
**Classification:** INTERNAL — SECURITY
**Owner:** Security Engineer
**Phase:** 2 — Domain & System Architecture

---

## 1. Threat Modeling Methodology

**Framework:** STRIDE + Financial Domain Extensions
**Scope:** Full ERIN application (desktop + backend + AI)
**Assumptions:**
- Local workstation: Single user, trusted OS, 8 GB RAM
- Server deployment: Multi-user, network-exposed, hardened infrastructure
- AI: External LLM APIs + local small models

---

## 2. System Decomposition

### 2.1 Trust Boundaries

```
┌─────────────────────────────────────────────────────────────────────┐
│                      USER WORKSTATION (TRUSTED)                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ TAURI APP (UNTRUSTED CONTENT RENDERER)                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │
│  │  │ React UI    │  │ IPC Bridge  │  │ Rust Backend        │  │   │
│  │  │ (WebView)   │◄─┤ (Allowlist) │◄─┤ (Native, Trusted)   │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│         │                    │                    │                │
│         ▼                    ▼                    ▼                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ LOCAL FASTAPI (localhost:8000, UNTRUSTED NETWORK)           │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │
│  │  │ Domain APIs │  │ Internal    │  │ Provider Adapters   │  │   │
│  │  │ (AuthZ)     │  │ Event Bus   │  │ (External Calls)    │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│         │                    │                    │                │
│         ▼                    ▼                    ▼                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ DATA LAYER (TRUSTED STORAGE)                                 │   │
│  │  SQLite + DuckDB + Parquet + LanceDB (File System)          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (Future: Server Deployment)
┌─────────────────────────────────────────────────────────────────────┐
│                      SERVER INFRASTRUCTURE                           │
│  Load Balancer → API Pods → PostgreSQL / Redis / Object Storage     │
│  (TLS/mTLS)      (RBAC)     (Encrypted)    (Encrypted)              │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow Diagram (Key Flows)

| Flow | Source | Destination | Data Classification | Protection |
|------|--------|-------------|---------------------|------------|
| Market Data | Provider API | Ingestion Pipeline | Public/Market | TLS, signature verification |
| User Credentials | UI | Auth Service | Secret | Argon2id, TLS, short JWT |
| Portfolio Data | UI | Portfolio API | Confidential | TLS, RBAC, encryption at rest |
| AI Tool Calls | UI | AI Engine | Confidential | Sandbox, audit log, approval |
| Audit Events | All Services | Audit Log | Confidential | Append-only, hash chain |
| Model Results | Quant Engine | API | Confidential | TLS, RBAC |

---

## 3. STRIDE Analysis

### 3.1 Spoofing

| Threat ID | Scenario | Impact | Likelihood | Mitigation |
|-----------|----------|--------|------------|------------|
| STR-SPF-001 | Fake market data injected via compromised provider | Incorrect valuations, risk metrics | Medium | Provider adapter signature verification, multi-source reconciliation, data quality scoring |
| STR-SPF-002 | Session hijacking via stolen JWT | Unauthorized access to all user data | Medium | Short JWT expiry (15min), secure HttpOnly cookies, TLS, IP binding optional |
| STR-SPF-003 | Impersonation via stolen API keys (providers) | Unauthorized data access, cost abuse | Low | Key rotation, rate limiting, usage monitoring, secrets manager |
| STR-SPF-004 | Fake AI tool responses | Misleading research, wrong decisions | Medium | Tool allowlist, schema validation, output verification, audit trail |

### 3.2 Tampering

| Threat ID | Scenario | Impact | Likelihood | Mitigation |
|-----------|----------|--------|------------|------------|
| STR-TAM-001 | SQL injection in dynamic queries | Data corruption, exfiltration | Low | Parameterized queries only, ORM (SQLAlchemy), input validation |
| STR-TAM-002 | Parquet file modification on disk | Historical data corruption | Medium | File integrity monitoring (AIDE), append-only writes, checksums |
| STR-TAM-003 | Configuration modification | Security controls bypass | Low | Config checksums, signed config, immutable containers (server) |
| STR-TAM-004 | Model parameter manipulation | Incorrect risk/valuation outputs | Medium | Model version pinning, parameter validation, reproducibility hashes |
| STR-TAM-005 | AI prompt injection | Tool misuse, data exfiltration | High | System/user prompt separation, input sanitization, allowlist tools |

### 3.3 Repudiation

| Threat ID | Scenario | Impact | Likelihood | Mitigation |
|-----------|----------|--------|------------|------------|
| STR-REP-001 | User denies performing trade/valuation | Audit gap, compliance failure | Low | Immutable audit log with hash chain, digital signatures on exports |
| STR-REP-002 | Admin denies configuration change | Security incident investigation blocked | Low | Audit log for all admin actions, tamper-evident storage |
| STR-REP-003 | AI tool execution denied | Liability for automated actions | Medium | Full tool call audit with hash chain, human approval for HIGH/CRITICAL |

### 3.4 Information Disclosure

| Threat ID | Scenario | Impact | Likelihood | Mitigation |
|-----------|----------|--------|------------|------------|
| STR-INF-001 | PII in logs (email, positions) | Privacy violation, regulatory fine | Medium | Structured log redaction, log level control, no sensitive data in DEBUG |
| STR-INF-002 | Portfolio positions in error messages | Competitive intelligence leak | Medium | Error sanitization, generic user messages, detailed server-side only |
| STR-INF-003 | API keys in memory dumps | Credential theft | Low | Secrets manager (no env vars), memory zeroing, process isolation |
| STR-INF-004 | Model internals via AI responses | IP leakage | Medium | Output filtering, no internal params in responses, tool sandbox |

### 3.5 Denial of Service

| Threat ID | Scenario | Impact | Likelihood | Mitigation |
|-----------|----------|--------|------------|------------|
| STR-DOS-001 | Quote flood (10k+ symbols/sec) | UI freeze, memory exhaustion | Medium | Rate limiting per connection, backpressure, max subscription limit |
| STR-DOS-002 | Heavy backtest/simulation request | CPU/RAM exhaustion, 8GB limit breach | High | Resource quotas, job queue with priority, max concurrent jobs=2 |
| STR-DOS-003 | RAG query with massive context | LLM token limit, cost explosion | Medium | Token limits, chunk limits, query complexity scoring |
| STR-DOS-004 | Malicious Parquet (billion rows) | OOM on read | Low | Row group limits, schema validation, max file size check |

### 3.6 Elevation of Privilege

| Threat ID | Scenario | Impact | Likelihood | Mitigation |
|-----------|----------|--------|------------|------------|
| STR-ELE-001 | Tauri IPC exploit → native code execution | Full system compromise | Low | Capability allowlist, no `shell:allow-execute`, context isolation |
| STR-ELE-002 | Python deserialization (pickle) → RCE | Backend compromise | Low | No pickle, JSON/MessagePack only, Pydantic validation |
| STR-ELE-003 | Dependency confusion (malicious package) | Supply chain attack | Medium | Lockfiles, hash verification, sigstore, private registry |
| STR-ELE-004 | AI tool with WRITE access → file system | Data destruction, persistence | Medium | Read-only default, explicit approval, sandbox (seccomp/gVisor) |

---

## 4. Financial Domain Extensions

| Threat | Financial Impact | Mitigation |
|--------|------------------|------------|
| **Price Manipulation** | False VaR, incorrect P&L, bad trades | Multi-source reconciliation, outlier detection, manual override audit |
| **Model Drift** | Gradual valuation/risk errors | Model versioning, automated backtesting, monitoring alerts |
| **Data Poisoning** | Biased factors, wrong correlations | Data quality scores, lineage tracking, statistical validation |
| **Insider Trading Detection** | Compliance violation | Audit trail on sensitive data access, position change alerts |
| **Regulatory Reporting Errors** | Fines, license risk | Automated validation, reconciliation, audit trail |

---

## 5. Security Controls Matrix

| Control | Implementation | Verification |
|---------|----------------|--------------|
| **Authentication** | Argon2id (PBKDF), JWT HS256/RS256, MFA (TOTP) | Unit tests, penetration test |
| **Authorization** | RBAC middleware on all routes, resource-level permissions | Contract tests, integration tests |
| **Encryption in Transit** | TLS 1.3 (local: self-signed cert trusted), mTLS (server) | TLS scanner, cert validation |
| **Encryption at Rest** | SQLite: SQLCipher (optional), DuckDB: file encryption, Parquet: app-level | Key management review |
| **Secrets Management** | OS keychain (local), HashiCorp Vault/Sealed Secrets (server) | No secrets in code/config, rotation test |
| **Input Validation** | Pydantic strict mode on all APIs, allowlist enums | Fuzzing, property tests |
| **Output Encoding** | JSON serialization only, no template injection | Code review, SAST |
| **Rate Limiting** | Token bucket (Redis/local), per-endpoint config | Load test, chaos engineering |
| **Audit Logging** | Structured JSON, hash chain, immutable storage | Tamper detection test |
| **Dependency Scanning** | `cargo audit`, `pip-audit`, `npm audit`, Syft SBOM | CI gate, daily scheduled scan |
| **Container Hardening** | Distroless base, non-root, read-only fs, dropped capabilities | Trivy scan, CIS benchmark |
| **Desktop Hardening** | Tauri capability allowlist, no shell execute, CSP | Tauri audit, manual review |

---

## 6. AI Security Specific Controls

### 6.1 Tool Allowlist Framework
```python
# packages/ai-core/src/erin/ai_intelligence/security/tool_registry.py

TOOL_ALLOWLIST = {
    "market_data.get_quotes": ToolDef(
        read_only=True,
        sensitivity=SensitivityLevel.LOW,
        input_schema=GetQuotesInput,
        output_schema=QuoteBatch,
        sandbox_profile="network_readonly",
        timeout_seconds=10
    ),
    "portfolio.get_positions": ToolDef(
        read_only=True,
        sensitivity=SensitivityLevel.MEDIUM,
        input_schema=GetPositionsInput,
        output_schema=PositionsResponse,
        sandbox_profile="readonly",
        timeout_seconds=5
    ),
    "valuation.run_dcf": ToolDef(
        read_only=False,  # Creates valuation run
        sensitivity=SensitivityLevel.MEDIUM,
        input_schema=DCFInput,
        output_schema=ValuationRun,
        sandbox_profile="compute",
        timeout_seconds=30,
        requires_approval=False
    ),
    "filesystem.write_report": ToolDef(
        read_only=False,
        sensitivity=SensitivityLevel.HIGH,
        input_schema=WriteReportInput,
        output_schema=WriteReportOutput,
        sandbox_profile="filesystem_user_selected",
        timeout_seconds=10,
        requires_approval=True  # Human confirmation UI
    ),
    "code.execute_python": ToolDef(
        read_only=False,
        sensitivity=SensitivityLevel.CRITICAL,
        input_schema=ExecutePythonInput,
        output_schema=ExecutePythonOutput,
        sandbox_profile="python_seccomp",  # No network, no fs, limited CPU/mem
        timeout_seconds=60,
        requires_approval=True
    )
}
```

### 6.2 Sandbox Profiles
| Profile | Capabilities | Restrictions |
|---------|--------------|--------------|
| `network_readonly` | HTTP GET to allowlisted domains | No POST, no localhost, no file access |
| `readonly` | Read SQLite/DuckDB | No writes, no network |
| `compute` | CPU, memory, NumPy/SciPy | No network, no file I/O, 30s timeout |
| `filesystem_user_selected` | Write to user-picked path via dialog | No arbitrary paths, no execute |
| `python_seccomp` | Python stdlib + allowlisted packages | seccomp: no network, no fs, no spawn, 128MB RAM |

### 6.3 Prompt Injection Defenses
1. **System Prompt Isolation:** System prompt never exposed to user
2. **Input Sanitization:** Strip control characters, limit length, detect injection patterns
3. **Output Parsing:** Strict JSON schema validation on tool calls
4. **Tool Call Verification:** Every call checked against allowlist + user permissions
5. **Context Window Limits:** Max 4k tokens user input, 8k total

---

## 7. Desktop-Specific (Tauri)

### 7.1 Capability Allowlist (Minimal)
```json
{
  "capabilities": [
    "core:app:allow-exit",
    "core:window:allow-create",
    "core:window:allow-show",
    "core:window:allow-hide",
    "core:menu:allow-create",
    "fs:allow-read-file",      // User-selected via dialog only
    "fs:allow-write-file",     // User-selected via dialog only
    "fs:allow-read-dir",       // User-selected via dialog only
    "dialog:allow-open",
    "dialog:allow-save",
    "shell:allow-open",        // https:// URLs only
    "http:allow-request"       // localhost:8000 only
  ],
  "deny": [
    "shell:allow-execute",
    "fs:allow-read-all",
    "fs:allow-write-all",
    "protocol:allow-asset",
    "protocol:allow-asset-scope"
  ]
}
```

### 7.2 IPC Security
- **Allowlist:** Only explicitly defined commands
- **Schema Validation:** Every IPC message validated via JSON Schema
- **No Eval:** No dynamic code execution in Rust or JS
- **Context Isolation:** WebView `contextIsolation: true`, `nodeIntegration: false`

---

## 8. Server Deployment Hardening (Future)

| Layer | Controls |
|-------|----------|
| **Network** | VPC, private subnets, security groups, WAF, DDoS protection |
| **Compute** | Distroless containers, non-root, read-only rootfs, gVisor/Kata |
| **Data** | PostgreSQL TDE, S3 SSE-KMS, automatic key rotation, backup encryption |
| **Identity** | OIDC (Keycloak), mTLS service mesh (Istio/Linkerd), SPIFFE |
| **Observability** | Centralized logging (Loki), metrics (Prometheus), tracing (Tempo), SIEM integration |
| **Supply Chain** | Sigstore cosign, SLSA Level 3, admission controller (Kyverno) |

---

## 9. Security Testing Requirements

| Test Type | Frequency | Tools | Gate |
|-----------|-----------|-------|------|
| **SAST** | Every PR | Bandit, cargo-audit, Semgrep, SonarQube | CI block on HIGH |
| **DAST** | Weekly | OWASP ZAP, custom scripts | Release gate |
| **Dependency Scan** | Every PR + Daily | Syft + Grype, pip-audit, npm audit | CI block on CRITICAL |
| **Container Scan** | Every build | Trivy, Hadolint | CI block on HIGH |
| **Penetration Test** | Quarterly | Internal team + external | Release gate |
| **Threat Model Review** | Per major feature | STRIDE workshop | ADR required |
| **Red Team Exercise** | Annual | External firm | Board report |

---

## 10. Incident Response

### 10.1 Severity Levels
| Level | Definition | Response Time | Escalation |
|-------|------------|---------------|------------|
| **SEV-1 (Critical)** | Active exploit, data breach, full outage | 15 min | CISO, CEO, Legal |
| **SEV-2 (High)** | Vulnerability with exploit, partial outage | 1 hour | Security Lead, Engineering Lead |
| **SEV-3 (Medium)** | Vulnerability no exploit, degraded performance | 4 hours | Security Engineer |
| **SEV-4 (Low)** | Info disclosure minor, config drift | 24 hours | Security Engineer |

### 10.2 Response Playbook (SEV-1)
1. **Detect** → Alert (PagerDuty/email)
2. **Contain** → Isolate affected component (kill process, revoke tokens, block IP)
3. **Assess** → Determine scope (data accessed, systems compromised)
4. **Eradicate** → Patch vulnerability, rotate all credentials
5. **Recover** → Restore from clean backup, verify integrity
6. **Post-Mortem** → 48h blameless post-mortem, action items tracked

---

## 11. Compliance Mapping

| Requirement | ERIN Control | Evidence |
|-------------|--------------|----------|
| **OWASP ASVS 5.0 L2** | All V2-L2 controls implemented | Self-assessment + evidence |
| **NIST SSDF** | Secure development practices | SDLC documentation |
| **SOC 2 Type II** | Audit logging, access control, encryption | Audit artifacts (server) |
| **GDPR** | Data minimization, right to deletion, DPIA | Privacy impact assessment |
| **Financial Regulations** | Audit trail, data lineage, model governance | Compliance register |

---

## 12. Approval

**Security Engineer:** _________________ **Date:** __________

**Principal Architect:** _________________ **Date:** __________

**Chief Orchestrator:** _________________ **Date:** __________