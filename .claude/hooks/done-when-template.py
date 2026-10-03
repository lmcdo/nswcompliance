#!/usr/bin/env python
"""Keep the DONE WHEN format in context on every prompt.

The gate in done-when-gate.py is the enforcement. This is the reminder, and the
two do different jobs: the gate catches a turn that already drifted, this one
stops the drift starting. It exists separately because CLAUDE.md is loaded once
at session start and then competes with roughly sixty other rules, and because
context compaction can drop it entirely -- which is exactly when a long session
starts answering in prose again.

Deliberately short. A long injection on every prompt is noise, and the thing
being reinforced is four lines.

Prints to stdout, which Claude Code adds to the model's context. Exit 0 always;
a reminder must never block a prompt.
"""
import sys

TEMPLATE = """<done-when-format>
Before changing anything, state the completion criterion. When reporting, the
FIRST line carries the measured number.

  GOAL:       <one outcome, one sentence>
  DONE WHEN:  <one command> prints <one value>
  BUDGET:     <N attempts or N minutes>, then stop and report
  IF BLOCKED: report the measurement and stop; do not substitute another goal.

A number without the command that produced it is not a measurement. If a
measurement has not finished, say so and name the command -- do not report
prose in its place.
</done-when-format>"""


def main() -> int:
    sys.stdout.write(TEMPLATE)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
