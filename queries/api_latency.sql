-- API latency percentiles by endpoint
-- p95/p99 spikes = scale up warning; used for capacity planning
SELECT
  endpoint,
  COUNT(*)                                                        AS request_count,
  ROUND(AVG(latency_ms), 0)                                       AS avg_latency_ms,
  ROUND(PERCENTILE_CONT(latency_ms, 0.50) OVER (PARTITION BY endpoint), 0) AS p50_ms,
  ROUND(PERCENTILE_CONT(latency_ms, 0.95) OVER (PARTITION BY endpoint), 0) AS p95_ms,
  ROUND(PERCENTILE_CONT(latency_ms, 0.99) OVER (PARTITION BY endpoint), 0) AS p99_ms
FROM `usage-analytics-pipeline.usage_analytics.usage_events`
WHERE event_type = 'api_request'
  AND endpoint IS NOT NULL
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY endpoint, latency_ms
ORDER BY avg_latency_ms DESC;
