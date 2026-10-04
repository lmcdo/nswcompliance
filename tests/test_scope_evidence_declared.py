"""Every declared applicability key must carry the council's own sentence.

prior-art-checked: tests/test_applicability_provenance.py asserts the PROVENANCE
value _resolve returns for a given entry shape, and
tests/test_canterbury_bankstown_applicability.py and
tests/test_campbelltown_applicability.py assert one council's declared values.
Neither asserts the RULE that a declaration must carry evidence, which is
DQ-115's whole content, and no test walks every config in COUNCIL_CONFIGS.
Swept 2026-10-03 on origin/main 251b60ba.

WHY THIS IS A TEST AND NOT ONLY A PROBE
---------------------------------------
scripts/dq_probe_applicability_config.py counts the violations and prints a
number. A number nobody is forced to look at is how 193 keys sat undeclared for
months. This fails the build instead, so a new entry cannot be added without its
quote, and a quote cannot be deleted while its declaration stays.

IT IS A RATCHET, not an amnesty
-------------------------------
DQ-115's remaining population is listed in UNEVIDENCED below and does NOT fail.
Turning a known, tracked, deliberate state into a red build would make this file
the thing people disable. Two rules, both borrowed from
scripts/check_test_quarantine.py because that shape already works here:

  1. a violation that is NOT in the list FAILS — the list cannot grow silently;
  2. a listed entry that HAS gained its sentence also FAILS — so it is released
     from the list rather than left as standing permission.

WHAT IT DELIBERATELY DOES NOT CHECK
-----------------------------------
That the quote is TRUE. Confirming a sentence appears on the page it cites needs
the chapter PDF and belongs with the fidelity gate; this enforces only that the
authority is present and is DATA rather than a Python comment. A comment is
exactly as trustworthy as whoever typed it and is invisible to every consumer.
That gap is DQ-115's own stated weakness and is recorded, not papered over.
"""
from __future__ import annotations

import pytest

from enrichment.config import COUNCIL_CONFIGS

#: The two keys that are HARD FILTERS on the served answer. See any council
#: config's docstring: frontend-nextjs/app/api/provisions/for-property/route.ts
#: drops a row whose column neither is NULL, nor holds 'ALL', nor overlaps the
#: query, so declaring a value deletes the row from every other answer.
FILTER_KEYS = ("applicable_zones", "applicable_dev_types")


def declared_keys(entry: dict) -> set[str]:
    """The filter keys this entry has DECIDED, by either route.

    `scope_declined` (migrations/081) is a decision too: a person read the
    chapter, its stated scope could not be expressed in the field without hiding
    rules, and narrowing was declined. It needs its sentence just as much as a
    declared value does -- more so, because the reason IS the content. Without
    this, "declined" becomes the new silent default.
    """
    return ({k for k in FILTER_KEYS if k in entry}
            | {k for k in FILTER_KEYS if k in (entry.get("scope_declined") or ())})

#: Buckets an entry can live in. `sections` is walked although no config uses it
#: yet, so a section-level entry is covered from the first one written rather
#: than after someone remembers.
BUCKETS = ("chapter_topics", "parts", "sections")

#: A quote has to be long enough to BE a quote. The shortest real scope sentence
#: in the directory is Georges River's Part 3 ("applies to all forms of
#: development", 38 characters with its reference), so 40 is under every genuine
#: one and over every placeholder.
MIN_EVIDENCE_CHARS = 40

#: DQ-115's REMAINING population, measured 2026-10-03 after the 40-chapter pass
#: took it from 72 keys to these 47. Each is a declaration whose sentence was
#: looked for and not found, which is a different state from nobody having
#: looked. Do not add to this list to make a build pass.
#:
#:   woollahra D2-D6, E6, E8, F3, A3 — the scope sentence was not in the pages
#:     read. A declaration backed by a guess is worse than a count that stays up.
#:   canterbury-bankstown 7.5, 7.6, 11.13, 11.14, 11.15 — the cue hits were
#:     contents-page lines, and 7.5 came back as scrambled two-column text.
#:   canterbury-bankstown 10.1, 10.7 — these declare a NARROWED dev type, which
#:     the plan-level sentence cannot evidence; only the chapter's own can.
#:   parramatta 2, 5-9 — a whole-DCP PDF of 1,563 pages where a document-wide
#:     scan found four hits and none was a clean Part-level scope. Each Part's
#:     own opening page is needed.
#:   (penrith c10, hornsby part_1_general and georges_river part_3 were released
#:     2026-10-04: their comment sentences moved into scope_evidence, and every
#:     quoted span read OK against its PDF in dq_probe_scope_evidence_fidelity.py.)
UNEVIDENCED: frozenset[tuple[str, str, str, str]] = frozenset({
    ("woollahra", "parts", "A3", "applicable_zones"),
    ("woollahra", "parts", "A3", "applicable_dev_types"),
    ("woollahra", "parts", "D2", "applicable_zones"),
    ("woollahra", "parts", "D2", "applicable_dev_types"),
    ("woollahra", "parts", "D3", "applicable_zones"),
    ("woollahra", "parts", "D3", "applicable_dev_types"),
    ("woollahra", "parts", "D4", "applicable_zones"),
    ("woollahra", "parts", "D5", "applicable_zones"),
    ("woollahra", "parts", "D6", "applicable_zones"),
    ("woollahra", "parts", "E6", "applicable_zones"),
    ("woollahra", "parts", "E6", "applicable_dev_types"),
    ("woollahra", "parts", "E8", "applicable_zones"),
    ("woollahra", "parts", "E8", "applicable_dev_types"),
    ("woollahra", "parts", "F3", "applicable_zones"),
    ("woollahra", "parts", "F3", "applicable_dev_types"),
    ("canterbury-bankstown", "chapter_topics", "chapter_7_5_canterbury_local_centre", "applicable_zones"),
    ("canterbury-bankstown", "chapter_topics", "chapter_7_5_canterbury_local_centre", "applicable_dev_types"),
    ("canterbury-bankstown", "chapter_topics", "chapter_7_6_belmore_and_lakemba", "applicable_zones"),
    ("canterbury-bankstown", "chapter_topics", "chapter_7_6_belmore_and_lakemba", "applicable_dev_types"),
    ("canterbury-bankstown", "chapter_topics", "chapter_10_1_child_care_centres", "applicable_zones"),
    ("canterbury-bankstown", "chapter_topics", "chapter_10_1_child_care_centres", "applicable_dev_types"),
    ("canterbury-bankstown", "chapter_topics", "chapter_10_7_sex_services_premises", "applicable_zones"),
    ("canterbury-bankstown", "chapter_topics", "chapter_10_7_sex_services_premises", "applicable_dev_types"),
    ("canterbury-bankstown", "chapter_topics", "chapter_11_13_former_wsu_campus_milperra", "applicable_zones"),
    ("canterbury-bankstown", "chapter_topics", "chapter_11_13_former_wsu_campus_milperra", "applicable_dev_types"),
    ("canterbury-bankstown", "chapter_topics", "chapter_11_14_riverwood_estate", "applicable_zones"),
    ("canterbury-bankstown", "chapter_topics", "chapter_11_14_riverwood_estate", "applicable_dev_types"),
    ("canterbury-bankstown", "chapter_topics", "chapter_11_15_marco_avenue", "applicable_zones"),
    ("canterbury-bankstown", "chapter_topics", "chapter_11_15_marco_avenue", "applicable_dev_types"),
    ("parramatta", "parts", "2", "applicable_zones"),
    ("parramatta", "parts", "2", "applicable_dev_types"),
    ("parramatta", "parts", "5", "applicable_zones"),
    ("parramatta", "parts", "5", "applicable_dev_types"),
    ("parramatta", "parts", "6", "applicable_zones"),
    ("parramatta", "parts", "6", "applicable_dev_types"),
    ("parramatta", "parts", "7", "applicable_zones"),
    ("parramatta", "parts", "7", "applicable_dev_types"),
    ("parramatta", "parts", "8", "applicable_zones"),
    ("parramatta", "parts", "8", "applicable_dev_types"),
    ("parramatta", "parts", "9", "applicable_zones"),
    ("parramatta", "parts", "9", "applicable_dev_types"),
})


def _entries():
    """Yield (council_key, bucket, entry_key, entry) for every configured entry.

    Aliases are de-duplicated by IDENTITY, not by name: ku_ring_gai and
    ku-ring-gai point at the SAME dict, so counting by name would report one
    missing sentence twice and the number would move when an alias was added.
    """
    seen: set[int] = set()
    for council_key, config in COUNCIL_CONFIGS.items():
        if id(config) in seen:
            continue
        seen.add(id(config))
        for bucket in BUCKETS:
            for entry_key, entry in (config.get(bucket) or {}).items():
                if isinstance(entry, dict):
                    yield council_key, bucket, entry_key, entry


ENTRIES = list(_entries())


def _violations() -> set[tuple[str, str, str, str]]:
    """Every declared filter key with no usable sentence behind it."""
    found = set()
    for council, bucket, key, entry in ENTRIES:
        evidence = entry.get("scope_evidence") or {}
        for filter_key in declared_keys(entry):
            quote = evidence.get(filter_key)
            if not isinstance(quote, str) or len(quote.strip()) < MIN_EVIDENCE_CHARS:
                found.add((council, bucket, key, filter_key))
    return found


def test_the_registry_is_actually_walked():
    """A guard on this file, not on the configs.

    If COUNCIL_CONFIGS were renamed or a bucket spelling changed, every
    assertion below would pass over an empty list and this file would go green
    while checking nothing — the shape of failure the whole DQ effort exists to
    remove. So the walk asserts it found something first.
    """
    assert len(ENTRIES) > 50, f"only {len(ENTRIES)} entries walked — the registry moved"
    assert len({c for c, _, _, _ in ENTRIES}) >= 10


def test_no_new_declaration_without_its_sentence():
    """Rule 1: the unevidenced list cannot grow."""
    new = sorted(_violations() - UNEVIDENCED)
    assert not new, (
        f"{len(new)} declared applicability key(s) carry no scope_evidence and are "
        f"not in UNEVIDENCED:\n" + "\n".join(f"  {v}" for v in new) +
        "\n\nA declaration is a HARD FILTER on what a property is shown. Without "
        "the council's own sentence, no check can test it, no reviewer can "
        "spot-check it at scale, and the property page cannot say why the rule is "
        "on the list (DQ-115). Add the quote; do not add the key to UNEVIDENCED."
    )


def test_a_fixed_entry_is_released_from_the_list():
    """Rule 2: a listed entry that gained its sentence must leave the list.

    Without this the list becomes standing permission and quietly stops
    describing anything — the failure check_test_quarantine.py's second rule
    exists to prevent.
    """
    declared = {(c, b, k, fk) for c, b, k, e in ENTRIES for fk in declared_keys(e)}
    fixed = sorted((UNEVIDENCED & declared) - _violations())
    assert not fixed, (
        f"{len(fixed)} entr(y/ies) in UNEVIDENCED now carry their sentence and "
        f"must be removed from the list:\n" + "\n".join(f"  {v}" for v in fixed)
    )


def test_a_declined_key_is_never_also_declared():
    """`scope_declined` and a value are two answers to one question.

    _resolve checks scope_declined FIRST, so a contradicting pair would make the
    declared list dead code while the file reads as though it applied — the
    config-looks-right-and-does-nothing failure this directory keeps hitting.
    """
    both = [(c, b, k, fk) for c, b, k, e in ENTRIES for fk in FILTER_KEYS
            if fk in e and fk in (e.get("scope_declined") or ())]
    assert not both, (
        "these entries both DECLARE and DECLINE the same key; _resolve honours "
        "the decline and the declared value is never read: "
        + "; ".join(f"{b}" for b in sorted(both)))


def test_no_evidence_for_a_key_that_is_not_declared():
    """Evidence without a declaration is a quote watching an abandoned field.

    The reverse of rule 1, and it catches a real drift: a declaration removed
    while its sentence stays reads as configured to anyone opening the file,
    and `.get(k, ['ALL'])` quietly invents the value again.
    """
    orphans = []
    for council, bucket, key, entry in ENTRIES:
        decided = declared_keys(entry)
        for filter_key in (entry.get("scope_evidence") or {}):
            if filter_key in FILTER_KEYS and filter_key not in decided:
                orphans.append((council, bucket, key, filter_key))
    assert not orphans, (
        "scope_evidence present for a key that is NOT declared, so the entry "
        "reads as decided and resolves to ALL by fallthrough:\n"
        + "\n".join(f"  {o}" for o in sorted(orphans))
    )
