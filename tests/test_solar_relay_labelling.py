"""Solar is a RELAY. The surfaces that sell it must not describe it as modelling.

services/solar_yield.py makes exactly one external call — Google's Solar API
buildingInsights:findClosest — and declares DATA_SOURCES = ["Google Solar API"].
The only arithmetic of ours is reducing Google's DC figure by NREL PVWatts
published defaults. Everything else is relayed as Google reports it; the module
docstring says so in as many words: "a Google Solar API pass-through and
computes none".

The landing page said otherwise. Measured 2026-08-25, it credited NSW Gov
building footprints, Bureau of Meteorology climate records and Heritage NSW,
named Google NOWHERE, and its methodology paragraph described a pipeline that
does not exist:

    "Building footprints are matched to your address using NSW Government
     property boundary and structure data. Roof orientation and pitch are
     derived from the footprint geometry. Annual irradiance is calculated from
     Bureau of Meteorology climate records for your location."

None of that runs. The Bureau of Meteorology is never queried by this product.

WHY NOTHING CAUGHT IT. scripts/dq_probe_pvlib_claim.py exists for exactly this
defect — "we do not name a method we do not run" — and it was CLEAN throughout,
because it walks base.rglob("*.py"). The false method claim is TypeScript. A
guard that reads one language cannot see a claim written in another, and the
marketing surface is where claims live.

This test reads the served copy as text, which is the only way to check a
TypeScript constant from pytest without a build step, and is the same technique
dq_probe_pvlib_claim.py uses on Python.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_LANDING = _ROOT / "frontend-nextjs" / "components" / "reports" / "landing" / "data" / "solar.ts"
_PAGE = _ROOT / "frontend-nextjs" / "app" / "reports" / "solar-yield" / "page.tsx"
_SERVICE = _ROOT / "services" / "solar_yield.py"

#: Sources this product does NOT query. Naming one on a surface that sells the
#: product is the same defect DQ-50 tracks in stored reports — a credit for a
#: source that was never called — one layer further out.
_NOT_QUERIED = (
    "Bureau of Meteorology",
    "Bureau of Met",
    "NSW Government building footprint",
    "NSW Government property boundary",
)


def _copy() -> str:
    """The SERVED strings, with `//` comments stripped.

    Comments are not copy. The source files carry a note explaining that the
    Bureau of Meteorology is never queried, and without this the test would
    fail on its own explanation — punishing the documentation that stops the
    defect coming back. Only what ships is checked.
    """
    out = []
    for f in (_LANDING, _PAGE):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("//"):
                continue
            out.append(line)
    return "\n".join(out)


def test_the_service_still_makes_exactly_one_external_call():
    """The premise. If solar gains a real second source, this test must be revisited.

    Without this, the assertions below could keep passing after the product
    genuinely started querying the Bureau of Meteorology — at which point they
    would be forbidding a true statement.
    """
    service = _SERVICE.read_text(encoding="utf-8")
    assert 'DATA_SOURCES = ["Google Solar API"]' in service, (
        "solar_yield.py's declared sources changed; re-derive what the landing "
        "copy may claim before trusting this file"
    )
    external = [ln for ln in service.splitlines()
                if "requests.get(" in ln or "requests.post(" in ln]
    assert len(external) == 1, f"expected one outbound call, found {len(external)}: {external}"


@pytest.mark.parametrize("phrase", _NOT_QUERIED)
def test_the_copy_does_not_credit_a_source_solar_never_queries(phrase):
    assert phrase not in _copy(), (
        f"solar's served copy names {phrase!r}, which this product does not query. "
        f"One call goes to Google's Solar API and nowhere else."
    )


def test_the_copy_names_the_source_it_does_use():
    """Removing the false credits is only half of it.

    Deleting 'Bureau of Meteorology' and stopping there would leave the yield
    figure looking like ours, which is the thing §5 of the repair prompt asks
    to prevent: solar must never read as our modelling.
    """
    assert "Google" in _copy(), (
        "solar's copy does not name Google anywhere, so the relayed figure reads "
        "as our own modelling"
    )


def test_the_loss_adjustment_is_still_claimed_as_ours():
    """The one number we DO alter must stay attributed to us, not to Google.

    Over-correcting into 'everything is Google's' would misdescribe the
    delivered figure, which we compute by applying PVWatts defaults to Google's
    DC value. Honest in both directions or it is not honest.
    """
    service = _SERVICE.read_text(encoding="utf-8")
    assert "PVWATTS_DEFAULT_SYSTEM_LOSS" in service
    assert "PVWatts" in _copy(), (
        "the copy no longer says the loss adjustment is ours, so the delivered "
        "figure reads as Google's when it is not"
    )
