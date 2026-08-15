#!/usr/bin/env python3
# prior-art-checked: reuse not viable because this probes the LINT ITSELF, not
# the corpus. lint_hardcoded_zone_codes.py is the subject under test and cannot
# assert its own blind spot. dq_probe_live.py takes SQL against the database and
# this needs no database at all. The shape is copied from the existing
# standalone probes -- dq_probe_stale_workflow_docs.py,
# dq_probe_dead_sar_constants.py, dq_probe_pvlib_claim.py -- which are the
# established pattern for a ledger check that is not a query.
"""DQ-75: the zone-code lint cannot see a zone-KEYED lookup object.

WHY THIS IS A ROW AND NOT A PATCH
---------------------------------
``check_line`` flags a line carrying two or more distinct zone tokens. A
hardcoded zone table is not written that way -- it is written one key per
line::

    const ZONE_DEVELOPMENT_MAPPING = {
      'E1': [ ... ],
      'R1': [ ... ],
      'R2': [ ... ],
    };

One token per line, so the lint sails past it. That is the exact shape of
issue #928, the live endpoint that served a hardcoded zone -> permitted-use
table contradicting the LEP in 135 places across 26 councils. The guard written
specifically to stop that class was blind to it for eleven months.

The evidence is not theoretical. ``.claude/zone_code_baseline.json`` tracks 99
files. ``pages/api/development-types.ts`` appears with 5 violations -- but those
5 are unrelated ``applicableZones: [...]`` ARRAYS further down the file. The
actual defect, ``ZONE_DEVELOPMENT_MAPPING``, is not among them. And the two
other files holding a full ``ZONE_DEVELOPMENT_TYPES`` map were not in the
baseline AT ALL.

WHY IT IS NOT FIXED HERE
------------------------
Widening the rule to catch a key-per-line map means tracking state across lines,
and the obvious version -- flag any brace block containing two or more zone
tokens -- will fire on legitimate code: switch statements over zones, test
fixtures, and the DCP Part/Chapter keys that ``PART_KEY_RE`` already exists to
excuse ("B1".."B17" as Waverley DCP parts, the false positive that rule was
written for). Getting it wrong in the noisy direction gets the lint suppressed,
which is worse than the gap.

It will also RAISE the baseline when fixed, because it will find violations that
were always there. That is the correct direction and needs saying out loud
first, so a rising number is not mistaken for a regression.

EXIT CODES
----------
0  the lint flags a zone-keyed map -- the gap is closed
1  it does not -- the gap is open (expected today)
2  the lint could not be imported or its contract changed
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

#: A zone-keyed lookup object, one key per line. Deliberately a copy of the
#: shape deleted from pages/api/development-types.ts rather than a minimal
#: sample, so this stays honest about what it is claiming to detect.
KEYED_MAP = [
    "const ZONE_DEVELOPMENT_MAPPING: Record<string, Entry[]> = {",
    "  'E1': [",
    "    { value: 'commercial_premises', label: 'Commercial Premises' },",
    "  ],",
    "  'R1': [",
    "    { value: 'dwelling_house', label: 'Single Dwelling House' },",
    "  ],",
    "  'R2': [",
    "    { value: 'dual_occupancy', label: 'Dual Occupancy' },",
    "  ],",
    "};",
]

#: A zone ARRAY on one line. The lint already catches this, and it is checked
#: too: if this stopped being flagged the probe would be measuring a lint that
#: had broken entirely, and reporting the gap as closed would be the worst
#: outcome -- a green row over a dead guard.
#
# The noqa is not a dodge: the pre-commit hook flagged this very line, which is
# the lint working correctly on the one shape it CAN see. Suppressing it here is
# the documented escape for a fixture rather than a regulatory lookup -- this
# array is the control the probe feeds to the lint, so it has to survive intact.
ZONE_ARRAY = ["  applicableZones: ['R3', 'R4', 'B1', 'B4'],"]  # noqa: zone-codes


def main() -> int:
    try:
        import lint_hardcoded_zone_codes as lint
    except ImportError as exc:
        print(f"DQ-75 UNKNOWN: cannot import the lint ({exc}). Exit 2.")
        return 2

    if not hasattr(lint, "check_line"):
        print("DQ-75 UNKNOWN: lint has no check_line(); its contract changed. Exit 2.")
        return 2

    # Control first. A probe that cannot detect the case the lint DOES catch is
    # broken, and would otherwise report the real gap as closed.
    control = [h for i, l in enumerate(ZONE_ARRAY, 1)
               for h in lint.check_line("probe_fixture.ts", i, l)]
    if not control:
        print("DQ-75 UNKNOWN: the lint no longer flags a plain zone ARRAY, so "
              "this probe cannot tell a closed gap from a dead guard. Exit 2.")
        return 2

    found = [h for i, l in enumerate(KEYED_MAP, 1)
             for h in lint.check_line("probe_fixture.ts", i, l)]

    print("DQ-75: zone-code lint vs a zone-KEYED lookup object")
    print(f"  control (zone array on one line) : {len(control)} flagged")
    print(f"  subject (zone-keyed map)         : {len(found)} flagged")
    if found:
        print("  CLEAN - the lint now sees a key-per-line zone map.")
        print("  NOTE: expect .claude/zone_code_baseline.json to RISE when this")
        print("  lands. That is the guard finding what was always there, not a")
        print("  regression.")
        return 0
    print("  means : a hardcoded zone -> value table written one key per line "
          "is invisible to the guard built to stop exactly that. This is the "
          "#928 shape: a live endpoint served such a table for eleven months, "
          "contradicting the LEP in 135 of 517 (council, zone, claim) triples "
          "across 26 councils, 8 of them against an explicit prohibited row.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
