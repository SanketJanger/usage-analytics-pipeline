import json
import base64
import logging
from datetime import datetime, timezone
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = "usage-analytics-pipeline"
DATASET_ID = "usage_analytics"
TABLE_ID   = "usage_events"

client     = bigquery.Client(project=PROJECT_ID)
table_ref  = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

def process_event(cloud_event, context=None):
    try:
        if hasattr(cloud_event, 'data'):
            raw = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
        else:
            raw = base64.b64decode(cloud_event["data"]).decode("utf-8")

        event = json.loads(raw)
        logger.info(f"Processing event: {event.get('event_id', 'unknown')[:8]}")

        ts = event.get("timestamp")
        if ts and "T" in ts:
            ts = ts.replace("+00:00", "").replace("Z", "")
            if "." in ts:
                ts = ts[:26]
        
        row = {
            "event_id":    event.get("event_id"),
            "event_type":  event.get("event_type"),
            "component":   event.get("component"),
            "user_id":     event.get("user_id"),
            "session_id":  event.get("session_id"),
            "timestamp":   ts,
            "latency_ms":  event.get("latency_ms"),
            "status_code": event.get("status_code"),
            "endpoint":    event.get("endpoint"),
            "metadata":    event.get("metadata"),
        }

        errors = client.insert_rows_json(table_ref, [row])
        if errors:
            logger.error(f"BigQuery insert errors: {errors}")
        else:
            logger.info(f"Inserted event {row['event_id'][:8]} | type={row['event_type']} | component={row['component']}")

    except Exception as e:
        logger.error(f"Failed to process event: {e}")
        raise
