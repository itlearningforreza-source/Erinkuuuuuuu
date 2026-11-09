"""Penetration Testing & Vulnerability Scanning - Security testing framework."""

import asyncio
import hashlib
import json
import logging
import secrets
import socket
import ssl
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Callable, TYPE_CHECKING
import nmap
import requests
import re
import os
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
import aiohttp
import yaml

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ScanType(str, Enum):
    NETWORK = "NETWORK"
    WEB_APPLICATION = "WEB_APPLICATION"
    API = "API"
    DATABASE = "DATABASE"
    CONFIGURATION = "CONFIGURATION"
    DEPENDENCY = "DEPENDENCY"
    CONTAINER = "CONTAINER"
    INFRASTRUCTURE = "INFRASTRUCTURE"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ScanStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class Vulnerability:
    """Security vulnerability finding."""
    vuln_id: str = field(default_factory=lambda: f"vuln_{secrets.token_hex(8)}")
    title: str = ""
    description: str = ""
    severity: Severity = Severity.INFO
    cvss_score: float = 0.0
    cve_id: str = ""
    cwe_id: str = ""
    affected_component: str = ""
    affected_version: str = ""
    fixed_version: str = ""
    location: str = ""
    evidence: str = ""
    remediation: str = ""
    references: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    scanner: str = ""
    scan_id: str = ""
    false_positive: bool = False
    risk_accepted: bool = False
    remediation_status: str = "OPEN"  # OPEN, IN_PROGRESS, FIXED, WONT_FIX
    remediation_notes: str = ""

    def to_dict(self) -> dict:
        return {
            "vuln_id": self.vuln_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "cvss_score": self.cvss_score,
            "cve_id": self.cve_id,
            "cwe_id": self.cwe_id,
            "affected_component": self.affected_component,
            "affected_version": self.affected_version,
            "fixed_version": self.fixed_version,
            "location": self.location,
            "evidence": self.evidence,
            "remediation": self.remediation,
            "references": self.references,
            "tags": self.tags,
            "discovered_at": self.discovered_at.isoformat(),
            "scanner": self.scanner,
            "scan_id": self.scan_id,
            "false_positive": self.false_positive,
            "risk_accepted": self.risk_accepted,
            "remediation_status": self.remediation_status,
            "remediation_notes": self.remediation_notes,
        }


@dataclass
class ScanResult:
    """Results of a security scan."""
    scan_id: str = field(default_factory=lambda: f"scan_{secrets.token_hex(8)}")
    scan_type: ScanType = ScanType.NETWORK
    target: str = ""
    status: ScanStatus = ScanStatus.PENDING
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    scanner: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    error: str = ""

    def add_vulnerability(self, vuln: Vulnerability):
        vuln.scan_id = self.scan_id
        self.vulnerabilities.append(vuln)
        self._update_summary()

    def _update_summary(self):
        self.summary = {
            "total": len(self.vulnerabilities),
            "critical": len([v for v in self.vulnerabilities if v.severity == Severity.CRITICAL]),
            "high": len([v for v in self.vulnerabilities if v.severity == Severity.HIGH]),
            "medium": len([v for v in self.vulnerabilities if v.severity == Severity.MEDIUM]),
            "low": len([v for v in self.vulnerabilities if v.severity == Severity.LOW]),
            "info": len([v for v in self.vulnerabilities if v.severity == Severity.INFO]),
        }

    def to_dict(self) -> dict:
        return {
            "scan_id": self.scan_id,
            "scan_type": self.scan_type.value,
            "target": self.target,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
            "summary": self.summary,
            "scanner": self.scanner,
            "config": self.config,
        }


class BaseScanner:
    """Base class for security scanners."""

    def __init__(self, scan_type: ScanType):
        self.scan_type = scan_type
        self.logger = logging.getLogger(f"scanner.{scan_type.value.lower()}")

    async def scan(self, target: str, config: Dict[str, Any] = None) -> ScanResult:
        """Run a scan against target."""
        scan = ScanResult(
            scan_type=self.scan_type,
            target=target,
            status=ScanStatus.RUNNING,
            scanner=self.__class__.__name__,
            config=config or {},
        )

        try:
            await self._run_scan(scan, target, config or {})
            scan.status = ScanStatus.COMPLETED
        except Exception as e:
            scan.status = ScanStatus.FAILED
            scan.error = str(e)
            self.logger.error(f"Scan failed: {e}")
        finally:
            scan.completed_at = datetime.utcnow()
            scan.duration_seconds = (scan.completed_at - scan.started_at).total_seconds()

        return scan

    async def _run_scan(self, scan: ScanResult, target: str, config: Dict[str, Any]):
        """Override in subclass to implement scan logic."""
        raise NotImplementedError


class NetworkScanner(BaseScanner):
    """Network port and service scanner using nmap."""

    def __init__(self):
        super().__init__(ScanType.NETWORK)

    async def _run_scan(self, scan: ScanResult, target: str, config: Dict[str, Any]):
        # Parse target (can be IP, CIDR, hostname)
        ports = config.get("ports", "1-1000")
        scan_type = config.get("scan_type", "syn")
        timing = config.get("timing", "T4")
        scripts = config.get("scripts", "default,vuln")

        # Build nmap arguments
        args = f"-p {ports} -s{scan_type.upper()} -T{timing[-1]} --script {scripts} -oX -"

        try:
            nm = nmap.PortScanner()
            scan_data = nm.scan(hosts=target, arguments=args)

            for host, host_data in scan_data.get("scan", {}).items():
                # Host info
                host_info = {
                    "host": host,
                    "state": host_data.get("state", "unknown"),
                    "hostnames": host_data.get("hostnames", []),
                }

                # Ports and services
                for proto in ["tcp", "udp"]:
                    if proto in host_data:
                        for port, port_data in host_data[proto].items():
                            service = port_data.get("name", "unknown")
                            version = port_data.get("version", "")
                            product = port_data.get("product", "")
                            state = port_data.get("state", "unknown")

                            # Check for known vulnerabilities
                            vulns = self._check_vulnerabilities(service, version, product)
                            for vuln in vulns:
                                vuln.location = f"{host}:{port}/{proto}"
                                vuln.scanner = "nmap"
                                scan.add_vulnerability(vuln)

                            # Check SSL/TLS
                            if port in [443, 8443, 9443] or service in ["https", "ssl"]:
                                ssl_vulns = await self._check_ssl_tls(target, port)
                                for vuln in ssl_vulns:
                                    vuln.location = f"{host}:{port}"
                                    vuln.scanner = "nmap"
                                    scan.add_vulnerability(vuln)

        except Exception as e:
            scan.logs.append(f"Nmap scan error: {e}")

    def _check_vulnerabilities(self, service: str, version: str, product: str) -> List[Vulnerability]:
        """Check for known vulnerabilities based on service/version."""
        vulns = []

        # Common vulnerable versions (simplified)
        vulnerable_versions = {
            "openssh": {
                "7.2": [("CVE-2016-10012", "HIGH", "OpenSSH 7.2 - User enumeration")],
                "7.4": [("CVE-2016-10012", "HIGH", "OpenSSH 7.4 - User enumeration")],
                "7.9": [("CVE-2019-6111", "MEDIUM", "OpenSSH 7.9 - scp client vulnerability")],
            },
            "apache": {
                "2.4.29": [("CVE-2018-11776", "HIGH", "Apache Struts2 RCE")],
                "2.4.41": [("CVE-2019-10092", "MEDIUM", "Apache HTTP Server mod_rewrite")],
            },
            "nginx": {
                "1.14": [("CVE-2019-9511", "HIGH", "HTTP/2 flood")],
            },
        }

        product_lower = product.lower()
        for component, versions in vulnerable_versions.items():
            if component in product_lower:
                for ver, vulns in versions.items():
                    if version.startswith(ver):
                        for cve_id, severity, desc in vulns:
                            yield Vulnerability(
                                title=f"{product} {version} - {desc}",
                                description=f"Vulnerable version of {product} detected: {version}",
                                severity=Severity(severity),
                                cve_id=cve_id,
                                affected_component=product,
                                affected_version=version,
                                remediation=f"Upgrade {product} to latest version",
                                scanner="nmap_vuln_check",
                            )

    async def _check_ssl_tls(self, host: str, port: int) -> List[Vulnerability]:
        """Check SSL/TLS configuration."""
        vulns = []

        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with socket.create_connection((host, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()

                    # Check TLS version
                    if version in ["TLSv1", "TLSv1.1"]:
                        yield Vulnerability(
                            title=f"Deprecated TLS Version: {version}",
                            description=f"Server supports deprecated TLS version {version}",
                            severity=Severity.HIGH,
                            cve_id="",
                            affected_component="TLS",
                            location=f"{host}:{port}",
                            remediation="Disable TLS 1.0 and 1.1, enable TLS 1.2+",
                            scanner="ssl_check",
                        )

                    # Check cipher strength
                    if cipher:
                        cipher_name, cipher_version, cipher_bits = cipher
                        if cipher_bits < 128:
                            yield Vulnerability(
                                title=f"Weak Cipher: {cipher_name}",
                                description=f"Weak cipher suite in use: {cipher_name} ({cipher_bits} bits)",
                                severity=Severity.MEDIUM,
                                affected_component="TLS Cipher",
                                location=f"{host}:{port}",
                                remediation="Disable weak ciphers, enable only AES-GCM 128+ bit",
                                scanner="ssl_check",
                            )

                    # Check certificate
                    if cert:
                        not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                        days_until_expiry = (not_after - datetime.utcnow()).days
                        if days_until_expiry < 30:
                            yield Vulnerability(
                                title="SSL Certificate Expiring Soon",
                                description=f"Certificate expires in {days_until_expiry} days",
                                severity=Severity.HIGH if days_until_expiry < 7 else Severity.MEDIUM,
                                affected_component="SSL Certificate",
                                location=f"{host}:{port}",
                                remediation="Renew SSL certificate",
                                scanner="ssl_check",
                            )

        except Exception as e:
            self.logger.debug(f"SSL check failed for {host}:{port}: {e}")

        return list(vulns)


class WebAppScanner(BaseScanner):
    """Web application vulnerability scanner."""

    def __init__(self):
        super().__init__(ScanType.WEB_APPLICATION)

    async def _run_scan(self, scan: ScanResult, target: str, config: Dict[str, Any]):
        base_url = target.rstrip("/")
        max_depth = config.get("max_depth", 3)
        max_pages = config.get("max_pages", 100)
        auth = config.get("auth", {})

        # Crawl
        pages = await self._crawl(base_url, max_depth, max_pages, auth)

        # Test each page for vulnerabilities
        for page in pages:
            await self._test_page(scan, page, auth)

    async def _crawl(self, base_url: str, max_depth: int, max_pages: int, auth: Dict) -> List[Dict]:
        """Crawl website to discover pages."""
        visited = set()
        to_visit = [(base_url, 0)]
        pages = []

        async with aiohttp.ClientSession() as session:
            while to_visit and len(visited) < max_pages:
                url, depth = to_visit.pop(0)
                if url in visited or depth > max_depth:
                    continue

                visited.add(url)

                try:
                    async with session.get(url, timeout=10) as resp:
                        if resp.status == 200:
                            content = await resp.text()
                            pages.append({
                                "url": url,
                                "status": resp.status,
                                "content": content,
                                "headers": dict(resp.headers),
                                "forms": self._extract_forms(content),
                                "links": self._extract_links(content, base_url),
                            })

                            if depth < max_depth:
                                for link in self._extract_links(content, base_url):
                                    if link not in visited:
                                        to_visit.append((link, depth + 1))
                except Exception as e:
                    pass

        return pages

    def _extract_forms(self, html: str) -> List[Dict]:
        forms = []
        form_pattern = re.compile(r'<form[^>]*>(.*?)</form>', re.DOTALL | re.IGNORECASE)
        input_pattern = re.compile(r'<input[^>]*>', re.IGNORECASE)

        for form_match in form_pattern.finditer(html):
            form_html = form_match.group(0)
            action = re.search(r'action=["\']([^"\']*)["\']', form_html, re.IGNORECASE)
            method = re.search(r'method=["\']([^"\']*)["\']', form_html, re.IGNORECASE)

            inputs = []
            for inp in input_pattern.finditer(form_html):
                name = re.search(r'name=["\']([^"\']*)["\']', inp)
                input_type = re.search(r'type=["\']([^"\']*)["\']', inp)
                inputs.append({
                    "name": name.group(1) if name else "",
                    "type": input_type.group(1) if input_type else "text",
                })

            forms.append({
                "action": action.group(1) if action else "",
                "method": method.group(1).upper() if method else "GET",
                "inputs": inputs,
            })

        return forms

    def _extract_links(self, html: str, base_url: str) -> List[str]:
        links = []
        link_pattern = re.compile(r'<a[^>]+href=["\']([^"\']+)["\']', re.IGNORECASE)
        for match in link_pattern.finditer(html):
            href = match.group(1)
            if href.startswith("/"):
                href = urljoin(base_url, href)
            elif href.startswith("http"):
                pass
            else:
                href = urljoin(base_url, href)

            # Filter same domain
            if urlparse(href).netloc == urlparse(base_url).netloc:
                links.append(href)

        return list(set(links))

    async def _test_page(self, scan: ScanResult, page: Dict, auth: Dict):
        """Test a page for vulnerabilities."""
        url = page["url"]
        forms = page["forms"]

        # Test forms for SQL injection
        for form in forms:
            await self._test_sqli(scan, url, form)

        # Test for XSS
        await self._test_xss(scan, url, page)

        # Test for CSRF
        await self._test_csrf(scan, url, page)

        # Check headers
        await self._check_headers(scan, url, page["headers"])

    async def _test_sqli(self, scan: ScanResult, url: str, form: Dict):
        """Test for SQL injection."""
        payloads = [
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' UNION SELECT NULL--",
            "'; DROP TABLE users--",
        ]

        async with aiohttp.ClientSession() as session:
            for payload in payloads:
                for inp in form["inputs"]:
                    if inp["type"] in ["text", "search", "email", "password"]:
                        data = {inp["name"]: payload}
                        for other_inp in form["inputs"]:
                            if other_inp != inp:
                                data[other_inp["name"]] = "test"

                        try:
                            if form["method"] == "POST":
                                async with session.post(form["action"] or url, data=data) as resp:
                                    content = await resp.text()
                                    if self._detect_sqli(content):
                                        scan.add_vulnerability(Vulnerability(
                                            title="SQL Injection",
                                            description=f"Potential SQL injection in form at {url}",
                                            severity=Severity.HIGH,
                                            cve_id="",
                                            affected_component=f"Form at {url}",
                                            location=url,
                                            evidence=f"Payload: {payload}",
                                            remediation="Use parameterized queries",
                                            scanner="sqli_test",
                                        ))
                            else:
                                async with session.get(url, params=data) as resp:
                                    content = await resp.text()
                                    if self._detect_sqli(content):
                                        scan.add_vulnerability(Vulnerability(
                                            title="SQL Injection (GET)",
                                            description=f"Potential SQL injection in GET parameters at {url}",
                                            severity=Severity.HIGH,
                                            cve_id="",
                                            affected_component=f"GET parameters at {url}",
                                            location=url,
                                            evidence=f"Payload: {payload}",
                                            remediation="Use parameterized queries",
                                            scanner="sqli_test",
                                        ))
                        except Exception:
                            pass

    def _detect_sqli(self, content: str) -> bool:
        errors = [
            "sql syntax", "mysql_fetch", "ora-01756", "postgresql",
            "syntax error", "unclosed quotation", "sqlstate",
            "mysql_num_rows", "mysql_fetch_array", "pg_query",
            "sqlite3", "odbc", "jdbc", "sql server",
        ]
        content_lower = content.lower()
        return any(err in content_lower for err in errors)

    async def _test_xss(self, scan: ScanResult, url: str, page: Dict):
        """Test for Cross-Site Scripting."""
        payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert(1)",
            "<svg onload=alert(1)>",
        ]

        async with aiohttp.ClientSession() as session:
            for payload in payloads:
                # Test in forms
                for form in page["forms"]:
                    for inp in form["inputs"]:
                        if inp["type"] in ["text", "search", "textarea"]:
                            data = {inp["name"]: payload}
                            for other in form["inputs"]:
                                if other != inp:
                                    data[other["name"]] = "test"

                            try:
                                if form["method"] == "POST":
                                    async with session.post(form["action"] or url, data=data) as resp:
                                        content = await resp.text()
                                        if payload in content:
                                            self._add_xss_vuln(scan, url, "stored", payload)
                                else:
                                    async with session.get(url, params=data) as resp:
                                        content = await resp.text()
                                        if payload in content:
                                            self._add_xss_vuln(scan, url, "reflected", payload)
                            except Exception:
                                pass

        # Test URL parameters
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        for param in params:
            for payload in payloads:
                test_params = params.copy()
                test_params[param] = [payload]
                test_url = urlunparse(parsed._replace(query=urlencode(test_params, doseq=True)))

                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(test_url) as resp:
                            content = await resp.text()
                            if payload in content:
                                self._add_xss_vuln(scan, test_url, "reflected", payload)
                except Exception:
                    pass

    def _add_xss_vuln(self, scan: ScanResult, url: str, xss_type: str, payload: str):
        scan.add_vulnerability(Vulnerability(
            title=f"Cross-Site Scripting ({xss_type})",
            description=f"Potential {xss_type} XSS vulnerability at {url}",
            severity=Severity.HIGH if xss_type == "stored" else Severity.MEDIUM,
            cve_id="",
            affected_component=f"URL: {url}",
            location=url,
            evidence=f"Payload: {payload}",
            remediation="Implement proper output encoding and CSP",
            scanner="xss_test",
        )

    async def _test_csrf(self, scan: ScanResult, url: str, page: Dict):
        """Test for CSRF vulnerabilities."""
        for form in page["forms"]:
            if form["method"] == "POST":
                # Check for CSRF token
                has_csrf = any(
                    "csrf" in inp["name"].lower() or "token" in inp["name"].lower()
                    for inp in form["inputs"]
                )
                if not has_csrf:
                    scan.add_vulnerability(Vulnerability(
                        title="Missing CSRF Protection",
                        description=f"Form at {url} lacks CSRF token",
                        severity=Severity.MEDIUM,
                        cve_id="",
                        affected_component=f"Form at {url}",
                        location=url,
                        remediation="Implement CSRF tokens in all state-changing forms",
                        scanner="csrf_test",
                    ))

    async def _check_headers(self, scan: ScanResult, url: str, headers: Dict):
        """Check security headers."""
        security_headers = {
            "X-Frame-Options": ("Missing X-Frame-Options", Severity.MEDIUM),
            "X-Content-Type-Options": ("Missing X-Content-Type-Options", Severity.LOW),
            "X-XSS-Protection": ("Missing X-XSS-Protection", Severity.LOW),
            "Content-Security-Policy": ("Missing CSP", Severity.MEDIUM),
            "Strict-Transport-Security": ("Missing HSTS", Severity.HIGH),
            "Referrer-Policy": ("Missing Referrer-Policy", Severity.LOW),
            "Permissions-Policy": ("Missing Permissions-Policy", Severity.LOW),
        }

        for header, (title, severity) in security_headers.items():
            if header not in headers:
                scan.add_vulnerability(Vulnerability(
                    title=title,
                    description=f"Missing security header: {header}",
                    severity=severity,
                    cve_id="",
                    affected_component=f"HTTP Headers at {url}",
                    location=url,
                    remediation=f"Add {header} header",
                    scanner="header_check",
                ))


class DependencyScanner(BaseScanner):
    """Dependency vulnerability scanner."""

    def __init__(self):
        super().__init__(ScanType.DEPENDENCY)

    async def _run_scan(self, scan: ScanResult, target: str, config: Dict[str, Any]):
        """Scan dependency files for known vulnerabilities."""
        # Check requirements.txt, package.json, Cargo.toml, go.mod, pom.xml, etc.
        dep_files = {
            "requirements.txt": self._parse_requirements,
            "package.json": self._parse_package_json,
            "Cargo.toml": self._parse_cargo_toml,
            "go.mod": self._parse_go_mod,
            "pom.xml": self._parse_pom_xml,
        }

        for filename, parser in dep_files.items():
            file_path = Path(target) / filename
            if file_path.exists():
                try:
                    vulns = await parser(file_path)
                    for vuln in vulns:
                        vuln.scanner = "dependency_scan"
                        scan.add_vulnerability(vuln)
                except Exception as e:
                    scan.logs.append(f"Error parsing {filename}: {e}")

        # Check against known vulnerability databases (OSV, NVD, GitHub Advisories)
        await self._check_vuln_databases(scan)

    async def _parse_requirements(self, file_path: Path) -> List[Vulnerability]:
        vulns = []
        content = file_path.read_text()
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                # Parse package==version
                match = re.match(r"^([a-zA-Z0-9_-]+)(?:==|>=|<=|~=|~=)([^\s#]+)", line)
                if match:
                    pkg, version = match.groups()
                    vulns = await self._check_package_vulns(pkg, version)
                    for vuln in vulns:
                        vulns.append(vuln)
        return vulns

    async def _parse_package_json(self, file_path: Path) -> List[Vulnerability]:
        data = json.loads(file_path.read_text())
        vulns = []
        for dep_type in ["dependencies", "devDependencies"]:
            for pkg, version in data.get(dep_type, {}).items():
                vulns = await self._check_package_vulns(pkg, version.lstrip("^~"))
                for vuln in vulns:
                    vuln.affected_component = f"npm package: {pkg}"
                    vuln.affected_version = version
                    yield vuln

    async def _check_package_vulns(self, package: str, version: str) -> List[Vulnerability]:
        """Check package against vulnerability databases (OSV, NVD, GitHub)."""
        vulns = []
        # In production, would query OSV.dev, GitHub Advisory Database, NVD
        # For now, return mock vulnerabilities for known vulnerable versions
        known_vulns = {
            "requests": {
                "2.20.0": [("CVE-2018-18074", "MEDIUM", "Requests Session object leak")],
                "2.19.0": [("CVE-2018-11628", "HIGH", "Request URI not properly encoded")],
            },
            "urllib3": {
                "1.24.1": [("CVE-2019-11324", "HIGH", "CRLF injection")],
                "1.25.0": [("CVE-2019-11236", "MEDIUM", "Header injection")],
            },
            "django": {
                "2.1": [("CVE-2019-3498", "HIGH", "Content spoofing")],
                "3.0": [("CVE-2020-7471", "HIGH", "SQL injection")],
            },
        }

        if package in known_vulns and version in known_vulns[package]:
            for cve_id, severity, desc in known_vulns[package][version]:
                yield Vulnerability(
                    title=f"{package} {version} - {desc}",
                    description=f"Vulnerable version of {package} detected: {version}",
                    severity=Severity(severity),
                    cve_id=cve_id,
                    affected_component=package,
                    affected_version=version,
                    remediation=f"Upgrade {package} to latest version",
                    scanner="dependency_scan",
                )

        return []


class ContainerScanner(BaseScanner):
    """Container image vulnerability scanner."""

    def __init__(self):
        super().__init__(ScanType.CONTAINER)

    async def _run_scan(self, scan: ScanResult, target: str, config: Dict[str, Any]):
        """Scan container image for vulnerabilities."""
        # In production, would use Trivy, Grype, or Clair
        # For now, simulate scan
        scan.logs.append(f"Scanning container image: {target}")

        # Check base image
        base_vulns = self._check_base_image(target)
        for vuln in base_vulns:
            vuln.scanner = "container_scan"
            scan.add_vulnerability(vuln)

        # Check installed packages
        pkg_vulns = self._check_packages(target)
        for vuln in pkg_vulns:
            vuln.scanner = "container_scan"
            scan.add_vulnerability(vuln)

        # Check configuration
        config_vulns = self._check_config(target)
        for vuln in config_vulns:
            vuln.scanner = "container_scan"
            scan.add_vulnerability(vuln)

    def _check_base_image(self, image: str) -> List[Vulnerability]:
        """Check base image for known vulnerabilities."""
        vulns = []
        # In production, would query vulnerability database
        # Simulate some common base image issues
        if "alpine:3.12" in image:
            vulns.append(Vulnerability(
                title="Alpine 3.12 - End of Life",
                description="Alpine 3.12 reached EOL, no security updates",
                severity=Severity.HIGH,
                cve_id="",
                affected_component="Base Image",
                affected_version="3.12",
                remediation="Upgrade to Alpine 3.18+",
                scanner="container_scan",
            ))
        return vulns

    def _check_packages(self, image: str) -> List[Vulnerability]:
        """Check installed packages for vulnerabilities."""
        # Would use Trivy/Grype in production
        return []

    def _check_config(self, image: str) -> List[Vulnerability]:
        """Check container configuration for security issues."""
        vulns = []
        # Check for common misconfigurations
        vulns.append(Vulnerability(
            title="Container Running as Root",
            description="Container runs as root user",
            severity=Severity.MEDIUM,
            cve_id="",
            affected_component="Container Config",
            remediation="Add USER directive in Dockerfile",
            scanner="container_config",
        ))
        vulns.append(Vulnerability(
            title="No Read-Only Root Filesystem",
            description="Container root filesystem is writable",
            severity=Severity.LOW,
            cve_id="",
            affected_component="Container Config",
            remediation="Add readOnlyRootFilesystem: true in securityContext",
            scanner="container_config",
        ))
        return vulns


class ConfigurationScanner(BaseScanner):
    """Configuration security scanner."""

    def __init__(self):
        super().__init__(ScanType.CONFIGURATION)

    async def _run_scan(self, scan: ScanResult, target: str, config: Dict[str, Any]):
        """Scan configuration files for security issues."""
        target_path = Path(target)

        # Check common config files
        config_files = {
            ".env": self._check_env_file,
            "docker-compose.yml": self._check_docker_compose,
            "docker-compose.yaml": self._check_docker_compose,
            "Dockerfile": self._check_dockerfile,
            "kubernetes.yaml": self._check_k8s,
            "k8s.yaml": self._check_k8s,
            "helm/values.yaml": self._check_helm_values,
            ".github/workflows/": self._check_github_actions,
        }

        for pattern, checker in config_files.items():
            for file_path in target_path.rglob(pattern):
                try:
                    vulns = await checker(file_path)
                    for vuln in vulns:
                        vuln.scanner = "config_scan"
                        scan.add_vulnerability(vuln)
                except Exception as e:
                    scan.logs.append(f"Error checking {file_path}: {e}")

    async def _check_env_file(self, file_path: Path) -> List[Vulnerability]:
        vulns = []
        content = file_path.read_text()
        for i, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            if line and not line.startswith("#"):
                # Check for secrets in env
                if any(kw in line.lower() for kw in ["password", "secret", "key", "token", "secret", "api_key"]):
                    if "=" in line and not line.startswith("#"):
                        vulns.append(Vulnerability(
                            title="Secret in Environment File",
                            description=f"Potential secret in .env file at line {i}",
                            severity=Severity.HIGH,
                            cve_id="",
                            affected_component=str(file_path),
                            location=f"{file_path}:{i}",
                            remediation="Use secret management (Vault, AWS Secrets Manager, etc.)",
                            scanner="env_scan",
                        ))
        return vulns

    async def _check_docker_compose(self, file_path: Path) -> List[Vulnerability]:
        vulns = []
        import yaml
        try:
            data = yaml.safe_load(file_path.read_text())
            services = data.get("services", {})
            for name, svc in services.items():
                # Check for privileged
                if svc.get("privileged"):
                    vulns.append(Vulnerability(
                        title="Privileged Container",
                        description=f"Service {name} runs in privileged mode",
                        severity=Severity.HIGH,
                        cve_id="",
                        affected_component=f"docker-compose: {name}",
                        remediation="Remove privileged: true",
                        scanner="docker_compose",
                    ))
                # Check for host network
                if svc.get("network_mode") == "host":
                    vulns.append(Vulnerability(
                        title="Host Network Mode",
                        description=f"Service {name} uses host network",
                        severity=Severity.MEDIUM,
                        cve_id="",
                        affected_component=f"docker-compose: {name}",
                        remediation="Avoid network_mode: host",
                        scanner="docker_compose",
                    ))
                # Check for secrets in environment
                env = svc.get("environment", {})
                if isinstance(env, dict):
                    for key, val in env.items():
                        if any(kw in key.lower() for kw in ["password", "secret", "key", "token"]):
                            if val and not val.startswith("${"):
                                vulns.append(Vulnerability(
                                    title="Secret in Docker Compose",
                                    description=f"Hardcoded secret in {name} environment",
                                    severity=Severity.HIGH,
                                    cve_id="",
                                    affected_component=f"docker-compose: {name}",
                                    remediation="Use secrets or .env file",
                                    scanner="docker_compose",
                                ))
        return vulns

    async def _check_dockerfile(self, file_path: Path) -> List[Vulnerability]:
        vulns = []
        content = file_path.read_text()
        lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            line = line.strip()
            # Check for root user
            if line.startswith("USER root") or (line.startswith("USER") and "0" in line):
                vulns.append(Vulnerability(
                    title="Container Running as Root",
                    description=f"Dockerfile line {i}: USER root",
                    severity=Severity.MEDIUM,
                    cve_id="",
                    affected_component=str(file_path),
                    location=f"{file_path}:{i}",
                    remediation="Create non-root user and use USER directive",
                    scanner="dockerfile",
                ))
            # Check for --privileged
            if "--privileged" in line:
                vulns.append(Vulnerability(
                    title="Privileged Container",
                    description=f"Dockerfile line {i}: --privileged flag",
                    severity=Severity.HIGH,
                    cve_id="",
                    affected_component=str(file_path),
                    location=f"{file_path}:{i}",
                    remediation="Remove --privileged flag",
                    scanner="dockerfile",
                ))
            # Check for latest tag
            if line.startswith("FROM") and ":latest" in line:
                vulns.append(Vulnerability(
                    title="Latest Tag Used",
                    description=f"Dockerfile line {i}: Using :latest tag",
                    severity=Severity.LOW,
                    cve_id="",
                    affected_component=str(file_path),
                    location=f"{file_path}:{i}",
                    remediation="Pin to specific version tag",
                    scanner="dockerfile",
                ))
        return vulns

    async def _check_k8s(self, file_path: Path) -> List[Vulnerability]:
        vulns = []
        import yaml
        try:
            docs = list(yaml.safe_load_all(file_path.read_text()))
            for doc in docs:
                if not doc or "kind" not in doc:
                    continue

                kind = doc["kind"]
                metadata = doc.get("metadata", {})
                name = metadata.get("name", "unknown")

                if kind == "Pod":
                    spec = doc.get("spec", {})
                    # Check for privileged
                    for container in spec.get("containers", []):
                        if container.get("securityContext", {}).get("privileged"):
                            vulns.append(Vulnerability(
                                title="Privileged Container",
                                description=f"Pod {name} container runs privileged",
                                severity=Severity.HIGH,
                                cve_id="",
                                affected_component=f"k8s: {kind}/{name}",
                                remediation="Remove privileged: true",
                                scanner="k8s",
                            ))
                        if container.get("securityContext", {}).get("runAsUser") == 0:
                            vulns.append(Vulnerability(
                                title="Container Running as Root",
                                description=f"Pod {name} container runs as root",
                                severity=Severity.MEDIUM,
                                cve_id="",
                                affected_component=f"k8s: {kind}/{name}",
                                remediation="Set runAsNonRoot: true",
                                scanner="k8s",
                            ))
                        # Check for hostPath volumes
                        for vol in spec.get("volumes", []):
                            if "hostPath" in vol:
                                vulns.append(Vulnerability(
                                    title="HostPath Volume",
                                    description=f"Pod {name} uses hostPath volume",
                                    severity=Severity.MEDIUM,
                                    cve_id="",
                                    affected_component=f"k8s: {kind}/{name}",
                                    remediation="Avoid hostPath volumes",
                                    scanner="k8s",
                                ))

        return vulns

    async def _check_helm_values(self, file_path: Path) -> List[Vulnerability]:
        import yaml
        vulns = []
        data = yaml.safe_load(file_path.read_text())
        # Check for common insecure defaults
        return vulns

    async def _check_github_actions(self, file_path: Path) -> List[Vulnerability]:
        vulns = []
        import yaml
        try:
            data = yaml.safe_load(file_path.read_text())
            jobs = data.get("jobs", {})
            for job_name, job in jobs.items():
                steps = job.get("steps", [])
                for step in steps:
                    uses = step.get("uses", "")
                    # Check for unpinned actions
                    if "@" not in uses and uses:
                        vulns.append(Vulnerability(
                            title="Unpinned GitHub Action",
                            description=f"Job {job_name} uses unpinned action: {uses}",
                            severity=Severity.MEDIUM,
                            cve_id="",
                            affected_component=f"github-actions: {job_name}",
                            remediation="Pin action to specific SHA",
                            scanner="github_actions",
                        ))
                    # Check for secrets in plaintext
                    env = step.get("env", {})
                    for key, val in env.items():
                        if any(kw in key.lower() for kw in ["secret", "password", "key", "token"]):
                            if val and not val.startswith("${"):
                                vulns.append(Vulnerability(
                                    title="Secret in GitHub Actions",
                                    description=f"Hardcoded secret in workflow env",
                                    severity=Severity.HIGH,
                                    cve_id="",
                                    affected_component=f"github-actions: {job_name}",
                                    remediation="Use GitHub Secrets",
                                    scanner="github_actions",
                                ))
        return vulns


class SecretScanner:
    """Scan for secrets in code and configuration."""

    PATTERNS = {
        "aws_access_key": (r"AKIA[0-9A-Z]{16}", Severity.CRITICAL),
        "aws_secret_key": (r"[A-Za-z0-9/+=]{40}", Severity.CRITICAL),
        "github_token": (r"ghp_[A-Za-z0-9]{36}", Severity.CRITICAL),
        "github_app_token": (r"ghs_[A-Za-z0-9]{36}", Severity.CRITICAL),
        "slack_token": (r"xoxb-[0-9]{11}-[0-9]{11}-[A-Za-z0-9]{24}", Severity.CRITICAL),
        "slack_webhook": (r"https://hooks.slack.com/services/[A-Z0-9]{8}/[A-Z0-9]{8}/[A-Za-z0-9]{24}", Severity.CRITICAL),
        "stripe_key": (r"sk_live_[A-Za-z0-9]{24}", Severity.CRITICAL),
        "stripe_test_key": (r"sk_test_[A-Za-z0-9]{24}", Severity.HIGH),
        "google_api_key": (r"AIza[0-9A-Za-z_-]{35}", Severity.HIGH),
        "firebase_key": (r"AAAA[A-Za-z0-9_-]{7}:[A-Za-z0-9_-]{140}", Severity.CRITICAL),
        "jwt_token": (r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", Severity.CRITICAL),
        "private_key": (r"-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----", Severity.CRITICAL),
        "ssh_private_key": (r"-----BEGIN OPENSSH PRIVATE KEY-----", Severity.CRITICAL),
        "generic_password": (r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^\s'\"]{8,}['\"]", Severity.HIGH),
        "generic_api_key": (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]", Severity.HIGH),
    }

    def __init__(self):
        self.compiled = {
            name: (re.compile(pattern), severity)
            for name, (pattern, severity) in self.PATTERNS.items()
        }

    def scan_file(self, file_path: Path) -> List[Vulnerability]:
        """Scan a file for secrets."""
        vulns = []
        try:
            content = file_path.read_text()
            for name, (pattern, severity) in self.compiled.items():
                matches = pattern.finditer(content)
                for match in matches:
                    # Get line number
                    line_no = content[:match.start()].count("\n") + 1
                    line_start = content.rfind("\n", 0, match.start()) + 1
                    line_end = content.find("\n", match.end())
                    if line_end == -1:
                        line_end = len(content)
                    context = content[line_start:line_end].strip()

                    vulns.append(Vulnerability(
                        title=f"Secret Detected: {name}",
                        description=f"Potential {name} found in source code",
                        severity=severity,
                        cve_id="",
                        affected_component=str(file_path),
                        location=f"{file_path}:{line_no}",
                        evidence=context[:200],
                        remediation="Remove secret from code, use secret management",
                        scanner="secret_scan",
                    ))
        except Exception as e:
            pass
        return vulns

    def scan_directory(self, directory: Path, extensions: List[str] = None) -> List[Vulnerability]:
        """Scan directory for secrets."""
        extensions = extensions or [".py", ".js", ".ts", ".json", ".yaml", ".yml", ".env", ".ini", ".conf", ".config", ".properties", ".xml", ".gradle", ".tf", ".tfvars"]
        vulns = []
        for ext in extensions:
            for file_path in Path(directory).rglob(f"*{ext}"):
                if file_path.is_file():
                    vulns.extend(self.scan_file(file_path))
        return vulns


class PenTestFramework:
    """Orchestrates comprehensive penetration testing."""

    def __init__(self):
        self.scanners = {
            ScanType.NETWORK: NetworkScanner(),
            ScanType.WEB_APPLICATION: WebAppScanner(),
            ScanType.API: WebAppScanner(),  # Reuse web app scanner for API
            ScanType.DATABASE: NetworkScanner(),  # Use network scanner for DB ports
            ScanType.DEPENDENCY: DependencyScanner(),
            ScanType.CONTAINER: ContainerScanner(),
            ScanType.CONFIGURATION: ConfigurationScanner(),
        }
        self.secret_scanner = SecretScanner()
        self._running_scans: Dict[str, ScanResult] = {}
        self._lock = threading.RLock()

    def get_scanner(self, scan_type: ScanType) -> BaseScanner:
        return self.scanners.get(scan_type)

    def run_scan(
        self,
        scan_type: ScanType,
        target: str,
        config: Dict[str, Any] = None
    ) -> ScanResult:
        """Run a single scan synchronously."""
        scanner = self.get_scanner(scan_type)
        if not scanner:
            raise ValueError(f"No scanner for type: {scan_type}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(scanner.scan(target, config))
        finally:
            loop.close()

    async def run_scan_async(
        self,
        scan_type: ScanType,
        target: str,
        config: Dict[str, Any] = None
    ) -> ScanResult:
        """Run a scan asynchronously."""
        scanner = self.get_scanner(scan_type)
        if not scanner:
            raise ValueError(f"No scanner for type: {scan_type}")
        return await scanner.scan(target, config)

    async def run_comprehensive_scan(
        self,
        target: str,
        scan_types: List[ScanType] = None,
        config: Dict[str, Any] = None
    ) -> Dict[ScanType, ScanResult]:
        """Run multiple scan types in parallel."""
        scan_types = scan_types or [
            ScanType.NETWORK,
            ScanType.WEB_APPLICATION,
            ScanType.DEPENDENCY,
            ScanType.CONFIGURATION,
        ]

        tasks = []
        for scan_type in scan_types:
            scanner = self.get_scanner(scan_type)
            if scanner:
                task = scanner.scan(target, config)
                tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        results_dict = {}
        for scan_type, result in zip(scan_types, results):
            if isinstance(result, Exception):
                logger.error(f"Scan {scan_type} failed: {result}")
                results_dict[scan_type] = ScanResult(
                    scan_type=scan_type,
                    target=target,
                    status=ScanStatus.FAILED,
                    error=str(result)
                )
            else:
                results_dict[scan_type] = result

        return results_dict

    def scan_secrets(self, target: str, extensions: List[str] = None) -> List[Vulnerability]:
        """Scan for secrets in codebase."""
        return self.secret_scanner.scan_directory(Path(target), extensions)

    def scan_secrets_in_file(self, file_path: str) -> List[Vulnerability]:
        return self.secret_scanner.scan_file(Path(file_path))

    def get_scan_summary(self, results: Dict[ScanType, ScanResult]) -> Dict[str, Any]:
        """Generate summary report from scan results."""
        total_vulns = 0
        by_severity = {s.value: 0 for s in Severity}
        by_type = {}
        critical_findings = []

        for scan_type, result in results.items():
            by_type[scan_type.value] = result.summary
            total_vulns += result.summary.get("total", 0)
            for sev, count in result.summary.items():
                by_severity[sev] += count

            for vuln in result.vulnerabilities:
                if vuln.severity in [Severity.CRITICAL, Severity.HIGH]:
                    critical_findings.append({
                        "scan_type": scan_type.value,
                        "title": vuln.title,
                        "severity": vuln.severity.value,
                        "component": vuln.affected_component,
                    })

        return {
            "total_scans": len(results),
            "total_vulnerabilities": total_vulns,
            "by_severity": by_severity,
            "by_scan_type": by_type,
            "critical_findings": critical_findings[:20],  # Top 20
        }

    def generate_report(self, results: Dict[ScanType, ScanResult], format: str = "json") -> str:
        """Generate penetration test report."""
        summary = self.get_scan_summary(results)

        if format == "json":
            return json.dumps({
                "summary": summary,
                "scans": {k.value: v.to_dict() for k, v in results.items()},
                "generated_at": datetime.utcnow().isoformat(),
            }, indent=2)
        elif format == "html":
            # Generate HTML report
            return self._generate_html_report(results, summary)
        elif format == "markdown":
            return self._generate_markdown_report(results, summary)
        else:
            return json.dumps(summary, indent=2)

    def _generate_html_report(self, results: Dict, summary: Dict) -> str:
        # Simplified HTML report
        html = """
        <html><head><title>Penetration Test Report</title>
        <style>body{font-family:Arial} table{border-collapse:collapse} th,td{border:1px solid #ddd;padding:8px} .critical{background:#ffcccc} .high{background:#ffebcc} .medium{background:#fff3cc} .low{background:#ccffcc}</style></head>
        <body><h1>Penetration Test Report</h1>
        <h2>Summary</h2>
        <p>Total Vulnerabilities: {total}</p>
        <table><tr><th>Severity</th><th>Count</th></tr>
        """
        for sev, count in summary["by_severity"].items():
            html += f"<tr class='{sev.lower()}'><td>{sev}</td><td>{count}</td></tr>"
        html += "</table><h2>Findings</h2>"
        for finding in summary["critical_findings"]:
            html += f"<div class='{finding['severity'].lower()}'><h3>{finding['title']}</h3><p>{finding['component']} - {finding['severity']}</p></div>"
        html += "</body></html>"
        return html

    def _generate_markdown_report(self, results: Dict, summary: Dict) -> str:
        md = f"# Penetration Test Report\n\nGenerated: {datetime.utcnow().isoformat()}\n\n"
        md += f"## Summary\n\nTotal Vulnerabilities: {summary['total_vulnerabilities']}\n\n"
        md += "### By Severity\n\n"
        for sev, count in summary["by_severity"].items():
            md += f"- **{sev}**: {count}\n"
        md += "\n### By Scan Type\n\n"
        for scan_type, counts in summary["by_scan_type"].items():
            md += f"- **{scan_type}**: {counts.get('total', 0)} total\n"
        md += "\n### Critical Findings\n\n"
        for finding in summary["critical_findings"]:
            md += f"- **{finding['title']}** ({finding['severity']}) - {finding['component']}\n"
        return md


def create_pentest_framework() -> PenTestFramework:
    return PenTestFramework()


def create_secret_scanner() -> SecretScanner:
    return SecretScanner()