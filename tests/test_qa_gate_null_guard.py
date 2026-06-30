"""Tests for the null-guard scanner refinement in scripts/qa_gate.py.

Recognises three common safe patterns that previously false-positived:
COUNT(*) in a Promise.all higher up, an early-return length guard in the handler,
and `const X = ...rows[0]` later read via X?.. Genuinely unguarded access still flags.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from qa_gate import scan_diff_for_unguarded_nulls  # noqa: E402


def _write(tmp, rel, content):
    p = os.path.join(tmp, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return rel


class TestNullGuardRefinement:
    def test_assign_then_optional_chain_not_flagged(self, tmp_path):
        rel = _write(
            str(tmp_path), "api/x/route.ts",
            "export async function GET() {\n"
            "  const res = await query('SELECT a FROM t WHERE id=$1', [id]);\n"
            "  const row = res.rows[0];\n"
            "  const a = row?.a === true;\n"
            "  return NextResponse.json({ a });\n}\n",
        )
        assert scan_diff_for_unguarded_nulls([rel], str(tmp_path)) == []

    def test_count_query_higher_up_not_flagged(self, tmp_path):
        rel = _write(
            str(tmp_path), "lib/c.ts",
            "async function counts() {\n"
            "  const queries = [\n"
            "    'SELECT COUNT(*) as count FROM t1',\n"
            "    'SELECT COUNT(*) as count FROM t2',\n"
            "  ];\n"
            "  const results = await Promise.all(queries.map(q => client.query(q)));\n"
            "  const [a, b] = results;\n"
            "  return {\n"
            "    t1: parseInt(a.rows[0].count),\n"
            "    t2: parseInt(b.rows[0].count),\n"
            "  };\n}\n",
        )
        assert scan_diff_for_unguarded_nulls([rel], str(tmp_path)) == []

    def test_early_return_length_guard_not_flagged(self, tmp_path):
        rel = _write(
            str(tmp_path), "api/y/route.ts",
            "export async function GET() {\n"
            "  const result = await query('SELECT v FROM t WHERE id=$1', [id]);\n"
            "  if (result.rows.length === 0) {\n"
            "    return NextResponse.json({ error: 'not found' }, { status: 404 });\n"
            "  }\n"
            "  const row = result.rows[0];\n"
            "  return NextResponse.json({ v: row.v });\n}\n",
        )
        assert scan_diff_for_unguarded_nulls([rel], str(tmp_path)) == []

    def test_genuinely_unguarded_still_flagged(self, tmp_path):
        rel = _write(
            str(tmp_path), "api/z/route.ts",
            "export async function GET() {\n"
            "  const r = await query('SELECT name FROM t WHERE id=$1', [id]);\n"
            "  const name = r.rows[0].name;\n"
            "  return NextResponse.json({ name });\n}\n",
        )
        assert len(scan_diff_for_unguarded_nulls([rel], str(tmp_path))) >= 1
