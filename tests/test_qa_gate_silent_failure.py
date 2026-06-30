"""Tests for the silent-failure scanner refinement in scripts/qa_gate.py.

Webhook routes are exempt (returning a 200 ack on a handler error is the required
idiom); a catch that returns any value is handled; truly-silent catches in normal
API routes are still flagged.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from qa_gate import scan_diff_for_silent_failures  # noqa: E402


def _write(tmp, rel, content):
    p = os.path.join(tmp, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return rel


class TestSilentFailureRefinement:
    def test_webhook_returning_200_ack_is_not_flagged(self, tmp_path):
        rel = _write(
            str(tmp_path), "api/stripe/webhook/route.ts",
            "export async function POST() {\n"
            "  try { await sideEffect(); } catch (err) {\n"
            "    console.error('e', err);\n"
            "    return NextResponse.json({ received: true });\n"
            "  }\n}\n",
        )
        assert scan_diff_for_silent_failures([rel], str(tmp_path)) == []

    def test_non_webhook_truly_silent_catch_still_flagged(self, tmp_path):
        rel = _write(
            str(tmp_path), "api/foo/route.ts",
            "export async function POST() {\n"
            "  try { await bad(); } catch (err) {\n"
            "    console.error('only logs', err);\n"
            "  }\n}\n",
        )
        assert len(scan_diff_for_silent_failures([rel], str(tmp_path))) >= 1

    def test_non_webhook_returning_error_response_is_not_flagged(self, tmp_path):
        rel = _write(
            str(tmp_path), "api/bar/route.ts",
            "export async function POST() {\n"
            "  try { await bad(); } catch (err) {\n"
            "    console.error('e', err);\n"
            "    return NextResponse.json({ error: 'failed' }, { status: 500 });\n"
            "  }\n}\n",
        )
        assert scan_diff_for_silent_failures([rel], str(tmp_path)) == []
