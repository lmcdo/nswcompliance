"""Mutation harness for the fabricated-citation removal.

Puts each citation back one at a time, runs the suite, requires FAILED, and
restores the file byte-for-byte. A row printed as HOLE is a gap in the tests,
not a bug in the code: it means the suite would not have noticed that citation
coming back.

Run it from anywhere; it chdirs to frontend-nextjs itself, because every path
below is relative to that directory and jest has to start there:

    python scripts/mutate_cite.py

Exits non-zero if any row is a hole. A row whose anchor stops matching is a
hole too, deliberately: it means the line it pinned has been rewritten and
nobody re-pointed the row, so that citation is no longer pinned by anything.
Correct the anchor to the new line. Do not delete the row.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mutate_lib import run  # noqa: E402

TESTS = ['__tests__/components/compliance/no-fabricated-citations.test.tsx']

MUTATIONS = [
    # ── the shared label ──
    ('make the label invent an instrument when none is given',
     'lib/citation-display.ts',
     '  const instrument = asTrimmedString(epiName);',
     "  const instrument = asTrimmedString(epiName) ?? 'Local Environmental Plan';",
     'a badge naming no instrument asserts authority it does not have'),

    ('make the label return a placeholder instead of null',
     'lib/citation-display.ts',
     '  return instrument ?? reference;',
     "  return instrument ?? reference ?? 'Clause 2.3';",
     'null is what lets the caller drop the badge entirely'),

    # ── the live LMR citation ──
    ('bring back the guessed SEPP (Housing) 2021',
     'components/compliance/ConstraintArithmeticCard.tsx',
     '  return sourceDocument ? `${sourceDocument} cl ${sourceClause}` : `clause ${sourceClause}`;',
     "  return `${sourceDocument || 'SEPP (Housing) 2021'} cl ${sourceClause}`;",
     'the live one: a real clause attributed to a guessed instrument'),

    # ── the live zoning card ──
    ('restore the default clause parameter',
     'components/compliance/LandUseZoningCard.tsx',
     '  legislativeClause\r\n}: LandUseZoningCardProps) {',
     "  legislativeClause = 'Clause 2.3'\r\n}: LandUseZoningCardProps) {",
     'the DEFAULT PARAMETER shape, which the counter cannot see'),

    ('render the badge even when it names nothing',
     'components/compliance/LandUseZoningCard.tsx',
     '            {citation && (',
     '            {true && (',
     'an empty badge still claims a source'),

    # ── the minimum-lot-size card ──
    ('restore the Inner West instrument default',
     'components/compliance/MinimumLotSizeCard.tsx',
     '  const citation = instrumentClauseLabel(epiName, legislativeClause);',
     "  const citation = instrumentClauseLabel(epiName || 'Inner West Local Environmental Plan 2022', legislativeClause);",
     "another council's lot attributed to the Inner West LEP"),

    # ── the height / FSR panels ──
    ('bring back Clause 4.3 for height',
     'components/compliance/ComplianceDashboard.tsx',
     "        const heightClause = asTrimmedString(result['Legislative Clause']);",
     "        const heightClause = asTrimmedString(result['Legislative Clause']) ?? 'Clause 4.3';",
     'the original defect'),

    ('bring back Clause 4.4 for FSR',
     'components/compliance/ComplianceDashboard.tsx',
     "        const fsrClause = asTrimmedString(fsrResult['Legislative Clause']);",
     "        const fsrClause = asTrimmedString(fsrResult['Legislative Clause']) ?? 'Clause 4.4';",
     'the original defect'),

    ('hardcode the LEP document id posted to /api/lep/full-text',
     'components/compliance/ComplianceDashboard.tsx',
     '  const documentId = `${epi.replace(/[^A-Za-z0-9]+/g, \'_\')}___NSW_Legislation`;',
     "  const documentId = 'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation';",
     "another council's lot would be served Inner West clause text"),

    ('bring back the Inner West LEP section header',
     'components/compliance/ComplianceDashboard.tsx',
     "              const lepName = asTrimmedString(lepLayer?.results?.[0]?.['EPI Name']);",
     "              const lepName = asTrimmedString(lepLayer?.results?.[0]?.['EPI Name']) ?? 'Inner West Local Environmental Plan 2022';",
     'the one my own ratchet caught and I had missed'),

    # ── heritage ──
    ('bring back Clause 5.10',
     'components/compliance/HeritageDetails.tsx',
     '      legislativeClause: heritage?.heritageClause || null,',
     "      legislativeClause: heritage?.heritageClause || 'Clause 5.10',",
     'the usual heritage clause, so a wrong one would never look wrong'),

    # ── the type guard the QA gate blocked the push over ──
    ('drop the typeof guard, so an untyped Portal value reaches .trim()',
     'lib/citation-display.ts',
     "  if (typeof value !== 'string') return null;",
     '  if (false) return null;',
     'a numeric EPI Name would throw and take the whole page down'),

    # ── cross-review findings, 2026-10-07 ──
    ('collapse the dedup key back onto the citation alone',
     'lib/compliance/constraint-dedup.ts',
     '      : JSON.stringify([c.type, c.value, c.unit ?? null, c.source.clause ?? null, c.source.document ?? null]);',
     "      : `${c.source.clause ?? ''}-${c.source.document ?? ''}`;",
     'with both clauses nulled, FSR collides with height and is silently dropped'),

    ('join the dedup key with a delimiter a field can contain',
     'lib/compliance/constraint-dedup.ts',
     '      : JSON.stringify([c.type, c.value, c.unit ?? null, c.source.clause ?? null, c.source.document ?? null]);',
     "      : `${c.type}:${c.value}:${c.unit ?? ''}:${c.source.clause ?? ''}-${c.source.document ?? ''}`;",
     "clause 'A-B' + document 'C' and clause 'A' + document 'B-C' forge one key"),

    ('let an untyped Legislative Clause reach the height citation',
     'components/compliance/ComplianceDashboard.tsx',
     '        const heightClause = asTrimmedString(result[\'Legislative Clause\']);',
     "        const heightClause: string | null = result['Legislative Clause'] || null;",
     'a numeric clause reaches ConstraintCard .match() and crashes the surface'),

    ('let a whitespace EPI name render as a blank LEP heading',
     'components/compliance/ComplianceDashboard.tsx',
     '              const lepName = asTrimmedString(lepLayer?.results?.[0]?.[\'EPI Name\']);',
     "              const lepName = lepLayer?.results?.[0]?.['EPI Name'] || null;",
     "'   ' is truthy, so the 'not named' message never shows"),

    # ── the honest one must survive ──
    ('delete the honest "not available" message',
     'components/compliance/ReferencedLegislationAccordion.tsx',
     "{ref.clause_reference || 'Clause Reference Not Available'}",
     '{ref.clause_reference}',
     'stating the absence is correct and must not be "fixed" into silence'),
]


if __name__ == '__main__':
    # Anchor to the repo, not to the caller's cwd. Running this from the wrong
    # directory used to mean every anchor matched 0 times, which the harness
    # reports as holes -- indistinguishable from a suite that genuinely fails to
    # catch the citations coming back.
    os.chdir(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          'frontend-nextjs'))
    sys.exit(run(tests=TESTS, mutations=MUTATIONS, tag='cite'))
