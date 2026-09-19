"""An hour of correct work, thrown away by a dead connection.

Two complete runs of city_of_sydney/section-3-general-provisions died at exactly the same
line, after doing everything right:

    [OCR] using OCR text for 141 pages
    Extracted: 94 sections
    psycopg2.OperationalError: server closed the connection unexpectedly
      ... in diff_provisions

The cursor is opened before extract_pdf_isolated and the first query after it is roughly
an hour later. libpq keepalives were added first, on the theory that the socket was being
reaped for idleness. The fourth run carried them and died identically, so that theory is
wrong: keepalives hold the TCP socket open while the pooler closes the SESSION, and no
socket-level setting reaches that.

psycopg2's `conn.closed` reports what THIS process did to the connection, not what the
server did — so a server-side close still reads as open until something is executed. The
ping is the only way to know.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SRC = (ROOT / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")


def _mod():
    import dcp_extract_changed
    return dcp_extract_changed


class _Cur:
    def __init__(self, fail): self.fail = fail
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def execute(self, *a, **k):
        if self.fail:
            raise Exception("server closed the connection unexpectedly")
    def close(self): pass


class _Conn:
    def __init__(self, dead=False):
        self.dead = dead
        self.closed_called = False
    def cursor(self): return _Cur(self.dead)
    def close(self): self.closed_called = True


class TestALiveConnectionIsLeftAlone:
    def test_a_working_connection_is_returned_unchanged(self, monkeypatch):
        """Reconnecting every time would throw away a perfectly good session and hide
        a genuine connection problem behind a reconnect loop."""
        m = _mod()
        monkeypatch.setattr(m.psycopg2, "connect",
                            lambda *a, **k: pytest.fail("reconnected a live connection"))
        c = _Conn(dead=False)
        assert m.revive(c) is c
        assert not c.closed_called


class TestADeadConnectionIsReplaced:
    def test_a_server_side_close_is_detected_and_replaced(self, monkeypatch):
        m = _mod()
        fresh = _Conn()
        monkeypatch.setattr(m.psycopg2, "connect", lambda *a, **k: fresh)
        dead = _Conn(dead=True)
        assert m.revive(dead) is fresh

    def test_the_dead_one_is_closed_rather_than_leaked(self, monkeypatch):
        """A batch of chapters would otherwise leave one dead connection per chapter
        held open against the pooler's client limit."""
        m = _mod()
        monkeypatch.setattr(m.psycopg2, "connect", lambda *a, **k: _Conn())
        dead = _Conn(dead=True)
        m.revive(dead)
        assert dead.closed_called

    def test_a_close_that_itself_fails_does_not_stop_the_reconnect(self, monkeypatch):
        """Closing a socket the server already dropped can raise. Losing the reconnect
        to the cleanup would be the same lost hour, one layer along."""
        m = _mod()
        fresh = _Conn()
        monkeypatch.setattr(m.psycopg2, "connect", lambda *a, **k: fresh)
        dead = _Conn(dead=True)
        dead.close = lambda: (_ for _ in ()).throw(Exception("already gone"))
        assert m.revive(dead) is fresh

    def test_it_does_not_rely_on_conn_closed(self):
        """conn.closed reports what THIS process did, not what the server did, so it
        reads 0 on a connection the pooler has already dropped. Only executing finds out."""
        fn = SRC[SRC.index("def revive(conn):"):]
        fn = fn[:fn.index("def extract_pdf_isolated")]
        # The docstring explains why conn.closed is useless here, so strip it before
        # looking: matching prose instead of code is how a test asserts nothing.
        body = fn.split('"""')[2] if fn.count('"""') >= 2 else fn
        assert ".closed" not in body, "revive is trusting conn.closed, which cannot see this"
        assert 'c.execute("SELECT 1")' in body


class TestItRunsAtTheBoundaryThatMatters:
    def test_the_chapter_revives_after_the_pdf_work_and_before_any_query(self):
        body = SRC[SRC.index("def extract_chapter("):]
        body = body[:body.index("def main(")]
        pdf_work = body.index("result, err = extract_pdf_isolated(")
        revived = body.index("conn = revive(conn)")
        first_query = body.index("diff_provisions(")
        assert pdf_work < revived < first_query, (
            "the connection must be re-established between the PDF work and the first "
            "query that uses it")

    def test_the_cursor_is_re_made_from_the_revived_connection(self):
        """A revived connection with the OLD cursor is no better: the cursor belongs to
        the connection that died."""
        body = SRC[SRC.index("def extract_chapter("):]
        body = body[:body.index("def main(")]
        i = body.index("conn = revive(conn)")
        assert "cur = conn.cursor()" in body[i:i + 200]

    def test_main_revives_its_own_connection_too(self):
        """extract_chapter takes conn as a PARAMETER, so rebinding inside it cannot reach
        main's. Without this the first chapter's hour of PDF work leaves every later
        chapter in the batch holding a dead connection."""
        body = SRC[SRC.index("def main("):]
        call = body.index("ok, review_data = extract_chapter(")
        assert "conn = revive(conn)" in body[call:call + 800]

    def test_keepalives_are_kept_as_well(self):
        """Not either/or. Keepalives still prevent the idle reap they were added for;
        they simply cannot prevent a pooler closing the session, which is what was
        measured. Removing them would re-open the failure they DO cover."""
        assert "keepalives=1" in SRC
        assert SRC.count("keepalives=1") >= 2, (
            "the reconnect must ask for keepalives too, or the replacement connection "
            "is weaker than the one it replaced")
