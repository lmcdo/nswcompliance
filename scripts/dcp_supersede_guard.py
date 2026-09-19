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

When the chapter has at least MIN_CODES section codes, it is refused if EITHER
  * MORE than LOSS_RATIO of its section codes are gone, or
  * it had more than MIN_ROWS rules and MORE than ROW_LOSS_RATIO of them are gone,
    even though the section codes survived. (Cross-review: a broken run emitting one
    rule per section keeps every code and still deletes most of the chapter.)
When it has too few codes to judge by, it is refused if it had more than MIN_ROWS rules
and MORE than LOSS_RATIO of them are gone. Otherwise it is allowed -- including a first
extraction, which has nothing to lose.

WHY THE ROW BAR IS LOOSER WHEN SECTIONS ARE KEPT
------------------------------------------------
Extractors disagree about granularity. The pdfplumber path stored a clause's objectives
and its controls as separate rules; the AI path emits one rule per clause. Waverley went
607 -> 264 distinct rules that way (measured 2026-09-11), mostly consolidation rather
than loss. A 50% row bar would refuse that; 75% refuses the incident (215 -> 26 is 88%)
and the one-rule-per-section collapse (215 -> 38 is 82%) while letting it through.

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
from dataclasses import dataclass, field

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from scripts.dcp_chapter_measure import leading_code
except ImportError:  # running from inside scripts/
    from dcp_chapter_measure import leading_code

LOSS_RATIO = 0.5       # "most": strictly more than half gone
ROW_LOSS_RATIO = 0.75  # rules gone while sections survive: strictly more than three-quarters
MIN_CODES = 5          # fewer codes than this is too small to judge by codes
MIN_ROWS = 20          # same floor as COUNT_DROP_MIN_BASELINE in dcp_extract_changed

# ── Legibility ───────────────────────────────────────────────────────────────
# A chapter can keep every section and every rule and still be ruined, because the
# replacement text is a two-column page read straight across: "4.2.4 Ground level
# setbacks Controls M Re c s L e e r o v d e M er e". None of the existing gates --
# count_drop, regeneration_artifact, map_change, restructure, or the section loss above
# -- looks at whether the words are still words, so a re-read that garbles a clause
# commits silently and reads as progress.
#
# The signature is DQ-78's, not a new one: the fraction of whitespace-separated tokens
# that are a single letter. Real prose sits near zero (only "a" and "I"); interleaved
# text is dominated by them. Its thresholds were read off the served distribution rather
# than chosen -- >=0.50 matched 34 rows, >=0.30 83, >=0.20 128, >=0.10 663 -- and the
# >=100-token floor is what separates a scrambled page from a short unit split like
# "s o o m m", which is DQ-77's defect and has its own remedy. The same measure backs
# frontend-nextjs/lib/provision-text-formatter.ts, so the gate, the ledger and the page
# a planner reads all mean the same thing by "scrambled".
#
# Verified to separate the case it was built for: city_of_sydney section 3 clause 3.2.3
# is served clean at ratio 0.021 and its queued replacement is 0.225, while the next
# highest row in the same run is 0.077 and the median is 0.016 -- the line sits in a gap,
# not among the data.
SCRAMBLE_MIN_TOKENS = 100   # below this a low token count makes the ratio meaningless
SCRAMBLE_MIN_RATIO = 0.20   # DQ-78's threshold, read off the distribution

# A rule that is ALREADY scrambled can still be made much worse, and listing which rules
# are scrambled cannot see that: the ref is in both sets, so the difference is empty and
# a 0.21 rule replaced by a 0.90 one commits. Each rule therefore carries its ratio and a
# material rise is refused too. 0.05 is a fifth of the rise this guard was built for
# (0.021 -> 0.225 on city_of_sydney 3.2.3) and well clear of noise: a sentence added to a
# 2,000-token rule moves the ratio by under 0.01, while the 155 scrambled rules live today
# run from 0.20 up to 0.91 — their top fifteen all sit above 0.62 — nowhere near a 0.05
# band. (The count was first written here as "fifteen": that was a LIMIT 15 in the query it
# came from, reported as if it were the total. The ratios were right, the population was
# ten times larger. Re-run it rather than trusting this line:
#   SELECT count(*) FROM (SELECT cardinality(regexp_split_to_array(btrim(provision_text),
#     '\s+')) n, (SELECT count(*) FROM unnest(regexp_split_to_array(btrim(provision_text),
#     '\s+')) w WHERE w ~ '^[A-Za-z]$') singles FROM regulatory_provisions WHERE is_current
#     AND source_chapter_key IS NOT NULL AND length(provision_text) > 80) x
#   WHERE n >= 100 AND singles::numeric/n >= 0.20;)
SCRAMBLE_WORSE_MARGIN = 0.05


class SectionLossRefused(RuntimeError):
    """A write would have replaced a chapter with a version missing most of its sections."""


@dataclass(frozen=True)
class Snapshot:
    codes: frozenset
    rows: int
    # {identity: (ref_number for display, single-letter ratio)} for every live rule
    # matching DQ-78's signature. Keyed on ref_number AND section_header because
    # ref_number alone is neither unique nor guaranteed non-null: the column is nullable,
    # and five refs carry two current provisions each. Where two rows still share a key
    # the WORSE ratio is kept, which errs toward refusing.
    scrambled_rules: dict = field(default_factory=dict)

    @property
    def scrambled(self) -> int:
        return len(self.scrambled_rules)


@dataclass(frozen=True)
class Verdict:
    refused: bool
    measure: str            # "codes" | "rows" | "not judged"
    before: int
    after: int
    lost: tuple             # section codes present before and absent after
    gained: int             # section codes present after and absent before

    def describe(self, council: str, chapter_key: str) -> str:
        head = f"{council}/{chapter_key}: "
        if self.measure == "codes":
            return head + (
                f"{self.before} sections before, {self.after} after -- {len(self.lost)} "
                f"lost ({len(self.lost) / self.before:.0%}), {self.gained} new. "
                f"Lost e.g. {', '.join(self.lost[:8])}")
        if self.measure == "rows":
            kept = "sections mostly kept, " if not self.lost else ""
            return head + (
                f"{kept}{self.before} rules before, {self.after} after "
                f"({(self.before - self.after) / self.before:.0%} gone)")
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

    # DQ-78's signature, in SQL so a chapter's whole text never crosses the wire.
    #
    # is_current ONLY -- deliberately NOT v2_is_actionable, which DQ-78's own query
    # carries. Rows this worker inserts get v2_is_actionable NULL (the classifier decides
    # later; only a preamble is set FALSE), so an actionable filter would exclude every
    # newly written row, the AFTER count could never rise above the BEFORE count, and the
    # guard would be permanently dead while appearing to run. A test pins this.
    cur.execute(
        r"""
        SELECT COALESCE(ref_number, '') || '|' || COALESCE(section_header, '') AS identity,
               COALESCE(ref_number, section_header, '(unnumbered)') AS shown,
               MAX(singles::numeric / n) AS ratio
        FROM (
            SELECT ref_number, section_header,
                   cardinality(regexp_split_to_array(btrim(provision_text), '\s+')) AS n,
                   (SELECT count(*) FROM unnest(
                        regexp_split_to_array(btrim(provision_text), '\s+')) w
                    WHERE w ~ '^[A-Za-z]$') AS singles
            FROM regulatory_provisions
            WHERE source_council = %s AND source_chapter_key = %s AND is_current = TRUE
              AND length(provision_text) > 80
        ) x
        WHERE n >= %s AND singles::numeric / n >= %s
        GROUP BY 1, 2
        """,
        (council, chapter_key, SCRAMBLE_MIN_TOKENS, SCRAMBLE_MIN_RATIO),
    )
    return Snapshot(codes=codes, rows=len(headers),
                    scrambled_rules={ident: (shown, float(ratio))
                                     for ident, shown, ratio in cur.fetchall()})


def judge(before: Snapshot, after: Snapshot) -> Verdict:
    """Pure. Did `after` lose most of what `before` held?"""
    lost = tuple(sorted(before.codes - after.codes))
    gained = len(after.codes - before.codes)
    rows_gone = before.rows - after.rows
    if len(before.codes) >= MIN_CODES:
        if len(lost) > LOSS_RATIO * len(before.codes):
            return Verdict(True, "codes", len(before.codes), len(after.codes), lost, gained)
        if before.rows > MIN_ROWS and rows_gone > ROW_LOSS_RATIO * before.rows:
            return Verdict(True, "rows", before.rows, after.rows, lost, gained)
        return Verdict(False, "codes", len(before.codes), len(after.codes), lost, gained)
    if before.rows > MIN_ROWS:
        refused = rows_gone > LOSS_RATIO * before.rows
        return Verdict(refused, "rows", before.rows, after.rows, lost, gained)
    return Verdict(False, "not judged", before.rows, after.rows, lost, gained)


class LegibilityRefused(RuntimeError):
    """A write would have replaced readable rules with two-column interleave."""


def judge_legibility(before: Snapshot, after: Snapshot) -> list:
    """Pure. Which rules this version damages, and by how much.

    Two kinds of damage, and listing which rules are scrambled sees only the first:

      * a rule that was readable and is now scrambled. Counting instead of comparing
        misses even this, because a commit can repair one rule and break another: measured
        on city_of_sydney section 3, committing it deletes the scrambled junk ref "2012"
        and scrambles clause 3.2.3, so the total is 1 before and 1 after.
      * a rule that was ALREADY scrambled and is now much worse -- 0.21 replaced by 0.90.
        Its ref is in both sets, so a set difference is empty and the worse text commits.
        Fifteen live rules sit between 0.62 and 0.91 today, so this is not hypothetical.

    Returns [(shown_ref, before_ratio or None, after_ratio)], worst rise first. Empty when
    nothing got worse -- which includes a chapter that stayed as garbled as it was, and
    one that improved. Both must pass, or this would block the re-read that repairs them.
    """
    damaged = []
    for ident, (shown, after_ratio) in after.scrambled_rules.items():
        prior = before.scrambled_rules.get(ident)
        if prior is None:
            damaged.append((shown, None, after_ratio))
        elif after_ratio - prior[1] > SCRAMBLE_WORSE_MARGIN:
            damaged.append((shown, prior[1], after_ratio))
    return sorted(damaged, key=lambda d: -(d[2] - (d[1] or 0.0)))


def enforce_legibility(cur, council: str, chapter_key: str, before: Snapshot,
                       allowed: frozenset = frozenset()) -> list:
    """Judge the chapter's legibility as it now stands in this transaction; raise if worse.

    Call after the writes and BEFORE commit, exactly like enforce(). The caller rolls
    back on the raise, so the approval survives and the chapter is refused again every
    run until the extraction is fixed or a person overrides it by name.
    """
    after = snapshot(cur, council, chapter_key)
    added = judge_legibility(before, after)
    if not added:
        return []
    shown = "; ".join(
        f"{ref} {'newly scrambled at' if was is None else f'{was:.2f} ->'} {now:.2f}"
        for ref, was, now in added[:5])
    detail = (f"{council}/{chapter_key}: {len(added)} rule(s) are newly scrambled, or "
              f"materially more scrambled, in this version than in the one it replaces "
              f"({before.scrambled} scrambled before, {after.scrambled} after -- totals "
              f"that can stay level while the rules behind them change). The figure is "
              f"the fraction of words that are a single letter: a two-column page read "
              f"straight across, so the words are not words. {shown}")
    if f"{council}/{chapter_key}" in allowed:
        print(f"    [legibility] ALLOWED by --allow-garble: {detail}")
        return added
    raise LegibilityRefused(
        "REFUSED: this version is less legible than the one it replaces. " + detail
        + f". Fix the extraction rather than committing it; if the new text really is "
          f"right, re-run with --allow-garble {council}/{chapter_key}")


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
        "REFUSED: this version would lose most of the chapter. "
        + verdict.describe(council, chapter_key)
        + f". If that is intended, re-run with --allow-section-loss {council}/{chapter_key}")
