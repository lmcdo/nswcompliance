"""The AI reader is given the chapter's page range, and its re-read passes stay inside it."""
from __future__ import annotations

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import ai_extractor as ai  # noqa: E402


def test_the_extractor_passes_its_page_range_to_the_ai_reader():
    src = (Path(__file__).resolve().parents[1] / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")
    assert "ai_extract_chapter(self.pdf_path, self.council, page_range=self.page_range)" in src


def _fake_pc(lines):
    m = types.ModuleType("page_coverage")
    m.pdf_page_lines = lambda path: lines
    m.running_lines = lambda ls: set()
    m.skipped_pages = lambda ls, texts, running: sorted(ls)   # every page offered counts as left out
    m.runs = lambda pages, n: [(p, p) for p in pages]
    m.holds_rules = lambda ls: False
    return m


def test_the_page_coverage_reread_never_reads_another_chapters_pages(monkeypatch):
    monkeypatch.setitem(sys.modules, "page_coverage", _fake_pc({p: ["x"] for p in range(1, 237)}))
    monkeypatch.setattr(ai, "figure_pages_override", lambda: set())
    monkeypatch.setattr(ai, "_subset_bytes", lambda reader, a, b: b"pdf")
    monkeypatch.setattr(ai, "_place_on_pages", lambda *a: None)
    asked = []
    monkeypatch.setattr(ai, "_call_and_parse_with_empty_retry", lambda m, b, p: asked.append(1) or [])
    ai._reread_skipped_pages("x.pdf", None, "mistral", [], owned=(52, 79))
    assert len(asked) == 28                                  # pages 52-79 only, not 236


def test_the_sentence_reread_only_judges_the_chapters_own_pages(monkeypatch):
    monkeypatch.setitem(sys.modules, "page_coverage", _fake_pc({}))
    monkeypatch.setattr(ai, "_page_texts_for_sentences", lambda path, running: {p: "t" for p in range(1, 237)})
    seen = {}
    monkeypatch.setattr(ai, "missing_sentences", lambda pages, texts: seen.setdefault("p", sorted(pages)) and {})
    monkeypatch.setattr(ai, "missing_table_numbers", lambda pages, texts: {})
    ai._reread_missing_sentences("x.pdf", None, "mistral", [], owned=(52, 79))
    assert seen["p"] == list(range(52, 80))
