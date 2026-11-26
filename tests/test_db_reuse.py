"""Unit tests for services/db_reuse.py with no database: a fake pool and fake connections stand in for psycopg2.
One real-database test at the bottom (opt in: PYTEST_REAL_DB=1 DATABASE_URL=... pytest -o addopts= -m database)."""
import os
import threading
import time

import pytest

from services import db_reuse, evidence_council, lmr_area_lga

DSN = "postgresql://fake/db"
REAL_DSN = os.environ.get("DATABASE_URL")   # read before any fixture replaces it: only the opt-in real-database test uses it


class PoolError(Exception):
    pass


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.closed = False

    def execute(self, sql, params=None):
        c = self.conn
        c.executed.append(sql)
        c.events.append(sql)
        if c.fail_execute:
            raise RuntimeError("server closed the connection")
        self._row = (1,)
        if sql.startswith("SET statement_timeout = "):
            c.last_timeout_ms = int(sql.rsplit("=", 1)[1])
        elif sql == "SHOW default_transaction_read_only":
            self._row = (c.read_only,)
        elif sql == "SHOW statement_timeout":
            ms = c.last_timeout_ms
            self._row = (c.timeout_str if c.timeout_str is not None else (f"{ms // 1000}s" if ms % 1000 == 0 else f"{ms}ms"),)

    def fetchone(self):
        return self._row

    def close(self):
        self.closed = True


class FakeConn:
    def __init__(self, fail_execute=False, read_only="on", timeout_str=None):
        self.read_only = read_only          # what SHOW default_transaction_read_only answers
        self.timeout_str = timeout_str      # what SHOW statement_timeout answers (None: derived from the last SET)
        self.last_timeout_ms = 0
        self.commits = 0
        self.events = []                    # SQL and "COMMIT"/"ROLLBACK" in order
        self.closed = 0
        self.autocommit = False
        self.rollbacks = 0
        self.cursors = 0
        self.executed = []
        self.fail_execute = fail_execute
        self.fail_rollback = False
        self.entered = 0
        self.exited = []

    def cursor(self):
        self.cursors += 1
        return FakeCursor(self)

    def commit(self):
        self.commits += 1
        self.events.append("COMMIT")

    def rollback(self):
        self.events.append("ROLLBACK")
        if self.fail_rollback:
            raise RuntimeError("rollback failed")
        self.rollbacks += 1

    def close(self):
        self.closed = 1

    def __enter__(self):
        self.entered += 1
        return self

    def __exit__(self, *exc):
        self.exited.append(exc)
        return False


class FakePool:
    def __init__(self, maxconn=db_reuse.POOL_MAX, factory=FakeConn):
        self.maxconn = maxconn
        self.factory = factory
        self.idle = []
        self.used = []
        self.made = []          # every connection the pool ever created
        self.puts = []          # (conn, close)
        self._lock = threading.Lock()

    def getconn(self):
        with self._lock:
            if self.idle:
                c = self.idle.pop()
            else:
                if len(self.used) >= self.maxconn:
                    raise PoolError("connection pool exhausted")
                c = self.factory()
                self.made.append(c)
            self.used.append(c)
            return c

    def putconn(self, conn, close=False):
        with self._lock:
            self.puts.append((conn, close))
            if conn in self.used:
                self.used.remove(conn)
            if close:
                conn.close()
            elif not conn.closed:
                self.idle.append(conn)


def _reset():
    db_reuse._states.clear()


def selects(c):
    return c.executed.count("SELECT 1")


def meta_of(conn):
    """The bookkeeping dict for a connection object, from whichever pool state holds it (None when none does)."""
    for st in db_reuse._states.values():
        if conn in st.meta:
            return st.meta[conn]
    return None


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", DSN)
    monkeypatch.delenv("DB_REUSE", raising=False)
    _reset()
    yield
    _reset()


@pytest.fixture
def fakes(monkeypatch):
    s = type("S", (), {})()
    s.pools = []
    s.pool_factory = lambda: FakePool()
    s.directs = []
    s.make_pool_error = None
    s.direct_factory = FakeConn

    def make_pool(dsn, ct, st):
        if s.make_pool_error:
            raise s.make_pool_error
        p = s.pool_factory()
        p.args = (dsn, ct, st)
        s.pools.append(p)
        return p

    def direct(dsn, ct, st):
        c = s.direct_factory()      # same contract as the real _direct: configure and verify, or close and raise
        c.args = (dsn, ct, st)
        s.directs.append(c)
        try:
            db_reuse._configure(c, st)
        except Exception:
            c.close()
            raise
        return c

    monkeypatch.setattr(db_reuse, "_make_pool", make_pool)
    monkeypatch.setattr(db_reuse, "_direct", direct)
    return s


def under(lease):
    return object.__getattribute__(lease, "_conn")


def test_no_database_url_returns_none(fakes, monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    assert db_reuse.connect(3, 3000) is None
    assert fakes.pools == [] and fakes.directs == []


def test_empty_database_url_returns_none(fakes, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "")
    assert db_reuse.connect(3, 3000) is None


def test_reuse_off_gives_direct_connection_and_never_makes_pool(fakes, monkeypatch):
    monkeypatch.setenv("DB_REUSE", "0")
    c = db_reuse.connect(3, 3000)
    assert c is fakes.directs[0] and not isinstance(c, db_reuse._Lease)
    assert c.args == (DSN, 3, 3000)
    assert fakes.pools == []
    c.close()
    assert c.closed == 1


def test_reuse_other_value_still_pools(fakes, monkeypatch):
    monkeypatch.setenv("DB_REUSE", "1")
    c = db_reuse.connect(3, 3000)
    assert isinstance(c, db_reuse._Lease) and len(fakes.pools) == 1 and fakes.directs == []


def test_pool_made_with_the_callers_settings(fakes):
    db_reuse.connect(7, 4242)
    assert fakes.pools[0].args == (DSN, 7, 4242)


def test_second_connect_after_close_reuses_same_connection(fakes):
    a = db_reuse.connect(3, 3000)
    ua = under(a)
    a.close()
    b = db_reuse.connect(3, 3000)
    assert under(b) is ua
    pool = fakes.pools[0]
    assert len(fakes.pools) == 1 and len(pool.made) == 1
    assert fakes.directs == []
    assert ua.closed == 0


def test_second_connect_without_close_gets_a_different_connection(fakes):
    a = db_reuse.connect(3, 3000)
    b = db_reuse.connect(3, 3000)
    assert under(a) is not under(b)
    assert len(fakes.pools[0].made) == 2


def test_close_rolls_back_and_returns_once_and_is_idempotent(fakes):
    lease = db_reuse.connect(3, 3000)
    conn, pool = under(lease), fakes.pools[0]
    r0 = conn.rollbacks          # the first-use SELECT 1 check rolls back once itself
    lease.close()
    assert conn.rollbacks == r0 + 1
    assert pool.puts == [(conn, False)]
    assert conn.closed == 0
    lease.close()
    lease.close()
    assert conn.rollbacks == r0 + 1 and len(pool.puts) == 1
    assert meta_of(conn)["last"] is not None


def test_close_records_last_used_time(fakes):
    lease = db_reuse.connect(3, 3000)
    conn = under(lease)
    before = time.monotonic()
    lease.close()
    assert before <= meta_of(conn)["last"] <= time.monotonic()


def test_autocommit_passes_through_and_is_reset_on_close(fakes):
    lease = db_reuse.connect(3, 3000)
    conn = under(lease)
    lease.autocommit = True
    assert conn.autocommit is True and lease.autocommit is True
    lease.close()
    assert conn.autocommit is False
    nxt = db_reuse.connect(3, 3000)
    assert under(nxt) is conn and nxt.autocommit is False


def test_attribute_passthrough(fakes):
    lease = db_reuse.connect(3, 3000)
    conn = under(lease)
    c0, r0 = conn.cursors, conn.rollbacks
    cur = lease.cursor()
    assert isinstance(cur, FakeCursor) and cur.conn is conn and conn.cursors == c0 + 1
    lease.rollback()
    assert conn.rollbacks == r0 + 1
    conn.marker = "x"
    assert lease.marker == "x"
    with pytest.raises(AttributeError):
        lease.no_such_attribute
    lease.some_new = 5          # a set goes to the connection, not the lease
    assert conn.some_new == 5 and "some_new" not in vars(lease)


def test_context_manager_forwards_to_connection(fakes):
    lease = db_reuse.connect(3, 3000)
    conn = under(lease)
    with lease as got:
        assert got is lease
        assert conn.entered == 1
    assert len(conn.exited) == 1 and conn.exited[0] == (None, None, None)
    assert conn.closed == 0


def test_context_manager_forwards_exception(fakes):
    lease = db_reuse.connect(3, 3000)
    conn = under(lease)
    with pytest.raises(ValueError):
        with lease:
            raise ValueError("boom")
    assert conn.exited[0][0] is ValueError


def test_recently_used_connection_is_not_checked(fakes):
    a = db_reuse.connect(3, 3000)
    conn = under(a)
    a.close()
    cursors_before = conn.cursors
    b = db_reuse.connect(3, 3000)
    assert under(b) is conn
    assert conn.cursors == cursors_before
    assert selects(conn) == 1       # only the first-ever check (new connection), none on reuse


def test_idle_connection_is_checked_with_select_1(fakes):
    a = db_reuse.connect(3, 3000)
    conn = under(a)
    a.close()
    meta_of(conn)["last"] = time.monotonic() - (db_reuse.RECENT_S + 5)
    executed_before = list(conn.executed)
    b = db_reuse.connect(3, 3000)
    assert under(b) is conn
    assert conn.executed == executed_before + ["SELECT 1"]
    assert fakes.pools[0].puts[-1][1] is False        # kept, not discarded


def test_recent_window_boundary(fakes, monkeypatch):
    a = db_reuse.connect(3, 3000)
    conn = under(a)
    a.close()
    n = len(conn.executed)
    t0 = meta_of(conn)["last"]
    monkeypatch.setattr(db_reuse.time, "monotonic", lambda: t0 + db_reuse.RECENT_S - 0.5)
    b = db_reuse.connect(3, 3000)
    assert len(conn.executed) == n and under(b) is conn
    b.close()
    t1 = meta_of(conn)["last"]
    monkeypatch.setattr(db_reuse.time, "monotonic", lambda: t1 + db_reuse.RECENT_S + 0.5)
    db_reuse.connect(3, 3000)
    assert len(conn.executed) == n + 1


def test_unknown_connection_is_checked(fakes):
    """A connection with no last-used record (new from the pool) is verified, not trusted."""
    db_reuse.connect(3, 3000)
    assert selects(fakes.pools[0].made[0]) == 1


def test_closed_connection_is_discarded_and_replaced(fakes):
    a = db_reuse.connect(3, 3000)
    conn = under(a)
    a.close()
    conn.closed = 2                       # the database dropped it while idle
    pool = fakes.pools[0]
    b = db_reuse.connect(3, 3000)
    assert under(b) is not conn
    assert (conn, True) in pool.puts
    assert meta_of(conn) is None
    assert fakes.directs == []
    assert len(pool.made) == 2


def test_closed_connection_is_not_sent_select_1(fakes):
    a = db_reuse.connect(3, 3000)
    conn = under(a)
    a.close()
    conn.closed = 2
    n = len(conn.executed)
    db_reuse.connect(3, 3000)
    assert len(conn.executed) == n


def test_connection_whose_select_1_fails_is_discarded_and_replaced(fakes):
    a = db_reuse.connect(3, 3000)
    conn = under(a)
    a.close()
    meta_of(conn)["last"] = time.monotonic() - 1000
    conn.fail_execute = True
    b = db_reuse.connect(3, 3000)
    assert under(b) is not conn
    assert (conn, True) in fakes.pools[0].puts and conn.closed == 1
    assert meta_of(conn) is None
    assert fakes.directs == []


def test_two_stale_in_a_row_fall_to_direct_connection(fakes):
    fakes.pool_factory = lambda: FakePool(factory=lambda: FakeConn(fail_execute=True))
    c = db_reuse.connect(3, 3000)
    assert c is fakes.directs[0] and not isinstance(c, db_reuse._Lease)
    pool = fakes.pools[0]
    assert len(pool.made) == 2
    assert [close for _c, close in pool.puts] == [True, True]
    assert all(m.closed == 1 for m in pool.made)
    c.close()
    assert c.closed == 1


def test_pool_exhausted_gives_a_direct_connection_that_really_closes(fakes):
    fakes.pool_factory = lambda: FakePool(maxconn=2)
    held = [db_reuse.connect(3, 3000), db_reuse.connect(3, 3000)]
    c = db_reuse.connect(3, 3000)
    assert c is fakes.directs[0] and not isinstance(c, db_reuse._Lease)
    assert c.args == (DSN, 3, 3000)
    c.close()
    assert c.closed == 1
    assert len(fakes.pools[0].made) == 2
    for h in held:
        h.close()
    assert all(m.closed == 0 for m in fakes.pools[0].made)


def test_pool_creation_failure_gives_a_direct_connection(fakes):
    fakes.make_pool_error = RuntimeError("cannot connect")
    c = db_reuse.connect(3, 3000)
    assert c is fakes.directs[0] and not isinstance(c, db_reuse._Lease)
    assert fakes.pools == []
    c.close()
    assert c.closed == 1


def test_rollback_failure_on_close_closes_the_connection(fakes):
    lease = db_reuse.connect(3, 3000)
    conn = under(lease)
    meta_of(conn)["last"] = time.monotonic()
    conn.fail_rollback = True
    lease.close()
    assert fakes.pools[0].puts == [(conn, True)]
    assert conn.closed == 1
    assert meta_of(conn) is None
    nxt = db_reuse.connect(3, 3000)
    assert under(nxt) is not conn


def test_putconn_failure_on_close_does_not_raise(fakes):
    lease = db_reuse.connect(3, 3000)

    def boom(conn, close=False):
        raise RuntimeError("pool gone")

    fakes.pools[0].putconn = boom
    lease.close()          # must not raise
    lease.close()


def test_different_settings_make_a_new_pool(fakes):
    db_reuse.connect(3, 3000).close()
    db_reuse.connect(3, 3000).close()
    assert len(fakes.pools) == 1
    db_reuse.connect(3, 8000).close()
    assert len(fakes.pools) == 2 and fakes.pools[1].args == (DSN, 3, 8000)
    db_reuse.connect(5, 8000).close()
    assert len(fakes.pools) == 3 and fakes.pools[2].args == (DSN, 5, 8000)


def test_different_dsn_makes_a_new_pool(fakes, monkeypatch):
    db_reuse.connect(3, 3000).close()
    monkeypatch.setenv("DATABASE_URL", "postgresql://other/db")
    db_reuse.connect(3, 3000)
    assert len(fakes.pools) == 2 and fakes.pools[1].args[0] == "postgresql://other/db"


def test_changing_settings_keeps_old_connection_bookkeeping_in_the_old_state_only(fakes):
    a = db_reuse.connect(3, 3000)
    conn = under(a)
    a.close()
    old_state = db_reuse._states[(DSN, 3, 3000, os.getpid())]
    db_reuse.connect(3, 8000)
    new_state = db_reuse._states[(DSN, 3, 8000, os.getpid())]
    assert conn in old_state.meta and old_state.meta[conn]["last"] is not None
    assert conn not in new_state.meta


def test_different_process_makes_a_new_pool(fakes, monkeypatch):
    db_reuse.connect(3, 3000).close()
    assert len(fakes.pools) == 1
    monkeypatch.setattr(os, "getpid", lambda: 987654)
    db_reuse.connect(3, 3000)
    assert len(fakes.pools) == 2
    db_reuse.connect(3, 3000)
    assert len(fakes.pools) == 2   # and then it is stable in the new process


def test_eight_threads_get_distinct_connections_and_all_return(fakes):
    n = 8
    barrier = threading.Barrier(n)
    leases, errors = [], []
    lock = threading.Lock()

    def work():
        try:
            lease = db_reuse.connect(3, 3000)
            with lock:
                leases.append(lease)
            barrier.wait(timeout=10)       # all eight hold a connection at the same time
            lease.cursor()
            lease.close()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    ts = [threading.Thread(target=work) for _ in range(n)]
    [t.start() for t in ts]
    [t.join(timeout=20) for t in ts]
    assert errors == []
    assert len(leases) == n and all(isinstance(x, db_reuse._Lease) for x in leases)
    assert len({id(under(x)) for x in leases}) == n
    pool = fakes.pools[0]
    assert len(fakes.pools) == 1 and len(pool.made) == n and fakes.directs == []
    assert len(pool.puts) == n and pool.used == [] and len(pool.idle) == n
    assert all(close is False for _c, close in pool.puts)


def test_pool_max_plus_one_concurrent_is_direct(fakes):
    held = [db_reuse.connect(3, 3000) for _ in range(db_reuse.POOL_MAX)]
    assert all(isinstance(h, db_reuse._Lease) for h in held)
    extra = db_reuse.connect(3, 3000)
    assert not isinstance(extra, db_reuse._Lease) and len(fakes.directs) == 1


@pytest.mark.parametrize("mod", [lmr_area_lga, evidence_council])
def test_stage_connect_delegates_to_db_reuse(mod, monkeypatch):
    seen = []
    sentinel = object()
    monkeypatch.setattr(db_reuse, "connect", lambda ct, st: seen.append((ct, st)) or sentinel)
    assert mod._connect() is sentinel
    assert seen == [(mod.CONNECT_TIMEOUT_S, mod.STATEMENT_TIMEOUT_MS)]


def test_stages_pass_their_own_distinct_timeouts(monkeypatch):
    seen = []
    monkeypatch.setattr(db_reuse, "connect", lambda ct, st: seen.append((ct, st)))
    lmr_area_lga._connect()
    evidence_council._connect()
    assert seen[0] == (3, 3000) and seen[1] == (3, 8000)


def test_stage_connect_returns_none_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    assert lmr_area_lga._connect() is None and evidence_council._connect() is None


# -- real database (opt in) ---------------------------------------------------

@pytest.mark.database
def test_real_connections_are_reused_read_only_with_the_timeout_and_no_open_transaction(monkeypatch):
    if os.environ.get("PYTEST_REAL_DB") != "1" or not REAL_DSN:
        pytest.skip("real database test: run with PYTEST_REAL_DB=1 DATABASE_URL=... pytest -o addopts= -m database")
    import psycopg2
    import psycopg2.errors
    import psycopg2.extensions as ext

    monkeypatch.setenv("DATABASE_URL", REAL_DSN)
    a = db_reuse.connect(10, 4000)
    assert isinstance(a, db_reuse._Lease)
    cur = a.cursor()
    cur.execute("SELECT pg_backend_pid()")
    pid_a = cur.fetchone()[0]
    cur.execute("SHOW default_transaction_read_only")
    assert cur.fetchone()[0] == "on"
    cur.execute("SHOW statement_timeout")
    assert cur.fetchone()[0] == "4s"
    under_a = under(a)
    assert under_a.status == ext.STATUS_IN_TRANSACTION     # the read left a transaction open ...
    a.close()
    assert under_a.status == ext.STATUS_READY               # ... and close() rolled it back
    assert under_a.closed == 0

    b = db_reuse.connect(10, 4000)
    assert under(b) is under_a
    cur = b.cursor()
    cur.execute("SELECT pg_backend_pid()")
    assert cur.fetchone()[0] == pid_a
    cur.execute("SHOW default_transaction_read_only")
    assert cur.fetchone()[0] == "on"
    cur.execute("SHOW statement_timeout")
    assert cur.fetchone()[0] == "4s"
    with pytest.raises(psycopg2.errors.ReadOnlySqlTransaction):
        cur.execute("CREATE TABLE _db_reuse_should_fail (x int)")
    b.rollback()
    b.autocommit = True
    b.close()
    assert under_a.autocommit is False and under_a.status == ext.STATUS_READY

    c = db_reuse.connect(10, 4000)
    cur = c.cursor()
    cur.execute("SELECT pg_backend_pid()")
    assert cur.fetchone()[0] == pid_a
    c.close()


# -- read-only configuration ----------------------------------------------------

SETS = ["SET default_transaction_read_only = on", "SET statement_timeout = 3000"]


def test_new_pooled_connection_is_configured_with_exact_sql_and_commit_before_show(fakes):
    lease = db_reuse.connect(3, 3000)
    conn = under(lease)
    ev = conn.events
    i = ev.index(SETS[0])
    assert ev[i:i + 6] == [SETS[0], SETS[1], "COMMIT", "SHOW default_transaction_read_only", "SHOW statement_timeout", "ROLLBACK"]
    assert conn.commits == 1 and conn.last_timeout_ms == 3000
    assert meta_of(conn)["configured"] is True


def test_timeout_set_is_the_one_passed(fakes):
    conn = under(db_reuse.connect(3, 8000))
    assert "SET statement_timeout = 8000" in conn.executed and conn.last_timeout_ms == 8000


def test_pooled_connection_is_configured_exactly_once(fakes):
    a = db_reuse.connect(3, 3000)
    conn = under(a)
    a.close()
    for _ in range(3):
        x = db_reuse.connect(3, 3000)
        assert under(x) is conn
        x.close()
    assert conn.commits == 1
    assert conn.executed.count(SETS[0]) == 1 and conn.executed.count(SETS[1]) == 1
    assert conn.executed.count("SHOW default_transaction_read_only") == 1


def test_idle_recheck_does_not_reconfigure(fakes):
    a = db_reuse.connect(3, 3000)
    conn = under(a)
    a.close()
    meta_of(conn)["last"] = time.monotonic() - 1000
    db_reuse.connect(3, 3000)
    assert selects(conn) == 2 and conn.executed.count(SETS[0]) == 1


def test_each_new_connection_is_configured(fakes):
    a = db_reuse.connect(3, 3000)
    b = db_reuse.connect(3, 3000)
    for lease in (a, b):
        assert under(lease).executed.count(SETS[0]) == 1 and meta_of(under(lease))["configured"] is True


def test_pooled_connection_not_read_only_is_never_handed_out(fakes):
    fakes.pool_factory = lambda: FakePool(factory=lambda: FakeConn(read_only="off"))
    c = db_reuse.connect(3, 3000)         # the direct one is healthy
    assert c is fakes.directs[0] and not isinstance(c, db_reuse._Lease) and c.closed == 0
    pool = fakes.pools[0]
    assert len(pool.made) == 2 and [close for _c, close in pool.puts] == [True, True]
    assert all(m.closed == 1 for m in pool.made)
    assert all(not st.meta for st in db_reuse._states.values())


def test_refused_everywhere_raises_and_closes_the_direct_connection(fakes):
    fakes.pool_factory = lambda: FakePool(factory=lambda: FakeConn(read_only="off"))
    fakes.direct_factory = lambda: FakeConn(read_only="off")
    with pytest.raises(RuntimeError):
        db_reuse.connect(3, 3000)
    assert len(fakes.directs) == 1 and fakes.directs[0].closed == 1
    assert all(m.closed == 1 for m in fakes.pools[0].made)
    assert fakes.pools[0].idle == [] and fakes.pools[0].used == []


def test_timeout_mismatch_is_refused(fakes):
    fakes.pool_factory = lambda: FakePool(factory=lambda: FakeConn(timeout_str="0"))
    fakes.direct_factory = lambda: FakeConn(timeout_str="30s")
    with pytest.raises(RuntimeError):
        db_reuse.connect(3, 3000)
    assert fakes.directs[0].closed == 1 and all(m.closed == 1 for m in fakes.pools[0].made)


@pytest.mark.parametrize("ms,shown", [(3000, "3s"), (3000, "3000ms"), (3500, "3500ms"), (8000, "8s"), (1, "1ms")])
def test_accepted_timeout_forms(fakes, ms, shown):
    fakes.pool_factory = lambda: FakePool(factory=lambda: FakeConn(timeout_str=shown))
    lease = db_reuse.connect(3, ms)
    assert isinstance(lease, db_reuse._Lease) and fakes.directs == []


@pytest.mark.parametrize("ms,shown", [(3500, "3s"), (3000, "3500ms"), (3000, "4s"), (3000, "3")])
def test_rejected_timeout_forms(ms, shown):
    with pytest.raises(RuntimeError):
        db_reuse._configure(FakeConn(timeout_str=shown), ms)


def test_empty_timeout_is_rejected_for_non_whole_second():
    with pytest.raises(RuntimeError):
        db_reuse._configure(FakeConn(timeout_str=""), 3500)


@pytest.mark.parametrize("value", ["off", "", "ON ", "true"])
def test_read_only_value_must_be_exactly_on(value):
    with pytest.raises(RuntimeError):
        db_reuse._configure(FakeConn(read_only=value), 3000)


def test_configure_accepts_a_good_session():
    c = FakeConn()
    db_reuse._configure(c, 3000)
    assert c.commits == 1 and c.rollbacks == 1


def test_reuse_off_path_configures_and_verifies(fakes, monkeypatch):
    monkeypatch.setenv("DB_REUSE", "0")
    c = db_reuse.connect(3, 3000)
    assert c is fakes.directs[0] and c.executed.count(SETS[0]) == 1 and c.commits == 1
    assert "SHOW default_transaction_read_only" in c.executed
    assert fakes.pools == []


def test_reuse_off_path_refuses_a_session_that_is_not_read_only(fakes, monkeypatch):
    monkeypatch.setenv("DB_REUSE", "0")
    fakes.direct_factory = lambda: FakeConn(read_only="off")
    with pytest.raises(RuntimeError):
        db_reuse.connect(3, 3000)
    assert fakes.directs[0].closed == 1 and fakes.pools == []


def test_a_connection_configured_for_one_pool_is_not_configured_for_another(fakes):
    a = db_reuse.connect(3, 3000)
    ca = under(a)
    a.close()
    b = db_reuse.connect(3, 8000)
    cb = under(b)
    assert cb is not ca
    assert cb.executed.count("SET statement_timeout = 8000") == 1 and cb.last_timeout_ms == 8000
    assert ca.last_timeout_ms == 3000
    assert ca not in db_reuse._states[(DSN, 3, 8000, os.getpid())].meta


def test_configured_forgotten_when_connection_is_discarded(fakes):
    a = db_reuse.connect(3, 3000)
    conn = under(a)
    a.close()
    meta_of(conn)["last"] = time.monotonic() - 1000
    conn.fail_execute = True
    db_reuse.connect(3, 3000)
    assert meta_of(conn) is None


def test_configured_forgotten_when_reset_fails_on_close(fakes):
    a = db_reuse.connect(3, 3000)
    conn = under(a)
    assert meta_of(conn)["configured"] is True
    conn.fail_rollback = True
    a.close()
    assert meta_of(conn) is None


def test_configure_failure_on_a_pooled_connection_discards_it_and_tries_again(fakes):
    made = []

    def factory():
        c = FakeConn(read_only="off" if not made else "on")
        made.append(c)
        return c

    fakes.pool_factory = lambda: FakePool(factory=factory)
    lease = db_reuse.connect(3, 3000)
    assert isinstance(lease, db_reuse._Lease) and under(lease) is made[1]
    assert made[0].closed == 1 and meta_of(made[0]) is None and fakes.directs == []


# ---- psycopg2's own pool class, with a fake connection: the fakes above cannot show whether the real pool KEEPS a returned connection ----
class _Info:
    transaction_status = 0   # psycopg2.extensions.TRANSACTION_STATUS_IDLE


class _RealPoolConn:
    def __init__(self):
        self.closed = 0
        self.info = _Info()
        self.rollbacks = 0

    def close(self):
        self.closed = 1

    def rollback(self):
        self.rollbacks += 1


def test_the_real_psycopg2_pool_keeps_returned_connections_so_the_next_stage_gets_the_same_one(monkeypatch):
    """psycopg2 closes a returned connection unless fewer than minconn are idle: with minconn 0 nothing was ever reused (found on the real database 2026-11-26)."""
    import psycopg2

    try:
        import psycopg2.pool  # noqa: F401
    except ImportError:
        pytest.skip("psycopg2 is stubbed in this run (tests/conftest_mocks.py): run with PYTEST_REAL_DB=1 to use the real driver")
    made = []

    def fake_connect(*a, **k):
        c = _RealPoolConn()
        made.append(c)
        return c

    monkeypatch.setattr(psycopg2, "connect", fake_connect)
    pool = db_reuse._make_pool("postgresql://fake/db", 3, 3000)
    assert len(made) == 1                      # one connection opened when the pool is made, not eight
    first = pool.getconn()
    pool.putconn(first)
    assert first.closed == 0                   # kept, not closed
    assert pool.getconn() is first and len(made) == 1
    taken = [first] + [pool.getconn() for _ in range(db_reuse.POOL_MAX - 1)]
    assert len({id(c) for c in taken}) == db_reuse.POOL_MAX
    for c in taken:
        pool.putconn(c)
    assert all(c.closed == 0 for c in taken)   # up to POOL_MAX are kept for later stages


@pytest.mark.parametrize("bad", [None, 0, -5, True, "3000", 3.5])
def test_a_statement_timeout_that_is_not_a_positive_whole_number_is_refused_before_anything_is_sent(bad):
    conn = FakeConn()
    with pytest.raises(ValueError):
        db_reuse._configure(conn, bad)
    assert conn.events == [] and conn.cursors == 0   # no SQL was issued and no cursor was opened


# -- pool states, closed leases, per-connection bookkeeping --------------------------------

def test_two_callers_with_different_timeouts_alternating_make_exactly_two_pools(fakes):
    for _ in range(10):
        a = db_reuse.connect(3, 3000)
        a.close()
        b = db_reuse.connect(3, 8000)
        b.close()
    assert len(fakes.pools) == 2
    assert [p.args for p in fakes.pools] == [(DSN, 3, 3000), (DSN, 3, 8000)]
    assert [len(p.made) for p in fakes.pools] == [1, 1]            # each pool made one connection and reused it 10 times
    assert all(close is False for p in fakes.pools for _c, close in p.puts) and [len(p.puts) for p in fakes.pools] == [10, 10]
    assert len(db_reuse._states) == 2
    assert {st.statement_timeout_ms: st.pool for st in db_reuse._states.values()} == {3000: fakes.pools[0], 8000: fakes.pools[1]}
    assert fakes.pools[0].made[0].last_timeout_ms == 3000 and fakes.pools[1].made[0].last_timeout_ms == 8000
    assert fakes.directs == []


def test_get_state_returns_the_same_state_for_the_same_key_and_a_new_one_for_another(fakes):
    s1 = db_reuse._get_state(DSN, 3, 3000)
    assert db_reuse._get_state(DSN, 3, 3000) is s1
    s2 = db_reuse._get_state(DSN, 3, 8000)
    assert s2 is not s1 and s2.pool is not s1.pool and s2.statement_timeout_ms == 8000
    assert len(fakes.pools) == 2


def _snapshot(c):
    return (c.cursors, c.rollbacks, c.commits, list(c.events), c.autocommit, c.entered, list(c.exited), c.closed)


@pytest.mark.parametrize("fail_rollback", [False, True])
def test_a_closed_lease_refuses_every_use_and_does_not_touch_the_connection(fakes, fail_rollback):
    lease = db_reuse.connect(3, 3000)
    conn = under(lease)
    pool = fakes.pools[0]
    conn.fail_rollback = fail_rollback
    lease.close()
    assert pool.puts == [(conn, fail_rollback)]                     # discarded when the reset failed, kept otherwise
    before = _snapshot(conn)
    assert issubclass(db_reuse.ClosedLeaseError, RuntimeError)
    with pytest.raises(db_reuse.ClosedLeaseError):
        lease.cursor()
    with pytest.raises(db_reuse.ClosedLeaseError):
        lease.rollback()
    with pytest.raises(db_reuse.ClosedLeaseError):
        lease.commit()
    with pytest.raises(db_reuse.ClosedLeaseError):
        lease.autocommit
    with pytest.raises(db_reuse.ClosedLeaseError):
        lease.autocommit = True
    with pytest.raises(db_reuse.ClosedLeaseError):
        lease.anything_else = 1
    with pytest.raises(db_reuse.ClosedLeaseError):
        with lease:
            pass
    assert _snapshot(conn) == before
    assert not hasattr(conn, "anything_else")
    lease.close()
    lease.close()
    assert pool.puts == [(conn, fail_rollback)]                     # put back (or discarded) exactly once


def test_closed_lease_use_does_not_reach_the_next_holder_of_the_same_connection(fakes):
    a = db_reuse.connect(3, 3000)
    conn = under(a)
    a.close()
    b = db_reuse.connect(3, 3000)
    assert under(b) is conn
    n = conn.cursors
    with pytest.raises(db_reuse.ClosedLeaseError):
        a.cursor()
    assert conn.cursors == n
    assert b.cursor().conn is conn                                  # the new holder is unaffected


def test_close_marks_the_lease_closed_before_resetting_the_connection(fakes):
    lease = db_reuse.connect(3, 3000)
    conn = under(lease)
    seen = []
    real_rollback = conn.rollback

    def rollback():
        try:
            lease.cursor()
        except db_reuse.ClosedLeaseError:
            seen.append("closed")
        real_rollback()

    conn.rollback = rollback
    lease.close()
    assert seen == ["closed"]


def test_meta_is_keyed_by_the_connection_object(fakes):
    lease = db_reuse.connect(3, 3000)
    conn = under(lease)
    state = db_reuse._states[(DSN, 3, 3000, os.getpid())]
    assert list(state.meta) == [conn] and list(state.meta)[0] is conn
    assert not any(isinstance(k, int) for k in state.meta)
    assert state.meta[conn] == {"configured": True, "last": None}   # checked out: configured, not yet handed back
    lease.close()
    assert state.meta[conn]["configured"] is True and state.meta[conn]["last"] is not None


def test_a_discarded_connection_loses_its_meta(fakes):
    lease = db_reuse.connect(3, 3000)
    conn = under(lease)
    state = db_reuse._states[(DSN, 3, 3000, os.getpid())]
    assert conn in state.meta
    state.discard(conn)
    assert conn not in state.meta and (conn, True) in fakes.pools[0].puts and conn.closed == 1


def test_a_new_connection_is_always_configured_whatever_the_bookkeeping_says_about_another(fakes):
    old, fresh = FakeConn(), FakeConn()
    fakes.pool_factory = lambda: FakePool(factory=lambda: fresh)
    state = db_reuse._get_state(DSN, 3, 3000)
    state.meta[old] = {"configured": True, "last": time.monotonic()}   # an earlier connection, already set up
    lease = db_reuse.connect(3, 3000)
    assert under(lease) is fresh
    assert fresh.executed.count(SETS[0]) == 1 and fresh.commits == 1
    assert state.meta[fresh]["configured"] is True
    assert state.meta[old]["configured"] is True and old.executed == []   # the other one is untouched


def test_a_connection_with_no_meta_is_checked_and_configured(fakes):
    state = db_reuse._get_state(DSN, 3, 3000)
    conn = FakeConn()
    state.pool.idle.append(conn)
    lease = db_reuse.connect(3, 3000)
    assert under(lease) is conn and selects(conn) == 1 and conn.executed.count(SETS[0]) == 1


def test_a_connection_discarded_from_one_state_never_appears_in_another(fakes):
    a = db_reuse.connect(3, 3000)
    conn = under(a)
    a.close()
    meta_of(conn)["last"] = time.monotonic() - 1000
    conn.fail_execute = True
    b = db_reuse.connect(3, 3000)                                   # conn fails its check: discarded from the 3000 state
    assert under(b) is not conn
    c = db_reuse.connect(3, 8000)                                   # another state
    s3000 = db_reuse._states[(DSN, 3, 3000, os.getpid())]
    s8000 = db_reuse._states[(DSN, 3, 8000, os.getpid())]
    assert conn not in s3000.meta and conn not in s8000.meta and meta_of(conn) is None
    assert set(s3000.meta) == {under(b)} and set(s8000.meta) == {under(c)}
    assert set(s3000.meta) <= set(fakes.pools[0].made) and set(s8000.meta) <= set(fakes.pools[1].made)


def test_a_different_pid_makes_a_new_state_and_leaves_the_old_one_untouched(fakes, monkeypatch):
    pid = os.getpid()
    a = db_reuse.connect(3, 3000)
    conn = under(a)
    a.close()
    old_state = db_reuse._states[(DSN, 3, 3000, pid)]
    snap = {k: dict(v) for k, v in old_state.meta.items()}
    puts, made = list(old_state.pool.puts), list(old_state.pool.made)
    ev = list(conn.events)
    monkeypatch.setattr(os, "getpid", lambda: pid + 1)
    child = db_reuse.connect(3, 3000)
    new_state = db_reuse._states[(DSN, 3, 3000, pid + 1)]
    assert new_state is not old_state and new_state.pool is not old_state.pool and len(fakes.pools) == 2
    assert under(child) is not conn
    assert db_reuse._states[(DSN, 3, 3000, pid)] is old_state
    assert old_state.meta == snap and old_state.pool.puts == puts and old_state.pool.made == made and conn.events == ev
    assert conn not in new_state.meta and under(child) in new_state.meta
    child.close()
    monkeypatch.setattr(os, "getpid", lambda: pid)
    again = db_reuse.connect(3, 3000)
    assert under(again) is conn and len(fakes.pools) == 2           # back in the parent: its own pool and connection


def test_checkout_failure_in_configure_discards_the_connection_and_its_meta(fakes):
    fakes.pool_factory = lambda: FakePool(factory=lambda: FakeConn(read_only="off"))
    state = db_reuse._get_state(DSN, 3, 3000)
    with pytest.raises(RuntimeError):
        state.checkout()
    assert state.meta == {} and len(state.pool.puts) == 1 and state.pool.puts[0][1] is True and state.pool.puts[0][0].closed == 1


def test_checkout_failure_when_not_usable_discards_the_connection(fakes):
    state = db_reuse._get_state(DSN, 3, 3000)
    conn = FakeConn()
    conn.closed = 2
    state.pool.idle.append(conn)
    with pytest.raises(RuntimeError):
        state.checkout()
    assert state.pool.puts == [(conn, True)] and conn not in state.meta and conn.executed == []


def test_a_cursor_taken_from_a_lease_is_closed_when_the_lease_closes_so_it_cannot_reach_a_connection_lent_to_another_stage(fakes):
    first = db_reuse.connect(3, 3000)
    cur = first.cursor()
    assert cur.closed is False
    first.close()
    assert cur.closed is True
    second = db_reuse.connect(3, 3000)
    assert object.__getattribute__(second, "_conn") is object.__getattribute__(first, "_conn")   # the same connection, now lent to the next stage
    assert second.cursor().closed is False


def test_a_cursor_that_will_not_close_means_the_connection_is_closed_not_returned_to_the_pool(fakes, monkeypatch):
    lease = db_reuse.connect(3, 3000)
    cur = lease.cursor()
    monkeypatch.setattr(cur, "close", lambda: (_ for _ in ()).throw(RuntimeError("will not close")), raising=False)
    conn = object.__getattribute__(lease, "_conn")
    lease.close()
    assert fakes.pools[0].puts[-1] == (conn, True)      # discarded (closed), never returned for the next stage to use
    assert conn not in db_reuse._states[next(iter(db_reuse._states))].meta


def test_a_discard_the_pool_cannot_complete_closes_the_connection_itself(fakes, monkeypatch):
    lease = db_reuse.connect(3, 3000)
    conn = object.__getattribute__(lease, "_conn")
    state = object.__getattribute__(lease, "_state")
    monkeypatch.setattr(state.pool, "putconn", lambda c, close=False: (_ for _ in ()).throw(RuntimeError("pool broken")))
    closed = []
    monkeypatch.setattr(conn, "close", lambda: closed.append(True), raising=False)
    state.discard(conn)
    assert closed == [True] and conn not in state.meta
