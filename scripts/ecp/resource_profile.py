#!/usr/bin/env python3
"""
ERIN Engineering Control Plane - Resource Profiler

Profiles memory and CPU usage against defined budgets.
"""

import argparse
import json
import psutil
import subprocess
import time
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict

@dataclass
class ResourceBudget:
    peak_rss_mb: int
    cpu_percent: int

@dataclass
class ProfileResult:
    profile: str
    peak_rss_mb: float
    peak_cpu_percent: float
    budget_peak_rss_mb: int
    budget_cpu_percent: int
    passed: bool
    duration_seconds: float

BUDGETS = {
    "minimal": ResourceBudget(peak_rss_mb=3500, cpu_percent=50),
    "standard": ResourceBudget(peak_rss_mb=6000, cpu_percent=80),
    "ci": ResourceBudget(peak_rss_mb=4000, cpu_percent=100),
    "server": ResourceBudget(peak_rss_mb=0, cpu_percent=0),  # Unlimited
}

def run_profile(profile_name: str, duration: int = 30) -> ProfileResult:
    """Run resource profiling for the specified profile."""
    budget = BUDGETS.get(profile_name)
    if not budget:
        raise ValueError(f"Unknown profile: {profile_name}")

    print(f"Starting resource profile: {profile_name} (budget: {budget.peak_rss_mb}MB RSS, {budget.cpu_percent}% CPU)")

    # Start the application
    # For now, just monitor current process as placeholder
    # In reality, this would start the full ERIN stack
    proc = subprocess.Popen([
        sys.executable, "-c", "import time; time.sleep(30)"
    ])

    peak_rss = 0
    peak_cpu = 0
    start_time = time.time()

    try:
        while proc.poll() is None:
            try:
                p = psutil.Process(proc.pid)
                mem = p.memory_info().rss / 1024 / 1024  # MB
                cpu = p.cpu_percent()
                peak_rss = max(peak_rss, mem)
                peak_cpu = max(peak_cpu, cpu)
                time.sleep(0.1)
            except psutil.NoSuchProcess:
                break
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)

    duration_seconds = time.time() - start_time

    # For server profile, always pass
    if profile_name == "server":
        passed = True
    else:
        passed = (peak_rss <= budget.peak_rss_mb and peak_cpu <= budget.cpu_percent)

    return ProfileResult(
        profile=profile_name,
        peak_rss_mb=peak_rss,
        peak_cpu_percent=peak_cpu,
        budget_peak_rss_mb=budget.peak_rss_mb,
        budget_cpu_percent=budget.cpu_percent,
        passed=passed,
        duration_seconds=duration_seconds
    )

def main():
    parser = argparse.ArgumentParser(description="ERIN Resource Profiler")
    parser.add_argument("--profile", choices=list(BUDGETS.keys()), default="standard", help="Profile to run")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    parser.add_argument("--output", type=Path, help="Output JSON file")
    args = parser.parse_args()

    result = run_profile(args.profile, args.duration)

    print(f"\nResource Profile Results ({args.profile}):")
    print(f"  Peak RSS: {result.peak_rss_mb:.1f} MB (budget: {result.budget_peak_rss_mb} MB)")
    print(f"  Peak CPU: {result.peak_cpu_percent:.1f}% (budget: {result.budget_cpu_percent}%)")
    print(f"  Duration: {result.duration_seconds:.1f}s")
    print(f"  Status: {'PASSED' if result.passed else 'FAILED'}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(asdict(result), f, indent=2)
        print(f"Results written to {args.output}")

    return 0 if result.passed else 1

if __name__ == "__main__":
    sys.exit(main())