"""Adversarial tests for scripts/run_alerts_dispatch.py.

Covers the break-it scenarios from the plan:
  - Pure email builder rendered from a RECORDED /check payload (fixture).
  - Zero new items -> send_resend is never called (forcing a send must fail).
  - Failed Resend send -> dedup state (mark_notified) is NOT advanced.
  - Both ePlanning endpoints down -> no state update at all (retry semantics).
  - Liability language absent from the factual email copy.

No network, no DB — the DB and Resend seams are monkeypatched.
"""
import json
import os
import sys

import pytest

# Append only (do not reorder sys.path for the shared session). run_alerts_dispatch
# handles the services/ path + package-form import itself.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS = os.path.join(_ROOT, "scripts")
if _SCRIPTS not in sys.path:
    sys.path.append(_SCRIPTS)

import run_alerts_dispatch as dispatch  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "threat_radar_new_apps.json")

LIABILITY_WORDS = [
    "safe", "feasible", "compliant", "should", "recommend", "suitable",
    "adequate", "sufficient", "approved", "guaranteed", "certified",
    "confirmed", "verified", "ensure", "assure", "accurate", "definitive",
    "comprehensive", "reliable",
]


@pytest.fixture
def new_apps():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def subscription():
    return {
        "id": "test-sub-1",
        "address": "9 Amy St, Marrickville NSW 2204",
        "email": "founder@example.com",
        "lat": -33.903,
        "lng": 151.159,
        "inputs": {"council_name": "Inner West", "seen_application_numbers": []},
        "unsubscribe_token": "tok_abc123",
    }


# ---------------------------------------------------------------------------
# Pure builder — golden output from a recorded payload
# ---------------------------------------------------------------------------

def test_email_subject_counts_items(subscription, new_apps):
    email = dispatch.build_alert_email(subscription, new_apps, "https://x/unsub?token=t")
    assert email["subject"] == f"{len(new_apps)} new development applications near {subscription['address']}"


def test_email_singular_when_one_item(subscription, new_apps):
    email = dispatch.build_alert_email(subscription, new_apps[:1], "https://x/unsub?token=t")
    assert "1 new development application near" in email["subject"]
    assert "applications" not in email["subject"]  # singular, no trailing s


def test_email_renders_verbatim_application_number(subscription, new_apps):
    email = dispatch.build_alert_email(subscription, new_apps, "https://x/unsub?token=t")
    num = new_apps[0].get("PlanningPortalApplicationNumber")
    assert num  # fixture sanity
    assert num in email["html"]
    assert num in email["text"]


def test_email_includes_unsubscribe_url(subscription, new_apps):
    url = "https://verify.plotdetect.com.au/api/satellite/threat-radar/unsubscribe?token=tok_abc123"
    email = dispatch.build_alert_email(subscription, new_apps, url)
    assert url in email["html"]
    assert url in email["text"]


def test_email_includes_source_line_and_sender_identity(subscription, new_apps):
    email = dispatch.build_alert_email(subscription, new_apps, "https://x/unsub?token=t")
    assert dispatch.SOURCE_LINE in email["text"]
    assert "PlotDetect Pty Ltd" in email["text"]
    assert "NSW Planning Portal application feeds" in email["text"]


def test_email_copy_has_no_liability_language(subscription, new_apps):
    email = dispatch.build_alert_email(subscription, new_apps, "https://x/unsub?token=t")
    body = (email["subject"] + " " + email["text"]).lower()
    hits = [w for w in LIABILITY_WORDS if f" {w}" in f" {body}" or f"{w} " in f"{body} "]
    # word-boundary-ish check: split into tokens
    tokens = set(body.replace("/", " ").replace(".", " ").replace(",", " ").split())
    hits = [w for w in LIABILITY_WORDS if w in tokens]
    assert hits == [], f"liability words in email copy: {hits}"


def test_missing_value_renders_em_dash(subscription):
    item = {"PlanningPortalApplicationNumber": "PAN-1", "_distance_m": 10}
    email = dispatch.build_alert_email(subscription, [item], "https://x/unsub?token=t")
    # Type/Status/Lodged absent -> em dash, never a fabricated value
    assert "—" in email["text"]


def test_email_shows_development_type_joined(subscription, new_apps):
    """The nested DevelopmentType list is joined into a readable 'What' line."""
    email = dispatch.build_alert_email(subscription, new_apps, "https://x/unsub?token=t")
    # fixture app 0 is a multi-type application (demolition/subdivision/new dwelling)
    assert "Subdivision" in email["text"]
    assert "What" in email["text"]


def test_email_formats_cost_as_dollars(subscription, new_apps):
    email = dispatch.build_alert_email(subscription, new_apps, "https://x/unsub?token=t")
    assert "$1,144,000" in email["text"]  # from the fixture's CostOfDevelopment 1144000.0


def test_email_shows_exhibition_deadline_when_present(subscription, new_apps):
    email = dispatch.build_alert_email(subscription, new_apps, "https://x/unsub?token=t")
    # fixture app 0 has AssessmentExhibitionEndDate 2026-07-21T00:00:00
    assert "Submissions open until" in email["text"]
    assert "2026-07-21" in email["text"]
    assert "T00:00:00" not in email["text"]  # datetime trimmed to the day


def test_email_omits_exhibition_when_absent(subscription):
    item = {
        "PlanningPortalApplicationNumber": "PAN-NOEXHIB",
        "ApplicationType": "Development Application",
        "_distance_m": 30,
        "CostOfDevelopment": 100000,
    }
    email = dispatch.build_alert_email(subscription, [item], "https://x/unsub?token=t")
    assert "Submissions open until" not in email["text"]


def test_dev_type_and_cost_helpers_are_null_safe():
    assert dispatch._dev_type({"DevelopmentType": [{"DevelopmentType": "Dwelling house"}]}) == "Dwelling house"
    assert dispatch._dev_type({"DevelopmentType": "Pool"}) == "Pool"
    assert dispatch._dev_type({}) == "—"
    assert dispatch._cost({"CostOfDevelopment": 340000.0}) == "$340,000"
    assert dispatch._cost({}) == "—"
    assert dispatch._fmt_date("2026-07-21T00:00:00") == "2026-07-21"
    assert dispatch._fmt_date(None) == "—"


def test_val_returns_verbatim_or_dash():
    assert dispatch._val({"a": "X"}, "a") == "X"
    assert dispatch._val({"a": None}, "a") == "—"
    assert dispatch._val({"a": ""}, "a") == "—"
    assert dispatch._val({}, "missing") == "—"


# ---------------------------------------------------------------------------
# Dispatch loop — state-advance discipline (the silent-drop trap)
# ---------------------------------------------------------------------------

def _wire(monkeypatch, subs, apps, api_ok=True, send_ok=True):
    """Monkeypatch the DB + network seams; return a calls-record dict."""
    calls = {"send": 0, "notified": [], "checked": []}
    monkeypatch.setattr(dispatch, "_get_conn", lambda: object())
    monkeypatch.setattr(dispatch, "load_active_subscriptions", lambda conn: subs)
    monkeypatch.setattr(dispatch, "_fetch_das", lambda council: (apps, api_ok, {}))
    monkeypatch.setattr(dispatch, "_filter_nearby", lambda apps_, lat, lng: apps_)

    def fake_send(email, to, key, frm):
        calls["send"] += 1
        return send_ok

    def fake_notified(conn, sid, seen):
        calls["notified"].append(str(sid))

    def fake_checked(conn, sid):
        calls["checked"].append(str(sid))

    monkeypatch.setattr(dispatch, "send_resend", fake_send)
    monkeypatch.setattr(dispatch, "mark_notified", fake_notified)
    monkeypatch.setattr(dispatch, "mark_checked", fake_checked)
    # Some conn objects get .close() called
    monkeypatch.setattr(dispatch, "_get_conn", lambda: type("C", (), {"close": lambda self: None})())
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    return calls


def test_zero_new_items_never_sends(monkeypatch, subscription):
    # Subscription has already seen the only nearby app -> zero new items.
    seen_app = {"PlanningPortalApplicationNumber": "PAN-SEEN", "_distance_m": 5}
    sub = dict(subscription)
    sub["inputs"] = {"council_name": "Inner West", "seen_application_numbers": ["PAN-SEEN"]}
    calls = _wire(monkeypatch, [sub], [seen_app], api_ok=True, send_ok=True)
    rc = dispatch.dispatch(dry_run=False)
    assert calls["send"] == 0, "must not send when there are no new applications"
    assert calls["notified"] == []
    assert calls["checked"] == ["test-sub-1"], "no-new still stamps last_checked"
    assert rc == 0


def test_failed_send_does_not_advance_dedup(monkeypatch, subscription, new_apps):
    calls = _wire(monkeypatch, [subscription], new_apps, api_ok=True, send_ok=False)
    rc = dispatch.dispatch(dry_run=False)
    assert calls["send"] == 1
    assert calls["notified"] == [], "dedup state MUST NOT advance on a failed send"
    assert rc == 2, "a failed send is a degraded run (exit 2)"


def test_successful_send_advances_dedup(monkeypatch, subscription, new_apps):
    calls = _wire(monkeypatch, [subscription], new_apps, api_ok=True, send_ok=True)
    rc = dispatch.dispatch(dry_run=False)
    assert calls["send"] == 1
    assert calls["notified"] == ["test-sub-1"], "dedup advances only after a 2xx send"
    assert rc == 0


def test_api_down_touches_no_state(monkeypatch, subscription, new_apps):
    calls = _wire(monkeypatch, [subscription], new_apps, api_ok=False, send_ok=True)
    rc = dispatch.dispatch(dry_run=False)
    assert calls["send"] == 0, "no send attempt when ePlanning is unavailable"
    assert calls["notified"] == []
    assert calls["checked"] == [], "last_checked NOT stamped on API failure — next run retries"
    assert rc == 0


def test_dry_run_never_sends(monkeypatch, subscription, new_apps):
    calls = _wire(monkeypatch, [subscription], new_apps, api_ok=True, send_ok=True)
    rc = dispatch.dispatch(dry_run=True)
    assert calls["send"] == 0
    assert calls["notified"] == []
    assert rc == 0


def test_one_failing_subscription_does_not_abort_the_run(monkeypatch, subscription, new_apps):
    good = dict(subscription, id="good")
    bad = dict(subscription, id="bad", inputs={"council_name": "", "seen_application_numbers": []})
    calls = _wire(monkeypatch, [bad, good], new_apps, api_ok=True, send_ok=True)
    rc = dispatch.dispatch(dry_run=False)
    # bad has no council_name -> counted failure; good still sends
    assert "good" in calls["notified"]
    assert rc == 2, "one per-subscription failure degrades the run to exit 2"
