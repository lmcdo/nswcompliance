"""Table rows proven cell by cell (scripts/council_quote_table.py), on lines placed like a real PDF table.

prior-art-checked: new module; council_quote's own tests cover running text. Shapes from the 2026-10-13 re-read:
Blacktown parking rates ("Bulky goods premises | 1 space per 45sq.m GFA"), Leichhardt tree retention table.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import citation_proof as cp  # noqa: E402
import council_quote as cq  # noqa: E402


def table_stream(cells):
    """cells: [(page, y, x, text)] in the order the text layer reads them (column by column, as PDFs often do)."""
    lines, cased = [], {}
    for page, y, x, t in cells:
        ln = cp.Line(page, y, x, t.lower())
        lines.append(ln)
        cased[(page, y, x, t.lower())] = t
    return cq.Stream(SimpleNamespace(lines=lines), cased)


def row(text, page=1):
    return {"id": 1, "source_council": "x", "pdf_page": page, "page_check": None, "provision_text": text}


# a two-column rate table read column by column: names first, then rates
PARKING = [(1, 100, 50, "Bulky goods premises"), (1, 120, 50, "Gymnasium"), (1, 140, 50, "Restaurant or cafe"),
           (1, 100, 300, "1 space per 45sq.m GFA"), (1, 120, 300, "1 space per 25sq.m GFA"),
           (1, 140, 300, "1 space per 30sq.m GFA")]


def test_a_row_is_proven_when_its_cells_share_one_printed_row():
    out = cq.judge(row("Gymnasium | 1 space per 25sq.m GFA"), [table_stream(PARKING)])
    assert out["status"] == "exact" and out["reason"] == "table_rows"
    assert out["quote"] == "Gymnasium | 1 space per 25sq.m GFA" and out["quote_page"] == 1


def test_a_rate_paired_with_the_wrong_use_is_refused():
    """The rate exists on the page, but on another row: never proven."""
    out = cq.judge(row("Gymnasium | 1 space per 45sq.m GFA"), [table_stream(PARKING)])
    assert out["status"] != "exact"


def test_cells_out_of_order_are_refused():
    out = cq.judge(row("1 space per 25sq.m GFA | Gymnasium"), [table_stream(PARKING)])
    assert out["reason"] != "table_rows"


def test_several_rows_are_all_proven_or_none():
    ok = cq.judge(row("Bulky goods premises | 1 space per 45sq.m GFA\nRestaurant or cafe | 1 space per 30sq.m GFA"),
                  [table_stream(PARKING)])
    assert ok["reason"] == "table_rows" and ok["quote"].count("\n") == 1
    bad = cq.judge(row("Bulky goods premises | 1 space per 45sq.m GFA\nRestaurant or cafe | 1 space per 99sq.m GFA"),
                   [table_stream(PARKING)])
    assert bad["status"] != "exact"


def test_a_row_on_another_page_far_away_is_not_used():
    cells = [(c[0] + 5, *c[1:]) for c in PARKING]          # the table is on page 6; the rule says page 1
    out = cq.judge(row("Gymnasium | 1 space per 25sq.m GFA", page=1), [table_stream(cells)])
    assert out["status"] != "exact"


def test_prose_without_cells_is_not_a_table():
    import council_quote_table as cqt
    assert cqt.prove_rows("Gymnasium needs 1 space per 25sq.m GFA", [table_stream(PARKING)], 1, cq.norm) is None


def test_a_compact_table_does_not_pair_a_cell_with_the_next_row():
    """Cross-review 2026-10-13: rows 6 points apart; the next row's rate must never prove this row."""
    compact = [(1, 100, 50, "Gymnasium"), (1, 106, 50, "Bulky goods premises"),
               (1, 106, 300, "1 space per 45sq.m GFA"), (1, 100, 300, "1 space per 25sq.m GFA")]
    out = cq.judge(row("Gymnasium | 1 space per 45sq.m GFA"), [table_stream(compact)])
    assert out["status"] != "exact"
    ok = cq.judge(row("Gymnasium | 1 space per 25sq.m GFA"), [table_stream(compact)])
    assert ok["reason"] == "table_rows"


def test_a_cell_running_into_the_next_row_is_refused():
    """Cross-review 2026-10-13: 'Gymnasium Bulky goods premises' spans two printed rows of the first column."""
    out = cq.judge(row("Gymnasium Bulky goods premises | 1 space per 45sq.m GFA"), [table_stream(PARKING)])
    assert out["status"] != "exact"


def test_a_plain_line_between_two_rows_is_never_copied():
    lines = ["Setback | Minimum", "a stray half row", "Front | 10m"]
    assert cqt.prove_rows("\n".join(lines), [], 1, cq.norm) is None
