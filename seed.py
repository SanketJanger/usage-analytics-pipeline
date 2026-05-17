import json, time, uuid, random, sys
from datetime import datetime, timezone
from google.cloud import pubsub_v1

PROJECT_ID = "usage-analytics-pipeline"
TOPIC_ID   = "usage-events"

publisher  = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

COMPONENTS = ["product-listing","checkout","search","user-profile","recommendations","ad-banner"]
ENDPOINTS  = ["/api/products","/api/checkout","/api/search","/api/user","/api/recommendations"]
UI_ACTIONS = ["page_view","button_click","scroll","filter_apply","search_query"]

def generate_event(user_id, session_id):
    if random.random() < 0.6:
        return {
            "event_id":    str(uuid.uuid4()),
            "event_type":  "ui_interaction",
            "component":   random.choice(COMPONENTS),
            "user_id":     user_id,
            "session_id":  session_id,
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "latency_ms":  None,
            "status_code": None,
            "endpoint":    None,
            "metadata":    json.dumps({"action": random.choice(UI_ACTIONS)})
        }
    status = random.choices([200,201,400,404,500], weights=[70,10,8,7,5])[0]
    return {
        "event_id":    str(uuid.uuid4()),
        "event_type":  "api_request",
        "component":   random.choice(COMPONENTS),
        "user_id":     user_id,
        "session_id":  session_id,
        "timestamp":   datetime.now(timezone.utc).isoformat(),
        "latency_ms":  random.randint(20, 2000),
        "status_code": status,
        "endpoint":    random.choice(ENDPOINTS),
        "metadata":    json.dumps({"method": random.choice(["GET","POST","PUT"])})
    }

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    users    = [str(uuid.uuid4()) for _ in range(20)]
    sessions = [str(uuid.uuid4()) for _ in range(50)]
    futures  = []

    print(f"Seeding {n} events to {topic_path}")
    print("=" * 50)

    for i in range(n):
        event = generate_event(random.choice(users), random.choice(sessions))
        data  = json.dumps(event).encode("utf-8")
        futures.append(publisher.publish(topic_path, data))
        if (i + 1) % 50 == 0:
            print(f"  Published {i+1}/{n} events...")
        time.sleep(0.05)

    [f.result() for f in futures]
    print("=" * 50)
    print(f"✓ {n} events published successfully")
    print(f"  Check BigQuery in ~15 seconds")
    print(f"  Run: bq query --nouse_legacy_sql 'SELECT COUNT(*) FROM `usage-analytics-pipeline.usage_analytics.usage_events`'")

if __name__ == "__main__":
    main()
