-- Event volume by component and type (last 24 hours)
-- Shows which components are most active — drives product prioritization decisions
SELECT
  component,
  event_type,
  COUNT(*)                                            AS event_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
FROM `usage-analytics-pipeline.usage_analytics.usage_events`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY component, event_type
ORDER BY event_count DESC;
