# Architecture

## System Flow

```
Client
  │
  ▼
┌─────────────────────────────────────────┐
│  gateway-service  (port 8080)           │
│  Spring Cloud Gateway + GlobalFilter    │
│  Publishes ApiAnalyticsEvent to Kafka   │
└──────────────┬──────────────────────────┘
               │  Kafka topic: api-events
               ▼
┌─────────────────────────────────────────┐
│  analytics-service  (port 8081)         │
│  Kafka consumer → saves to ES           │
│  @Scheduled → computes aggregations     │
│  REST API for dashboards                │
└──────┬───────────────────────────┬──────┘
       │  Elasticsearch            │  Kafka topic: analytics-events
       ▼                           ▼
┌─────────────────┐   ┌─────────────────────────────┐
│  Kibana :5601   │   │  alert-service  (port 8082)  │
│  Dashboards     │   │  Evaluates thresholds        │
└─────────────────┘   │  Notifies Slack / Email      │
                      └─────────────────────────────┘

All services → OpenTelemetry Collector (4317) → Jaeger (16686)
```

## Common Configuration

All credentials and settings are centralised in `config/common-config.yml`.
Each service imports it via:

```yaml
spring:
  config:
    import: "optional:file:../config/common-config.yml"
```

Override any value with environment variables (e.g., `KAFKA_BOOTSTRAP_SERVERS`).

## Kafka Topics

| Topic | Producer | Consumer |
|---|---|---|
| `api-events` | gateway-service | analytics-service |
| `api-events-dlq` | Spring DLQ recovery | manual replay |
| `analytics-events` | analytics-service | alert-service |
