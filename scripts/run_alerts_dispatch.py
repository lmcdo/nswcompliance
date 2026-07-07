#!/usr/bin/env python3
"""Property-alerts dispatcher: email subscribers about new DAs near their address.

prior-art-checked: reuses services/threat_radar.py (_fetch_das, _filter_nearby,
_get_conn — the existing subscription + check machinery) and follows
scripts/run_monitors.py conventions (Telegram summary, exit-code contract).
No email-dispatch capability exists anywhere in the repo (the `resend` npm dep
has zero usages; no Python Resend client) — this is the missing last mile.

Run modes:
    python scripts/run_alerts_dispatch.py            # real run (sends email)
    python scripts/run_alerts_dispatch.py --dry-run  # prints would-send emails, sends nothing

Exit codes (run_monitors contract, #572 precedent):
    0 = ran cleanly (sending alerts is normal operation, not a findings signal)
    2 = ran with per-subscription failures (degraded; Telegram already alerted)
    1 = run-level failure (no DB, missing migration, crash)

State rules (the silent-drop trap):
    - Dedup state and last_notified_at advance ONLY after a 2xx from Resend.
    - A failed send leaves the subscription untouched — items re-send next run.
    - Both ePlanning endpoints down -> no state update at all (retry semantics
      identical to services/threat_radar.py check()).

Required env: DATABASE_URL, RESEND_API_KEY (real runs).
Optional env: ALERTS_FROM_EMAIL, ALERTS_UNSUBSCRIBE_BASE, TELEGRAM_BOT_TOKEN,
TELEGRAM_CHAT_ID.
"""
from __future__ import annotations

import argparse
import html
import logging
import os
import sys
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import requests

# Import the threat_radar helpers via the `services.` package form the test suite
# uses (single module identity). services/ must be on sys.path only *during* this
# import (threat_radar does a bare `from audit_trail import`); we remove it again
# immediately so a shared process — the pytest session — is never left with
# services/ on path, which would let sibling modules (e.g. intelligence_brief)
# re-import under a second identity and fail pydantic model validation.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.append(_p)
_SERVICES = os.path.join(_ROOT, "services")
_services_added = _SERVICES not in sys.path
if _services_added:
    sys.path.append(_SERVICES)
try:
    from services.threat_radar import _fetch_das, _filter_nearby, _get_conn, ALERT_RADIUS_M  # noqa: E402
except ModuleNotFoundError:  # Docker monitors image: /app/services is on PYTHONPATH
    from threat_radar import _fetch_das, _filter_nearby, _get_conn, ALERT_RADIUS_M  # noqa: E402
finally:
    if _services_added:
        try:
            sys.path.remove(_SERVICES)
        except ValueError:
            pass

try:
    from run_monitors import send_telegram  # noqa: E402
except ImportError:  # pragma: no cover — scripts/ not on path in some test contexts
    def send_telegram(msg: str) -> None:  # type: ignore[misc]
        # failsoft: the summary alert is best-effort; results are already logged
        logging.getLogger(__name__).info("telegram unavailable: %s", msg[:200])

logger = logging.getLogger("alerts_dispatch")

RESEND_URL = "https://api.resend.com/emails"
DEFAULT_FROM = "PlotDetect Alerts <alerts@plotdetect.com.au>"
DEFAULT_UNSUB_BASE = "https://verify.plotdetect.com.au/api/satellite/threat-radar/unsubscribe"

SOURCE_LINE = "Application details are as published by the NSW Planning Portal at the time of this check."
FOOTER_IDENTITY = "PlotDetect Pty Ltd, Sydney, Australia — info@plotdetect.com.au"


def _val(item: dict, key: str) -> str:
    """Verbatim value or an em dash — no interpretation, no invented defaults."""
    v = item.get(key)
    if v is None or v == "":
        return "—"
    return str(v)


def _item_address(item: dict) -> str:
    loc = (item.get("Location") or [{}])[0]
    return str(loc.get("FullAddress") or "—")


def build_alert_email(subscription: dict, items: list[dict], unsubscribe_url: str) -> dict:
    """Pure builder: subscription row + new applications -> {subject, html, text}.

    Factual listings only — every value verbatim from the NSW Planning Portal
    application feeds. No commentary, no assessment.
    """
    address = subscription["address"]
    n = len(items)
    plural = "" if n == 1 else "s"
    subject = f"{n} new development application{plural} near {address}"

    rows_html = []
    rows_text = []
    for item in items:
        num = _val(item, "PlanningPortalApplicationNumber")
        if num == "—":
            num = _val(item, "ApplicationNumber")
        app_type = _val(item, "ApplicationType")
        status = _val(item, "ApplicationStatus")
        lodged = _val(item, "LodgementDate")
        dist = _val(item, "_distance_m")
        site = _item_address(item)
        cells = [num, app_type, status, lodged, f"{dist} m", site]
        rows_html.append(
            "<tr>"
            + "".join(
                f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{html.escape(c)}</td>"
                for c in cells
            )
            + "</tr>"
        )
        rows_text.append(f"- {num} | {app_type} | {status} | lodged {lodged} | {dist} m | {site}")

    intro = (
        f"New development application{plural} lodged within {ALERT_RADIUS_M} m of "
        f"{address}, from the NSW Planning Portal application feeds."
    )
    source_block = (
        f"{SOURCE_LINE} Data source: NSW Planning Portal application feeds "
        f"(OnlineDA / OnlineCDC). Radius: {ALERT_RADIUS_M} m."
    )
    header_cells = "".join(
        f"<th style='padding:6px 10px'>{h}</th>"
        for h in ("Application", "Type", "Status", "Lodged", "Distance", "Site")
    )

    html_body = (
        '<div style="font-family:Arial,Helvetica,sans-serif;color:#1f2937;max-width:680px">'
        f"<h2 style='font-size:18px'>{html.escape(subject)}</h2>"
        f"<p style='font-size:14px'>{html.escape(intro)}</p>"
        '<table style="border-collapse:collapse;font-size:13px;width:100%">'
        f"<thead><tr style='text-align:left;background:#f9fafb'>{header_cells}</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody></table>"
        f"<p style='font-size:12px;color:#6b7280'>{html.escape(source_block)}</p>"
        "<hr style='border:none;border-top:1px solid #eee'>"
        f"<p style='font-size:12px;color:#6b7280'>{html.escape(FOOTER_IDENTITY)}<br>"
        "You subscribed to development-application alerts for this address. "
        f"<a href='{html.escape(unsubscribe_url)}'>Unsubscribe</a></p></div>"
    )

    text_body = "\n".join(
        [
            subject,
            "",
            intro,
            "",
            *rows_text,
            "",
            source_block,
            "",
            FOOTER_IDENTITY,
            f"Unsubscribe: {unsubscribe_url}",
        ]
    )
    return {"subject": subject, "html": html_body, "text": text_body}


def send_resend(email: dict, to_addr: str, api_key: str, from_addr: str) -> bool:
    """POST to the Resend HTTPS API. True only on a 2xx response."""
    try:
        r = requests.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "from": from_addr,
                "to": [to_addr],
                "subject": email["subject"],
                "html": email["html"],
                "text": email["text"],
            },
            timeout=20,
        )
        if 200 <= r.status_code < 300:
            return True
        logger.error("Resend %s: %s", r.status_code, r.text[:300])
        return False
    except Exception as e:
        # failsoft: a send failure is a counted failure; state is never advanced on it
        logger.error("Resend send failed: %s", e)
        return False


def load_active_subscriptions(conn) -> list[dict]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "SELECT id, address, email, lat, lng, inputs, unsubscribe_token "
            "FROM threat_radar_subscriptions WHERE active=true"
        )
        return [dict(r) for r in cur.fetchall()]


def mark_checked(conn, sub_id) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE threat_radar_subscriptions SET last_checked=NOW() WHERE id=%s",
            (str(sub_id),),
        )
    conn.commit()


def mark_notified(conn, sub_id, seen: set) -> None:
    """Advance dedup state — call ONLY after a confirmed 2xx send."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE threat_radar_subscriptions "
            "SET last_checked=NOW(), last_notified_at=NOW(), "
            "    inputs = inputs || jsonb_build_object('seen_application_numbers', %s::jsonb) "
            "WHERE id=%s",
            (psycopg2.extras.Json(sorted(seen)), str(sub_id)),
        )
    conn.commit()


def dispatch(dry_run: bool = False) -> int:
    api_key = os.environ.get("RESEND_API_KEY") or ""
    from_addr = os.environ.get("ALERTS_FROM_EMAIL", DEFAULT_FROM)
    unsub_base = os.environ.get("ALERTS_UNSUBSCRIBE_BASE", DEFAULT_UNSUB_BASE)
    if not api_key and not dry_run:
        print("RESEND_API_KEY missing — refusing a real run (use --dry-run)", file=sys.stderr)
        return 1

    conn = _get_conn()
    try:
        subs = load_active_subscriptions(conn)
    except psycopg2.errors.UndefinedColumn:
        print(
            "threat_radar_subscriptions is missing alert columns "
            "(unsubscribe_token / last_notified_at) — run the migration first.",
            file=sys.stderr,
        )
        conn.close()
        return 1

    sent = no_new = api_skipped = failures = 0
    for sub in subs:
        try:
            inputs = sub.get("inputs") or {}
            council = inputs.get("council_name") or ""
            if not council:
                logger.warning("subscription %s has no council_name — skipped", sub["id"])
                failures += 1
                continue
            seen = set(inputs.get("seen_application_numbers") or [])

            apps, api_ok, _per = _fetch_das(council)
            if not api_ok:
                # both ePlanning endpoints failed — leave state untouched, retry next run
                api_skipped += 1
                continue

            nearby = _filter_nearby(apps, float(sub["lat"]), float(sub["lng"]))
            new_items = []
            for app in nearby:
                num = app.get("PlanningPortalApplicationNumber") or app.get("ApplicationNumber") or ""
                if num and num not in seen:
                    new_items.append(app)
                    seen.add(num)

            if not new_items:
                if not dry_run:
                    mark_checked(conn, sub["id"])
                no_new += 1
                continue

            unsub_url = f"{unsub_base}?token={sub['unsubscribe_token']}"
            email = build_alert_email(sub, new_items, unsub_url)

            if dry_run:
                print(f"\n=== DRY RUN — would send to {sub['email']} ===")
                print(f"Subject: {email['subject']}")
                print(email["text"])
                sent += 1
                continue

            if send_resend(email, sub["email"], api_key, from_addr):
                mark_notified(conn, sub["id"], seen)
                sent += 1
            else:
                # state NOT advanced — items re-send next run rather than vanish
                failures += 1
        except Exception as e:
            logger.exception("subscription %s failed: %s", sub.get("id"), e)
            failures += 1

    conn.close()

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = (
        f"alerts-dispatch {stamp}: {len(subs)} subscriptions — "
        f"{sent} emailed, {no_new} no-new, {api_skipped} api-skipped, {failures} failed"
        f"{' [DRY RUN]' if dry_run else ''}"
    )
    print(summary)
    if failures and not dry_run:
        send_telegram(f"⚠️ {summary}")
        return 2
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Property-alerts email dispatcher")
    parser.add_argument("--dry-run", action="store_true", help="print would-send emails, send nothing")
    args = parser.parse_args()
    return dispatch(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
