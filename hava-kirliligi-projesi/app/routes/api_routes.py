# app/routes/api_routes.py

import os
import math
import traceback
from datetime import datetime, timedelta
from typing import List, Optional, Any

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
import psycopg2
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from dotenv import load_dotenv

from app.routes.websocket import manager  # broadcast için

# Ortam değişkenlerini yükle
load_dotenv()

# --- Pydantic modelleri ---
class Anomaly(BaseModel):
    latitude: float
    longitude: float
    parameter: str
    value: float
    timestamp: Optional[str]

class ForecastPoint(BaseModel):
    time: str
    value: float

class HeatmapPoint(BaseModel):
    latitude: float
    longitude: float
    count: int

router = APIRouter()

def get_db_connection():
    try:
        return psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB bağlantı hatası: {e}")

# 1) Anomaly listeleme (zaman aralığı desteğiyle)
@router.get("/anomalies", response_model=List[Anomaly])
def list_anomalies(
    start: Optional[str] = Query(
        None, description="ISO formatında başlangıç zamanı, örn. 2025-04-30T00:00:00"
    ),
    end: Optional[str] = Query(
        None, description="ISO formatında bitiş zamanı, örn. 2025-04-30T23:59:59"
    ),
    limit: int = Query(100, gt=0, description="Kaç kayıt çekilsin")
):
    # Gelen sorguyu log'la ki hangi start/end geliyor görelim
    print(f"📥 /anomalies?start={start}&end={end}&limit={limit}")

    clauses: List[str] = []
    params: List[Any] = []

    if start:
        try:
            dt_start = datetime.fromisoformat(start)
        except ValueError:
            raise HTTPException(status_code=400, detail="start parametresi ISO formatında olmalı")
        clauses.append("timestamp >= %s")
        params.append(dt_start)

    if end:
        try:
            # Biraz ileri kaydır ki kullanıcı <tarih>Txx:yy girse bile,
            # o dakikadaki tüm kayıtları kapsasın
            dt_end = datetime.fromisoformat(end) + timedelta(seconds=1)
        except ValueError:
            raise HTTPException(status_code=400, detail="end parametresi ISO formatında olmalı")
        clauses.append("timestamp <= %s")
        params.append(dt_end)

    sql = """
        SELECT latitude, longitude, parameter, value, timestamp
        FROM pollution_data
    """
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY timestamp DESC NULLS LAST LIMIT %s"
    params.append(limit)

    print("▶️ Çalıştırılan SQL:", sql, params)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(sql, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        Anomaly(
            latitude=r[0],
            longitude=r[1],
            parameter=r[2],
            value=r[3],
            timestamp=r[4].isoformat() if r[4] else None
        )
        for r in rows
    ]

# 2) Anomaly broadcast
@router.post("/broadcast-anomaly")
async def broadcast_anomaly(data: Anomaly):
    await manager.broadcast_json(data.dict())
    return {"status": "broadcasted"}

# 3) Bölgesel veri endpoint’i
@router.get("/data", response_model=List[Anomaly])
def list_data(
    lat: float = Query(..., description="Merkez enlem"),
    lon: float = Query(..., description="Merkez boylam"),
    radius_km: float = Query(25.0, gt=0, description="Yarıçap (km)")
):
    lat_rad = math.radians(lat)
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * math.cos(lat_rad))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT latitude, longitude, parameter, value, timestamp
        FROM pollution_data
        WHERE latitude BETWEEN %s AND %s
          AND longitude BETWEEN %s AND %s
        ORDER BY timestamp DESC
        """,
        (lat - dlat, lat + dlat, lon - dlon, lon + dlon),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        Anomaly(
            latitude=r[0], longitude=r[1],
            parameter=r[2], value=r[3],
            timestamp=r[4].isoformat() if r[4] else None
        )
        for r in rows
    ]

# 4) Heatmap endpoint
@router.get("/heatmap", response_model=List[HeatmapPoint])
def get_heatmap(
    grid_size_deg: float = Query(0.01, gt=0, description="Grid boyutu derece cinsinden")
):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
          floor(latitude / %s) * %s AS lat_bin,
          floor(longitude / %s) * %s AS lon_bin,
          COUNT(*) AS cnt
        FROM pollution_data
        GROUP BY lat_bin, lon_bin
        """,
        (grid_size_deg, grid_size_deg, grid_size_deg, grid_size_deg),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        HeatmapPoint(latitude=r[0], longitude=r[1], count=r[2])
        for r in rows
    ]

# 5) Forecast endpoint
@router.get("/forecast", response_model=List[ForecastPoint])
def get_forecast(
    parameter: str = Query(..., description="PM2.5, PM10, NO2, SO2 veya O3"),
    hours: int = Query(24, ge=1, le=48, description="Kaç saatlik tahmin (max 48)")
):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT date_trunc('hour', timestamp) AS hr,
                   AVG(value) AS avg_val
            FROM pollution_data
            WHERE parameter = %s
              AND timestamp > NOW() - INTERVAL '72 hours'
            GROUP BY hr
            ORDER BY hr
            """,
            (parameter,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if len(rows) < 1:
            raise HTTPException(
                status_code=422,
                detail=f"{parameter} için son 72 saatte en az 1 saatlik veri gerekiyor."
            )

        df = pd.DataFrame(rows, columns=["time", "value"])
        df["time"] = pd.to_datetime(df["time"])
        df.set_index("time", inplace=True)
        df = df.asfreq("H")
        df["value"].interpolate(method="time", inplace=True)

        seasonal_periods = 24
        use_seasonal = len(df) >= seasonal_periods * 2

        model = ExponentialSmoothing(
            df["value"],
            trend="add",
            seasonal="add" if use_seasonal else None,
            seasonal_periods=seasonal_periods if use_seasonal else None
        )
        fit = model.fit(optimized=True)
        fc = fit.forecast(hours)

        return [
            ForecastPoint(time=ts.isoformat(), value=round(float(v), 2))
            for ts, v in fc.items()
        ]

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Forecast error: {e}")
