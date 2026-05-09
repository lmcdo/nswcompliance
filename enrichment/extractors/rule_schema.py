#!/usr/bin/env python3
"""
ExtractedRule schema — Python side of the data contract.

Mirrors frontend-nextjs/lib/schemas/extracted-rule.ts exactly.
Used by deterministic extractors, LLM caller, and validation gates.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class ComplianceType(str, Enum):
    NUMERIC_CHECK = "numeric_check"
    MERIT_ASSESSMENT = "merit_assessment"
    BINARY_PROHIBITION = "binary_prohibition"
    PROCEDURAL = "procedural"


class ExtractionMethod(str, Enum):
    REGEX = "regex"
    HEADING_RULE = "heading_rule"
    TABLE_PARSE = "table_parse"
    LLM = "llm"


class ExtractionConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


VALID_VALUE_TYPES = {
    "setback", "height", "fsr", "lot_area", "lot_width", "site_coverage",
    "landscaping", "deep_soil", "parking", "parking_spaces", "dimension",
    "wall_height", "floor_area", "dwelling_density", "solar_access",
    "privacy_distance", "other",
}

VALID_RELATIONSHIPS = {"supplements", "overrides", "defers_to", "see_also"}


@dataclass
class RuleCondition:
    when: str
    then_value: Optional[float] = None
    then_unit: Optional[str] = None
    then_text: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class RuleReference:
    target: str
    relationship: str  # supplements | overrides | defers_to | see_also

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ExtractedRule:
    compliance_type: str  # ComplianceType value
    extraction_method: str  # ExtractionMethod value
    extraction_confidence: str  # ExtractionConfidence value

    # Numeric values
    value_type: Optional[str] = None
    value_min: Optional[float] = None
    value_max: Optional[float] = None
    value_exact: Optional[float] = None
    unit: Optional[str] = None
    context: Optional[str] = None

    # Conditional/tiered
    conditions: list[RuleCondition] = field(default_factory=list)

    # Cross-references
    references: list[RuleReference] = field(default_factory=list)

    # Spatial
    has_spatial_component: Optional[bool] = None

    # Provenance
    raw_match: Optional[str] = None

    def to_dict(self) -> dict:
        d = {}
        d["compliance_type"] = self.compliance_type
        d["extraction_method"] = self.extraction_method
        d["extraction_confidence"] = self.extraction_confidence

        if self.value_type is not None:
            d["value_type"] = self.value_type
        if self.value_min is not None:
            d["value_min"] = self.value_min
        if self.value_max is not None:
            d["value_max"] = self.value_max
        if self.value_exact is not None:
            d["value_exact"] = self.value_exact
        if self.unit is not None:
            d["unit"] = self.unit
        if self.context is not None:
            d["context"] = self.context
        if self.conditions:
            d["conditions"] = [c.to_dict() for c in self.conditions]
        if self.references:
            d["references"] = [r.to_dict() for r in self.references]
        if self.has_spatial_component is not None:
            d["has_spatial_component"] = self.has_spatial_component
        if self.raw_match is not None:
            d["raw_match"] = self.raw_match

        return d


class ExtractionStatus(str, Enum):
    COMPLETE = "complete"
    LLM_COMPLETE = "llm_complete"
    REVIEW_NEEDED = "review_needed"
    SKIPPED = "skipped"


# ============================================================================
# VALIDATION
# ============================================================================

PLAUSIBILITY = {
    "setback": (0, 100),
    "height": (0, 200),
    "wall_height": (0, 200),
    "fsr": (0, 20),
    "lot_area": (0, 100000),
    "lot_width": (0, 200),
    "site_coverage": (0, 100),
    "landscaping": (0, 100),
    "deep_soil": (0, 100),
    "parking": (0, 1000),
    "parking_spaces": (0, 1000),
    "solar_access": (0, 100),
    "privacy_distance": (0, 100),
}


def validate_rule(rule: dict) -> list[str]:
    """Validate a single ExtractedRule dict. Returns list of error strings."""
    errors = []

    # Required fields
    for f in ("compliance_type", "extraction_method", "extraction_confidence"):
        if f not in rule:
            errors.append(f"Missing required field: {f}")

    ct = rule.get("compliance_type")
    if ct and ct not in [e.value for e in ComplianceType]:
        errors.append(f"Invalid compliance_type: {ct}")

    em = rule.get("extraction_method")
    if em and em not in [e.value for e in ExtractionMethod]:
        errors.append(f"Invalid extraction_method: {em}")

    ec = rule.get("extraction_confidence")
    if ec and ec not in [e.value for e in ExtractionConfidence]:
        errors.append(f"Invalid extraction_confidence: {ec}")

    vt = rule.get("value_type")
    if vt and vt not in VALID_VALUE_TYPES:
        errors.append(f"Invalid value_type: {vt}")

    # Numeric plausibility
    if vt and vt in PLAUSIBILITY:
        lo, hi = PLAUSIBILITY[vt]
        for fname in ("value_min", "value_max", "value_exact"):
            v = rule.get(fname)
            if v is not None and (v < lo or v > hi):
                errors.append(f"Implausible {vt} {fname}={v} (expected {lo}-{hi})")

    # Percentage unit check
    if rule.get("unit") == "%":
        for fname in ("value_min", "value_max", "value_exact"):
            v = rule.get(fname)
            if v is not None and (v < 0 or v > 100):
                errors.append(f"Implausible percentage {fname}={v}%")

    # Min/max consistency
    vmin = rule.get("value_min")
    vmax = rule.get("value_max")
    if vmin is not None and vmax is not None and vmin > vmax:
        errors.append(f"value_min ({vmin}) > value_max ({vmax})")

    # Compliance type consistency
    if ct == "numeric_check":
        has_value = any(rule.get(f) is not None for f in ("value_min", "value_max", "value_exact"))
        has_conditions = bool(rule.get("conditions"))
        if not has_value and not has_conditions:
            errors.append("numeric_check must have a value or conditions")

    # Condition completeness
    for cond in rule.get("conditions", []):
        if cond.get("then_value") is None and not cond.get("then_text"):
            errors.append(f"Condition '{cond.get('when', '?')}' has no outcome")

    # Reference validity
    for ref in rule.get("references", []):
        if ref.get("relationship") not in VALID_RELATIONSHIPS:
            errors.append(f"Invalid reference relationship: {ref.get('relationship')}")

    return errors


def validate_provision_rules(rules: list[dict]) -> list[str]:
    """Validate an array of rules for a provision."""
    errors = []
    if not isinstance(rules, list):
        return ["Expected list of rules"]

    for i, rule in enumerate(rules):
        rule_errors = validate_rule(rule)
        errors.extend(f"Rule[{i}]: {e}" for e in rule_errors)

    return errors
