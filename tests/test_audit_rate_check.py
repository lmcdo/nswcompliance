"""audit_rate_check: pooled serious-error rate bound for outreach claim OC-18, run on real files."""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import audit_rate_check as arc  # noqa: E402

TODAY = date(2026, 10, 16)


def make_run(root: Path, name: str, packets: int, addresses: int, severe: int = 0, unsure: int = 0):
    d = root / name
    d.mkdir(parents=True)
    (d / "packets.jsonl").write_text("".join(json.dumps({"rule_key": f"{i}:{i}"}) + "\n" for i in range(packets)))
    (d / "summary.json").write_text(json.dumps([{"idx": str(i), "served": 10} for i in range(addresses)]))
    labels = [{"rule_key": f"s{i}", "label": "severe", "reason": "x", "category": "wrong-words"} for i in range(severe)]
    labels += [{"rule_key": f"u{i}", "label": "unsure", "reason": "x"} for i in range(unsure)]
    labels += [{"rule_key": f"o{i}", "label": "ok", "reason": "x"} for i in range(20)]
    (d / "labels.jsonl").write_text("".join(json.dumps(x) + "\n" for x in labels))


def test_pass(tmp_path):
    make_run(tmp_path, "2026-10-10-a", 700, 60, severe=1)
    ok, msg = arc.evaluate(tmp_path, TODAY)
    assert ok, msg
    assert msg.startswith("PASS") and "severe 1" in msg


def test_too_old(tmp_path):
    make_run(tmp_path, "2026-09-01-a", 700, 60)
    ok, msg = arc.evaluate(tmp_path, TODAY)
    assert not ok and "no audit run within 30 days" in msg


def test_pools_only_recent_runs(tmp_path):
    make_run(tmp_path, "2026-09-01-old", 700, 60, severe=30)
    make_run(tmp_path, "2026-10-15-new", 600, 60)
    ok, msg = arc.evaluate(tmp_path, TODAY)
    assert ok and "packets 600" in msg


def test_too_few_packets(tmp_path):
    make_run(tmp_path, "2026-10-10-a", 499, 60)
    ok, msg = arc.evaluate(tmp_path, TODAY)
    assert not ok and "only 499 rules" in msg


def test_too_few_addresses(tmp_path):
    make_run(tmp_path, "2026-10-10-a", 700, 49)
    ok, msg = arc.evaluate(tmp_path, TODAY)
    assert not ok and "only 49 addresses" in msg


def test_bound_too_high(tmp_path):
    make_run(tmp_path, "2026-10-10-a", 560, 60, severe=6)
    ok, msg = arc.evaluate(tmp_path, TODAY)
    assert not ok and "not below 2.0" in msg


def test_unsure_counted_as_severe(tmp_path):
    # 3 severe alone passes at 560 rules; 3 severe + 3 unsure must fail.
    make_run(tmp_path / "a", "2026-10-10-r", 560, 60, severe=3)
    assert arc.evaluate(tmp_path / "a", TODAY)[0]
    make_run(tmp_path / "b", "2026-10-10-r", 560, 60, severe=3, unsure=3)
    ok, msg = arc.evaluate(tmp_path / "b", TODAY)
    assert not ok and "unsure 3" in msg


def test_unknown_label_rejected(tmp_path):
    make_run(tmp_path, "2026-10-10-a", 700, 60)
    (tmp_path / "2026-10-10-a" / "labels.jsonl").write_text(json.dumps({"rule_key": "x", "label": "fine"}) + "\n")
    try:
        arc.evaluate(tmp_path, TODAY)
    except ValueError as e:
        assert "unknown label" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_bound_known_value():
    assert abs(arc.upper_bound_per_100(0, 100) - 2.9957) < 0.01
