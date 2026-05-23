# Kibana Dashboards

## Import Order

1. Apply index mappings first:
   ```
   curl -X PUT http://localhost:9200/api-events \
        -u elastic:changeme \
        -H 'Content-Type: application/json' \
        -d @../index-mappings/api-events-mapping.json
   ```

2. Create an Index Pattern in Kibana → Stack Management → Index Patterns:
   - Pattern: `api-events*`
   - Time field: `timestamp`

## Recommended Visualizations

| Dashboard | Description |
|---|---|
| Request Volume | Line chart of requests/min grouped by tenant |
| Error Rate | Percentage error over time per endpoint |
| Latency Percentiles | p95/p99 latency over time |
| Top Endpoints | Data table of highest-traffic endpoints |
| Error Explorer | Data table of recent error events |
| Status Code Distribution | Pie/donut chart of 2xx/4xx/5xx breakdown |
