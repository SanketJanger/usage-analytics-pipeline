-- Most active components by unique users
-- Drives recommendations and feature investment decisions
SELECT
  component,
  COUNT(DISTINCT user_id)   AS unique_users,
  COUNT(*)                  AS total_events,
  ROUND(COUNT(*) / COUNT(DISTINCT user_id), 1) AS events_per_user
FROM `usage-analytics-pipeline.usage_analytics.usage_events`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY component
ORDER BY unique_users DESC;
