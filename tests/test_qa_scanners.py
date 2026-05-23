"""Tests for qa_gate.py type boundary and silent failure scanners."""

import importlib.util
import os
import tempfile
import pytest

# Load qa_gate module
_spec = importlib.util.spec_from_file_location(
    "qa_gate",
    os.path.join(os.path.dirname(__file__), "..", "scripts", "qa_gate.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

scan_type = _mod.scan_diff_for_type_boundaries
scan_silent = _mod.scan_diff_for_silent_failures


def _write_file(tmpdir: str, name: str, content: str) -> str:
    path = os.path.join(tmpdir, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return name


# ── Heuristic A: falsy JSX guard ──


class TestFalsyJSXGuard:
    def test_flags_numeric_looking_variable(self, tmp_path):
        name = _write_file(str(tmp_path), "Comp.tsx", """\
export function Comp({ count }: { count: number }) {
  return <div>{count && <span>{count}</span>}</div>
}
""")
        results = scan_type([name], str(tmp_path))
        assert len(results) == 1
        assert "count" in results[0]
        assert "falsy" in results[0].lower()

    def test_ignores_boolean_variable(self, tmp_path):
        name = _write_file(str(tmp_path), "Comp.tsx", """\
export function Comp({ isActive }: { isActive: boolean }) {
  return <div>{isActive && <span>Active</span>}</div>
}
""")
        results = scan_type([name], str(tmp_path))
        assert len(results) == 0

    def test_ignores_qa_ignore_comment(self, tmp_path):
        name = _write_file(str(tmp_path), "Comp.tsx", """\
export function Comp({ count }: { count: number }) {
  return <div>{count && <span>{count}</span>}</div>  // qa-ignore: type-boundary
}
""")
        results = scan_type([name], str(tmp_path))
        assert len(results) == 0

    def test_skips_test_files(self, tmp_path):
        name = _write_file(str(tmp_path), "test/Comp.tsx", """\
export function Comp({ count }: { count: number }) {
  return <div>{count && <span>{count}</span>}</div>
}
""")
        results = scan_type([name], str(tmp_path))
        assert len(results) == 0

    def test_skips_non_tsx_files(self, tmp_path):
        name = _write_file(str(tmp_path), "file.py", """\
if count and do_something():
    pass
""")
        results = scan_type([name], str(tmp_path))
        assert len(results) == 0


# ── Heuristic B: strict null check ──


class TestStrictNullCheck:
    def test_flags_triple_equals_null(self, tmp_path):
        name = _write_file(str(tmp_path), "utils.ts", """\
function check(val: string | null | undefined) {
  if (val === null) return 'missing';
  return val;
}
""")
        results = scan_type([name], str(tmp_path))
        assert len(results) == 1
        assert "=== null" in results[0]

    def test_allows_double_equals_null(self, tmp_path):
        name = _write_file(str(tmp_path), "utils.ts", """\
function check(val: string | null | undefined) {
  if (val == null) return 'missing';
  return val;
}
""")
        results = scan_type([name], str(tmp_path))
        assert len(results) == 0

    def test_allows_null_or_undefined_check(self, tmp_path):
        name = _write_file(str(tmp_path), "utils.ts", """\
function check(val: string | null | undefined) {
  if (val === null || val === undefined) return 'missing';
  return val;
}
""")
        results = scan_type([name], str(tmp_path))
        assert len(results) == 0


# ── Heuristic C: empty catch blocks in API routes ──


class TestEmptyCatch:
    def test_flags_empty_catch_in_route(self, tmp_path):
        name = _write_file(str(tmp_path), "api/route.ts", """\
export async function GET() {
  try {
    const data = await fetch('/api');
  } catch (e) {
  }
}
""")
        results = scan_silent([name], str(tmp_path))
        assert any("empty catch" in r.lower() for r in results)

    def test_ignores_empty_catch_in_component(self, tmp_path):
        name = _write_file(str(tmp_path), "components/Comp.tsx", """\
export function Comp() {
  try {
    localStorage.setItem('key', 'val');
  } catch (e) {
  }
}
""")
        results = scan_silent([name], str(tmp_path))
        assert len(results) == 0

    def test_allows_catch_with_throw(self, tmp_path):
        name = _write_file(str(tmp_path), "api/route.ts", """\
export async function GET() {
  try {
    const data = await fetch('/api');
  } catch (e) {
    console.error(e);
    throw e;
  }
}
""")
        results = scan_silent([name], str(tmp_path))
        assert len(results) == 0

    def test_flags_log_only_catch_in_route(self, tmp_path):
        name = _write_file(str(tmp_path), "api/route.ts", """\
export async function GET() {
  try {
    const data = await fetch('/api');
  } catch (e) {
    console.error('failed', e);
  }
}
""")
        results = scan_silent([name], str(tmp_path))
        assert any("only logs" in r.lower() for r in results)


# ── Heuristic D: catch returning success ──


class TestCatchReturningSuccess:
    def test_flags_catch_returning_200(self, tmp_path):
        name = _write_file(str(tmp_path), "api/route.ts", """\
export async function GET() {
  try {
    const data = await fetchData();
    return NextResponse.json({ data });
  } catch (e) {
    return NextResponse.json({ data: [] });
  }
}
""")
        results = scan_silent([name], str(tmp_path))
        assert any("returns success" in r.lower() for r in results)

    def test_allows_catch_returning_error_status(self, tmp_path):
        name = _write_file(str(tmp_path), "api/route.ts", """\
export async function GET() {
  try {
    const data = await fetchData();
    return NextResponse.json({ data });
  } catch (e) {
    return NextResponse.json({ error: e.message }, { status: 500 });
  }
}
""")
        results = scan_silent([name], str(tmp_path))
        assert len(results) == 0
