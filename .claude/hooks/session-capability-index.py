#!/usr/bin/env python3
"""SessionStart hook — injects thin capability index into context.

Counts existing data sources across three layers so Claude cannot claim
ignorance of what the codebase already has. ~10 lines of output.

Exit 0 always (never block session start). Stdout goes into context.
"""

import os
import re
import sys


def count_pattern(filepath: str, pattern: str) -> int:
    """Count regex matches in a file. Returns 0 if file missing."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return len(re.findall(pattern, f.read()))
    except FileNotFoundError:
        return 0


def list_matches(filepath: str, pattern: str) -> list[str]:
    """Return all regex group(1) matches from a file."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return re.findall(pattern, f.read())
    except FileNotFoundError:
        return []


def main():
    project = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    # --- 1. Spatial overlay layers (PostGIS) ---
    ingest_path = os.path.join(project, "scripts", "ingest_spatial_overlays.py")
    # Count entries in LAYER_CONFIG — each has "service" key
    overlay_count = count_pattern(ingest_path, r'"service":\s*"')

    # --- 2. Planning portal constraint queries (frontend) ---
    portal_path = os.path.join(project, "frontend-nextjs", "lib", "nsw-planning-portal.ts")
    portal_constraints = count_pattern(portal_path, r'(?:mineSubsidence|contaminatedLand|drinkingWater|terrestrialBiodiversity|coastalEnvironment|riparianLand|wetlands|anef|bushfire|flood|heritage)')
    # Deduplicate by just counting unique constraint types
    portal_types = list_matches(portal_path, r'(mineSubsidence|contaminatedLand|drinkingWaterCatchment|terrestrialBiodiversity|coastalEnvironment|riparianLand|wetlands|anef)')
    portal_unique = len(set(portal_types))

    # --- 3. Satellite/analysis services ---
    services_dir = os.path.join(project, "services")
    service_files = []
    if os.path.isdir(services_dir):
        service_files = [
            f for f in os.listdir(services_dir)
            if f.endswith(".py") and not f.startswith("__")
            and f not in ("utils.py", "config.py")
        ]

    # --- 4. Conveyancing orchestrator data sources ---
    conveyancing_path = os.path.join(project, "services", "conveyancing.py")
    convey_sources = count_pattern(conveyancing_path, r'def\s+_(?:fetch|get|query|check)')

    # --- 5. SEE intake auto-answered constraints ---
    intake_path = os.path.join(project, "frontend-nextjs", "lib", "see", "intake.ts")
    auto_unique = count_pattern(intake_path, r"Auto-answered from")

    # --- Output thin index ---
    print("CAPABILITY INDEX (auto-generated at session start):")
    print(f"  Spatial overlays (PostGIS): {overlay_count} layer types ingested")
    print(f"  Planning portal queries: {portal_unique} constraint types live in frontend")
    print(f"  SEE intake auto-answers: {auto_unique} constraints auto-populated from portal data")
    print(f"  Service modules: {len(service_files)} in services/")
    print(f"  Conveyancing data fetchers: {convey_sources} parallel queries")
    print(f"  Run /audit-capabilities before any architecture or data-source investigation.")

    sys.exit(0)


if __name__ == "__main__":
    main()
