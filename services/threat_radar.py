"""
Neighbour Development Threat Radar -- FastAPI router.

POST /pipeline/threat-radar/subscribe   -- add address to monitoring
POST /pipeline/threat-radar/check       -- weekly check for one subscription (Trigger.dev cron)
GET  /pipeline/threat-radar/subscriptions -- list active (used by Trigger.dev task)

Data: NSW ePlanning API (public, no auth).
Dedup: seen application numbers stored in threat_radar_subscriptions.inputs JSONB.
"""
import json, logging, math, os
from datetime import datetime, timedelta
from typing import Optional

import psycopg2, psycopg2.extras, requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from audit_trail import DataSourceQuery, log_audit_trail, get_current_disclaimer_version

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["satellite"])

DA_URL  = "https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineDA"
CDC_URL = "https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineCDC"
ALERT_RADIUS_M = 200
WINDOW_DAYS = 8


class SubscribeRequest(BaseModel):
    address: str
    prop_id: Optional[str] = None
    lat: float
    lng: float
    email: str
    council_name: str

    def validate_email(self) -> None:
        if "@" not in self.email or "." not in self.email.split("@")[-1]:
            raise ValueError(f"Invalid email address: {self.email}")


class CheckRequest(BaseModel):
    subscription_id: str


def _get_conn():
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        return psycopg2.connect(dsn)
    return psycopg2.connect(
        host=os.environ.get("DB_HOST","127.0.0.1"),
        database=os.environ.get("DB_NAME","nsw_planning"),
        user=os.environ.get("DB_USER","postgres"),
        password=os.environ.get("DB_PASSWORD",""),
        port=int(os.environ.get("DB_PORT",5432)),
    )


def _lookup_property_context(lat: float, lng: float) -> dict:
    """Query spatial_overlays for subscriber's zone and TOD precinct status."""
    result = {"zone": None, "tod_precinct": None, "tod_type": None}
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL statement_timeout = '5000'")
            cur.execute(
                """
                SELECT value, layer_type
                FROM spatial_overlays
                WHERE layer_type IN ('zone', 'tod_precinct', 'tod_accelerated')
                  AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                ORDER BY layer_type, currency_date DESC
                """,
                (lng, lat),
            )
            for row in cur.fetchall():
                lt = row["value"]
                if row["layer_type"] == "zone":
                    result["zone"] = lt
                elif row["layer_type"] in ("tod_precinct", "tod_accelerated"):
                    result["tod_precinct"] = True
                    result["tod_type"] = row["layer_type"]
    except Exception as e:
        logger.warning(f"Property context lookup: {e}")
    finally:
        if conn:
            conn.close()
    return result


def _haversine(lat1, lng1, lat2, lng2) -> float:
    R = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2-lat1); dl = math.radians(lng2-lng1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return R*2*math.atan2(math.sqrt(a), math.sqrt(1-a))


# Maps any user-submitted or NSW-Spatial-Services-derived LGA name →
# exact council name string the NSW ePlanning API expects.
# Keys are lowercase. NSW Spatial Services returns uppercase LGA names (e.g. "INNER WEST"),
# user input is variable — both are normalised to lowercase before lookup.
_COUNCIL_NAME_MAP = {
    # Sydney — only council with non-standard API name
    "sydney":                           "Council of the City of Sydney",
    "city of sydney":                   "Council of the City of Sydney",
    "sydney city":                      "Council of the City of Sydney",
    "sydney city council":              "Council of the City of Sydney",
    "council of the city of sydney":    "Council of the City of Sydney",
    # Inner west
    "inner west":                       "Inner West Council",
    # Parramatta
    "parramatta":                       "City of Parramatta Council",
    "city of parramatta":               "City of Parramatta Council",
    # Northern beaches
    "northern beaches":                 "Northern Beaches Council",
    # Amalgamated councils no longer on API
    "gosford":                          "Central Coast Council",
    "wyong":                            "Central Coast Council",
    # Common user shorthands
    "randwick":                         "Randwick City Council",
    "waverley":                         "Waverley Council",
    "woollahra":                        "Woollahra Municipal Council",
    "mosman":                           "Mosman Municipal Council",
    "north sydney":                     "North Sydney Council",
    "willoughby":                       "Willoughby City Council",
    "lane cove":                        "Lane Cove Municipal Council",
    "hunters hill":                     "Hunters Hill Council",
    "ryde":                             "Ryde City Council",
    "ku-ring-gai":                      "Ku-ring-gai Council",
    "hornsby":                          "Hornsby Shire Council",
    "the hills":                        "The Hills Shire Council",
    "hills shire":                      "The Hills Shire Council",
    "blacktown":                        "Blacktown City Council",
    "penrith":                          "Penrith City Council",
    "blue mountains":                   "Blue Mountains City Council",
    "hawkesbury":                       "Hawkesbury City Council",
    "camden":                           "Camden Council",
    "campbelltown":                     "Campbelltown City Council",
    "wollondilly":                      "Wollondilly Shire Council",
    "liverpool":                        "Liverpool City Council",
    "fairfield":                        "Fairfield City Council",
    "canterbury-bankstown":             "Canterbury-Bankstown Council",
    "canterbury bankstown":             "Canterbury-Bankstown Council",
    "georges river":                    "Georges River Council",
    "sutherland":                       "Sutherland Shire Council",
    "sutherland shire":                 "Sutherland Shire Council",
    "bayside":                          "Bayside Council",
    "strathfield":                      "Strathfield Municipal Council",
    "burwood":                          "Burwood Council",
    "cumberland":                       "Cumberland Council",
    "wollongong":                       "Wollongong City Council",
    "shellharbour":                     "Shellharbour City Council",
    "kiama":                            "Kiama Municipal Council",
    "shoalhaven":                       "Shoalhaven City Council",
    "newcastle":                        "Newcastle City Council",
    "lake macquarie":                   "Lake Macquarie City Council",
    "cessnock":                         "Cessnock City Council",
    "maitland":                         "Maitland City Council",
    "port stephens":                    "Port Stephens Council",
    "central coast":                    "Central Coast Council",
    "bathurst":                         "Bathurst Regional Council",
    "orange":                           "Orange City Council",
    "dubbo":                            "Dubbo Regional Council",
    "tamworth":                         "Tamworth Regional Council",
    "wagga wagga":                      "Wagga Wagga City Council",
    "wagga":                            "Wagga Wagga City Council",
    "albury":                           "Albury City Council",
}


def _normalise_council(council_name: str) -> str:
    """Return the exact council name string the NSW ePlanning API expects."""
    key = council_name.strip().lower()
    return _COUNCIL_NAME_MAP.get(key, council_name.strip())


def _fetch_das(council_name: str, days_back: int = WINDOW_DAYS) -> tuple[list, bool, dict]:
    """
    Fetch DAs and CDCs from NSW ePlanning API.
    Returns (applications, api_available, per_endpoint_counts).
    api_available is False only if BOTH endpoints failed — used to skip updating last_checked.
    per_endpoint_counts maps each URL to its app count (or error string).
    """
    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    council = _normalise_council(council_name)
    filters_header = json.dumps({"filters": {"CouncilName": [council], "LodgementDateFrom": since}})
    headers = {
        "filters": filters_header,
        "PageSize": "200",
        "PageNumber": "1",
        "Cache-Control": "no-cache",
    }
    apps = []
    any_success = False
    per_endpoint: dict = {}
    for url in (DA_URL, CDC_URL):
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()
            batch = data.get("Application") or data.get("ApplicationList") or []
            apps.extend(batch)
            per_endpoint[url] = len(batch)
            any_success = True
        except Exception as e:
            logger.warning(f"ePlanning {url}: {e}")
            per_endpoint[url] = f"error: {e}"
    return apps, any_success, per_endpoint


def _filter_nearby(apps: list, lat: float, lng: float) -> list:
    nearby = []
    for app in apps:
        try:
            # Coordinates are in Location[0].X / Location[0].Y (strings)
            loc = (app.get("Location") or [{}])[0]
            alat = float(app.get("Latitude") or loc.get("Y") or 0)
            alng = float(app.get("Longitude") or loc.get("X") or 0)
            if alat == 0 and alng == 0:
                continue
            d = _haversine(lat, lng, alat, alng)
            if d <= ALERT_RADIUS_M:
                nearby.append({**app, "_distance_m": round(d,1)})
        except Exception:
            pass
    return nearby


@router.post("/threat-radar/subscribe")
def subscribe(req: SubscribeRequest):
    try:
        req.validate_email()
    except ValueError as e:
        raise HTTPException(422, str(e))

    # Units/CRS entry check (campaign item 4): a swapped/projected coordinate
    # would silently monitor the wrong place for the subscription's lifetime.
    try:
        from services.geometry_checks import check_point_nsw
    except ImportError:
        from geometry_checks import check_point_nsw
    coord_reason = check_point_nsw(req.lat, req.lng)
    if coord_reason:
        raise HTTPException(
            422, f"Subscription could not be created: {coord_reason}")

    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Return existing active subscription rather than creating a duplicate
            cur.execute(
                "SELECT id FROM threat_radar_subscriptions WHERE address=%s AND email=%s AND active=true",
                (req.address, req.email),
            )
            existing = cur.fetchone()
            if existing:
                return {"subscription_id": str(existing["id"]), "address": req.address, "status": "active"}

            cur.execute(
                "INSERT INTO threat_radar_subscriptions "
                "(address,prop_id,lat,lng,email,active,inputs) "
                "VALUES (%s,%s,%s,%s,%s,true,%s) RETURNING id",
                (req.address, req.prop_id, req.lat, req.lng, req.email,
                 psycopg2.extras.Json({"council_name": req.council_name,
                                       "seen_application_numbers": []}))
            )
            row = cur.fetchone()
        conn.commit()
    finally:
        if conn:
            conn.close()
    return {"subscription_id": str(row["id"]), "address": req.address, "status": "active"}


@router.post("/threat-radar/check")
def check(req: CheckRequest):
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM threat_radar_subscriptions WHERE id=%s AND active=true",
                        (req.subscription_id,))
            sub = cur.fetchone()
    finally:
        if conn:
            conn.close()
    if not sub:
        raise HTTPException(404, "Subscription not found")

    inputs = sub.get("inputs") or {}
    council = inputs.get("council_name") or ""
    seen = set(inputs.get("seen_application_numbers") or [])
    property_context = _lookup_property_context(float(sub["lat"]), float(sub["lng"]))  # noqa: bracket-access (NOT NULL DB columns)
    if not council:
        raise HTTPException(422, "council_name missing from subscription")

    apps, api_available, per_endpoint = _fetch_das(council)

    # Build audit data source objects for each ePlanning endpoint
    query_params = {"council": council, "days_back": WINDOW_DAYS, "radius_m": ALERT_RADIUS_M}
    ds_online_da = DataSourceQuery("NSW ePlanning OnlineDA", DA_URL, query_params)
    ds_online_cdc = DataSourceQuery("NSW ePlanning OnlineCDC", CDC_URL, query_params)

    da_result = per_endpoint.get(DA_URL)
    cdc_result = per_endpoint.get(CDC_URL)
    if isinstance(da_result, int):
        ds_online_da.record_response({"count": da_result}, features_returned=da_result)
    else:
        ds_online_da.error = str(da_result) if da_result else "no response"
    if isinstance(cdc_result, int):
        ds_online_cdc.record_response({"count": cdc_result}, features_returned=cdc_result)
    else:
        ds_online_cdc.error = str(cdc_result) if cdc_result else "no response"

    if not api_available:
        # Both ePlanning endpoints failed — don't update last_checked or seen set.
        # The next run will retry rather than treating this as a successful empty check.
        logger.warning(f"Skipping last_checked update for {req.subscription_id} — ePlanning API unavailable")

        # Audit trail even on failure (non-blocking)
        log_audit_trail(
            report_id=req.subscription_id,
            pipeline_name="threat-radar",
            input_params={"subscription_id": req.subscription_id, "address": sub["address"],
                          "lat": float(sub["lat"]), "lng": float(sub["lng"]), "council": council},
            data_sources=[ds_online_da, ds_online_cdc],
            output_summary={"api_error": True, "new_application_count": 0},
            disclaimer_version=get_current_disclaimer_version("threat-radar"),
            intermediate_calculations={
                "total_das_fetched": 0, "total_cdcs_fetched": 0, "radius_m": ALERT_RADIUS_M,
                "api_available": False,
            },
        )

        return {
            "subscription_id": req.subscription_id,
            "address": sub["address"],
            "new_application_count": 0,
            "new_applications": [],
            "total_nearby": 0,
            "checked_at": None,
            "property_context": property_context,
            "api_error": "NSW ePlanning API unavailable — check will retry next run",
        }

    nearby = _filter_nearby(apps, sub["lat"], sub["lng"])
    new_apps = []
    for app in nearby:
        num = app.get("PlanningPortalApplicationNumber") or app.get("ApplicationNumber") or ""
        if num and num not in seen:
            new_apps.append(app); seen.add(num)

    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE threat_radar_subscriptions "
                "SET last_checked=NOW(), "
                "    inputs = inputs || jsonb_build_object('seen_application_numbers',%s::jsonb) "
                "WHERE id=%s",
                (psycopg2.extras.Json(list(seen)), req.subscription_id)
            )
        conn.commit()
    finally:
        if conn:
            conn.close()

    # Audit trail (non-blocking — won't prevent check results delivery on failure)
    checked_at = datetime.utcnow().isoformat()
    da_count = per_endpoint.get(DA_URL, 0) if isinstance(per_endpoint.get(DA_URL), int) else 0
    cdc_count = per_endpoint.get(CDC_URL, 0) if isinstance(per_endpoint.get(CDC_URL), int) else 0
    log_audit_trail(
        report_id=req.subscription_id,
        pipeline_name="threat-radar",
        input_params={
            "subscription_id": req.subscription_id,
            "address": sub["address"],
            "lat": float(sub["lat"]),
            "lng": float(sub["lng"]),
            "council": council,
        },
        data_sources=[ds_online_da, ds_online_cdc],
        output_summary={
            "new_application_count": len(new_apps),
            "total_nearby": len(nearby),
            "checked_at": checked_at,
        },
        disclaimer_version=get_current_disclaimer_version("threat-radar"),
        intermediate_calculations={
            "total_das_fetched": da_count,
            "total_cdcs_fetched": cdc_count,
            "total_apps_before_filter": len(apps),
            "nearby_within_radius": len(nearby),
            "new_unseen_apps": len(new_apps),
            "radius_m": ALERT_RADIUS_M,
            "window_days": WINDOW_DAYS,
            "api_available": True,
            "property_context": property_context,
        },
    )

    return {
        "subscription_id": req.subscription_id,
        "address": sub["address"],
        "new_application_count": len(new_apps),
        "new_applications": new_apps,
        "total_nearby": len(nearby),
        "checked_at": checked_at,
        "property_context": property_context,
    }


@router.get("/threat-radar/subscriptions")
def list_subscriptions():
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id,address,email,lat,lng FROM threat_radar_subscriptions WHERE active=true")
            rows = cur.fetchall()
    finally:
        if conn:
            conn.close()
    return {"subscriptions": [dict(r) for r in rows]}


# prior-art-checked: this IS the extension of the existing subscription module in
# this same file — no unsubscribe capability exists anywhere in the repo (the
# subscribe/check endpoints above have no deactivation path; audit 2026-07-07).
@router.get("/threat-radar/unsubscribe")
def unsubscribe(token: str):
    """Deactivate a subscription by its unsubscribe token.

    Token-only lookup — no email parameter, so the endpoint cannot be used to
    probe whether an address or email is subscribed (enumeration guard).
    Idempotent: a second click on the same link returns the same confirmation.
    """
    if not token or len(token) > 100:
        raise HTTPException(422, "Missing or invalid token")
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "UPDATE threat_radar_subscriptions SET active=false "
                "WHERE unsubscribe_token=%s RETURNING id",
                (token,),
            )
            row = cur.fetchone()
        conn.commit()
    finally:
        if conn:
            conn.close()
    if row is None:
        # UPDATE matches regardless of current active value, so an already-
        # unsubscribed token still returns a row — no row means unknown token.
        raise HTTPException(404, "Unknown unsubscribe link")
    return {
        "status": "unsubscribed",
        "message": "You will no longer receive development application alerts for this address.",
    }
