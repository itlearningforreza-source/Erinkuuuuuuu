#!/usr/bin/env python3
"""
ERIN Engineering Control Plane - Security Scanner

Runs comprehensive security scans: SAST, dependency audit, container scan, secrets.
"""

import subprocess
import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class SecurityFinding:
    scanner: str
    severity: str
    file: str
    line: int
    rule: str
    message: str
    cve: str = ""

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}

def run_command(cmd: List[str]) -> subprocess.CompletedProcess:
    """Run a command and return completed process."""
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)

def parse_bandit(output: str) -> List[SecurityFinding]:
    findings = []
    try:
        data = json.loads(output)
        for result in data.get("results", []):
            findings.append(SecurityFinding(
                scanner="bandit",
                severity=result.get("issue_severity", "MEDIUM").upper(),
                file=result.get("filename", ""),
                line=result.get("line_number", 0),
                rule=result.get("test_id", ""),
                message=result.get("issue_text", ""),
            ))
    except json.JSONDecodeError:
        pass
    return findings

def parse_cargo_audit(output: str) -> List[SecurityFinding]:
    findings = []
    try:
        data = json.loads(output)
        for vuln in data.get("vulnerabilities", {}).get("list", []):
            findings.append(SecurityFinding(
                scanner="cargo-audit",
                severity=vuln.get("severity", "MEDIUM").upper(),
                file=vuln.get("package", ""),
                line=0,
                rule=vuln.get("id", ""),
                message=vuln.get("description", ""),
                cve=vuln.get("id", ""),
            ))
    except json.JSONDecodeError:
        pass
    return findings

def parse_npm_audit(output: str) -> List[SecurityFinding]:
    findings = []
    try:
        data = json.loads(output)
        for vuln in data.get("vulnerabilities", {}).values():
            sev = vuln.get("severity", "moderate").upper()
            if sev == "MODERATE":
                sev = "MEDIUM"
            findings.append(SecurityFinding(
                scanner="npm-audit",
                severity=sev,
                file=vuln.get("name", ""),
                line=0,
                rule=vuln.get("via", [{}])[0].get("title", "") if vuln.get("via") else "",
                message=vuln.get("overview", ""),
            ))
    except json.JSONDecodeError:
        pass
    return findings

def parse_pip_audit(output: str) -> List[SecurityFinding]:
    findings = []
    try:
        data = json.loads(output)
        for vuln in data.get("vulnerabilities", []):
            findings.append(SecurityFinding(
                scanner="pip-audit",
                severity=vuln.get("severity", "MEDIUM").upper(),
                file=vuln.get("package", ""),
                line=0,
                rule=vuln.get("id", ""),
                message=vuln.get("description", ""),
                cve=vuln.get("id", ""),
            ))
    except json.JSONDecodeError:
        pass
    return findings

def run_scanner(name: str, cmd: List[str], parser) -> List[SecurityFinding]:
    print(f"Running {name}...")
    result = run_command(cmd)
    if result.returncode != 0 and result.returncode != 1:  # 1 often means findings found
        print(f"  {name} failed with exit code {result.returncode}")
        print(result.stderr[:500])
        return []
    return parser(result.stdout)

def main():
    parser = argparse.ArgumentParser(description="ERIN Security Scanner")
    parser.add_argument("--fast", action="store_true", help="Run only fast scanners")
    parser.add_argument("--output", type=Path, help="Output JSON file")
    args = parser.parse_args()

    all_findings = []

    # Python SAST
    result = run_command(["bandit", "-r", ".", "-f", "json", "-x", "tests,models,scripts"])
    all_findings.extend(parse_bandit(result.stdout))

    # Rust audit
    result = run_command(["cargo", "audit", "--json"])
    all_findings.extend(parse_cargo_audit(result.stdout))

    # Node audit
    result = run_command(["pnpm", "audit", "--json"])
    all_findings.extend(parse_npm_audit(result.stdout))

    # Python pip-audit
    result = run_command(["pip-audit", "--format=json"])
    all_findings.extend(parse_pip_audit(result.stdout))

    if not args.fast:
        # Semgrep
        result = run_command(["semgrep", "--config=auto", "--json", "--quiet", "."])
        try:
            data = json.loads(result.stdout)
            for r in data.get("results", []):
                all_findings.append(SecurityFinding(
                    scanner="semgrep",
                    severity=r.get("extra", {}).get("severity", "MEDIUM").upper(),
                    file=r.get("path", ""),
                    line=r.get("start", {}).get("line", 0),
                    rule=r.get("check_id", ""),
                    message=r.get("extra", {}).get("message", ""),
                ))
        except json.JSONDecodeError:
            pass

        # TruffleHog (secrets)
        result = run_command(["trufflehog", "filesystem", ".", "--json"])
        try:
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    data = json.loads(line)
                    all_findings.append(SecurityFinding(
                        scanner="trufflehog",
                        severity="HIGH",
                        file=data.get("path", ""),
                        line=data.get("line", 0),
                        rule="SECRET_DETECTED",
                        message=data.get("secret", "")[:100],
                    ))
        except json.JSONDecodeError:
            pass

    # Sort by severity
    all_findings.sort(key=lambda f: SEVERITY_ORDER.get(f.severity, 5))

    # Print summary
    print(f"\n{'='*60}")
    print(f"SECURITY SCAN SUMMARY")
    print(f"{'='*60}")

    by_severity = {}
    for f in all_findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1

    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        count = by_severity.get(sev, 0)
        if count > 0:
            print(f"  {sev:8}: {count}")

    total = len(all_findings)
    print(f"  {'TOTAL':8}: {total}")

    # Check gate
    critical_high = sum(1 for f in all_findings if f.severity in ("CRITICAL", "HIGH"))
    if critical_high > 0:
        print(f"\n✗ SECURITY GATE FAILED: {critical_high} critical/high findings")
        for f in all_findings:
            if f.severity in ("CRITICAL", "HIGH"):
                print(f"  [{f.severity}] {f.scanner}: {f.file}:{f.line} - {f.message}")
        sys.exit(1)
    else:
        print("\n✓ Security gate passed - no critical/high findings")
        sys.exit(0)

if __name__ == "__main__":
    main()