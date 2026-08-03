# prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md)
from prose_gate.diff import added_since, added_staged, parse_added_lines


def test_added_since_reports_only_new_lines(git_repo):
    git_repo.write("page.tsx", "line one\nline two\n")
    git_repo.commit_all("add page")
    git_repo.run("checkout", "-b", "feature")
    git_repo.write("page.tsx", "line one\nINSERTED A\nline two\nINSERTED B\n")
    git_repo.commit_all("insert lines")

    files = added_since("main")
    assert files == {"page.tsx": [(2, "INSERTED A"), (4, "INSERTED B")]}


def test_added_since_ignores_deleted_files(git_repo):
    git_repo.write("gone.md", "text\n")
    git_repo.commit_all("add file")
    git_repo.run("checkout", "-b", "feature")
    git_repo.run("rm", "gone.md")
    git_repo.commit_all("remove file")

    assert added_since("main") == {}


def test_added_since_uses_merge_base(git_repo):
    git_repo.run("checkout", "-b", "feature")
    git_repo.write("new.md", "feature text\n")
    git_repo.commit_all("feature work")
    # main moves on independently; its changes must not appear in the diff
    git_repo.run("checkout", "main")
    git_repo.write("main_only.md", "main text\n")
    git_repo.commit_all("main work")
    git_repo.run("checkout", "feature")

    files = added_since("main")
    assert "new.md" in files
    assert "main_only.md" not in files


def test_added_staged(git_repo):
    git_repo.write("draft.md", "staged sentence\n")
    git_repo.run("add", "draft.md")

    assert added_staged() == {"draft.md": [(1, "staged sentence")]}


def test_parse_handles_multiple_files_and_hunks():
    diff = (
        "diff --git a/a.md b/a.md\n"
        "--- a/a.md\n"
        "+++ b/a.md\n"
        "@@ -0,0 +1 @@\n"
        "+first\n"
        "diff --git a/b.md b/b.md\n"
        "--- a/b.md\n"
        "+++ b/b.md\n"
        "@@ -5,0 +6,2 @@\n"
        "+six\n"
        "+seven\n"
    )
    assert parse_added_lines(diff) == {
        "a.md": [(1, "first")],
        "b.md": [(6, "six"), (7, "seven")],
    }
