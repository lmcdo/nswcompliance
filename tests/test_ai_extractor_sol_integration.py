"""The Sol provider against the REAL OpenAI API. Opt-in, costs a fraction of a cent.

tests/test_ai_extractor.py stubs the SDK, so it proves the request is built correctly
but cannot prove the API accepts it -- a wrong content-part type, a model name the
account cannot reach, or a PDF the model cannot read would all pass a stub. This sends
a one-page PDF generated here and checks the provisions come back.

Run:
    PYTEST_REAL_API=1 pytest -m integration tests/test_ai_extractor_sol_integration.py -o addopts=
"""
import io
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

pytestmark = pytest.mark.integration


def _require_real_api():
    if os.environ.get("PYTEST_REAL_API") != "1":
        pytest.skip("Real-API test. Run with PYTEST_REAL_API=1 pytest -m integration "
                    "tests/test_ai_extractor_sol_integration.py -o addopts=")
    from dotenv import load_dotenv
    from dq_db import main_checkout  # a worktree has no .env of its own
    load_dotenv(main_checkout() / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.fail("PYTEST_REAL_API=1 was set but OPENAI_API_KEY is missing -- an "
                    "explicitly requested real-API test must not pass by skipping.")


def _one_page_pdf() -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.drawString(72, 780, "C1 Low Density Residential")
    c.drawString(72, 760, "1.2 Setbacks")
    c.drawString(72, 740, "Controls")
    c.drawString(72, 720, "C1 The front setback is to be a minimum of 6 metres.")
    c.showPage()
    c.save()
    return buf.getvalue()


def test_sol_reads_a_pdf_and_returns_parseable_provisions():
    _require_real_api()
    import ai_extractor

    raw = ai_extractor._call_with_retry("sol", _one_page_pdf(), ai_extractor.PROMPT)
    provisions = ai_extractor.parse_provisions(raw)
    assert provisions, f"no provisions parsed from Sol's answer: {raw[:300]!r}"
    joined = " ".join(str(p.get("text", "")) for p in provisions)
    assert "6 metres" in joined, f"the control text did not come back: {joined[:300]!r}"
