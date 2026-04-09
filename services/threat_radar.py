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


def _fetch_das(council_name: str, days_back: int = WINDOW_DAYS) -> list:
    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    council = _normalise_council(council_name)
    # Filters passed as HTTP header (not query param) — confirmed from NSW ePlanning API
    filters_header = json.dumps({"filters": {"CouncilName": [council], "LodgementDateFrom": since}})
    headers = {
        "filters": filters_header,
        "PageSize": "200",
        "PageNumber": "1",
        "Cache-Control": "no-cache",
    }
    apps = []
    for url in (DA_URL, CDC_URL):
        try:
            r = requests.get(url, headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()
            apps.extend(data.get("Application") or data.get("ApplicationList") or [])
        except Exception as e:
            logger.warning(f"ePlanning {url}: {e}")
    return apps


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
        except (TypeError, ValueError):
            pass
    return nearby


@router.post("/threat-radar/subscribe")
def subscribe(req: SubscribeRequest):
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
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
    return {"subscription_id": str(row["id"]), "address": req.address, "status": "active"}


@router.post("/threat-radar/check")
def check(req: CheckRequest):
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM threat_radar_subscriptions WHERE id=%s AND active=true",
                        (req.subscription_id,))
            sub = cur.fetchone()
    if not sub:
        raise HTTPException(404, "Subscription not found")

    inputs = sub.get("inputs") or {}
    council = inputs.get("council_name","")
    seen = set(inputs.get("seen_application_numbers") or [])
    if not council:
        raise HTTPException(422, "council_name missing from subscription")

    apps = _fetch_das(council)
    nearby = _filter_nearby(apps, sub["lat"], sub["lng"])
    new_apps = []
    for app in nearby:
        num = app.get("PlanningPortalApplicationNumber") or app.get("ApplicationNumber","")
        if num and num not in seen:
            new_apps.append(app); seen.add(num)

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE threat_radar_subscriptions "
                "SET last_checked=NOW(), "
                "    inputs = inputs || jsonb_build_object('seen_application_numbers',%s::jsonb) "
                "WHERE id=%s",
                (psycopg2.extras.Json(list(seen)), req.subscription_id)
            )
        conn.commit()

    return {
        "subscription_id": req.subscription_id,
        "address": sub["address"],
        "new_application_count": len(new_apps),
        "new_applications": new_apps,
        "total_nearby": len(nearby),
        "checked_at": datetime.utcnow().isoformat(),
    }


@router.get("/threat-radar/subscriptions")
def list_subscriptions():
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT id,address,email,lat,lng FROM threat_radar_subscriptions WHERE active=true")
            rows = cur.fetchall()
    return {"subscriptions": [dict(r) for r in rows]}
