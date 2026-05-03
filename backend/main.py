"""
PM2.5 Air Quality Monitor — Backend API Service (WAQI Edition)
FastAPI · Stateful (PostgreSQL) + WAQI Proxy + Prometheus Library
"""

import asyncio
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import httpx
import psycopg2
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WAQI_BASE = "https://api.waqi.info"
WAQI_TOKEN = os.getenv("WAQI_API_TOKEN")

CACHE_TTL_DATA = 1800       # 30 min
CACHE_TTL_DISCOVERY = 3600  # 1 hour for station list

THAI_BOUNDS = "5.6,97.3,20.5,105.7"

_discovery_cache: dict[str, tuple[Any, float]] = {}
_data_cache: dict[str, tuple[Any, float]] = {}

def cache_get(store: dict, key: str, ttl: float) -> Any | None:
    entry = store.get(key)
    if entry:
        value, ts = entry
        if time.time() - ts < ttl:
            return value
        del store[key]
    return None

def cache_set(store: dict, key: str, value: Any) -> None:
    store[key] = (value, time.time())

# ---------------------------------------------------------------------------
# WAQI client
# ---------------------------------------------------------------------------

_WAQI_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Thailand-PM25-Monitor/3.0",
}

async def waqi_get(endpoint: str, params: dict | None = None) -> dict:
    if not WAQI_TOKEN:
        raise HTTPException(status_code=500, detail="WAQI_API_TOKEN not configured")

    params = {**(params or {}), "token": WAQI_TOKEN}

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            url = f"{WAQI_BASE}/{endpoint}"
            resp = await client.get(url, params=params, headers=_WAQI_HEADERS)
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "ok":
                msg = data.get("data", "Unknown WAQI error")
                raise HTTPException(status_code=502, detail=f"WAQI error: {msg}")
            return data
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"WAQI returned {exc.response.status_code}: {exc.response.text[:200]}",
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"WAQI unreachable: {exc}")

# ---------------------------------------------------------------------------
# AQI helpers
# ---------------------------------------------------------------------------

def aqi_us_to_pm25_approx(aqi_us: int | None) -> float | None:
    if aqi_us is None:
        return None
    a = float(aqi_us)
    if a <= 50:
        return round(a * 12.0 / 50.0, 1)
    elif a <= 100:
        return round(12.1 + (a - 51) * (35.4 - 12.1) / 49.0, 1)
    elif a <= 150:
        return round(35.5 + (a - 101) * (55.4 - 35.5) / 49.0, 1)
    elif a <= 200:
        return round(55.5 + (a - 151) * (150.4 - 55.5) / 49.0, 1)
    elif a <= 300:
        return round(150.5 + (a - 201) * (250.4 - 150.5) / 99.0, 1)
    else:
        return round(250.5 + (a - 301) * (500.4 - 250.5) / 199.0, 1)

def pm25_to_aqi(pm25: float | None) -> dict:
    if pm25 is None:
        return {"label": "N/A", "color": "#6b7280", "level": 0}
    if pm25 <= 12.0:
        return {"label": "Good", "color": "#22c55e", "level": 1}
    if pm25 <= 35.4:
        return {"label": "Moderate", "color": "#eab308", "level": 2}
    if pm25 <= 55.4:
        return {"label": "Unhealthy for Sensitive Groups", "color": "#f97316", "level": 3}
    if pm25 <= 150.4:
        return {"label": "Unhealthy", "color": "#ef4444", "level": 4}
    if pm25 <= 250.4:
        return {"label": "Very Unhealthy", "color": "#a855f7", "level": 5}
    return {"label": "Hazardous", "color": "#7f1d1d", "level": 6}

# ---------------------------------------------------------------------------
# Discovery engine
# ---------------------------------------------------------------------------

_discovered_stations: list[dict] = []
_discovery_task: asyncio.Task | None = None

async def discover_thailand() -> list[dict]:
    global _discovered_stations
    hit = cache_get(_discovery_cache, "thailand_stations", CACHE_TTL_DISCOVERY)
    if hit is not None:
        _discovered_stations = hit
        return hit

    raw = await waqi_get("map/bounds", {"latlng": THAI_BOUNDS})
    stations = []
    for s in raw.get("data", []):
        aqi_val = s.get("aqi")
        try:
            aqi_int = int(aqi_val)
        except (ValueError, TypeError):
            aqi_int = None

        stations.append({
            "uid": s["uid"],
            "lat": s.get("lat"),
            "lon": s.get("lon"),
            "aqi": aqi_int,
        })

    cache_set(_discovery_cache, "thailand_stations", stations)
    _discovered_stations = stations
    return stations

async def _background_discovery():
    try:
        await discover_thailand()
    except Exception as exc:
        print(f"[discovery] background discovery failed: {exc}")

def start_discovery():
    global _discovery_task
    if _discovery_task is None or _discovery_task.done():
        _discovery_task = asyncio.create_task(_background_discovery())

# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

async def fetch_station_data(uid: int) -> dict | None:
    key = f"waqi:{uid}"
    hit = cache_get(_data_cache, key, CACHE_TTL_DATA)
    if hit is not None:
        return hit

    try:
        raw = await waqi_get(f"feed/@{uid}")
    except HTTPException:
        return None

    d = raw.get("data", {})
    if not d:
        return None

    city_info = d.get("city", {})
    name = city_info.get("name", "Unknown")
    geo = city_info.get("geo", [None, None])
    lat = geo[0] if geo else None
    lon = geo[1] if len(geo) > 1 else None

    iaqi = d.get("iaqi", {})
    pm25_aqi = None
    if isinstance(iaqi.get("pm25"), dict):
        pm25_aqi = iaqi["pm25"].get("v")

    pm25 = aqi_us_to_pm25_approx(pm25_aqi) if pm25_aqi is not None else None
    ts = d.get("time", {}).get("iso")

    result = {
        "id": uid,
        "name": name,
        "city": name,
        "country": "TH",
        "lat": lat,
        "lon": lon,
        "pm25": pm25,
        "updated": ts,
        "aqi": pm25_to_aqi(pm25),
    }
    cache_set(_data_cache, key, result)
    return result

# ---------------------------------------------------------------------------
# Lifespan & App Init
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    if WAQI_TOKEN:
        start_discovery()
    yield

app = FastAPI(
    title="Thailand PM2.5 Monitor — API",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── เปิดใช้งาน Prometheus Instrumentator ─────────────────────────────────────
# ตัวนี้จะสร้าง Endpoint /metrics ให้เราแบบอัตโนมัติ 
# และเก็บข้อมูล request counts, latency, status codes ให้ครบถ้วน
Instrumentator().instrument(app).expose(app)
# ─────────────────────────────────────────────────────────────────────────────

# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/locations", summary="All Thai PM2.5 monitoring stations")
async def get_locations():
    if not _discovered_stations:
        start_discovery()
        stations = cache_get(_discovery_cache, "thailand_stations", CACHE_TTL_DISCOVERY) or []
    else:
        stations = _discovered_stations

    if not stations:
        return {"count": 0, "locations": []}

    sem = asyncio.Semaphore(5)

    async def bounded_fetch(station: dict):
        async with sem:
            return await fetch_station_data(station["uid"])

    results = await asyncio.gather(*(bounded_fetch(s) for s in stations))
    locations = [r for r in results if r is not None and r["pm25"] is not None]
    locations.sort(key=lambda x: (x["pm25"] or 0), reverse=True)

    return {"count": len(locations), "locations": locations}

@app.get("/api/measurements/{location_id}", summary="24-hour PM2.5 history")
async def get_measurements(location_id: int):
    key = f"meas_{location_id}"
    hit = cache_get(_data_cache, key, CACHE_TTL_DATA)
    if hit is not None and "measurements" in hit:
        return hit

    result = {"location_id": location_id, "measurements": []}
    cache_set(_data_cache, key, result)
    return result

@app.get("/api/summary", summary="National PM2.5 aggregate statistics")
async def get_summary():
    loc_data = await get_locations()
    locations = loc_data["locations"]
    values = [l["pm25"] for l in locations if l["pm25"] is not None]

    if values:
        avg = round(sum(values) / len(values), 1)
        max_val = round(max(values), 1)
        min_val = round(min(values), 1)
        worst = max(locations, key=lambda l: l["pm25"] or 0)
    else:
        avg = max_val = min_val = None
        worst = None

    dist: dict[str, int] = defaultdict(int)
    for l in locations:
        dist[l["aqi"]["label"]] += 1

    return {
        "total_stations": len(locations),
        "stations_with_data": len(values),
        "pm25_avg": avg,
        "pm25_max": max_val,
        "pm25_min": min_val,
        "worst_station": {
            "name": worst["name"],
            "city": worst["city"],
            "pm25": worst["pm25"],
            "aqi": worst["aqi"],
        } if worst else None,
        "aqi_distribution": dict(dist),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

@app.post("/api/discover", summary="Trigger background discovery refresh")
async def trigger_discovery():
    start_discovery()
    return {
        "status": "discovery_started",
        "scope": "thailand",
        "note": "Data will appear in /api/locations once discovery completes.",
    }

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        database=os.getenv("DB_NAME", "mydatabase"),
        user=os.getenv("DB_USER", "user"),
        password=os.getenv("DB_PASSWORD", "password"),
        port=5432,
    )

class FavoriteRequest(BaseModel):
    station_name: str
    pm25_value: float

@app.post("/api/favorites", summary="Save favorite station to Database")
def add_favorite(fav: FavoriteRequest):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO favorites (station_name, pm25_value) VALUES (%s, %s)",
            (fav.station_name, fav.pm25_value),
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "success", "message": f"Saved {fav.station_name} to database"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/favorites", summary="Get favorite stations from Database")
def get_favorites():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, station_name, pm25_value, created_at FROM favorites ORDER BY created_at DESC"
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        result = [
            {"id": r[0], "station_name": r[1], "pm25_value": r[2], "created_at": r[3]}
            for r in rows
        ]
        return {"favorites": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", summary="Liveness probe")
async def health():
    return {
        "status": "ok",
        "cache_entries": len(_data_cache) + len(_discovery_cache),
        "discovered_stations": len(_discovered_stations),
    }