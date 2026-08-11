# prior-art-checked: no existing manifest builder (repo grep 2026-08-03:
# brief_manifest.py builds the BRIEF's source manifest from DataFields, not an
# execution record from computation inputs; audit_trail.py logs endpoint-level
# queries with the deploy SHA but not the objects a computation consumed).
"""Execution manifests for satellite-derived reports.

Output-grounding campaign item 4 (§7 finding 2): citing Scene A while the
result came from cached Scene B is undetectable under bare citation. A
manifest must therefore be DERIVED FROM THE OBJECTS ACTUALLY PASSED INTO THE
COMPUTATION at the point of use — these helpers accept the live objects
(pystac Items, response fragments) and refuse to be assembled from a parallel
lookup by construction: they have no I/O.

Versioning: each service declares an ``ALGORITHM_VERSION`` constant naming its
algorithm revision (bumped when the method changes, not per deploy). The
deploy identity is separate and automatic: ``deploy_sha`` from
``RAILWAY_GIT_COMMIT_SHA`` (the same source audit_trail.py stamps), so a
manifest pins BOTH "which method" and "which build".
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

MANIFEST_KEY = "execution_manifest"
MANIFEST_SCHEMA_VERSION = 1


def stac_item_identity(item) -> dict:
    """Identity of one pystac Item, taken from the object itself."""
    dt = getattr(item, "datetime", None)
    props = getattr(item, "properties", None) or {}
    return {
        "id": getattr(item, "id", None),
        "datetime": dt.isoformat() if dt else props.get("datetime"),
        "cloud_cover": props.get("eo:cloud_cover"),
        "platform": props.get("platform"),
    }


def stac_items_identity(items) -> list[dict]:
    return [stac_item_identity(i) for i in (items or [])]


def build_manifest(
    *,
    product: str,
    algorithm_version: str,
    inputs: dict,
    query_params: Optional[dict] = None,
    parcel_identity: Optional[dict] = None,
) -> dict:
    """Assemble the envelope manifest.

    ``inputs`` carries the per-source identity dicts the SERVICE derived from
    its live objects (scene lists, imagery dates, raster keys). This function
    only adds the invariant frame: product, algorithm + deploy versions,
    schema version, and the build timestamp.
    """
    manifest = {
        "schema": MANIFEST_SCHEMA_VERSION,
        "product": product,
        "algorithm_version": algorithm_version,
        "deploy_sha": (os.environ.get("RAILWAY_GIT_COMMIT_SHA") or "")[:12] or None,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "inputs": inputs,
    }
    if query_params:
        manifest["query_params"] = query_params
    if parcel_identity:
        manifest["parcel_identity"] = parcel_identity
    return manifest
