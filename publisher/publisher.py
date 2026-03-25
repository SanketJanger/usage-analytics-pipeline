import json
import time
import uuid
import random
from datetime import datetime, timezone
from google.cloud import pubsub_v1
from faker import Faker

fake = Faker()

PROJECT_ID = "usage-analytics-pipeline"
TOPIC_ID   = "usage-events"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

COMPONENTS = ["product-listing", "checkout", "search", "user-profile", "recommendations", "ad-banner"]
ENDPOINTS  = ["/api/products", "/api/checkout", "/api/search", "/api/user", "/api/recommendations"]
UI_ACTIONS = ["page_view", "button_click", "scroll", "filter_apply", "search_query"]

def generate_ui_event(user_id, session_id):
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

def generate_api_event(user_id, session_id):
    status = random.choices([200, 201, 400, 404, 500], weights=[70, 10, 8, 7, 5])[0]
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
        "metadata":    json.dumps({"method": random.choice(["GET", "POST", "PUT"])})
    }

def publish_event(event):
    data = json.dumps(event).encode("utf-8")
    future = publisher.publish(topic_path, data)
    print(f"Published {event['event_type']} | component={event['component']} | id={event['event_id'][:8]}")
    return future.result()

if __name__ == "__main__":
    print(f"Publishing to {topic_path}")
    print("Press Ctrl+C to stop\n")
    users    = [str(uuid.uuid4()) for _ in range(20)]
    sessions = [str(uuid.uuid4()) for _ in range(50)]
    count = 0
    try:
        while True:
            user_id    = random.choice(users)
            session_id = random.choice(sessions)
            if random.random() < 0.6:
                publish_event(generate_ui_event(user_id, session_id))
            else:
                publish_event(generate_api_event(user_id, session_id))
            count += 1
            if count % 10 == 0:
                print(f"--- {count} events published ---")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"\nDone. Total events published: {count}")
