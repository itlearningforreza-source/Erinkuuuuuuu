#!/usr/bin/env python3
"""
ERIN Engineering Control Plane - Contract Validation

Checks for breaking changes in Pydantic models and OpenAPI contracts.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Any
from dataclasses import dataclass

@dataclass
class BreakingChange:
    type: str
    model: str
    field: str
    details: str

def extract_pydantic_models(file_path: Path) -> Dict[str, Any]:
    """Extract Pydantic model schemas from a Python file."""
    # This is a simplified version - in practice you'd import and inspect
    # For now, return empty dict as placeholder
    return {}

def check_breaking_changes(old_schema: Dict, new_schema: Dict, model_name: str) -> List[BreakingChange]:
    """Check for breaking changes between two JSON schemas."""
    changes = []

    # Check required fields
    old_required = set(old_schema.get("required", []))
    new_required = set(new_schema.get("required", []))
    removed_required = old_required - new_required
    for field in removed_required:
        changes.append(BreakingChange(
            type="REQUIRED_FIELD_REMOVED",
            model=model_name,
            field=field,
            details=f"Required field '{field}' was removed from {model_name}"
        ))

    # Check properties
    old_props = old_schema.get("properties", {})
    new_props = new_schema.get("properties", {})

    for prop_name, old_prop in old_props.items():
        if prop_name not in new_props:
            changes.append(BreakingChange(
                type="PROPERTY_REMOVED",
                model=model_name,
                field=prop_name,
                details=f"Property '{prop_name}' was removed from {model_name}"
            ))
        else:
            new_prop = new_props[prop_name]
            if not is_type_compatible(old_prop, new_prop):
                changes.append(BreakingChange(
                    type="TYPE_NARROWED",
                    model=model_name,
                    field=prop_name,
                    details=f"Property '{prop_name}' type was narrowed in {model_name}"
                ))

    # Check enum values
    for prop_name, old_prop in old_props.items():
        if prop_name in new_props:
            old_enum = old_prop.get("enum", [])
            new_enum = new_props[prop_name].get("enum", [])
            if old_enum and new_enum:
                removed_values = set(old_enum) - set(new_enum)
                if removed_values:
                    changes.append(BreakingChange(
                        type="ENUM_VALUES_REMOVED",
                        model=model_name,
                        field=prop_name,
                        details=f"Enum values {removed_values} removed from {prop_name}"
                    ))

    return changes

def is_type_compatible(old_type: Dict, new_type: Dict) -> bool:
    """Check if new_type is compatible with old_type (not more restrictive)."""
    old_t = old_type.get("type")
    new_t = new_type.get("type")

    if old_t != new_t:
        # Allow some widening
        if old_t == "integer" and new_t == "number":
            return True
        if old_t == "string" and new_t == "string":
            return True
        return False

    # Check format restrictions
    old_format = old_type.get("format")
    new_format = new_type.get("format")
    if old_format and new_format and old_format != new_format:
        return False

    # Check constraints
    for constraint in ["minimum", "maximum", "minLength", "maxLength", "pattern"]:
        old_val = old_type.get(constraint)
        new_val = new_type.get(constraint)
        if old_val is not None and new_val is not None:
            if constraint in ["minimum", "minLength"]:
                if new_val > old_val:
                    return False
            elif constraint in ["maximum", "maxLength"]:
                if new_val < old_val:
                    return False

    return True

def main():
    print("Contract validation check - placeholder implementation")
    print("In production, this would compare current schemas with baseline")
    return 0

if __name__ == "__main__":
    sys.exit(main())