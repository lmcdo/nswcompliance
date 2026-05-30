#!/usr/bin/env python3
"""UserPromptSubmit hook — deep capability audit on keyword trigger.

When the user's prompt contains architecture/data-source investigation
keywords, this hook injects a full capability manifest into context.
For non-matching prompts, exits silently (no output, no delay).

This prevents the failure mode where Claude researches external APIs
without first checking what the codebase already has.

Exit 0 always (never block user input). Stdout goes into context.
"""

import json
import os
import re
import sys
from pathlib import Path


# Keywords that suggest data-source or architecture investigation
TRIGGER_PATTERNS = [
    r"\bdata\s+source",
    r"\bwhat\s+(?:do\s+we|data|sources?|apis?)\s+(?:have|exist)",
    r"\bwhat(?:'s|\s+is)\s+(?:already\s+)?(?:built|integrated|available|live)",
    r"\bcapabilit(?:y|ies)\b",
    r"\bmethodology\b",
    r"\barchitecture\b",
    r"\bdisclosure\s+profile",
    r"\bclimate\s+(?:risk|data|score|assessment)",
    r"\bnew\s+(?:data|api|integration|pipeline|service)",
    r"\baudit[\s-]?capabilit",
    r"\bwhat\s+(?:spatial|overlay|constraint)",
    r"\bexisting\s+(?:data|service|api|source|pipeline|integration)",
    r"\bstage\s+4",  # Intelligence brief Stage 4 = climate
    r"\bwire\s+(?:up|in|existing)",
    r"\bport\s+(?:from|to|over)",
    r"\bwhat\s+(?:can|do)\s+we\s+(?:already|currently)",
]


def prompt_matches(prompt: str) -> bool:
    """Check if prompt contains any trigger keywords."""
    prompt_lower = prompt.lower()
    return any(re.search(p, prompt_lower) for p in TRIGGER_PATTERNS)


def scan_spatial_overlays(project: str) -> list[dict]:
    """Parse LAYER_CONFIG from ingest_spatial_overlays.py."""
    path = os.path.join(project, "scripts", "ingest_spatial_overlays.py")
    layers = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        # Extract layer entries: "layer_name": { ... "service": "X" ... }
        for m in re.finditer(
            r'"([a-z_]+)"\s*:\s*\{[^}]*"service":\s*"([^"]+)"',
            content, re.DOTALL
        ):
            layers.append({
                "key": m.group(1),
                "service": m.group(2),
            })
    except FileNotFoundError:
        pass
    return layers


def scan_portal_constraints(project: str) -> list[str]:
    """Find planning portal constraint types queried in frontend."""
    path = os.path.join(project, "frontend-nextjs", "lib", "nsw-planning-portal.ts")
    constraints = set()
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        # PlanningConstraints type fields
        for m in re.finditer(r"(\w+)\??\s*:\s*(?:boolean|string|number|any)", content):
            field = m.group(1)
            if field not in ("id", "address", "lot", "plan", "lat", "lng", "zone"):
                constraints.add(field)
        # Explicit service_name queries
        for m in re.finditer(r'service_name["\s:=]+["\']([^"\']+)', content):
            constraints.add(m.group(1))
    except FileNotFoundError:
        pass
    return sorted(constraints)


def scan_services(project: str) -> list[dict]:
    """List service modules with their main public functions."""
    services_dir = os.path.join(project, "services")
    results = []
    if not os.path.isdir(services_dir):
        return results
    for fname in sorted(os.listdir(services_dir)):
        if not fname.endswith(".py") or fname.startswith("__"):
            continue
        if fname in ("utils.py", "config.py", "__init__.py"):
            continue
        fpath = os.path.join(services_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            public_fns = re.findall(r"^def\s+([a-z_]\w+)\(", content, re.MULTILINE)
            public_fns = [f for f in public_fns if not f.startswith("_")]
            results.append({"file": fname, "functions": public_fns[:5]})
        except FileNotFoundError:
            continue
    return results


def scan_conveyancing_sources(project: str) -> list[str]:
    """List data fetch functions from conveyancing orchestrator."""
    path = os.path.join(project, "services", "conveyancing.py")
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return re.findall(r"def\s+(_?(?:fetch|get|query|check)\w+)\(", content)
    except FileNotFoundError:
        return []


def scan_see_intake(project: str) -> list[str]:
    """List auto-answered constraint keys from SEE intake."""
    path = os.path.join(project, "frontend-nextjs", "lib", "see", "intake.ts")
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return list(set(re.findall(r'"([a-z_]+(?:subsidence|contaminated|drinking|bushfire|flood|heritage|anef)[a-z_]*)"', content)))
    except FileNotFoundError:
        return []


def main():
    # Parse stdin for user prompt
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, Exception):
        sys.exit(0)

    prompt = input_data.get("prompt", "")
    if not prompt or not prompt_matches(prompt):
        sys.exit(0)

    # Prefer CLAUDE_PROJECT_DIR (always set by Claude Code) over cwd from stdin
    project = os.environ.get("CLAUDE_PROJECT_DIR", input_data.get("cwd", os.getcwd()))

    # Run all scans
    overlays = scan_spatial_overlays(project)
    portal = scan_portal_constraints(project)
    services = scan_services(project)
    convey = scan_conveyancing_sources(project)
    see_auto = scan_see_intake(project)

    # Output full manifest
    print("=" * 60)
    print("CAPABILITY AUDIT (auto-triggered by data/architecture keywords)")
    print("Audit your own codebase BEFORE researching external sources.")
    print("=" * 60)

    print(f"\n## Spatial Overlays (PostGIS) — {len(overlays)} layers")
    for layer in overlays:
        print(f"  - {layer['key']} (via {layer['service']})")

    print(f"\n## Planning Portal Constraints (live frontend queries) — {len(portal)} types")
    for c in portal[:20]:
        print(f"  - {c}")

    print(f"\n## Service Modules — {len(services)} files")
    for svc in services:
        fns = ", ".join(svc["functions"][:3])
        more = f" (+{len(svc['functions'])-3} more)" if len(svc["functions"]) > 3 else ""
        print(f"  - {svc['file']}: {fns}{more}")

    print(f"\n## Conveyancing Orchestrator — {len(convey)} data fetchers")
    for fn in convey:
        print(f"  - {fn}()")

    if see_auto:
        print(f"\n## SEE Intake Auto-Answers — {len(see_auto)} constraints")
        for key in sorted(see_auto):
            print(f"  - {key}")

    print("\n" + "=" * 60)
    print("Check these sources BEFORE proposing new integrations or APIs.")
    print("=" * 60)

    sys.exit(0)


if __name__ == "__main__":
    main()
