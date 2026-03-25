# Usage Analytics Pipeline — GCP

I built this to understand how companies like Rakuten, Uber, and Netflix make real-time decisions from user behavior data. Not the ML part — the plumbing underneath it. The part that answers "which feature is getting hammered right now?" and "is our checkout API about to fall over?"

The pipeline captures two kinds of events: what users are doing in the UI (clicks, page views, searches) and how the backend is responding (latency, status codes, errors). Everything flows through Pub/Sub into BigQuery, where you can actually ask interesting questions about it.

---

## How it works
```
Python publisher → Pub/Sub topic → Cloud Function → BigQuery → Looker Studio
```

**Publisher** (`publisher/publisher.py`) simulates a live product with 6 components — checkout, search, product listing, recommendations, ad banner, and user profile. Every 500ms it generates either a UI interaction event or an API request event and publishes it to a Pub/Sub topic. In a real system this would be your actual frontend and backend emitting these events.

**Pub/Sub** acts as the buffer between the publisher and the processor. The producer and consumer are completely decoupled — the publisher doesn't know or care what happens to the message after it sends it. This is the same pattern used in Kafka and RabbitMQ. The topic is `usage-events`, with a push subscription that triggers the Cloud Function automatically on every new message.

**Cloud Function** (`cloud_function/main.py`) is a serverless Python function that wakes up on every Pub/Sub message, decodes the payload, validates the fields, and writes a structured row to BigQuery. No server to manage — it scales to zero when idle and spins up instantly when events arrive.

**BigQuery** stores everything in a single `usage_events` table with a standardized schema. The schema was designed so that both UI events and API events fit in the same table — UI events leave `latency_ms` and `status_code` null, API events leave `metadata` minimal. This single-table design makes cross-event queries simple.

**Looker Studio** sits on top of BigQuery and renders live charts — event volume by component, error rates by endpoint, latency trends over time. It connects natively to BigQuery with no extra infrastructure.

---

## The schema

This was the most important design decision. I wanted one table that could handle both UI interactions and API metrics without ugly joins.

| Field | Type | Notes |
|---|---|---|
| event_id | STRING | UUID, primary key |
| event_type | STRING | `ui_interaction` or `api_request` |
| component | STRING | Which part of the product — checkout, search, etc. |
| user_id | STRING | Anonymized — consistent across sessions |
| session_id | STRING | Groups events from a single browsing session |
| timestamp | TIMESTAMP | UTC, set at publish time |
| latency_ms | INTEGER | Null for UI events, populated for API events |
| status_code | INTEGER | HTTP status — 200, 400, 404, 500, etc. |
| endpoint | STRING | `/api/checkout`, `/api/search`, etc. |
| metadata | STRING | JSON blob — action type for UI, HTTP method for API |

---

## What the queries tell you

**Event volume** — which components are getting the most traffic right now. If `checkout` suddenly spikes, either there's a sale happening or something is in a retry loop hammering the endpoint.

**API latency (p50/p95/p99)** — average latency is almost useless. p95 and p99 tell you what your worst-case users are experiencing. If p99 on `/api/checkout` creeps from 400ms to 2000ms, you're about to have a bad day. That's your signal to scale before users start complaining.

**Error rate breakdown** — 4xx vs 5xx matters. A spike in 4xx means clients are sending bad requests (maybe a frontend bug after a deploy). A spike in 5xx means your backend is failing — that's the one that pages the on-call engineer at 3am.

**User activity by component** — unique users and events per user per component. Low unique users + high events per user on a component usually means a small group of power users. High unique users + low events per user means people visit once and leave — that's a UX problem worth investigating.

---

## What I learned building this

Pub/Sub's decoupling is genuinely useful — I could shut down the Cloud Function completely, keep publishing events, and when the function came back up it would process the backlog from where it left off. That reliability property doesn't exist if you're calling an API directly.

Cloud Functions cold start is real. First invocation after idle takes ~2 seconds. For a latency-sensitive pipeline you'd want minimum instances set to 1 — costs a few cents a month but eliminates the cold start.

BigQuery's `INSERT` latency for streaming inserts is around 1-2 seconds end to end from publish to queryable. For a batch ETL pipeline this wouldn't matter, but for real-time dashboards you feel it.

IAM on GCP is more granular than I expected. The service account needs separate roles for Pub/Sub publishing, Pub/Sub subscribing, BigQuery writing, Cloud Run invoking, and Eventarc event receiving. Getting this wrong silently drops events with no obvious error — that took some debugging.

---

## Running it yourself

You'll need a GCP project with these APIs enabled: Pub/Sub, Cloud Functions, BigQuery, Cloud Build, Cloud Run, Eventarc.
```bash
git clone https://github.com/SanketJanger/usage-analytics-pipeline.git
cd usage-analytics-pipeline

# Create Pub/Sub resources
gcloud pubsub topics create usage-events
gcloud pubsub subscriptions create usage-events-sub --topic=usage-events

# Create BigQuery dataset and table
bq mk --dataset YOUR_PROJECT_ID:usage_analytics
bq mk --table YOUR_PROJECT_ID:usage_analytics.usage_events bigquery/schema.json

# Deploy the Cloud Function
gcloud functions deploy usage-event-processor \
  --gen2 --runtime=python311 --region=us-central1 \
  --source=./cloud_function --entry-point=process_event \
  --trigger-topic=usage-events

# Start publishing events
cd publisher
pip install -r requirements.txt
python publisher.py
```

After ~30 seconds you should see rows appearing in BigQuery. Run the queries in `/queries` to explore the data.

---

## Stack
Python · Google Cloud Pub/Sub · Cloud Functions (Gen2) · BigQuery · Looker Studio · Eventarc · GCP IAM

## Architecture diagram

![Architecture](screenshots/architecture.jpg)
