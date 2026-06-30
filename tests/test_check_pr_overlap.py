"""Unit tests for the pure overlap logic in scripts/check_pr_overlap.py."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from pr_overlap_guard import compute_overlaps  # noqa: E402


def _pr(number, head, files, title="t"):
    return {"number": number, "title": title, "headRefName": head, "files": [{"path": f} for f in files]}


class TestComputeOverlaps:
    def test_detects_overlap(self):
        prs = [_pr(493, "fix/lep-name-from-epi", ["frontend-nextjs/components/compliance/LepControls.tsx"])]
        hits = compute_overlaps("my-branch", ["frontend-nextjs/components/compliance/LepControls.tsx"], prs)
        assert hits == [(493, "t", ["frontend-nextjs/components/compliance/LepControls.tsx"])]

    def test_excludes_current_branch_own_pr(self):
        prs = [_pr(608, "my-branch", ["a.ts"])]
        assert compute_overlaps("my-branch", ["a.ts"], prs) == []

    def test_no_overlap_returns_empty(self):
        prs = [_pr(1, "other", ["x.ts"])]
        assert compute_overlaps("my-branch", ["y.ts"], prs) == []

    def test_partial_overlap_reports_only_shared_files(self):
        prs = [_pr(2, "other", ["a.ts", "b.ts", "c.ts"])]
        hits = compute_overlaps("my-branch", ["b.ts", "z.ts"], prs)
        assert hits == [(2, "t", ["b.ts"])]

    def test_multiple_prs_each_reported(self):
        prs = [_pr(10, "o1", ["a.ts"]), _pr(11, "o2", ["a.ts", "b.ts"])]
        hits = compute_overlaps("my-branch", ["a.ts"], prs)
        assert {h[0] for h in hits} == {10, 11}

    def test_malformed_pr_files_do_not_crash(self):
        prs = [{"number": 3, "title": "t", "headRefName": "o", "files": None}]
        assert compute_overlaps("my-branch", ["a.ts"], prs) == []
