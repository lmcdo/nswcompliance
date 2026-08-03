# prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md)
"""Shared fixtures: throwaway git repositories built in tmp_path."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


class GitRepo:
    def __init__(self, root: Path):
        self.root = root

    def run(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    def write(self, rel_path: str, content: str) -> None:
        path = self.root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def commit_all(self, message: str) -> None:
        self.run("add", "-A")
        self.run("commit", "-m", message, "--no-verify")


@pytest.fixture
def git_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GitRepo:
    """An initialised git repo with one commit on 'main'; cwd is the repo."""
    repo = GitRepo(tmp_path)
    repo.run("init", "-b", "main")
    repo.run("config", "user.email", "test@example.com")
    repo.run("config", "user.name", "Test")
    repo.write("README.md", "seed\n")
    repo.commit_all("initial")
    monkeypatch.chdir(tmp_path)
    return repo
