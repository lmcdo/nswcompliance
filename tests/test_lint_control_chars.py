"""scripts/lint_control_chars.py must catch a backspace hidden in a regex."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_repo_is_clean():
    r = subprocess.run([sys.executable, "scripts/lint_control_chars.py"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_backspace_is_caught():
    sys.path.insert(0, str(ROOT / "scripts"))
    import lint_control_chars as lcc
    assert lcc.BAD.search(b'X = re.compile(r"\x08detached")')
    assert not lcc.BAD.search(rb'X = re.compile(r"\bdetached")' + b"\t# tab is fine")


def test_flag_packets_in_place_pattern_matches_again():
    sys.path.insert(0, str(ROOT / "scripts" / "address_audit"))
    import flag_packets
    assert flag_packets.IN_PLACE.search("In Ashfield, the setback is 3 m")
