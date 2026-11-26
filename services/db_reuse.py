# prior-art-checked: 2026-11-26. A grep of services/ and scripts/ for "ThreadedConnectionPool", "SimpleConnectionPool" and "pool" finds none for the area check or the evidence call: services/lmr_area_lga.py and
# services/evidence_council.py each open (and close) a fresh read-only connection per stage, and the evidence call makes five to seven of them. The stage timings in the service log (2026-11-26) put 3 of the 5
# seconds of a normal call in those stages, and a new connection from the service to the database costs most of a second. Plans: ce-layers-own-copy-SHIP-SCOPE-2026-11-25.md (the evidence call's remaining cost).
"""Reuse read-only database connections for the area check and the evidence call.

A stage calls connect() exactly where it used to call psycopg2.connect(), and close() exactly where it used to close: close() hands the connection back to a small pool instead of ending it, so the next
stage (and the next request) skips the connection set-up. The stage's connection is the same read-only, short-timeout connection it always was, and once it has called close() it can no longer be used.

Read-only and the statement timeout are set with SET commands after connecting and then checked with SHOW. Passing them as connection options (what the stages did before) does nothing through the Supabase
pooler: measured 2026-11-26, a connection made that way as the service's database role was read-write with a 30-minute statement timeout. If the SETs do not take effect the connection is refused, never used.

Design:
  * one pool per (database, connect timeout, statement timeout, process): the two callers ask for different statement timeouts and each keeps its own pool; a forked process never uses its parent's pool;
  * what is known about each pooled connection (set up already, when last used) is kept with the pool, keyed by the connection object itself, so it can never be attached to a different connection;
  * a connection that sat idle for a while is checked with SELECT 1 when it is taken from the pool; one the database has dropped is thrown away and a new one is made;
  * a connection is rolled back when it comes back (a read leaves a transaction open) and its autocommit setting is reset, so one stage cannot affect the next;
  * if every pooled connection is in use, or the pool cannot be made, the stage gets an ordinary connection that really closes, exactly as before;
  * DB_REUSE=0 turns the pool off (every stage gets an ordinary connection, still made read-only and checked).
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

POOL_MAX = 8            # noqa: regulatory-number -- engineering limit on pooled connections per pool (the area check runs at most four stages at once), not a planning figure
RECENT_S = 20.0         # noqa: regulatory-number -- a connection used this recently is trusted without a SELECT 1 (the database's idle limits are minutes), not a planning figure

_lock = threading.Lock()
_states: dict[tuple, "_PoolState"] = {}


class ClosedLeaseError(RuntimeError):
    """A stage used its connection after calling close()."""


def _options(statement_timeout_ms: int) -> str:
    return f"-c statement_timeout={statement_timeout_ms} -c default_transaction_read_only=on"


def _configure(conn: Any, statement_timeout_ms: int) -> None:
    """Make the session read-only with the statement timeout, then prove it. Raises if the database does not report both: a connection that is not read-only is never handed out."""
    if not isinstance(statement_timeout_ms, int) or isinstance(statement_timeout_ms, bool) or statement_timeout_ms <= 0:
        raise ValueError(f"the statement timeout must be a positive whole number of milliseconds, got {statement_timeout_ms!r}")
    cur = conn.cursor()
    cur.execute("SET default_transaction_read_only = on")
    cur.execute("SET statement_timeout = %d" % statement_timeout_ms)
    conn.commit()   # a SET inside a transaction is undone by a rollback: commit so it holds for the whole session
    cur.execute("SHOW default_transaction_read_only")
    read_only = cur.fetchone()[0]
    cur.execute("SHOW statement_timeout")
    timeout = cur.fetchone()[0]
    cur.close()
    conn.rollback()
    ms = statement_timeout_ms
    accepted = {f"{ms}ms"} | ({f"{ms // 1000}s"} if ms % 1000 == 0 else set())   # Postgres prints whole seconds as '3s' and the rest in milliseconds
    if read_only != "on" or timeout not in accepted:
        raise RuntimeError(f"database session is not read-only with the statement timeout (read_only={read_only}, statement_timeout={timeout})")


def _direct(dsn: str, connect_timeout_s: int, statement_timeout_ms: int) -> Any:
    import psycopg2

    conn = psycopg2.connect(dsn, connect_timeout=connect_timeout_s, options=_options(statement_timeout_ms))
    try:
        _configure(conn, statement_timeout_ms)
    except Exception:
        conn.close()
        raise
    return conn


def _make_pool(dsn: str, connect_timeout_s: int, statement_timeout_ms: int) -> Any:
    from psycopg2.pool import ThreadedConnectionPool

    pool = ThreadedConnectionPool(1, POOL_MAX, dsn, connect_timeout=connect_timeout_s, options=_options(statement_timeout_ms))   # opens one connection now
    # psycopg2 keeps a returned connection only while fewer than `minconn` are idle, and closes it otherwise (with a minimum of 0 nothing would ever be reused). It opens `minconn` connections when the pool is made,
    # so the pool is made with 1 and the retention limit is raised afterwards: connections are opened as stages ask, and up to POOL_MAX are kept for the next stage. tests/test_db_reuse.py checks this.
    pool.minconn = POOL_MAX
    return pool


class _PoolState:
    """One pool and what is known about its connections. `meta` is keyed by the connection object (held, so its identity cannot be reused) and is only ever written for that connection."""

    def __init__(self, pool: Any, statement_timeout_ms: int):
        self.pool = pool
        self.statement_timeout_ms = statement_timeout_ms
        self.meta: dict[Any, dict] = {}

    def discard(self, conn: Any) -> None:
        self.meta.pop(conn, None)
        try:
            self.pool.putconn(conn, close=True)
        except Exception:  # noqa: BLE001
            pass

    def usable(self, conn: Any) -> bool:
        """False for a closed connection, and for one that has sat idle long enough that the database may have dropped it and that does not answer SELECT 1."""
        if getattr(conn, "closed", 1):
            return False
        last = self.meta.get(conn, {}).get("last")
        if last is not None and time.monotonic() - last <= RECENT_S:
            return True
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            conn.rollback()
            return True
        except Exception:  # noqa: BLE001 -- a dropped or broken connection is replaced, never reused
            return False

    def checkout(self) -> Any:
        """A usable connection, set up read-only with the timeout, or raise (the connection is then discarded)."""
        conn = self.pool.getconn()
        try:
            if not self.usable(conn):
                raise RuntimeError("pooled connection is closed or does not answer")
            meta = self.meta.setdefault(conn, {"configured": False, "last": None})
            if not meta.get("configured"):
                _configure(conn, self.statement_timeout_ms)
                meta["configured"] = True
            return conn
        except Exception:
            self.discard(conn)
            raise


def _get_state(dsn: str, connect_timeout_s: int, statement_timeout_ms: int) -> _PoolState:
    key = (dsn, connect_timeout_s, statement_timeout_ms, os.getpid())   # the process is part of the key: a forked process never shares its parent's pool
    with _lock:
        state = _states.get(key)
        if state is None:
            state = _states[key] = _PoolState(_make_pool(dsn, connect_timeout_s, statement_timeout_ms), statement_timeout_ms)
        return state


class _Lease:
    """What a stage holds: the pooled connection for every use (cursor, rollback, autocommit and so on), except that close() returns it to the pool, after which any use raises."""

    def __init__(self, conn: Any, state: _PoolState):
        object.__setattr__(self, "_conn", conn)
        object.__setattr__(self, "_state", state)
        object.__setattr__(self, "_open", True)

    def _live(self) -> Any:
        if not object.__getattribute__(self, "_open"):
            raise ClosedLeaseError("this connection was already closed: it has been returned to the pool and may be in use by another stage")
        return object.__getattribute__(self, "_conn")

    def __getattr__(self, name: str) -> Any:
        return getattr(self._live(), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(self._live(), name, value)

    def __enter__(self) -> Any:
        self._live().__enter__()
        return self

    def __exit__(self, *exc: Any) -> Any:
        return self._live().__exit__(*exc)

    def close(self) -> None:
        if not object.__getattribute__(self, "_open"):
            return
        conn, state = object.__getattribute__(self, "_conn"), object.__getattribute__(self, "_state")
        object.__setattr__(self, "_open", False)   # from here on this lease cannot touch the connection, whatever happens next
        try:
            if getattr(conn, "autocommit", False):
                conn.autocommit = False
            conn.rollback()
            state.meta.setdefault(conn, {"configured": True, "last": None})["last"] = time.monotonic()
            state.pool.putconn(conn)
        except Exception as exc:  # noqa: BLE001 -- a connection that cannot be reset is closed, never handed to the next stage
            logger.warning("db reuse: closing a connection that could not be reset: %s", exc)
            state.discard(conn)


def connect(connect_timeout_s: int, statement_timeout_ms: int) -> Any:
    """A read-only connection for one stage: from the pool when it can be, else an ordinary one. None when DATABASE_URL is not set (the stage then reports no answer, as before)."""
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return None
    if os.environ.get("DB_REUSE", "1") == "0":
        return _direct(dsn, connect_timeout_s, statement_timeout_ms)
    try:
        state = _get_state(dsn, connect_timeout_s, statement_timeout_ms)
        for _ in range(2):   # the first connection taken may be one the database dropped while it sat idle: replace it once
            try:
                return _Lease(state.checkout(), state)
            except Exception as exc:  # noqa: BLE001 -- a dropped or not-read-only connection was discarded; try once more, then the ordinary path
                logger.warning("db reuse: a pooled connection was not usable: %s", exc)
    except Exception as exc:  # noqa: BLE001 -- pool exhausted or not possible: an ordinary connection, exactly as before
        logger.warning("db reuse: using an ordinary connection (%s)", exc)
    return _direct(dsn, connect_timeout_s, statement_timeout_ms)
