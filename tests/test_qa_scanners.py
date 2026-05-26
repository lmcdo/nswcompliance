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
scan_python = _mod.scan_diff_for_python_adversarial
scan_untyped = _mod.scan_diff_for_untyped_method_calls


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


# ── Layer 8: Python adversarial scanner ──


class TestPythonSplitIndex:
    def test_flags_unguarded_split_index(self, tmp_path):
        name = _write_file(str(tmp_path), "service.py", """\
def process(zone_code):
    prefix = zone_code.split()[0]
    return prefix
""")
        results = scan_python([name], str(tmp_path))
        assert len(results) == 1
        assert "split" in results[0].lower()
        assert "IndexError" in results[0]

    def test_allows_strip_before_split(self, tmp_path):
        name = _write_file(str(tmp_path), "service.py", """\
def process(zone_code):
    prefix = zone_code.strip().split()[0]
    return prefix
""")
        results = scan_python([name], str(tmp_path))
        assert len(results) == 0

    def test_allows_conditional_split(self, tmp_path):
        name = _write_file(str(tmp_path), "service.py", """\
def process(zone_code):
    prefix = zone_code.split()[0] if zone_code and zone_code.strip() else ""
    return prefix
""")
        results = scan_python([name], str(tmp_path))
        assert len(results) == 0

    def test_skips_test_files(self, tmp_path):
        name = _write_file(str(tmp_path), "tests/test_service.py", """\
def test_split():
    prefix = "R2 Low".split()[0]
    assert prefix == "R2"
""")
        results = scan_python([name], str(tmp_path))
        assert len(results) == 0

    def test_skips_comments_and_docstrings(self, tmp_path):
        name = _write_file(str(tmp_path), "service.py", '''\
def process():
    """Example: val.split()[0] gets first token."""
    # zone.split()[0] would be the prefix
    return None
''')
        results = scan_python([name], str(tmp_path))
        assert len(results) == 0


class TestPythonUnsafeCast:
    def test_flags_float_on_db_value(self, tmp_path):
        name = _write_file(str(tmp_path), "service.py", """\
def process(row):
    val = row.get("amount")
    total = float(val) * 1.1
    return total
""")
        results = scan_python([name], str(tmp_path))
        assert any("float" in r and "None" in r for r in results)

    def test_allows_guarded_cast(self, tmp_path):
        name = _write_file(str(tmp_path), "service.py", """\
def process(row):
    val = row.get("amount")
    if val is not None:
        total = float(val) * 1.1
        return total
    return 0
""")
        results = scan_python([name], str(tmp_path))
        assert len(results) == 0


class TestPythonGetNullTrap:
    def test_flags_get_with_falsy_default_feeding_math(self, tmp_path):
        name = _write_file(str(tmp_path), "service.py", """\
def compute(data):
    count = data.get("total", 0)
    result = count + 1
    return result
""")
        results = scan_python([name], str(tmp_path))
        assert any("null trap" in r.lower() or ".get(" in r for r in results)

    def test_allows_get_without_math(self, tmp_path):
        name = _write_file(str(tmp_path), "service.py", """\
def display(data):
    label = data.get("name", "")
    print(label)
""")
        results = scan_python([name], str(tmp_path))
        assert len(results) == 0


# ── Layer 9: Untyped method call scanner (TS) ──


class TestUntypedMethodCalls:
    def test_flags_toUpperCase_on_body_input(self, tmp_path):
        name = _write_file(str(tmp_path), "api/route.ts", """\
export async function POST(req: NextRequest) {
  const body = await req.json();
  const { name } = body;
  const upper = name.toUpperCase();
  return NextResponse.json({ upper });
}
""")
        results = scan_untyped([name], str(tmp_path))
        assert len(results) == 1
        assert "toUpperCase" in results[0]
        assert "name" in results[0]

    def test_allows_typeof_guarded(self, tmp_path):
        name = _write_file(str(tmp_path), "api/route.ts", """\
export async function POST(req: NextRequest) {
  const body = await req.json();
  const { name } = body;
  const upper = typeof name === 'string' ? name.toUpperCase() : name;
  return NextResponse.json({ upper });
}
""")
        results = scan_untyped([name], str(tmp_path))
        assert len(results) == 0

    def test_allows_optional_chaining(self, tmp_path):
        name = _write_file(str(tmp_path), "api/route.ts", """\
export async function POST(req: NextRequest) {
  const body = await req.json();
  const { name } = body;
  const upper = name?.toUpperCase();
  return NextResponse.json({ upper });
}
""")
        results = scan_untyped([name], str(tmp_path))
        assert len(results) == 0

    def test_allows_null_check_guard(self, tmp_path):
        name = _write_file(str(tmp_path), "api/route.ts", """\
export async function POST(req: NextRequest) {
  const body = await req.json();
  const { name } = body;
  if (!name) return NextResponse.json({ error: 'missing' }, { status: 400 });
  const upper = name.toUpperCase();
  return NextResponse.json({ upper });
}
""")
        results = scan_untyped([name], str(tmp_path))
        assert len(results) == 0

    def test_skips_string_literals(self, tmp_path):
        name = _write_file(str(tmp_path), "api/route.ts", """\
const x = "hello".toUpperCase();
""")
        results = scan_untyped([name], str(tmp_path))
        assert len(results) == 0

    def test_skips_known_safe_objects(self, tmp_path):
        name = _write_file(str(tmp_path), "api/route.ts", """\
const upper = JSON.stringify(data).toUpperCase();
""")
        results = scan_untyped([name], str(tmp_path))
        assert len(results) == 0

    def test_deduplicates_same_variable(self, tmp_path):
        name = _write_file(str(tmp_path), "api/route.ts", """\
export async function POST(req: NextRequest) {
  const body = await req.json();
  const { code } = body;
  const a = code.toUpperCase();
  const b = code.toLowerCase();
  const c = code.trim();
}
""")
        results = scan_untyped([name], str(tmp_path))
        # Should report only once for 'code', not three times
        assert len(results) == 1

    def test_skips_test_files(self, tmp_path):
        name = _write_file(str(tmp_path), "test/api.ts", """\
const body = await req.json();
const { name } = body;
const upper = name.toUpperCase();
""")
        results = scan_untyped([name], str(tmp_path))
        assert len(results) == 0
