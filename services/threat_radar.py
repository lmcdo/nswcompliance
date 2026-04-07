"""
Neighbour Development Threat Radar -- FastAPI router.

POST /pipeline/threat-radar/subscribe   -- add address to monitoring
POST /pipeline/threat-radar/check       -- weekly check for one subscription (Trigger.dev cron)
GET  /pipeline/threat-radar/subscriptions -- list active (used by Trigger.dev task)

Data: NSW ePlanning API (public, no auth).
Dedup: seen application numbers stored in threat_radar_subscriptions.inputs JSONB.
"""
import logging, math, os
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


def _fetch_das(council_name: str, days_back: int = WINDOW_DAYS) -> list:
    since = (datetime.utcnow()-timedelta(days=days_back)).strftime("%Y/%m/%d")
    params = {"filters": f"[{{CouncilName,{council_name}}}]",
              "pageSize": 200, "pageNumber": 1, "lodgementDateFrom": since}
    apps = []
    for url in (DA_URL, CDC_URL):
        try:
            r = requests.get(url, params=params, timeout=20)
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
            alat = float(app.get("Latitude") or app.get("Y") or 0)
            alng = float(app.get("Longitude") or app.get("X") or 0)
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
