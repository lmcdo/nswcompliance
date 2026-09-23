#!/usr/bin/env python3
"""Ledger checks that need Python, not SQL.

prior-art-checked: reuse not viable because `scripts/dq_probe_live.py` is
SQL-only by construction (its PROBES map holds a SQL string the runner
executes) and two of these five are STATIC analyses of the repo, not queries.
`scripts/dq_probe_applicability_config.py` is the same shape as this file and
is the precedent being followed, not duplicated: it answers two applicability
questions and nothing here touches applicability.

WHY THESE FIVE
--------------
`.claude/dq_checks.json` polices a status in both directions, but only for a
row that HAS a check. A row declared open with `check: null` is the one state
the ratchet cannot see: it can rot, be silently fixed, or be quietly wrong, and
nothing says so. Five rows sat there. Each carried a real reason for having no
check, and each reason is answered below by measuring something FALSIFIABLE
rather than by inventing a target:

  DQ-31  "a check needs a definition of 'consolidated' that does not exist"
         -> count the INDEPENDENT implementations of the decision. Two is not
            consolidated; one is. That needs no definition, only a count.
  DQ-42  "assert the guard exists rather than that the portal is correct"
         -> measure the guard's OUTCOME: a portal date must never attach across
            a plan-identity mismatch. Asserting the code exists would pass on a
            guard that had stopped working.
  DQ-43  "depends on a plan-identity model that does not exist yet"
         -> measure the PRECONDITION that makes the model necessary: councils
            whose served rows span more than one plan NAME, so nobody can tell
            a genuine two-plan council from a sloppily-registered one.
  DQ-53  "the suite-wide census was never done, so there is no target"
         -> the check IS the census. Count it.
  DQ-58  "a live fetch would make CI depend on nine council websites"
         -> the row prescribes its own fix: a stored status column written by
            the monitor, then a probe over the column. Assert the column, and
            offer the live fetch behind an explicit opt-in.

DQ-104 and DQ-105 were added afterwards for the same reason the first five are
here -- one needs a tokeniser, the other needs the config registry imported --
so no SQL string in `dq_probe_live.py` can express either. The file is named for
the five it started with; it is now simply the home for checks SQL cannot ask.

Contract copied from `dq_probe_live.py` deliberately: exit 0 only when the count
is 0, exit 2 when the source cannot be reached, and every number prints how it
was produced. Read-only throughout -- no statement here writes.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


# -- DQ-31 -------------------------------------------------------------------
#: Naming the verdict is not deciding it. A file is an INDEPENDENT
#: implementation only when it APPLIES the standard's gate -- compares it,
#: branches on it -- and produces a verdict of its own.
_ELIGIBILITY_VERDICT = re.compile(
    r"eligibleTypes|assessmentStatus|is_eligible|evaluate_eligibility")

#: The gate itself, spelled both ways the two codebases spell it.
_GATE = r"isLMRArea|in_lmr_area|requires_lmr_area"

#: The gate USED IN A DECISION, not merely named. A prop declaration
#: (``isLMRArea?: boolean``), a pass-through in an object literal, and a comment
#: quoting old code are all mentions -- and all three exist in this repo.
#:
#: ``\?(?!:)`` and not ``\?``: TypeScript's optional-property marker is
#: ``isLMRArea?: boolean``, which a bare ``\?`` reads as the start of a
#: ternary. That one character made HousingSEPPEligibilityCard.tsx -- a
#: component that declares the flag as a prop and passes it through -- count as
#: an implementation of the eligibility decision.
_GATE_APPLIED = re.compile(
    r"(?:" + _GATE + r")\s*(?:===|!==|==|!=|\?(?!:))"  # compared
    r"|typeof\s+(?:" + _GATE + r")"                    # type-tested
    r"|if\s*\(?\s*!?\s*(?:" + _GATE + r")"             # branched on
    r"|(?:and|or|not)\s+(?:" + _GATE + r")"            # combined in a predicate
)


def probe_31():
    """Independent implementations of the Housing SEPP eligibility decision.

    DQ-31's first half -- an absent ``isLMRArea`` meaning "yes" -- closed
    2026-08-01. The open half is that the decision exists TWICE.
    `services/housing_sepp_eligibility.py` says so in its own docstring: it
    "PORTS the gate logic from the frontend app/api/housing-sepp/eligibility/
    route.ts (the only prior implementation)" and is "the consolidation's single
    source of truth", with "the LEP/SEPP tab migrates onto it (P3)" still
    outstanding. Two copies of one regulated decision drift apart, and counting
    them needs no definition of "consolidated" beyond "more than one".

    THE FIRST VERSION OF THIS DETECTOR COUNTED MENTIONS and read 2 when the
    answer is 1. It matched any file naming the gate, so it swept in
    ``lib/ai/router.ts``, where the only occurrence is a COMMENT quoting the old
    code, and ``HousingSEPPEligibilityCard.tsx``, which declares ``isLMRArea?:
    boolean`` as a prop and passes it through. Neither decides anything. It also
    assumed the Python service used the frontend's spelling; it does not
    (``in_lmr_area``), so the one file that matters was missed while two
    irrelevant ones were reported. Applying-not-naming is the distinction.

    Counted as copies BEYOND the first, so a single implementation reads 0.
    """
    hits = {}
    for base, patterns in (("frontend-nextjs", ("*.ts", "*.tsx")), ("services", ("*.py",))):
        for pat in patterns:
            for f in (ROOT / base).rglob(pat):
                posix = f.as_posix()
                if "node_modules" in posix or "__tests__" in posix or "/tests/" in posix:
                    continue
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if _ELIGIBILITY_VERDICT.search(text) and _GATE_APPLIED.search(text):
                    hits[(f.relative_to(ROOT).as_posix(), "")] = 1
    return max(len(hits) - 1, 0), hits


# -- DQ-53 -------------------------------------------------------------------
_FIXTURE_LOAD = re.compile(
    r"json\.loads?\(|read_text\(|load_fixture|_golden\(|golden|fixture")

#: Project packages. A call into one of these is a call into the code under
#: test; a call to json, pytest or the stdlib is not.
_PROJECT_PKGS = ("services", "src", "enrichment", "scripts")


def _root_pkg(dotted) -> str:
    """First segment of a dotted module name, or '' when there is none.

    `"".split(".")` returns `['']`, not `[]`, so indexing is safe in CPython --
    but a relative import (``from . import x``) gives ``n.module = None`` and a
    future ast change need not preserve either. Returning '' for anything empty
    keeps the caller's membership test correct without an IndexError, and ''
    matches no entry in _PROJECT_PKGS.
    """
    head = (dotted or "").strip().split(".")
    return head[0] if head else ""


def _project_names(tree):
    """Names bound by an import FROM this project, anywhere in the module."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module:
            if _root_pkg(n.module) in _PROJECT_PKGS:
                out.update(a.asname or a.name for a in n.names)
        elif isinstance(n, ast.Import):
            for a in n.names:
                root = _root_pkg(a.name)
                if root in _PROJECT_PKGS:
                    out.add(a.asname or root)
    return out


def _calls_into_project(fn, names) -> bool:
    """Does this function actually EXERCISE the code it claims to contract?"""
    for n in ast.walk(fn):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        while isinstance(f, ast.Attribute):     # Model.method() -> root Model
            f = f.value
        if isinstance(f, ast.Name) and f.id in names:
            return True
    return False


def probe_53():
    """Contract tests that compare two STORED artefacts instead of a live call.

    The named instance: a test commented "locks ClimateHazardOutput to the exact
    keys HazardScore.to_dict emits" compared the contract to a stored golden
    fixture. When ``to_dict`` gained a key, contract and fixture were both
    missing it -- wrong in the SAME direction -- so it stayed green for weeks
    while neither matched reality. A contract test that never calls the producer
    cannot fail in the way its own name claims.

    Counted as: a test function whose name contains "contract", which loads a
    stored artefact, and which never calls into services/ src/ enrichment/ or
    scripts/ at all.

    THE FIRST VERSION OF THIS DETECTOR WAS WRONG and is worth recording, because
    it failed in the direction that sends someone to "fix" a working test. It
    looked for a live call as a METHOD -- ``.to_dict(``, ``.model_dump(`` -- and
    reported three false positives on this suite:
    ``test_db_contract_normalise_roundtrip`` calls ``_normalise_outputs(...)``,
    a plain function, and ``test_strata_contract_accepts_registration_date``
    calls ``StrataServiceOutput.model_validate(...)``, a method the list did not
    name. Both exercise the real code. Asking "does it call into the project at
    all" is the question that separates the two cases; enumerating call shapes
    is a way of missing one.
    """
    hits = {}
    for f in sorted((ROOT / "tests").rglob("test_*.py")):
        try:
            src = f.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src)
        except (OSError, SyntaxError):
            continue
        names = _project_names(tree)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if "contract" not in node.name.lower():
                continue
            body = ast.get_source_segment(src, node) or ""
            if _FIXTURE_LOAD.search(body) and not _calls_into_project(node, names):
                hits[(f.relative_to(ROOT).as_posix(), node.name)] = 1
    return len(hits), hits


# -- DB-backed probes --------------------------------------------------------
def probe_42(cur):
    """A portal date attached across a plan-identity mismatch.

    The NSW Planning Portal's /dcp records are stale for at least five served
    LGAs -- pre-merger plans for Canterbury-Bankstown, Cumberland and Georges
    River among them. That is upstream and not fixable here, which is why the
    row is `guarded` rather than open. What IS ours is the cross-check in
    `scripts/fetch_dcp_as_at_dates.py`: a portal date must never attach to a
    plan whose identity differs from the one actually served.

    Measuring the OUTCOME rather than asserting the code exists is deliberate.
    A check that greps for the guard passes on a guard that has stopped working
    -- the failure `feedback-detect-a-guard-by-forcing-its-failure` names. This
    one goes non-zero the moment a mismatched date is stored.
    """
    cur.execute(
        """SELECT lga, portal_plan_name, currency_confirmed_plan
             FROM dcp_plan_as_at
            WHERE portal_date IS NOT NULL
              AND currency_confirmed_plan IS NOT NULL
              AND portal_plan_name IS DISTINCT FROM currency_confirmed_plan"""
    )
    rows = cur.fetchall()
    return len(rows), {(r[0], "portal=%r served=%r" % (r[1], r[2])): 1 for r in rows}


def probe_43(cur):
    """Served councils whose current rows span more than one plan NAME.

    `dcp_plan_as_at` is keyed by LGA (28 rows, measured 2026-09-23), so one
    as-at date covers every row a council serves. That is only safe while a
    council serves one plan.

    This measures the PRECONDITION, not the harm, and the distinction is the
    reason the row has waited: checked 2026-09-23, ku_ring_gai's three spellings
    -- "Ku-ring-gai DCP" for its Section B parts, "Ku-ring-gai DCP 2024" for
    Section A, and a third for Part 5 -- are ONE plan registered three ways.
    Reading this count as "two plans, wrongly dated" would have been a false
    positive, and nearly was.

    That ambiguity IS the thing to fix. While several names are in play nobody
    can distinguish a genuine two-plan council from a sloppily-registered one,
    and the plan-identity model this row waits on cannot be built on top of it.
    Reconciling the names OR building the model takes this to zero.

    BLIND SPOT, stated rather than hidden: the registry join needs
    `source_chapter_key`, and 7,254 of 20,261 served rows carry NULL there
    (measured 2026-09-23), so this sees 13,007 rows. A council serving a second
    plan ENTIRELY through key-less rows is invisible here. Widening it means
    giving those rows a chapter key, not loosening the join.
    """
    cur.execute(
        """SELECT rp.source_council,
                  array_agg(DISTINCT r.dcp_name ORDER BY r.dcp_name) AS plan_names,
                  bool_or(a.currency_date IS NOT NULL)               AS renders_a_date
             FROM regulatory_provisions rp
             JOIN dcp_chapter_registry r
               ON r.council = rp.source_council
              AND replace(r.chapter_key, '-', '_')
                  = replace(coalesce(rp.source_chapter_key, ''), '-', '_')
             LEFT JOIN dcp_plan_as_at a ON a.lga = rp.source_council
            WHERE rp.is_current AND rp.v2_is_actionable
            GROUP BY 1
           HAVING count(DISTINCT r.dcp_name) > 1
            ORDER BY 1"""
    )
    rows = cur.fetchall()
    return len(rows), {
        (r[0], "%d names, renders_a_date=%s: %s" % (len(r[1]), r[2], r[1])): 1
        for r in rows
    }


def probe_58(cur, live: bool = False):
    """Registry page URLs whose reachability is recorded nowhere.

    Three of nine `council_page_url` values were dead when measured in a real
    browser on 2026-08-13 (canada_bay, camden, ryde). Nobody finds out until a
    user clicks a citation, and the registry is what the 'observed current'
    as-at basis derives from -- so a rotted URL means that council can never
    earn a date.

    The row prescribed its own fix and this follows it: a stored
    `url_page_last_status` written by the existing monitor, then a probe over
    the column. Writing it as a live fetch instead puts nine council websites
    into CI's dependency graph -- three behind Cloudflare, which 403s automated
    clients -- and a check that goes red for reasons unrelated to the defect
    gets deleted. So the default asks whether the INSTRUMENT exists, which can
    only go green by building it, and ``--live`` does the real fetch on demand.
    """
    cur.execute(
        """SELECT count(*) FROM information_schema.columns
            WHERE table_name = 'dcp_chapter_registry'
              AND column_name = 'url_page_last_status'"""
    )
    if cur.fetchone()[0] == 0:
        cur.execute(
            """SELECT count(DISTINCT council_page_url) FROM dcp_chapter_registry
                WHERE is_active AND council_page_url IS NOT NULL"""
        )
        n = cur.fetchone()[0]
        return n, {("no url_page_last_status column",
                    "%d distinct page URLs whose status is recorded nowhere" % n): 1}

    cur.execute(
        """SELECT DISTINCT council, council_page_url, url_page_last_status
             FROM dcp_chapter_registry
            WHERE is_active AND council_page_url IS NOT NULL
              AND (url_page_last_status IS NULL OR url_page_last_status <> 200)"""
    )
    rows = cur.fetchall()
    return len(rows), {(r[0], "status=%s %s" % (r[2], r[1])): 1 for r in rows}


def probe_104(cur):
    """SERVED provisions whose text was read BACKWARDS by the reader.

    A PDF laid out right-to-left in places -- most often inside a figure or a
    table -- comes back mirrored: `kcabtes` for setback, `etis yradnuob
    htaptoof` for "site boundary footpath", `sertem syerots thgieh` for "metres
    storeys height". These are served to a planner as development controls.

    Found 2026-09-23 from a screenshot of the review queue, where a reviewer was
    being asked to confirm whether 0.41 was correct in a row whose own text read
    `kcabtes m0.2`. There is no judgement to make about that, and nothing
    detected it: `_AUTO_REJECT_REASONS` named three failures and none of them
    was this, so the row became `pending` instead of being rejected for a
    re-read. The detector now exists and this counts what is ALREADY LIVE,
    which the enqueue-time gate cannot reach.

    The vocabulary is IMPORTED from `dcp_extract_changed`, not restated. Two
    copies would drift, and a probe measuring a different rule from the gate is
    how a number stops meaning what its row says it means.

    Same family as DQ-78 (scrambled map labels) and distinct from it: DQ-78
    counts a run of single letters, this counts whole words in reverse. Neither
    sees the other -- measured 2026-09-23, DQ-78 reads 34 and this reads 27.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    from dcp_extract_changed import reversed_text_tokens

    cur.execute(
        """SELECT id, source_council, provision_text
             FROM regulatory_provisions
            WHERE is_current AND v2_is_actionable"""
    )
    hits = {}
    for pid, council, text in cur.fetchall():
        toks = {t.lower() for t in reversed_text_tokens(text)}
        if len(toks) >= 2:
            hits[(council or "STATEWIDE", "id=%d %s" % (pid, sorted(toks)[:4]))] = 1
    return len(hits), hits


#: The Inner West three reach their scope through dedicated matchers in
#: `tag_with_provenance`, not through COUNCIL_CONFIGS, so they are configured
#: even though the registry does not list them.
_DEDICATED_MATCHER_COUNCILS = frozenset({"marrickville", "ashfield", "leichhardt"})


def probe_105(cur):
    """Served rules belonging to a council with NO applicability config at all.

    DQ-33 counts the same defect globally, against a floor of 1,158 that may
    only fall. That works as a ratchet on the councils already configured and
    FAILS COMPLETELY as an onboarding check: measured 2026-09-23 the global
    count was 924, so a brand-new council could publish 234 rules that apply to
    every development type and nothing would say a word. A total hides a
    per-council regression -- `feedback-counting-is-not-comparing` -- and here
    the thing it hides is the one step of onboarding that is not automatic.

    Everything else a new council meets is universal. `classify_row_fidelity`
    takes no council argument, so reversed text, garbled glyphs, junk refs and
    emptied provisions are caught for any council from its first extraction.
    The applicability config is the exception: it is a hand-written file saying
    which zones and development types each chapter binds, read from that
    council's own Application sections, and nothing can derive it.

    Measured 2026-09-23: 8 of 14 serving councils have none -- parramatta,
    blacktown, northern_beaches, penrith, hornsby, georges_river, cumberland
    and inner_west -- serving 1,052 rules between them, of which 559 actually
    fall through to every development type today.

    COUNTS COUNCILS, NOT ROWS, and the distinction is deliberate. The defect is
    that a council has no config; how many of its rows currently fall through
    depends on whether the text regex happened to find a zone or a type in each
    one, which is noise. Counting rows would let a council with no config read
    0 because its prose happened to match, and would move up and down on
    re-extraction without anything being decided. The row exposure is carried in
    the detail so the size stays visible.

    Reachable only by writing the configs. Deleting a council's rows would also
    take it to zero, which is why `passes_when` names the direction.

    ASKS THE TAGGER, not the registry, and the first version did not. It
    compared each `source_council` string against COUNCIL_CONFIGS, which is a
    different question from the one that decides a row's scope: the tagger keys
    on DOCUMENT_ID. Measured 2026-09-23, `inner_west` was reported as an
    unconfigured council on the strength of 11 rows -- 10 of them from
    "Marrickville_DCP_2011__..." and 1 from "Ashfield_DCP_2007__...", both of
    which the tagger resolves perfectly well, with 10 of the 11 already tagged.
    Inner West is the most deeply configured council in the product. The rows
    simply carry the parent slug in `source_council` while naming a predecessor
    plan in their document_id, and only the latter is consulted.

    So: a council is unconfigured when NOT ONE of its served rows reaches a
    config. A council where some chapters resolve and others do not is DQ-102's
    population, not this one.

    RESOLVED PER ROW, WITH ITS OWN TEXT -- the second correction, from the same
    afternoon. Passing an empty string in place of the provision text breaks the
    `parts`-path councils: Waverley and Woollahra key on a section code that
    `_extract_section_code` reads OUT OF THE TEXT, so with no text they resolve
    to nothing and a fully configured council is reported as having none.
    Measured 2026-09-23 that is exactly what happened to waverley -- 392 served
    rows, ZERO of them falling through, which is itself proof its config works.
    Both corrections have the same shape: the check must ask the question the
    TAGGER asks, with the inputs the tagger gets.
    """
    from enrichment.extractors.applicability_tagger import ApplicabilityTagger

    tagger = ApplicabilityTagger()
    cur.execute(
        """SELECT source_council, document_id, provision_text, v2_dev_type_source
             FROM regulatory_provisions
            WHERE is_current AND v2_is_actionable AND source_council IS NOT NULL"""
    )
    by_council = {}
    for council, doc, text, source in cur.fetchall():
        served, fallthrough, any_resolved = by_council.get(council, (0, 0, False))
        served += 1
        if source == "no_config":
            fallthrough += 1
        if not any_resolved:
            any_resolved = (tagger._detect_council(doc) is not None
                            or tagger._get_config_driven(doc, text or "") is not None)
        by_council[council] = (served, fallthrough, any_resolved)

    hits, watched = {}, {}
    for council, (served, fallthrough, any_resolved) in sorted(by_council.items()):
        if any_resolved:
            continue
        note = ("%d served, %d applying to every development type"
                % (served, fallthrough))
        if fallthrough == 0:
            # NO CONFIG, BUT NOTHING FALLING THROUGH. Watched, not counted --
            # and it is a narrow exception rather than an amnesty: the moment
            # `fallthrough` rises above 0 this council counts again, on the
            # next run, with no edit to this file.
            #
            # The docstring above argues against counting ROWS, because a
            # council could read 0 "because its prose happened to match" and
            # drift on re-extraction with nothing decided. That holds, and is
            # why the count is still per-council. It does not justify demanding
            # a config that cannot be written truthfully, which is the case
            # this branch exists for.
            #
            # cumberland, measured 2026-09-24: 29 served, 0 falling through.
            # Its DCP Part B is FIVE separate sub-parts sharing ONE
            # document_id, each carrying its own "1.1 Land to which this Part
            # applies" and naming a different scope -- "all residential
            # development types except for single dwelling house development",
            # "low rise dual occupancy", "residential flat building
            # development", "boarding house", and dwelling house plus secondary
            # dwelling. Their section codes COLLIDE: every sub-part has a 1.1
            # and a 2.4. Neither key the tagger uses -- document_id or section
            # code -- can separate them, so one entry would mis-scope four of
            # the five. The text regex reads each row's scope from its own
            # prose and gets all 29 right, which is why nothing falls through.
            #
            # The real defect is the DOCUMENT, not the missing config: five
            # plans registered as one. Until they are split, a config here
            # would be an invention.
            watched[(council, note + "  [watched: no config can be written "
                                     "while its sub-parts share a document_id]")] = 1
        else:
            hits[(council, note)] = 1
    # The count is offenders only. `watched` still prints, so a council that
    # genuinely needs a config cannot disappear from the report -- and a
    # watched one reappears in the count the moment a row starts falling
    # through.
    return len(hits), {**hits, **watched}


PROBES = {
    "DQ-105": (
        "Councils serving rules with NO applicability config at all",
        "Their rules apply to EVERY development type by fallthrough rather than by "
        "decision. DQ-33 counts the same defect globally against a floor, so a newly "
        "onboarded council hides inside the headroom -- 234 rows of it on 2026-09-23. "
        "This is per-council and cannot hide. Writing the config is the one onboarding "
        "step nothing can derive.",
        probe_105, True),
    "DQ-104": (
        "SERVED provisions whose text was read backwards by the reader",
        "Each row shows a planner mirrored words where a control should be -- "
        "`kcabtes` for setback, `etis yradnuob` for site boundary. Not a number "
        "to check: there is nothing to adjudicate in reversed text, which is why "
        "the fix is to reject and re-read rather than to queue it for a person.",
        probe_104, True),
    "DQ-31": (
        "Independent implementations of the Housing SEPP eligibility decision, beyond the first",
        "Each extra copy is one regulated decision written twice and free to drift. "
        "services/housing_sepp_eligibility.py was written to replace the route's copy, "
        "and its own docstring records that the tab has not migrated onto it yet.",
        probe_31, False),
    "DQ-42": (
        "Portal dates attached across a plan-identity mismatch",
        "A stale Planning Portal record has been allowed to date a plan it does not name, "
        "which is how a council gets an as-at date belonging to a different instrument.",
        probe_42, True),
    "DQ-43": (
        "Served councils whose current rows span more than one plan NAME",
        "One as-at date covers every row a council serves, which is safe only while it "
        "serves one plan. While several names are in play nobody can tell a genuine "
        "two-plan council from a sloppily-registered one.",
        probe_43, True),
    "DQ-53": (
        "Contract tests comparing two stored artefacts instead of a live call",
        "Each cannot fail in the way its own name claims: the contract and the fixture can "
        "be wrong in the same direction and the comparison stays green.",
        probe_53, False),
    "DQ-58": (
        "Registry page URLs whose reachability is recorded nowhere",
        "A dead citation link is invisible until a user clicks it, and the council it "
        "belongs to can never earn an 'observed current' date.",
        probe_58, True),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--id", required=True, choices=sorted(PROBES))
    ap.add_argument("--live", action="store_true",
                    help="DQ-58 only: fetch the page URLs instead of reading the column.")
    ap.add_argument("--limit-print", type=int, default=12)
    args = ap.parse_args()

    headline, means, fn, needs_db = PROBES[args.id]
    conn = None
    try:
        if needs_db:
            try:
                import dq_db

                conn = dq_db.connect()
            except Exception as exc:  # noqa: BLE001
                print("%s: UNKNOWN -- database unreachable (%s). Nothing was checked, "
                      "which is not a pass." % (args.id, exc), file=sys.stderr)
                return 2
            cur = conn.cursor()
            count, detail = fn(cur, args.live) if args.id == "DQ-58" else fn(cur)
        else:
            count, detail = fn()
    finally:
        if conn is not None:
            conn.close()

    print("%s: %s" % (args.id, headline))
    print("  count : %s" % format(count, ","))
    print("  means : %s" % means)
    if detail:
        print("  detail (%d):" % len(detail))
        for a, b in list(detail)[:args.limit_print]:
            print("    %s%s" % (a, ("  --  %s" % b) if b else ""))
        if len(detail) > args.limit_print:
            print("    ... %d more" % (len(detail) - args.limit_print))
    return 0 if count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
