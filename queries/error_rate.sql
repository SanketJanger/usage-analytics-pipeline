-- Error rate by endpoint (4xx and 5xx breakdown)
-- Spike in error rate = something is broken, page the on-call engineer
SELECT
  endpoint,
  COUNT(*)                                                                AS total_requests,
  COUNTIF(status_code BETWEEN 400 AND 499)                               AS client_errors_4xx,
  COUNTIF(status_code BETWEEN 500 AND 599)                               AS server_errors_5xx,
  ROUND(COUNTIF(status_code >= 400) * 100.0 / COUNT(*), 2)              AS error_rate_pct,
  ROUND(COUNTIF(status_code = 200) * 100.0 / COUNT(*), 2)              AS success_rate_pct
FROM `usage-analytics-pipeline.usage_analytics.usage_events`
WHERE event_type = 'api_request'
  AND endpoint IS NOT NULL
  AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY endpoint
ORDER BY error_rate_pct DESC;
