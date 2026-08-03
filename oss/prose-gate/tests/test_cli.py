# prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md)
import json

from prose_gate.cli import main


def test_full_mode_flags_and_exits_1(git_repo, capsys):
    git_repo.write("copy.md", "This outcome is guaranteed.\n")
    assert main(["--full", "copy.md"]) == 1
    out = capsys.readouterr().out
    assert "copy.md:1" in out
    assert "guaranteed" in out


def test_full_mode_clean_exits_0(git_repo, capsys):
    git_repo.write("copy.md", "Flood mapping sourced from council data.\n")
    assert main(["--full", "copy.md"]) == 0


def test_json_format(git_repo, capsys):
    git_repo.write("copy.md", "Approval is guaranteed.\n")
    assert main(["--full", "copy.md", "--format", "json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["findings"][0]["term"] == "guaranteed"


def test_diff_mode_only_flags_added_user_facing_lines(git_repo, capsys):
    git_repo.write("page.tsx", "<p>old text</p>\n")
    git_repo.write("engine.py", 'MESSAGE = "guaranteed"\n')
    git_repo.commit_all("base")
    git_repo.run("checkout", "-b", "feature")
    git_repo.write("page.tsx", "<p>old text</p>\n<p>Approval is guaranteed.</p>\n")
    git_repo.write("engine.py", 'MESSAGE = "guaranteed"\nOTHER = "guaranteed too"\n')
    git_repo.commit_all("changes")

    assert main(["--diff-base", "main"]) == 1
    out = capsys.readouterr().out
    assert "page.tsx:2" in out
    assert "engine.py" not in out  # .py is not user-facing by default


def test_staged_mode(git_repo, capsys):
    git_repo.write("copy.md", "A guaranteed outcome.\n")
    git_repo.run("add", "copy.md")
    assert main(["--staged"]) == 1


def test_unknown_preset_exits_2(git_repo, capsys):
    git_repo.write("copy.md", "text\n")
    assert main(["--full", "copy.md", "--preset", "nonexistent"]) == 2
    assert "unknown preset" in capsys.readouterr().err


def test_custom_preset_and_config(git_repo, capsys):
    git_repo.write(
        ".prose-gate.toml",
        'preset = "assurance"\nextra_terms = ["flood-proof"]\n'
        'user_facing = ["*.md"]\n',
    )
    git_repo.write("copy.md", "This lot is flood-proof.\n")
    assert main(["--full", "copy.md"]) == 1
    assert "flood-proof" in capsys.readouterr().out


def test_list_presets(git_repo, capsys):
    assert main(["--list-presets"]) == 0
    out = capsys.readouterr().out
    assert "assurance" in out
    assert "financial" in out
    assert "health" in out
