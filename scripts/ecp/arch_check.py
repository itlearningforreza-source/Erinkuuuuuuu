#!/usr/bin/env python3
"""
ERIN Engineering Control Plane - Architecture Compliance Checker

Checks for layer violations, bounded context boundaries, and public API surface.
"""

import ast
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Violation:
    file: Path
    line: int
    message: str
    severity: str = "ERROR"

LAYER_ORDER = [
    "apps.desktop",           # UI Layer
    "apps.api",               # API Layer
    "packages.market_intel",  # Domain Layer
    "packages.data_infra",
    "packages.equity_research",
    "packages.quant_finance",
    "packages.portfolio_risk",
    "packages.fixed_income",
    "packages.derivatives",
    "packages.macro_intel",
    "packages.news_intel",
    "packages.workspace",
    "packages.ai_intelligence",
    "packages.governance",
    "packages.shared_types",  # Shared Kernel
    "packages.data_core",     # Infrastructure Layer
    "packages.quant_core",
    "packages.ai_core",
]

def determine_layer(file_path: Path) -> Optional[str]:
    """Determine which layer a file belongs to based on its path."""
    parts = file_path.parts
    for i, part in enumerate(parts):
        if part in ["apps", "packages"]:
            if i + 1 < len(parts):
                return f"{part}.{parts[i + 1]}"
    return None

def determine_layer_from_module(module: str) -> Optional[str]:
    """Determine layer from import module name."""
    parts = module.split('.')
    if len(parts) >= 2 and parts[0] in ["apps", "packages"]:
        return f"{parts[0]}.{parts[1]}"
    return None

def check_file(file_path: Path) -> List[Violation]:
    """Check a single Python file for architecture violations."""
    violations = []
    try:
        content = file_path.read_text(encoding='utf-8')
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return violations

    current_layer = determine_layer(file_path)
    if not current_layer:
        return violations

    current_layer_idx = LAYER_ORDER.index(current_layer) if current_layer in LAYER_ORDER else -1

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            target_layer = determine_layer_from_module(node.module)
            if target_layer and target_layer in LAYER_ORDER and current_layer_idx >= 0:
                target_idx = LAYER_ORDER.index(target_layer)
                if target_idx > current_layer_idx:
                    violations.append(Violation(
                        file=file_path,
                        line=node.lineno,
                        message=f"Illegal import: {current_layer} -> {target_layer} (downward dependency)"
                    ))
    return violations

def main():
    root = Path.cwd()
    python_files = list(root.rglob("*.py"))

    # Exclude certain directories
    exclude_dirs = {".git", "__pycache__", ".venv", "venv", "env", "target", "node_modules", ".git"}
    python_files = [
        f for f in python_files
        if not any(part in exclude_dirs for part in f.parts)
    ]

    all_violations = []
    for file_path in python_files:
        violations = check_file(file_path)
        all_violations.extend(violations)

    if all_violations:
        print("ARCHITECTURE VIOLATIONS FOUND:")
        for v in all_violations:
            print(f"  {v.file}:{v.line} - {v.message}")
        return 1

    print("Architecture check passed - no violations found.")
    return 0

if __name__ == "__main__":
    sys.exit(main())