"""A depth claim must count the studies that can answer depth.

THE DEFECT. `floodStudies: 4` is the number of council flood studies ingested.
Five public surfaces used it to say "modelled flood **depth** ... 4 studies", and
`/for/conveyancers` named all four: "Hawkesbury, Tweed, Wollongong, Redbank".
Hawkesbury's FLOOD_STUDIES entry carries `has_depth: False` -- its rasters are
water LEVEL only, with no pre-computed depth band -- so it cannot answer a depth
question at any address. The true figure is three.

WHY NO CHECK CAUGHT IT. `verify_coverage_stats.py` compared the published 4
against `len(FLOOD_STUDIES)`, which is 4. The number was verified; the claim it
was protecting was not. That is the aim file's rule 10 -- "a check can PASS on the
wrong artifact, which is worse than not running" -- and it is the same shape as
the 71 it replaced: a count from one layer attached to a capability from another.

This file guards the two halves that verifier cannot see: that the constant keeps
matching the data, and that no SURFACE re-attaches a depth claim to the wrong one.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

COVERAGE_TS = ROOT / "frontend-nextjs" / "lib" / "coverage.ts"
FLOOD_TRUTH = ROOT / "services" / "flood_truth.py"
APP_DIR = ROOT / "frontend-nextjs" / "app"


def _flood_studies_block() -> str:
    text = FLOOD_TRUTH.read_text(encoding="utf-8")
    start = text.find("FLOOD_STUDIES: dict[str, dict] = {")
    assert start != -1, "FLOOD_STUDIES not found in services/flood_truth.py"
    return text[start:text.find("\n}\n", start)]


def _published() -> dict[str, int]:
    text = COVERAGE_TS.read_text(encoding="utf-8")
    m = re.search(r"export const COVERAGE\s*=\s*\{(.*?)\}\s*as const", text, re.S)
    assert m, "COVERAGE object not found in coverage.ts"
    return {k: int(v.replace(",", "")) for k, v in re.findall(r"(\w+):\s*([\d,]+)", m.group(1))}


def test_the_published_depth_count_matches_the_studies_that_carry_depth():
    block = _flood_studies_block()
    with_depth = len(re.findall(r'"has_depth":\s*True', block))
    assert _published()["floodDepthStudies"] == with_depth, (
        f"coverage.ts publishes floodDepthStudies="
        f"{_published().get('floodDepthStudies')} but {with_depth} FLOOD_STUDIES "
        f"entries carry has_depth=True"
    )


def test_depth_studies_cannot_exceed_studies_ingested():
    """The invariant the '130+' case needed: a subset cannot outnumber its set."""
    pub = _published()
    assert pub["floodDepthStudies"] <= pub["floodStudies"]


def test_hawkesbury_is_still_the_one_without_depth():
    """If Hawkesbury ever gains depth rasters this test fails, and it SHOULD --
    the copy naming Tweed/Wollongong/Redbank would then be understating us.

    Depth is water level minus ground level, so this only changes if someone
    computes it. That is a different rigour class from relaying a council's own
    raster, and it must not happen silently."""
    block = _flood_studies_block()
    m = re.search(r'"hawkesbury":\s*\{.*?"has_depth":\s*(\w+)', block, re.S)
    assert m, "hawkesbury entry or its has_depth flag not found"
    assert m.group(1) == "False", (
        "hawkesbury now claims has_depth=True. If real, update coverage.ts and the "
        "copy naming which councils carry depth; if accidental, this is a live "
        "depth claim for rasters that hold water level only."
    )


def _tsx_files() -> list[Path]:
    return sorted(APP_DIR.rglob("*.tsx"))


@pytest.mark.parametrize("path", _tsx_files(), ids=lambda p: p.name)
def test_no_surface_attaches_a_depth_claim_to_the_ingested_count(path: Path):
    """The guard that would have caught the original defect.

    A line may use floodStudies for "studies ingested". It may NOT use it in the
    same breath as a depth claim -- that is precisely what five surfaces did.
    """
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if "COVERAGE_DISPLAY.floodStudies" not in line and "COVERAGE.floodStudies" not in line:
            continue
        if re.search(r"\bdepth\b", line, re.I):
            pytest.fail(
                f"{path.relative_to(ROOT)}:{n} uses the INGESTED study count in a depth "
                f"claim. Use floodDepthStudies.\n    {line.strip()[:140]}"
            )
