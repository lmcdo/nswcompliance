"""The mutmut pin must be a version that has the flags mutation_health.py passes.

REAL FINDING, 2026-10-21. #777 (Dependabot, 2026-08-12) raised the pin from <3 to
>=3.6,<4. mutmut 3 removed --paths-to-mutate, --tests-dir, --runner and --no-progress
(read from mutmut 3.8.0's own CLI: `run` takes only --max-children and mutant names),
so the monthly maintenance-mutation job failed on every run after, and because the
script threw mutmut's output away, each run said only "no such table: Mutant".

prior-art-checked: no test tied the pin to the CLI the script uses.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TWO_X_ONLY = ("--paths-to-mutate", "--tests-dir", "--runner", "--no-progress")


def _pin() -> str:
    text = (ROOT / "scripts" / "requirements-maintenance.txt").read_text(encoding="utf-8")
    m = re.search(r"(?m)^mutmut\s*(\S+)", text)
    assert m, "no mutmut line in scripts/requirements-maintenance.txt"
    return m.group(1)


def test_a_script_on_the_2x_cli_is_pinned_below_3():
    src = (ROOT / "scripts" / "mutation_health.py").read_text(encoding="utf-8")
    used = [f for f in TWO_X_ONLY if f in src]
    if not used:
        return  # the script was ported to 3.x; nothing to hold
    pin = _pin()
    assert "<3" in pin.replace(" ", ""), (
        f"mutation_health.py passes {used}, which only mutmut 2.x has, but the pin is "
        f"'mutmut{pin}'. Pin <3, or port the script to the 3.x CLI first."
    )


def test_dependabot_does_not_offer_mutmut_majors():
    cfg = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert re.search(r'dependency-name:\s*"mutmut"\s*\n\s*update-types:\s*\["version-update:semver-major"\]', cfg)
