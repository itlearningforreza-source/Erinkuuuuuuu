#!/usr/bin/env python3
"""
ERIN Engineering Control Plane - Test Matrix Orchestrator

Orchestrates test execution across all test types.
"""

import subprocess
import sys
import argparse
from pathlib import Path
from typing import List

TEST_SUITES = {
    "unit": {
        "command": ["pytest", "tests/unit", "-v", "--tb=short", "-x"],
        "description": "Unit tests",
    },
    "integration": {
        "command": ["pytest", "tests/integration", "-v", "--tb=short", "-x"],
        "description": "Integration tests",
        "requires_services": True,
    },
    "contract": {
        "command": ["python", "-m", "scripts.ecp.contract_test"],
        "description": "Contract tests",
    },
    "property": {
        "command": ["pytest", "tests/property", "-v", "--tb=short", "-x"],
        "description": "Property-based tests",
    },
    "verification": {
        "command": ["pytest", "models/", "-m", "verification", "-v", "--tb=long"],
        "description": "Financial model verification",
    },
    "benchmarks": {
        "command": ["pytest", "tests/benchmarks", "--benchmark-only", "-v"],
        "description": "Performance benchmarks",
    },
    "e2e": {
        "command": ["pnpm", "playwright", "test"],
        "description": "E2E UI tests",
        "requires_build": True,
    },
    "security": {
        "command": ["python", "-m", "scripts.ecp.security_scan"],
        "description": "Security scans",
    },
    "architecture": {
        "command": ["python", "-m", "scripts.ecp.arch_check"],
        "description": "Architecture compliance",
    },
    "resources": {
        "command": ["python", "-m", "scripts.ecp.resource_profile", "--profile", "ci"],
        "description": "Resource profiling",
    },
}

def run_suite(name: str, config: dict) -> tuple[bool, str]:
    """Run a single test suite."""
    print(f"\n{'='*60}")
    print(f"Running {config['description']}...")
    print(f"{'='*60}")

    cmd = config["command"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print(f"✓ {config['description']} PASSED")
            return True, ""
        else:
            print(f"✗ {config['description']} FAILED")
            print(result.stdout)
            print(result.stderr)
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print(f"✗ {config['description']} TIMEOUT")
        return False, "Timeout"
    except Exception as e:
        print(f"✗ {config['description']} ERROR: {e}")
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description="ERIN Test Matrix Orchestrator")
    parser.add_argument("--suites", nargs="+", choices=list(TEST_SUITES.keys()) + ["all"],
                       default=["all"], help="Test suites to run")
    parser.add_argument("--parallel", action="store_true", help="Run suites in parallel")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    args = parser.parse_args()

    suites_to_run = list(TEST_SUITES.keys()) if "all" in args.suites else args.suites

    print(f"ERIN Test Matrix - Running suites: {', '.join(suites_to_run)}")

    results = {}
    failed = []

    for suite_name in suites_to_run:
        if suite_name not in TEST_SUITES:
            print(f"Unknown suite: {suite_name}")
            continue

        success, error = run_suite(suite_name, TEST_SUITES[suite_name])
        results[suite_name] = {"success": success, "error": error}

        if not success:
            failed.append(suite_name)
            if args.fail_fast:
                break

    # Summary
    print(f"\n{'='*60}")
    print("TEST MATRIX SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for r in results.values() if r["success"])
    total = len(results)

    for name, result in results.items():
        status = "PASS" if result["success"] else "FAIL"
        print(f"  {status:4} {TEST_SUITES[name]['description']}")

    print(f"\nTotal: {passed}/{total} passed")

    if failed:
        print(f"\nFailed suites: {', '.join(failed)}")
        return 1

    print("\nAll test suites passed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())