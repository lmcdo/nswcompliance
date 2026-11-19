"""scripts/rebuild_bushfire_overlay.py: stage into its own table, verify against the live map, swap atomically with a backup.

The swap is the dangerous step, so the tests pin when it must refuse and when it must roll back.
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import rebuild_bushfire_overlay as rb  # noqa: E402

POLY = {"type": "Polygon", "coordinates": [[[151.0, -33.0], [151.1, -33.0], [151.1, -33.1], [151.0, -33.0]]]}


def test_rows_are_built_like_the_loader_and_unusable_features_are_skipped():
    feats = [{"properties": {"OBJECTID": 5, "d_Category": 1.0}, "geometry": POLY},
             {"properties": {"OBJECTID": 7}, "geometry": None},
             {"properties": {"d_Category": 1}, "geometry": POLY}]
    rows = rb.build_rows(feats)
    assert [r[6] for r in rows] == [5] and rows[0][:6] == ("unknown", None, "bushfire", "1.0", None, None)


def test_a_short_live_id_list_stops_everything(monkeypatch):
    class R:
        def json(self):
            return {"objectIds": list(range(10))}

    monkeypatch.setattr(rb.requests, "get", lambda *a, **k: R())
    with pytest.raises(SystemExit, match="STOPPED"):
        rb.live_ids()


class _Cur:
    def __init__(self, counts=None):
        self.sql, self.rowcount, self.counts, self._last = [], 0, list(counts or []), None

    def execute(self, sql, args=None):
        self.sql.append(sql.strip().split()[0].upper() + " " + " ".join(sql.split()[1:4]))
        self._last = sql

    def fetchone(self):
        return (self.counts.pop(0),)


class _Conn:
    def __init__(self, cur):
        self.cur, self.committed, self.rolled_back, self.closed = cur, False, False, False

    def cursor(self):
        return self.cur

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def _swap(monkeypatch, live, staged, backup_rows=0, deleted=0, inserted=0):
    cur = _Cur(counts=[backup_rows])
    conn = _Conn(cur)
    monkeypatch.setattr(rb, "connect", lambda: conn)
    monkeypatch.setattr(rb, "backup_to_file", lambda c: (cur.sql.append("CREATE FILE BACKUP") or "file.csv", backup_rows))
    monkeypatch.setattr(rb, "live_ids", lambda: set(live))
    monkeypatch.setattr(rb, "staged_ids", lambda c: set(staged))

    def execute(sql, args=None):
        cur.sql.append(" ".join(sql.split())[:60])
        if sql.lstrip().upper().startswith("DELETE"):
            cur.rowcount = deleted
        elif sql.lstrip().upper().startswith("INSERT"):
            cur.rowcount = inserted

    cur.execute = execute
    return rb.swap(), conn, cur


def test_the_swap_refuses_when_staging_is_missing_areas_and_touches_nothing(monkeypatch, capsys):
    monkeypatch.setattr(rb, "missing_is_acceptable", lambda missing: (False, []))
    code, conn, cur = _swap(monkeypatch, live=range(100), staged=range(90))
    assert code == 1 and "REFUSED" in capsys.readouterr().out
    assert not any(q.upper().startswith(("DELETE", "INSERT", "CREATE")) for q in cur.sql) and not conn.committed and conn.closed


def test_the_swap_refuses_when_staging_holds_areas_the_live_map_does_not(monkeypatch, capsys):
    code, conn, cur = _swap(monkeypatch, live=range(100), staged=range(101))
    assert code == 1 and not conn.committed


def test_the_swap_backs_up_first_then_replaces_in_one_transaction(monkeypatch, capsys):
    code, conn, cur = _swap(monkeypatch, live=range(100), staged=range(100), backup_rows=500, deleted=500, inserted=120)
    assert code == 0 and conn.committed and not conn.rolled_back and conn.closed
    kinds = [q.split()[0].upper() for q in cur.sql if q.split()[0].upper() in ("CREATE", "DELETE", "INSERT")]
    assert kinds == ["CREATE", "DELETE", "INSERT"]                  # backup file, then delete, then insert, committed once at the end


def test_the_swap_rolls_back_when_the_backup_and_the_delete_disagree(monkeypatch, capsys):
    code, conn, _ = _swap(monkeypatch, live=range(100), staged=range(100), backup_rows=500, deleted=499, inserted=120)
    assert code == 1 and conn.rolled_back and not conn.committed and "ROLLED BACK" in capsys.readouterr().out


def test_the_swap_rolls_back_when_too_few_rows_were_inserted(monkeypatch, capsys):
    code, conn, _ = _swap(monkeypatch, live=range(1000), staged=range(1000), backup_rows=500, deleted=500, inserted=900)
    assert code == 1 and conn.rolled_back and not conn.committed


def test_the_swap_rolls_back_on_an_error(monkeypatch):
    cur = _Cur(counts=[5])
    conn = _Conn(cur)
    monkeypatch.setattr(rb, "connect", lambda: conn)
    monkeypatch.setattr(rb, "backup_to_file", lambda c: ("file.csv", 5))
    monkeypatch.setattr(rb, "live_ids", lambda: set(range(10)))
    monkeypatch.setattr(rb, "staged_ids", lambda c: set(range(10)))

    def boom(sql, args=None):
        if sql.lstrip().upper().startswith("DELETE"):
            raise RuntimeError("lock timeout")

    cur.execute = boom
    with pytest.raises(RuntimeError):
        rb.swap()
    assert conn.rolled_back and not conn.committed and conn.closed


def test_the_script_only_ever_deletes_bushfire_rows_and_never_truncates_or_drops():
    src = (REPO / "scripts" / "rebuild_bushfire_overlay.py").read_text(encoding="utf-8")
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    assert 'DELETE FROM spatial_overlays WHERE layer_type = %s", (LAYER,)' in code and code.upper().count("DELETE FROM") == 1
    assert "TRUNCATE" not in code.upper() and "DROP TABLE" not in code.upper()


def test_verify_fails_on_missing_ids_without_looking_at_points(monkeypatch, capsys):
    class C:
        def cursor(self):
            return self

        def set_session(self, **k):
            pass

        def execute(self, *a):
            pass

        def fetchall(self):
            return []

        def close(self):
            pass

    monkeypatch.setattr(rb, "connect", lambda: C())
    monkeypatch.setattr(rb, "live_ids", lambda: set(range(10)))
    monkeypatch.setattr(rb, "staged_ids", lambda c: set(range(9)))
    assert rb.verify() == 1
    assert "FAIL" in capsys.readouterr().out


def test_ids_the_service_leaves_out_of_a_batch_are_retried_smaller(monkeypatch, capsys):
    """Review of the real run: the service answered a batch with an empty list, the run counted it done, and 1,999 areas were never staged."""
    feat = lambda n: {"properties": {"OBJECTID": n, "d_Category": 1}, "geometry": POLY}  # noqa: E731
    calls = []

    def fetch_page_by_oids(service, layer, ids, base="Planning"):
        calls.append(list(ids))
        if len(ids) > 20:
            return {"features": []}                      # the big batch comes back empty
        return {"features": [feat(i) for i in ids]}

    monkeypatch.setattr(rb.ing, "fetch_page_by_oids", fetch_page_by_oids)
    cur = _Cur()
    conn = _Conn(cur)
    monkeypatch.setenv("DATABASE_URL", "x")
    monkeypatch.setattr(rb, "connect", lambda: conn)
    monkeypatch.setattr(rb, "live_ids", lambda: set(range(1, 101)))
    staged = {"ids": set()}
    monkeypatch.setattr(rb, "staged_ids", lambda c: set(staged["ids"]))
    inserted = []
    monkeypatch.setattr(rb, "execute_values", lambda cur_, sql, rows, template=None: (inserted.extend(r[6] for r in rows), staged["ids"].update(r[6] for r in rows)))
    monkeypatch.setattr(rb, "BATCH", 100)
    assert rb.stage() == 0
    assert sorted(inserted) == list(range(1, 101))             # every id was staged although the 100-id batch came back empty
    assert any(len(c) == 20 for c in calls)


def test_a_few_missing_areas_are_acceptable_only_if_each_has_no_usable_shape(monkeypatch):
    monkeypatch.setattr(rb.ing, "fetch_page_by_oids", lambda s, l, ids, base="Planning": {"features": [{"properties": {"OBJECTID": ids[0]}, "geometry": None}]})
    assert rb.missing_is_acceptable([5, 6]) == (True, [5, 6])        # answered, but no shape: not storable
    assert rb.missing_is_acceptable([]) == (True, [])
    monkeypatch.setattr(rb.ing, "fetch_page_by_oids", lambda s, l, ids, base="Planning": {"features": [{"properties": {"OBJECTID": ids[0]}, "geometry": POLY}]})
    assert rb.missing_is_acceptable([5])[0] is False                  # it has a shape: it should have been staged
    monkeypatch.setattr(rb.ing, "fetch_page_by_oids", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("500")))
    assert rb.missing_is_acceptable([5])[0] is False                  # could not even be fetched: not proven unstorable
    assert rb.missing_is_acceptable(list(range(rb.MAX_UNSTORABLE + 1)))[0] is False   # too many is a failure whatever they are


def test_ids_a_person_names_as_unobtainable_are_accepted_but_nothing_else(monkeypatch):
    monkeypatch.setattr(rb.ing, "fetch_page_by_oids", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("500")))
    monkeypatch.setattr(rb, "ACCEPTED", {5, 6})
    assert rb.missing_is_acceptable([5, 6]) == (True, [5, 6])
    assert rb.missing_is_acceptable([5, 7])[0] is False                # 7 was never named and cannot be proven unstorable
    monkeypatch.setattr(rb, "ACCEPTED", set(range(100)))
    assert rb.missing_is_acceptable(list(range(rb.MAX_UNSTORABLE + 1)))[0] is False   # a long list is never accepted


def test_the_backup_is_a_local_file_written_before_the_delete_and_streams_every_row(monkeypatch, tmp_path):
    rows = [("unknown", None, "bushfire", "1.0", None, None, i, "SRID=4326;MULTIPOLYGON(((0 0,1 0,1 1,0 0)))", None) for i in range(5)]

    class Cur2:
        itersize = 0

        def execute(self, sql, args=None):
            assert sql.lstrip().upper().startswith("SELECT") and "FROM spatial_overlays" in sql

        def __iter__(self):
            return iter(rows)

        def close(self):
            pass

    class C:
        def cursor(self, name=None):
            assert name == "bf_backup"
            return Cur2()

    class Cur:
        connection = C()

    monkeypatch.setattr(rb, "BACKUP_DIR", tmp_path)
    path, n = rb.backup_to_file(Cur())
    assert n == 5 and Path(path).exists() and len(Path(path).read_text(encoding="utf-8").splitlines()) == 6   # header + 5 rows


def test_the_swap_never_creates_a_second_copy_of_the_table_in_the_database():
    src = (REPO / "scripts" / "rebuild_bushfire_overlay.py").read_text(encoding="utf-8")
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    assert "CREATE TABLE {backup}" not in code and "CREATE TABLE spatial_overlays_bushfire_backup" not in code
