"""Results of every dcp-monitor run: one row per run, per council list read, per chapter checked.

prior-art-checked: before this nothing stored a run's outcome. r2_monitor wrote url_last_checked on
the registry (overwritten each run) and printed the rest, so "was this chapter actually checked, and
how" could not be asked of the database. data_source_health_checks (migration 043) is per external
API endpoint, not per document, so it is not reused. Tables: migrations/116_dcp_monitor_results.sql.

Also holds the two pure decisions the daily cadence needs (v6 resolutions 4, 9, 13 and the weekly
5% re-download), so they can be mutation-tested without a network or a database.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta

#: A file whose server sends no ETag is downloaded at most this often (HEAD every day in between).
FULL_DOWNLOAD_EVERY = timedelta(days=7)
#: 1 in SPOT_ONE_IN tagged chapters is re-downloaded each ISO week even when its tag matches,
#: to catch a server that keeps the tag while the bytes change.
SPOT_ONE_IN = 20
#: First run's age under which list alerts go to the log only (resolution 12, shadow week).
SHADOW_PERIOD = timedelta(days=7)

#: Every way a chapter's check can end. Stored as text so a new outcome needs no migration.
CHECKED = frozenset({"unchanged_etag", "unchanged_hash", "unchanged_head", "reexport", "changed",
                     "etag_lied"})
NOT_CHECKED = frozenset({"no_url", "waf_blocked", "rate_limited", "transient", "failed"})
OUTCOMES = CHECKED | NOT_CHECKED
#: Council list outcomes.
LIST_OUTCOMES = frozenset({"ok", "blocked", "empty", "error", "anomaly", "no_scraper"})


#: A stored size below this cannot be a PDF (r2_monitor.MIN_PDF_BYTES): download once to replace it.
#: DQ-79: row 766 kept url_content_length = 1 behind a matching ETag, so it was never re-measured.
MIN_STORED_BYTES = 1000


def decide_fetch(*, force: bool, stored_hash: str | None, stored_etag: str | None,
                 head_etag: str | None, stored_len: int | None, head_len: int | None,
                 last_downloaded: datetime | None, now: datetime, spot: bool) -> tuple[bool, str]:
    """Whether to download the file today, and why. HEAD has already been made.

    Tagged (both ETags present): download when the tag differs, the size differs, or on a spot
    check. (A size change behind an unchanged tag costs one download if it is only gzip noise.)
    Untagged: download when the size differs, or when the last full download is
    FULL_DOWNLOAD_EVERY old or unknown. Any missing baseline downloads.
    """
    if force:
        return True, "force"
    if not stored_hash:
        return True, "no_baseline"
    if stored_len is not None and int(stored_len) < MIN_STORED_BYTES:
        return True, "size_impossible"
    if stored_etag and head_etag and stored_etag != head_etag:
        return True, "etag_changed"
    if stored_len is not None and head_len is not None and int(stored_len) != int(head_len):
        return True, "size_changed"
    if stored_etag and head_etag:
        return (True, "spot_check") if spot else (False, "etag_match")
    if last_downloaded is None or now - last_downloaded >= FULL_DOWNLOAD_EVERY:
        return True, "untagged_weekly"
    return False, "untagged_recent"


def is_spot_check(chapter_id: int, now: datetime) -> bool:
    """Deterministic 1-in-SPOT_ONE_IN weekly pick, spread over the days of the week.

    The same chapter is picked on the same weekday all week, so a daily run hits it once and a
    missed day is not silently skipped twice.
    """
    year, week, weekday = now.isocalendar()
    h = int(hashlib.sha256(f"{chapter_id}:{year}-{week}".encode()).hexdigest(), 16)
    return h % SPOT_ONE_IN == 0 and (h // SPOT_ONE_IN) % 7 == weekday - 1


def shrank(previous: list[dict] | None, current: list[dict]) -> bool:
    """True when today's list keeps fewer than half of the last good list's links.

    Counted as links still present, not as a raw count, so a page that swapped most of its
    links for others (a homepage of the same size) is caught too. No previous list = first scan.
    """
    if not previous:
        return False
    before = {e.get("norm") for e in previous}
    kept = len(before & {e.get("norm") for e in current})
    return kept * 2 < len(before)


def in_shadow(first_run_at: datetime | None, now: datetime) -> bool:
    """List alerts are logged only until the first recorded run is SHADOW_PERIOD old."""
    return first_run_at is None or now - first_run_at < SHADOW_PERIOD


class Recorder:
    """Buffers one council's rows and writes them in one transaction. A dry run writes nothing."""

    def __init__(self, conn, dry_run: bool, mode: str):
        self.conn, self.dry_run, self.mode = conn, dry_run, mode
        self.run_id: int | None = None
        self.first_run_at: datetime | None = None
        self._chapters: list[tuple] = []
        self._councils: list[tuple] = []

    def start(self) -> None:
        if self.dry_run:
            return
        cur = self.conn.cursor()
        cur.execute("SELECT min(started_at) FROM dcp_monitor_runs")
        self.first_run_at = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO dcp_monitor_runs (mode, git_sha) VALUES (%s, %s) RETURNING id",
            (self.mode, os.environ.get("RAILWAY_GIT_COMMIT_SHA")),
        )
        self.run_id = cur.fetchone()[0]
        self.conn.commit()
        cur.close()

    def chapter(self, chapter_id: int, council: str, chapter_key: str, outcome: str,
                reason: str | None = None, detail: str | None = None) -> None:
        if outcome not in OUTCOMES:
            raise ValueError(f"unknown chapter outcome {outcome!r}")
        self._chapters.append((chapter_id, council, chapter_key, outcome, reason, (detail or "")[:500]))

    def council_list(self, council: str, page_url: str | None, outcome: str,
                     entries: list[dict] | None = None, fp: str | None = None,
                     alerts: list[str] | None = None, detail: str | None = None) -> None:
        if outcome not in LIST_OUTCOMES:
            raise ValueError(f"unknown list outcome {outcome!r}")
        self._councils.append((council, page_url, outcome, len(entries or []), fp,
                               json.dumps(entries or []), json.dumps(alerts or []), (detail or "")[:500]))

    def flush(self) -> None:
        """Write buffered rows. Called after each council so a crash loses one council at most."""
        if self.dry_run or self.run_id is None:
            self._chapters.clear()
            self._councils.clear()
            return
        cur = self.conn.cursor()
        cur.executemany(
            "INSERT INTO dcp_monitor_chapter_results (run_id, chapter_id, council, chapter_key, outcome,"
            " reason, detail) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [(self.run_id, *r) for r in self._chapters],
        )
        cur.executemany(
            "INSERT INTO dcp_monitor_council_results (run_id, council, page_url, outcome, link_count,"
            " list_fingerprint, links, alerts, detail) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)",
            [(self.run_id, *r) for r in self._councils],
        )
        self.conn.commit()
        cur.close()
        self._chapters.clear()
        self._councils.clear()

    def finish(self, summary: dict) -> None:
        self.flush()
        if self.dry_run or self.run_id is None:
            return
        cur = self.conn.cursor()
        cur.execute("UPDATE dcp_monitor_runs SET finished_at = NOW(), summary = %s::jsonb WHERE id = %s",
                    (json.dumps(summary, default=str), self.run_id))
        self.conn.commit()
        cur.close()

    def previous_list(self, council: str, page_url: str | None = None) -> list[dict] | None:
        """The last list read OK for this council's page, or None when there is none (first scan).

        Keyed by (council, page_url) so a council can have a second page (v7 red-team 2); a page
        whose address changed starts a fresh first scan rather than diffing against another page.
        page_url None = any page of the council.
        """
        if self.dry_run and self.run_id is None:
            try:
                return self._query_previous(council, page_url)
            except Exception:  # noqa: BLE001 - a dry run before the migration has no table
                self.conn.rollback()
                return None
        return self._query_previous(council, page_url)

    def council_list_checked(self, council: str, hub_url: str, discovered: list[dict],
                             held: dict[str, str], probe, send, now: datetime,
                             plans=()) -> list[str]:
        """Save today's list, diff it with the last good one, raise (or in shadow week log) alerts.

        `probe(url) -> bool | None` says whether a gone link's file still opens (None = unknown);
        `send(text)` delivers an alert. Returns the alert lines.
        """
        from verifyops_links import alert_lines, diff_lists, fingerprint, link_entries

        entries = link_entries(discovered)
        if not entries:
            self.council_list(council, hub_url, "empty", detail="scraper returned no links")
            return []
        previous = self.previous_list(council, hub_url)
        if shrank(previous, entries):
            # A homepage or error page that still has links (v7 red-team 1). Not saved as 'ok', so
            # tomorrow is still compared with the last good list, and the council goes red.
            self.council_list(council, hub_url, "anomaly", entries, fingerprint(entries),
                              detail=f"{len(entries)} links, under half of the last good list's "
                                     f"{len(previous)}: not saved as the list")
            return []
        diff = diff_lists(previous, entries)
        gone_alive = {} if diff.redesigned else {e["norm"]: probe(e["href"]) for e in diff.gone[:10]}
        lines = alert_lines(council, diff, held, gone_alive, plans)
        shadow = in_shadow(self.first_run_at, now)
        detail = "first scan: list saved, no alerts" if diff.first_scan else (
            f"{len(diff.new)} new, {len(diff.gone)} gone" + (" [shadow week: logged only]" if shadow else ""))
        self.council_list(council, hub_url, "ok", entries, fingerprint(entries), lines, detail)
        for line in lines:
            print(f"  [LIST{' SHADOW' if shadow else ''}] {line}")
        if lines and not shadow:
            send("DCP council list changed\n" + "\n".join(lines[:15]))
        return lines

    def _query_previous(self, council: str, page_url: str | None) -> list[dict] | None:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT links FROM dcp_monitor_council_results WHERE council = %s AND outcome = 'ok'"
            " AND (%s::text IS NULL OR page_url = %s) ORDER BY id DESC LIMIT 1",
            (council, page_url, page_url),
        )
        row = cur.fetchone()
        cur.close()
        if row is None:
            return None
        return row[0] if isinstance(row[0], list) else json.loads(row[0])
