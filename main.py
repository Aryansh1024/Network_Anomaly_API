from fastapi import FastAPI, HTTPException, Query
from rrd_reader import fetch_rrd
from anomaly_detector import zscore_anomaly, iqr_anomaly, trend_anomaly, flatline_anomaly
import os

app = FastAPI(
    title="Network Anomaly Detection API",
    description="Reads RRD time-series data and detects anomalies using statistical methods.",
    version="1.0.0",
)

# ── Data source registry ─────────────────────────────────────────────────────
# Update the file paths below to wherever you place the .rrd files on your PC
BASE_DIR = os.path.join(os.path.dirname(__file__), "data")

METRICS = {
    "mem_free": {
        "file":   "192_168_1_186_mem_free_559.rrd",
        "ds":     "mem_free",
        "device": "192.168.1.186",
        "unit":   "bytes",
        "description": "Free memory on the device",
    },
    "traffic_in": {
        "file":   "192_168_252_254_traffic_in_919.rrd",
        "ds":     "traffic_in",
        "device": "192.168.252.254",
        "unit":   "bytes/sec",
        "description": "Inbound interface traffic",
    },
    "traffic_out": {
        "file":   "192_168_252_254_traffic_in_919.rrd",
        "ds":     "traffic_out",
        "device": "192.168.252.254",
        "unit":   "bytes/sec",
        "description": "Outbound interface traffic",
    },
}


# ── Helper ───────────────────────────────────────────────────────────────────
def _get_df(metric: str, hours: int):
    if metric not in METRICS:
        raise HTTPException(status_code=404,
                            detail=f"Metric '{metric}' not found. "
                                   f"Available: {list(METRICS.keys())}")
    cfg  = METRICS[metric]
    path = os.path.join(BASE_DIR, cfg["file"])
    if not os.path.exists(path):
        raise HTTPException(status_code=500,
                            detail=f"RRD file not found at: {path}")
    return fetch_rrd(path, cfg["ds"], hours_back=hours), cfg


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/", summary="Health check")
def root():
    return {"status": "ok", "message": "Anomaly Detection API is running"}


@app.get("/metrics", summary="List all available metrics")
def list_metrics():
    return {
        k: {
            "device":      v["device"],
            "unit":        v["unit"],
            "description": v["description"],
        }
        for k, v in METRICS.items()
    }


@app.get("/data/{metric}", summary="Get raw time-series data for a metric")
def get_data(
    metric: str,
    hours: int = Query(24, ge=1, le=720, description="How many hours of data to fetch"),
):
    df, cfg = _get_df(metric, hours)
    if df.empty:
        return {"metric": metric, "device": cfg["device"],
                "count": 0, "data": []}
    return {
        "metric":  metric,
        "device":  cfg["device"],
        "unit":    cfg["unit"],
        "hours":   hours,
        "count":   len(df),
        "min":     round(df["value"].min(), 4),
        "max":     round(df["value"].max(), 4),
        "average": round(df["value"].mean(), 4),
        "data": [
            {"timestamp": str(r.timestamp), "value": round(r.value, 4)}
            for r in df.itertuples()
        ],
    }


@app.get("/anomaly/{metric}", summary="Detect anomalies in a metric")
def detect_anomaly(
    metric: str,
    hours:  int = Query(24, ge=1, le=720, description="Hours of data to analyze"),
    method: str = Query("all", enum=["all", "zscore", "iqr", "trend", "flatline"],
                        description="Detection algorithm to use"),
):
    df, cfg = _get_df(metric, hours)

    if df.empty:
        return {
            "metric":           metric,
            "device":           cfg["device"],
            "hours_analyzed":   hours,
            "data_points":      0,
            "suspected_anomaly": False,
            "anomaly_count":    0,
            "anomalies":        {},
        }

    results = {}
    if method in ("zscore", "all"):
        results["zscore"]   = zscore_anomaly(df)
    if method in ("iqr", "all"):
        results["iqr"]      = iqr_anomaly(df)
    if method in ("trend", "all"):
        results["trend"]    = trend_anomaly(df)
    if method in ("flatline", "all"):
        results["flatline"] = flatline_anomaly(df)

    total = sum(len(v) for v in results.values())

    return {
        "metric":            metric,
        "device":            cfg["device"],
        "unit":              cfg["unit"],
        "hours_analyzed":    hours,
        "data_points":       len(df),
        "suspected_anomaly": total > 0,
        "anomaly_count":     total,
        "anomalies":         results,
    }


@app.get("/anomaly/device/{device_ip}", summary="Check all metrics for a given device IP")
def detect_by_device(
    device_ip: str,
    hours: int = Query(24, ge=1, le=720),
):
    device_metrics = {
        k: v for k, v in METRICS.items() if v["device"] == device_ip
    }
    if not device_metrics:
        raise HTTPException(status_code=404,
                            detail=f"No metrics found for device {device_ip}")

    summary = {}
    for metric, cfg in device_metrics.items():
        path = os.path.join(BASE_DIR, cfg["file"])
        df   = fetch_rrd(path, cfg["ds"], hours_back=hours)
        all_anomalies = {}
        if not df.empty:
            all_anomalies = {
                "zscore":   zscore_anomaly(df),
                "iqr":      iqr_anomaly(df),
                "trend":    trend_anomaly(df),
                "flatline": flatline_anomaly(df),
            }
        total = sum(len(v) for v in all_anomalies.values())
        summary[metric] = {
            "suspected_anomaly": total > 0,
            "anomaly_count":     total,
            "data_points":       len(df),
            "anomalies":         all_anomalies,
        }

    return {
        "device":        device_ip,
        "hours_analyzed": hours,
        "metrics_checked": list(summary.keys()),
        "any_anomaly":   any(v["suspected_anomaly"] for v in summary.values()),
        "details":       summary,
    }
