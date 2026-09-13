#!/usr/bin/env python3
# prior-art-checked: neighbours opened, not guessed from their names.
#   dcp_extract_changed.is_count_drop   compares ROW counts of a fresh extraction with
#       the live chapter. A version that keeps its row count and loses its sections
#       passes it, and dcp_commit_approved's commit path never called it at all. Kept
#       as is; this compares SECTION CODES and runs on both write paths.
#   dcp_chapter_measure.leading_code     the definition of a section code. Imported,
#       not copied, so this guard and the measurement ledger cannot disagree.
#   dcp_commit_approved.commit_reviewed_from_queue   the write this guards. It
#       switched a whole chapter over without comparing anything.
"""Refuse to replace a chapter's live rules with a version that loses most of its sections.

WHY THIS EXISTS
---------------
On 2026-09-13 marrickville's part4-s1-low-density was found serving 26 rules across 8
sections -- not one setback, height or floor-space rule among them. The version it had
replaced, still in the table and switched off, held 215 rules across 38 sections. A
second AI extraction had been approved and committed, and the commit step switched the
whole chapter over without comparing the two. Mixed use went 225 rules -> 19 and
stormwater 16 sections -> 1 the same way. Nothing said so.

HOW
---
The chapter's live section codes are read BEFORE the write and AFTER it, inside the
same uncommitted transaction, and the outcome is judged -- not a prediction of it. One
check therefore covers a full replace, a targeted update and a renumbering alike.

  refused  when the chapter had at least MIN_CODES codes and MORE than LOSS_RATIO of
           them are gone afterwards;
  or       when it had too few codes to judge by but more than MIN_ROWS rules, and MORE
           than LOSS_RATIO of the rules are gone;
  allowed  otherwise -- including a first extraction, which has nothing to lose.

A renumbered chapter loses every old code and is refused too. That is deliberate: every
served citation changes, which a person should see. The refusal says how many new codes
arrived, so a renumbering is recognisable at a glance.

The only way past a refusal is a person naming the chapter:
    --allow-section-loss <council>/<chapter_key>
Nothing in the scheduled jobs passes it, so they fail closed.

KNOWN LIMIT
-----------
leading_code also reads a bare control marker ("C7") as a code, so a version whose
headers are control markers looks like it holds more sections than it does. That errs
toward refusing, never toward letting a loss through.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from scripts.dcp_chapter_measure import leading_code
except ImportError:  # running from inside scripts/
    from dcp_chapter_measure import leading_code

LOSS_RATIO = 0.5   # "most": strictly more than half gone
MIN_CODES = 5      # fewer codes than this is too small to judge by codes
MIN_ROWS = 20      # same floor as COUNT_DROP_MIN_BASELINE in dcp_extract_changed


class SectionLossRefused(RuntimeError):
    """A write would have replaced a chapter with a version missing most of its sections."""


@dataclass(frozen=True)
class Snapshot:
    codes: frozenset
    rows: int


@dataclass(frozen=True)
class Verdict:
    refused: bool
    measure: str            # "codes" | "rows" | "not judged"
    before: int
    after: int
    lost: tuple             # codes present before and absent after (codes measure only)
    gained: int             # codes present after and absent before

    def describe(self, council: str, chapter_key: str) -> str:
        head = f"{council}/{chapter_key}: "
        if self.measure == "codes":
            return head + (
                f"{self.before} sections before, {self.after} after -- {len(self.lost)} "
                f"lost ({len(self.lost) / self.before:.0%}), {self.gained} new. "
                f"Lost e.g. {', '.join(self.lost[:8])}")
        if self.measure == "rows":
            return head + (
                f"too few section codes to judge by; {self.before} rules before, "
                f"{self.after} after ({(self.before - self.after) / self.before:.0%} gone)")
        return head + f"not judged -- {self.before} rules before is too few to measure"


def snapshot(cur, council: str, chapter_key: str) -> Snapshot:
    """The live section codes and rule count of one chapter, as this cursor sees it."""
    cur.execute(
        """
        SELECT section_header FROM regulatory_provisions
        WHERE source_council = %s AND source_chapter_key = %s AND is_current = TRUE
        """,
        (council, chapter_key),
    )
    headers = [r[0] for r in cur.fetchall()]
    codes = frozenset(c for c in (leading_code(h) for h in headers) if c)
    return Snapshot(codes=codes, rows=len(headers))


def judge(before: Snapshot, after: Snapshot) -> Verdict:
    """Pure. Did `after` lose most of what `before` held?"""
    lost = tuple(sorted(before.codes - after.codes))
    gained = len(after.codes - before.codes)
    if len(before.codes) >= MIN_CODES:
        refused = len(lost) > LOSS_RATIO * len(before.codes)
        return Verdict(refused, "codes", len(before.codes), len(after.codes), lost, gained)
    if before.rows > MIN_ROWS:
        refused = (before.rows - after.rows) > LOSS_RATIO * before.rows
        return Verdict(refused, "rows", before.rows, after.rows, (), gained)
    return Verdict(False, "not judged", before.rows, after.rows, (), gained)


def enforce(cur, council: str, chapter_key: str, before: Snapshot,
            allowed: frozenset = frozenset()) -> Verdict:
    """Judge the chapter as it now stands in this transaction; raise if refused.

    Call after the writes and BEFORE commit. The caller rolls back on the raise.
    """
    verdict = judge(before, snapshot(cur, council, chapter_key))
    if not verdict.refused:
        return verdict
    if f"{council}/{chapter_key}" in allowed:
        print(f"    [section-loss] ALLOWED by --allow-section-loss: "
              f"{verdict.describe(council, chapter_key)}")
        return verdict
    raise SectionLossRefused(
        "REFUSED: this version would lose most of the chapter's sections. "
        + verdict.describe(council, chapter_key)
        + f". If that is intended, re-run with --allow-section-loss {council}/{chapter_key}")
