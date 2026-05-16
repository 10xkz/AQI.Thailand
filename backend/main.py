"""
PM2.5 Air Quality Monitor — Backend API Service (Air4Thai Edition)
FastAPI · Stateful (PostgreSQL) + Air4Thai Proxy + Prometheus Library
"""

import os
import time
import zlib
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import httpx
import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AIR4THAI_URL = "http://air4thai.pcd.go.th/services/getNewAQI_JSON.php"

CACHE_TTL_DATA = 1800  # 30 min

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
# Data fetching
# ---------------------------------------------------------------------------

def _parse_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def _parse_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def _air4thai_station_id(raw_id: str) -> int:
    seed = zlib.crc32(raw_id.encode("utf-8"))
    return -int(seed) if seed else -1

def _air4thai_timestamp(aqi_last: dict) -> str | None:
    date = aqi_last.get("date") if isinstance(aqi_last, dict) else None
    time_s = aqi_last.get("time") if isinstance(aqi_last, dict) else None
    if date and time_s:
        return f"{date}T{time_s}:00+07:00"
    return None

# เพิ่มฟังก์ชันดึงข้อมูลดิบรวมไว้ที่เดียว (ป้องกันการดึงซ้ำซ้อน)
async def fetch_raw_air4thai() -> dict:
    hit = cache_get(_data_cache, "air4thai:raw", CACHE_TTL_DATA)
    if hit is not None:
        return hit

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.get(AIR4THAI_URL)
            resp.raise_for_status()
            payload = resp.json()
            cache_set(_data_cache, "air4thai:raw", payload)
            return payload
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Air4Thai returned {exc.response.status_code}: {exc.response.text[:200]}",
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Air4Thai unreachable: {exc}")

async def fetch_air4thai_locations() -> list[dict]:
    hit = cache_get(_data_cache, "air4thai:stations", CACHE_TTL_DATA)
    if hit is not None:
        return hit

    # ใช้ข้อมูลดิบที่ Cache ไว้ ไม่ต้องยิง Request ใหม่
    payload = await fetch_raw_air4thai()
    stations = payload.get("stations") if isinstance(payload, dict) else []
    
    locations: list[dict] = []
    for s in stations or []:
        station_id = s.get("stationID") or s.get("stationId")
        if not station_id:
            continue

        aqi_last = s.get("AQILast") if isinstance(s, dict) else None
        if not isinstance(aqi_last, dict):
            aqi_last = {}

        pm25_val = None
        pm25_block = aqi_last.get("PM25") if isinstance(aqi_last, dict) else None
        if isinstance(pm25_block, dict):
            pm25_val = _parse_float(pm25_block.get("value"))

        if pm25_val is None:
            aqi_block = aqi_last.get("AQI") if isinstance(aqi_last, dict) else None
            aqi_val = _parse_int(aqi_block.get("aqi")) if isinstance(aqi_block, dict) else None
            if aqi_val is not None:
                pm25_val = aqi_us_to_pm25_approx(aqi_val)

        if pm25_val is None or pm25_val < 0:
            continue

        name = s.get("nameTH") or s.get("nameEN") or "Unknown"
        city = s.get("areaTH") or s.get("areaEN") or name
        lat = _parse_float(s.get("lat"))
        lon = _parse_float(s.get("long"))

        locations.append({
            "id": _air4thai_station_id(str(station_id)),
            "station_id": str(station_id),
            "name": name,
            "city": city,
            "country": "TH",
            "areaTH": s.get("areaTH"),
            "areaEN": s.get("areaEN"),
            "lat": lat,
            "lon": lon,
            "pm25": pm25_val,
            "updated": _air4thai_timestamp(aqi_last),
            "aqi": pm25_to_aqi(pm25_val),
        })

    locations.sort(key=lambda x: (x["pm25"] or 0), reverse=True)
    cache_set(_data_cache, "air4thai:stations", locations)
    return locations

# ---------------------------------------------------------------------------
# Lifespan & App Init
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
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

Instrumentator().instrument(app).expose(app)

# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/locations", summary="All Thai PM2.5 monitoring stations")
async def get_locations(source: str | None = None):
    locations = await fetch_air4thai_locations()
    return {"count": len(locations), "locations": locations, "source": "air4thai"}

@app.get("/api/measurements/{location_id}", summary="Current station data from Air4Thai")
async def get_measurements(location_id: int):
    locations = await fetch_air4thai_locations()
    loc = next((l for l in locations if l.get("id") == location_id), None)
    if not loc:
        raise HTTPException(status_code=404, detail=f"Location {location_id} not found in cache")

    station_id = loc.get("station_id")
    if not station_id:
        raise HTTPException(status_code=404, detail=f"No station_id mapping for location {location_id}")

    key = f"station:{station_id}"
    hit = cache_get(_data_cache, key, CACHE_TTL_DATA)
    if hit is not None:
        return hit

    # 👇 ใช้ข้อมูลดิบจาก Cache ทันที โดยไม่ต้อง Request ข้อมูลใหม่จากเว็บ Air4Thai แล้ว
    payload = await fetch_raw_air4thai()
    stations = payload.get("stations") if isinstance(payload, dict) else []
    station = next((s for s in stations if str(s.get("stationID")) == str(station_id)), None)

    if not station:
        raise HTTPException(status_code=404, detail=f"Station {station_id} not found in Air4Thai")

    aqi_last = station.get("AQILast") or {}
    result = {
        "location_id": location_id,
        "station_id": station_id,
        "station_name": station.get("nameTH") or station.get("nameEN") or station_id,
        "city": station.get("areaTH") or station.get("areaEN") or "",
        "lat": _parse_float(station.get("lat")),
        "lon": _parse_float(station.get("long")),
        "updated": _air4thai_timestamp(aqi_last),
        "parameters": {
            "PM25": aqi_last.get("PM25") or {"value": None, "color_id": 0, "aqi": None},
            "PM10": aqi_last.get("PM10") or {"value": None, "color_id": 0, "aqi": None},
            "O3":   aqi_last.get("O3")   or {"value": None, "color_id": 0, "aqi": None},
            "CO":   aqi_last.get("CO")   or {"value": None, "color_id": 0, "aqi": None},
            "NO2":  aqi_last.get("NO2")  or {"value": None, "color_id": 0, "aqi": None},
            "SO2":  aqi_last.get("SO2")  or {"value": None, "color_id": 0, "aqi": None},
            "AQI":  aqi_last.get("AQI")  or {"value": None, "color_id": 0, "aqi": None},
        },
    }
    cache_set(_data_cache, key, result)
    return result

@app.get("/api/summary", summary="National PM2.5 aggregate statistics")
async def get_summary(source: str | None = None):
    locations = await fetch_air4thai_locations()
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
        "source": "air4thai",
    }

@app.post("/api/discover", summary="Trigger background discovery refresh")
async def trigger_discovery():
    return {
        "status": "skipped",
        "scope": "thailand",
        "note": "Discovery is not required for Air4Thai-only mode.",
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
    station_id: str | None = None
    station_name: str
    pm25_value: float

@app.post("/api/favorites", summary="Save favorite station to Database")
def add_favorite(fav: FavoriteRequest):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO favorites (station_id, station_name, pm25_value) VALUES (%s, %s, %s)",
            (fav.station_id, fav.station_name, fav.pm25_value),
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
            "SELECT id, station_id, station_name, pm25_value, created_at FROM favorites ORDER BY created_at DESC"
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        result = [
            {"id": r[0], "station_id": r[1], "station_name": r[2], "pm25_value": r[3], "created_at": r[4]}
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
        "cache_entries": len(_data_cache),
        "discovered_stations": 0,
    }