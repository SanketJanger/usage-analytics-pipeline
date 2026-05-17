from fastapi import FastAPI, Query
from google.cloud import bigquery
from datetime import datetime, timezone
from typing import Optional

app = FastAPI(
    title="Usage Analytics API",
    description="REST API layer over the GCP real-time usage analytics pipeline",
    version="1.0.0"
)

PROJECT_ID = "usage-analytics-pipeline"
DATASET    = "usage_analytics"
TABLE      = "usage_events"
client     = bigquery.Client(project=PROJECT_ID)

def run_query(sql: str):
    return [dict(row) for row in client.query(sql).result()]

@app.get("/health")
def health():
    result = run_query(f"""
        SELECT COUNT(*) as total_events,
               MAX(timestamp) as last_event_at
        FROM `{PROJECT_ID}.{DATASET}.{TABLE}`
    """)
    last = result[0]["last_event_at"]
    return {
        "status": "healthy",
        "total_events": result[0]["total_events"],
        "last_event_at": last.isoformat() if last else None,
        "pipeline": "GCP Pub/Sub → Cloud Function → BigQuery",
        "checked_at": datetime.now(timezone.utc).isoformat()
    }

@app.get("/events/volume")
def event_volume(hours: int = Query(default=24, ge=1, le=168)):
    rows = run_query(f"""
        SELECT component, event_type,
               COUNT(*) as event_count,
               ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as pct_of_total
        FROM `{PROJECT_ID}.{DATASET}.{TABLE}`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        GROUP BY component, event_type
        ORDER BY event_count DESC
    """)
    return {
        "window_hours": hours,
        "total_components": len(set(r["component"] for r in rows)),
        "data": rows
    }

@app.get("/events/errors")
def error_rates(hours: int = Query(default=24, ge=1, le=168)):
    rows = run_query(f"""
        SELECT endpoint,
               COUNT(*) as total_requests,
               COUNTIF(status_code BETWEEN 400 AND 499) as client_errors_4xx,
               COUNTIF(status_code BETWEEN 500 AND 599) as server_errors_5xx,
               ROUND(COUNTIF(status_code >= 400) * 100.0 / COUNT(*), 2) as error_rate_pct,
               ROUND(COUNTIF(status_code = 200) * 100.0 / COUNT(*), 2) as success_rate_pct
        FROM `{PROJECT_ID}.{DATASET}.{TABLE}`
        WHERE event_type = 'api_request'
          AND endpoint IS NOT NULL
          AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        GROUP BY endpoint
        ORDER BY error_rate_pct DESC
    """)
    return {
        "window_hours": hours,
        "alert": any(r["error_rate_pct"] > 30 for r in rows),
        "flagged_endpoints": [r["endpoint"] for r in rows if r["error_rate_pct"] > 30],
        "data": rows
    }

@app.get("/events/latest")
def latest_events(limit: int = Query(default=20, ge=1, le=100)):
    rows = run_query(f"""
        SELECT event_id, event_type, component, endpoint,
               status_code, latency_ms, timestamp
        FROM `{PROJECT_ID}.{DATASET}.{TABLE}`
        ORDER BY timestamp DESC
        LIMIT {limit}
    """)
    for r in rows:
        if r.get("timestamp"):
            r["timestamp"] = r["timestamp"].isoformat()
    return {
        "count": len(rows),
        "data": rows
    }

@app.get("/events/users")
def user_activity(hours: int = Query(default=24, ge=1, le=168)):
    rows = run_query(f"""
        SELECT component,
               COUNT(DISTINCT user_id) as unique_users,
               COUNT(*) as total_events,
               ROUND(COUNT(*) / COUNT(DISTINCT user_id), 1) as events_per_user
        FROM `{PROJECT_ID}.{DATASET}.{TABLE}`
        WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR)
        GROUP BY component
        ORDER BY unique_users DESC
    """)
    return {
        "window_hours": hours,
        "data": rows
    }
