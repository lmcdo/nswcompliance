#!/usr/bin/env python3
# prior-art-checked: reuse not viable because nothing in this repo compares a SQL
# identifier written in code against the live database schema. The near neighbours
# were each opened and rejected on scope:
#   * tests/test_dcp_schema_gate.py — "schema gate" by name only; it inspects
#     EXTRACTED PROVISION TEXT for garbling artifacts. Never touches the catalog.
#   * scripts/brief_contract_drift.py — compares a Python service's OUTPUT DICT
#     KEYS to a typed S2 contract. Runtime payloads, not SQL, not the catalog.
#   * scripts/lint_bracket_access.py, scripts/lint_brief_failsoft.py — AST/text
#     lints over Python source with no database connection at all.
#   * scripts/check_*_schema.py (~20 files) — one-off "print me the columns of
#     table X" diagnostics, non-gating, hardcoded to a single table each.
#   * scripts/validate_zone_code_validity.py — validates stored DATA against
#     ground truth. This validates the CODE's references against the catalog.
#     Same three-state discipline, deliberately reused; different axis.
# Frontend sweep: frontend-nextjs/app/api/{check-contextual-cols,check-definitions,
# test-contextual-guidance}/route.ts touch information_schema, but each is an
# ad-hoc debug endpoint printing columns for one hardcoded table; none gate.
"""Validate that every table and column referenced in code exists in the database.

WHY THIS EXISTS
---------------
`dcp_general_provisions` and `dcp_general_requirements` were renamed to
`zz_legacy_*`. `frontend-nextjs/app/api/compliance/dcp-complete/route.ts` still
queries both — the first at STEP 1, marked "ALWAYS" — so the route raises and
returns HTTP 500 for every address it is called with.

3,207 Python tests, ~900 Jest tests, a TSC gate, a bracket lint, a fail-soft lint,
a liability scan and the QA gate all stayed green through this. SQL identifiers
live inside template literals and Python strings: the type checker cannot see
them, and no test that avoids a real database can either. There was no gate that
asserted the referenced objects still exist. This is that gate.

It generalises past the two known tables — the same blind spot covers the
documented `former_council` / `source_ref` column drift on `regulatory_provisions`
(see memory reference-db-connection-and-live-schema-2026-07).

THE RULE IT ENFORCES
--------------------
For every SQL string in the scanned roots:
  * every base table named after FROM / JOIN / UPDATE / INSERT INTO / DELETE FROM
    must exist in the live catalog (tables and views both count), and
  * every alias-qualified column (`alias.column`, where `alias` was bound to a
    real base table in the same statement) must exist on that table.

THREE-STATE, NEVER PASS/FAIL
----------------------------
Absence of proof is not proof of absence — conflating "could not check" with
"checked and fine" is exactly how DQ-30 stayed hidden behind a green tick. Every
reference lands in exactly one bucket:

  VALID        resolves against the live catalog
  INVALID      names an object the catalog does not have  -> the defect
  UNVERIFIABLE cannot be resolved by static reading, and is NOT a pass:
                 * the name is built at runtime (`FROM ${table}`)
                 * it is schema-qualified outside the search_path
                 * it is an alias bound to a CTE or derived table, so its
                   columns have no catalog entry to check against

Unqualified columns (`SELECT category FROM ...`) are deliberately OUT OF SCOPE
and counted separately as NOT CHECKED, never as VALID. Distinguishing a bare
column from a function name, keyword or literal needs a real SQL parser; guessing
would produce false alarms, and a check people learn to ignore is worse than no
check. The coverage number is printed so the gap stays visible.

Read-only. Opens one connection, issues two catalog SELECTs, writes nothing.

EXIT CODES
----------
  0  no INVALID references
  1  at least one INVALID reference (or --max-unverifiable exceeded)
  2  could not load the catalog — a blocker, never reported as a pass

USAGE
-----
  python scripts/validate_schema_contract.py
  python scripts/validate_schema_contract.py --root services --quiet
  python scripts/validate_schema_contract.py --max-unverifiable 40
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# Roots scanned by default: the two places that talk to the database.
DEFAULT_ROOTS = (
    ("frontend-nextjs/app/api", (".ts", ".tsx")),
    ("services", (".py",)),
)

# Schemas on the connection's search_path. An identifier qualified with anything
# else cannot be resolved from here and is reported UNVERIFIABLE, not INVALID.
SEARCH_PATH_SCHEMAS = ("public", "extensions")

# Words that can legally follow FROM/JOIN and are not table names.
_NOT_A_TABLE = {
    "select", "lateral", "only", "unnest", "generate_series", "jsonb_array_elements",
    "jsonb_array_elements_text", "json_array_elements", "regexp_split_to_table",
    "values", "dual",
}

# Words that can sit where an alias would and are not aliases.
_NOT_AN_ALIAS = {
    "where", "on", "using", "group", "order", "limit", "offset", "having", "window",
    "union", "intersect", "except", "left", "right", "inner", "outer", "full", "cross",
    "join", "set", "returning", "for", "fetch", "as", "and", "or", "not", "with",
    "values", "lateral", "natural", "tablesample", "into",
}

_SQL_VERB = re.compile(r"\b(select|insert\s+into|update|delete\s+from)\b", re.I)

# A literal only counts as SQL if it OPENS like SQL. Without this, any English
# sentence containing a SQL verb qualifies — verified false positives were an LLM
# system prompt ("...you select WHICH facts...") and a log line ("Skipping
# last_checked update for ..."), both of which then donated the following word as
# a table name. Deliberately excludes AND/OR/WHERE as openers: fragments starting
# that way rarely name a table, and admitting them re-opens the prose hole.
_SQL_OPENER = re.compile(
    r"^\s*\(?\s*(with|select|insert\s+into|update|delete\s+from|from|"
    r"(?:left|right|inner|outer|full|cross)\s+join|join|union|values)\b",
    re.I,
)

# Backstop for anything that slips past the opener test: common English words can
# never be table names.
_STOPWORDS = {
    "the", "a", "an", "this", "that", "these", "those", "for", "or", "and", "it",
    "its", "them", "each", "all", "any", "every", "some", "no", "not", "now",
    "here", "there", "you", "your", "our", "their", "which", "what", "when",
}

# A table reference: the keyword, then the name. The `(?<!do\s)` guard keeps
# `ON CONFLICT ... DO UPDATE SET` from reading `SET` as a table name.
_TABLE_REF = re.compile(
    r"\b(?<!do\s)(from|join|update|insert\s+into|delete\s+from)\s+"
    r"(?:only\s+)?"
    r"(\$\{[^}]*\}|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?|\()"
    r"(\s*\()?",
    re.I,
)

# `FROM tbl alias` / `FROM tbl AS alias` — used to bind columns to a table.
_ALIAS_BIND = re.compile(
    r"\b(?:from|join|update)\s+(?:only\s+)?"
    r"([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)"
    r"\s+(?:as\s+)?([A-Za-z_][A-Za-z0-9_]*)",
    re.I,
)

_CTE_NAME = re.compile(
    r"(?:\bwith\s+(?:recursive\s+)?|,\s*)([A-Za-z_][A-Za-z0-9_]*)\s+as\s*"
    r"(?:(?:not\s+)?materialized\s*)?\(",
    re.I,
)

_QUALIFIED_COL = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b")

# String literals that might carry SQL.
_TS_BACKTICK = re.compile(r"`([^`]*)`", re.S)
_PY_TRIPLE = re.compile(r'"""(.*?)"""|\'\'\'(.*?)\'\'\'', re.S)
_PY_SINGLE = re.compile(r'"([^"\n]*)"|\'([^\'\n]*)\'')

_FULL_LINE_COMMENT = re.compile(r"^[ \t]*(?://|#)", re.M)


# --------------------------------------------------------------------------- #
# extraction
# --------------------------------------------------------------------------- #
def _bare(identifier: str) -> str:
    """Last dotted segment of an identifier, lower-cased; '' if there isn't one.

    Written once rather than inlined at each call site: an identifier can arrive
    empty or whitespace-only from a malformed match, and four separate copies of
    `x.split('.')[-1].lower()` is four separate places for that to be handled
    differently.
    """
    cleaned = (identifier or "").strip()
    if not cleaned:
        return ""
    return cleaned.rsplit(".", 1)[-1].lower()


def _strip_commented_out_code(src: str) -> str:
    """Blank whole-line // and # comments.

    Commented-out query blocks are the one realistic source of phantom table
    references. Only FULL-line comments are removed: a mid-line `//` is usually a
    URL, and `--` is SQL's own comment marker, handled later inside the literal.
    """
    return "\n".join(
        "" if _FULL_LINE_COMMENT.match(line) else line for line in src.splitlines()
    )


def _strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    return re.sub(r"--[^\n]*", " ", sql)


def _neutralise_interpolation(sql: str) -> str:
    """Keep `${...}` where a table name goes, blank it everywhere else.

    A `${}` in the table slot means a runtime-built name (UNVERIFIABLE, and worth
    saying so). Anywhere else it is a value and its inner text — often JS property
    access like `${row.id}` — would otherwise be misread as a qualified column.
    """
    def repl(m: re.Match) -> str:
        before = sql[max(0, m.start() - 24):m.start()].lower()
        if re.search(r"\b(from|join|update|into)\s+$", before):
            return "${}"
        return " ? "

    sql = re.sub(r"\$\{[^{}]*\}", repl, sql)
    return re.sub(r"\$\d+", " ? ", sql)


def _python_string_literals(src: str):
    """Yield (text, line) for Python string constants, EXCLUDING docstrings.

    Parsed with `ast`, not regex, for one reason: docstrings are the dominant
    source of phantom table names. Prose like "update the record from the queue"
    trips every text-based heuristic — it opens with a SQL verb and contains FROM.
    The AST knows a docstring is the first statement of a module, class or
    function, so it can be removed by structure instead of by guesswork.
    f-strings contribute their literal parts, with each `{...}` replaced by the
    same runtime-value marker used for TS interpolation.
    """
    import ast

    try:
        tree = ast.parse(src)
    except SyntaxError:
        return

    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None) or []
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstrings:
                continue
            yield node.value, getattr(node, "lineno", 1)
        elif isinstance(node, ast.JoinedStr):
            parts = []
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    parts.append(v.value)
                else:
                    parts.append("${}")
            yield "".join(parts), getattr(node, "lineno", 1)


def iter_sql_literals(path: Path, src: str):
    """Yield (sql_text, line_number) for every string literal that looks like SQL."""
    if path.suffix == ".py":
        candidates = list(_python_string_literals(src))
    else:
        stripped = _strip_commented_out_code(src)
        candidates = [
            (m.group(1), stripped.count("\n", 0, m.start()) + 1)
            for m in _TS_BACKTICK.finditer(stripped)
        ]

    for text, line in candidates:
        if not _SQL_VERB.search(text) or not _SQL_OPENER.match(text):
            continue
        yield _neutralise_interpolation(_strip_sql_comments(text)), line


def analyse_sql(sql: str, extra_ctes: frozenset[str] = frozenset()):
    """Return (table_refs, alias_map, cte_names, qualified_cols, unqualified_count).

    table_refs is a list of raw names (or the literal '${}' for runtime-built).
    alias_map binds an alias to a base-table name, or to None when it is bound to
    a CTE or derived table — the difference between "check it" and "cannot".
    """
    # Stripped here as well as at extraction so the function is correct when called
    # directly (tests, future callers) and not only via iter_sql_literals. Idempotent.
    sql = _strip_sql_comments(sql)

    # File-level CTE names are unioned in: a query is often assembled from several
    # template fragments, so the `WITH x AS (` that defines a name can sit in a
    # different literal from the `FROM x` that uses it. Scoping CTEs per-statement
    # would report those as missing tables.
    ctes = {m.group(1).lower() for m in _CTE_NAME.finditer(sql)} | set(extra_ctes)

    tables: list[str] = []
    for m in _TABLE_REF.finditer(sql):
        keyword, name = m.group(1).lower(), m.group(2)
        if name == "(":
            continue  # derived table
        # A '(' after the name means a set-returning function in a FROM/JOIN, but
        # it is the column list in `INSERT INTO t (a, b)` — where the name is a
        # real table. Applying the skip to both loses every INSERT.
        if m.group(3) and keyword in ("from", "join"):
            continue
        if name.startswith("${"):
            tables.append("${}")
            continue
        if _bare(name) in _NOT_A_TABLE | _STOPWORDS:
            continue
        tables.append(name)

    alias_map: dict[str, str | None] = {}
    for m in _ALIAS_BIND.finditer(sql):
        table, alias = m.group(1), m.group(2)
        if alias.lower() in _NOT_AN_ALIAS:
            continue
        bare = _bare(table)
        alias_map[alias.lower()] = None if bare in ctes else table
    # A table used without an alias is still addressable by its own bare name.
    for t in tables:
        if t != "${}":
            bare = _bare(t)
            alias_map.setdefault(bare, None if bare in ctes else t)

    qualified: list[tuple[str, str]] = []
    for m in _QUALIFIED_COL.finditer(sql):
        qualifier, col = m.group(1).lower(), m.group(2)
        if qualifier in SEARCH_PATH_SCHEMAS:
            continue  # schema-qualified table name, not a column
        if qualifier in alias_map:
            qualified.append((qualifier, col))

    # Everything else that could be a bare column — counted, never judged.
    unqualified = len(re.findall(r"\bselect\b", sql, re.I))

    return tables, alias_map, ctes, qualified, unqualified


# --------------------------------------------------------------------------- #
# catalog
# --------------------------------------------------------------------------- #
DEFAULT_BASELINE = "scripts/schema_contract_baseline.json"

# prior-art-checked: reuse not viable as a shared module, but the CONVENTION here
# is deliberately copied rather than invented. The repo has two ratchets and both
# were opened: scripts/check_test_baselines.py compares a numeric floor per service
# and exposes nothing but main(); scripts/brief_field_coverage_ratchet.py::check()
# compares dict[layer -> field list]. Neither offers an importable baseline loader,
# and neither shape fits a set of (file, reference) pairs carrying triage metadata.
# What IS reused: the JSON-baseline-beside-the-script layout, the 0/1/2 exit codes,
# and the shrink-only rule that check_test_baselines.py enforces for test counts.
# (The guard's suggestions — intelligence_brief.py, conveyancing.py, the blog page —
# matched on ordinary English words like "baseline"/"accepted" and contain no
# baseline mechanism; each was checked before writing this.)


def load_baseline(repo: Path, path: str | None) -> dict:
    """Read the known-defect list. A missing file means no suppressions, not a pass."""
    import json

    p = repo / (path or DEFAULT_BASELINE)
    if not p.exists():
        return {"entries": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"ERROR: baseline {p} is unreadable ({exc}). Refusing to run rather "
              f"than guessing whether it suppresses nothing or everything.",
              file=sys.stderr)
        sys.exit(2)


def write_baseline(repo: Path, path: str | None, findings: dict) -> None:
    import json

    p = repo / (path or DEFAULT_BASELINE)
    entries = [
        {"file": f, "ref": ref, "kind": kind, "status": "unreviewed", "note": ""}
        for (f, ref), (kind, _lines) in sorted(findings.items())
    ]
    p.write_text(json.dumps({
        "_comment": "Known invalid SQL references, accepted so the gate can be "
                    "enforced today. This list may only SHRINK: a new entry fails "
                    "CI, and an entry that no longer occurs ALSO fails CI, so it "
                    "gets deleted rather than lingering as a permanent amnesty.",
        "entries": entries,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {p}")


def _repo_root() -> Path:
    here = Path(__file__).resolve().parent.parent
    return here


def _load_env() -> None:
    """Find .env in the checkout, then in the main worktree if this is a linked one."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(_repo_root() / ".env")
    if os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL"):
        return
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=_repo_root(), capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        if common:
            load_dotenv(Path(common).parent / ".env")
    except Exception:  # noqa: BLE001 - env discovery is best-effort
        pass


def load_catalog() -> tuple[set[str], dict[str, set[str]]]:
    """Return (table names, {table: {columns}}), all lower-cased."""
    _load_env()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — the catalog cannot be read, so nothing "
              "can be verified. This is a blocker, not a pass.", file=sys.stderr)
        sys.exit(2)
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 not installed — cannot read the catalog.", file=sys.stderr)
        sys.exit(2)

    schemas = tuple(SEARCH_PATH_SCHEMAS)
    conn = psycopg2.connect(url)
    try:
        conn.set_session(readonly=True, autocommit=True)
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30000'")
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema IN %s",
            (schemas,),
        )
        tables = {r[0].lower() for r in cur.fetchall()}
        cur.execute(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema IN %s",
            (schemas,),
        )
        cols: dict[str, set[str]] = defaultdict(set)
        for t, c in cur.fetchall():
            cols[t.lower()].add(c.lower())
        return tables, cols
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Validate SQL identifiers against the live schema.")
    ap.add_argument("--root", action="append",
                    help="Directory to scan (repeatable; default: frontend-nextjs/app/api, services).")
    ap.add_argument("--max-unverifiable", type=int, default=None,
                    help="Fail if UNVERIFIABLE references exceed this ratchet.")
    ap.add_argument("--baseline", default=None,
                    help=f"Known-defect file (default: {DEFAULT_BASELINE}). "
                         "Suppresses pre-existing findings; NEW ones still fail.")
    ap.add_argument("--write-baseline", action="store_true",
                    help="Rewrite the baseline from the current findings. Use once, "
                         "when adopting the gate — never to silence a new failure.")
    ap.add_argument("--quiet", action="store_true", help="Summary only.")
    args = ap.parse_args()

    repo = _repo_root()
    roots = ([(r, (".ts", ".tsx", ".py")) for r in args.root] if args.root
             else list(DEFAULT_ROOTS))

    tables, columns = load_catalog()
    if not tables:
        print("ERROR: catalog returned zero tables — cannot verify anything.", file=sys.stderr)
        return 2

    # Findings are keyed by (file, ref) and NOT by line number. A line number is a
    # positional identity: it churns on every unrelated edit above it, which would
    # make the baseline below fail for reasons that have nothing to do with the
    # defect. Same lesson as keying provisions by clause rather than by page.
    invalid_tables: dict[tuple[str, str], list[int]] = defaultdict(list)
    invalid_columns: dict[tuple[str, str], list[int]] = defaultdict(list)
    unverifiable: dict[str, list[str]] = defaultdict(list)
    n_valid_tables = n_valid_cols = n_files = n_stmts = n_unqualified = 0
    seen_tables: set[str] = set()

    for root, suffixes in roots:
        base = repo / root
        if not base.exists():
            print(f"WARNING: root not found, skipped: {root}", file=sys.stderr)
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in suffixes or not path.is_file():
                continue
            try:
                src = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            n_files += 1
            rel = path.relative_to(repo).as_posix()

            statements = list(iter_sql_literals(path, src))
            file_ctes = frozenset(
                m.group(1).lower()
                for sql, _ in statements
                for m in _CTE_NAME.finditer(sql)
            )

            for sql, line in statements:
                n_stmts += 1
                refs, alias_map, ctes, quals, unq = analyse_sql(sql, file_ctes)
                n_unqualified += unq

                for raw in refs:
                    if raw == "${}":
                        unverifiable[rel].append(f"L{line}: table name built at runtime (`${{}}`)")
                        continue
                    parts = raw.split(".")
                    if len(parts) == 2 and parts[0].lower() not in SEARCH_PATH_SCHEMAS:
                        unverifiable[rel].append(f"L{line}: {raw} (schema outside search_path)")
                        continue
                    bare = _bare(raw)
                    if bare in ctes:
                        continue  # a CTE, not a base table
                    seen_tables.add(bare)
                    if bare in tables:
                        n_valid_tables += 1
                    else:
                        invalid_tables[(rel, bare)].append(line)

                for alias, col in quals:
                    bound = alias_map.get(alias)
                    if bound is None:
                        unverifiable[rel].append(
                            f"L{line}: {alias}.{col} (alias bound to a CTE or subquery)")
                        continue
                    bare = _bare(bound)
                    if bare not in tables:
                        unverifiable[rel].append(
                            f"L{line}: {alias}.{col} (its table `{bare}` does not exist)")
                        continue
                    if col.lower() in columns.get(bare, set()):
                        n_valid_cols += 1
                    else:
                        invalid_columns[(rel, f"{bare}.{col}")].append(line)

    unverifiable = {f: sorted(set(v)) for f, v in unverifiable.items()}

    findings = {k: ("table", sorted(set(v))) for k, v in invalid_tables.items()}
    findings.update({k: ("column", sorted(set(v))) for k, v in invalid_columns.items()})
    n_unver = sum(len(v) for v in unverifiable.values())

    if args.write_baseline:
        write_baseline(repo, args.baseline, findings)
        return 0

    baseline = load_baseline(repo, args.baseline)
    # `or []` not a get() default: the key can EXIST holding null, in which case
    # the default is not applied and the comprehension would raise.
    baseline_entries = baseline.get("entries") or []
    known = {(e["file"], e["ref"]) for e in baseline_entries}
    new = {k: v for k, v in findings.items() if k not in known}
    accepted = {k: v for k, v in findings.items() if k in known}
    stale = known - set(findings)

    print(f"\n=== schema contract: {n_files} files, {n_stmts} SQL statements, "
          f"{len(tables)} catalog tables ===")
    print(f"  VALID        {n_valid_tables} table refs, {n_valid_cols} qualified column refs")
    print(f"  INVALID      {len(findings)} distinct refs name objects the database does not have")
    print(f"                 {len(new)} NEW (not in baseline)  |  {len(accepted)} pre-existing")
    print(f"  UNVERIFIABLE {n_unver}   <- cannot be resolved statically; NOT a pass")
    print(f"  NOT CHECKED  unqualified columns (out of scope by design)")

    def _show(title, items):
        if not items or args.quiet:
            return
        print(f"\n-- {title} --")
        for (f, ref), (kind, lines) in sorted(items.items()):
            note = next((e.get("note") or "" for e in baseline_entries
                         if e["file"] == f and e["ref"] == ref), "")
            loc = ",".join(f"L{n}" for n in lines)
            print(f"  {f}\n      {ref}  ({kind}, {loc})" + (f"\n        {note}" if note else ""))

    _show("NEW — this change introduced them", new)
    _show("PRE-EXISTING — accepted by baseline, must only shrink", accepted)

    if unverifiable and not args.quiet:
        print("\n-- UNVERIFIABLE (not passes) --")
        for f, items in sorted(unverifiable.items()):
            print(f"  {f}")
            for i in items:
                print(f"      {i}")

    print("\nNote: UNVERIFIABLE and NOT CHECKED are not passes. A reference is only "
          "verified when it was resolved against the live catalog.")
    if accepted:
        print(f"Note: {len(accepted)} known-bad reference(s) are suppressed by "
              f"{args.baseline or DEFAULT_BASELINE}. They are defects, not exemptions.")

    failed = False
    if new:
        print(f"\nFAILED: {len(new)} NEW reference(s) name database objects that do not exist.")
        failed = True
    if stale:
        # The baseline may only shrink. A fixed entry must be deleted from it, or
        # the file slowly becomes a permanent amnesty that nobody re-reads.
        print(f"\nFAILED: {len(stale)} baseline entr(ies) no longer occur — delete them "
              f"from {args.baseline or DEFAULT_BASELINE}:")
        for f, ref in sorted(stale):
            print(f"    {f}: {ref}")
        failed = True
    if args.max_unverifiable is not None and n_unver > args.max_unverifiable:
        print(f"\nFAILED: UNVERIFIABLE {n_unver} exceeds ratchet {args.max_unverifiable}.")
        failed = True
    if failed:
        return 1
    if findings:
        print("\nPASSED (with baseline): no NEW invalid references. "
              f"{len(accepted)} pre-existing still to fix.")
    else:
        print("\nPASSED: every resolvable table and qualified column reference exists.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
