"""Read one capture folder (written by capture.py). Every page-integrity check reads through this,
so the capture format is defined in exactly two places: capture.py writes it, load.py reads it.

prior-art-checked: no reader of this format exists; it is new with capture.py.
"""
from __future__ import annotations

import gzip
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

TAB_KEYS = ("sepp", "planning", "dcp")


class CaptureUnusable(Exception):
    """The capture failed or is incomplete. A check that hits this must exit 2, never pass."""


@dataclass
class Capture:
    folder: Path
    meta: dict[str, Any]
    calls: list[dict[str, Any]]
    rendered: dict[str, str] = field(default_factory=dict)

    def last(self, path: str, method: Optional[str] = None) -> Optional[dict[str, Any]]:
        """The last successful response to `path`. The page fires some calls 2-3 times; the last
        one is what is on screen."""
        hits = [c for c in self.calls
                if c["path"] == path and (method is None or c["method"] == method) and c["status"] < 400]
        return hits[-1] if hits else None

    def data(self, path: str, method: Optional[str] = None) -> Optional[Any]:
        """The JSON body of the last response, unwrapped from the {success, data} envelope."""
        c = self.last(path, method)
        if c is None or c["json"] is None:
            return None
        j = c["json"]
        d = j["data"] if isinstance(j, dict) and "data" in j and "success" in j else j
        # An empty body is no answer: treating {} as present made checks flag facts the route never
        # sent and report them as examined.
        return None if d in ({}, []) else d


def load(folder: Path | str) -> Capture:
    folder = Path(folder)
    meta_p = folder / "meta.json"
    if not meta_p.exists():
        raise CaptureUnusable(f"{folder}: no meta.json")
    meta = json.loads(meta_p.read_text(encoding="utf-8"))
    errors = json.loads((folder / "errors.json").read_text(encoding="utf-8")) if (folder / "errors.json").exists() else ["no errors.json"]
    if meta.get("exit") != 0 or errors:
        raise CaptureUnusable(f"{folder}: capture exit {meta.get('exit')}: {errors}")
    with gzip.open(folder / "calls.jsonl.gz", "rt", encoding="utf-8") as f:
        calls = [json.loads(line) for line in f if line.strip()]
    rendered = {}
    for k in TAB_KEYS:
        p = folder / "rendered" / f"{k}.txt"
        if not p.exists():
            raise CaptureUnusable(f"{folder}: no rendered/{k}.txt")
        rendered[k] = p.read_text(encoding="utf-8")
    return Capture(folder=folder, meta=meta, calls=calls, rendered=rendered)
