# Enterprise API Gateway Analytics & Observability Platform

A production-grade, event-driven observability platform built on Spring Boot 3, Apache Kafka, Elasticsearch, and Kubernetes. Designed to intercept API traffic, aggregate real-time analytics, and surface insights through interactive dashboards — with full distributed tracing and multi-tenant support.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Development Phases](#development-phases)
  - [Phase 1 — Infrastructure Setup](#phase-1--infrastructure-setup)
  - [Phase 2 — API Gateway Service](#phase-2--api-gateway-service)
  - [Phase 3 — Analytics Service](#phase-3--analytics-service)
  - [Phase 4 — Distributed Tracing (OpenTelemetry)](#phase-4--distributed-tracing-opentelemetry)
  - [Phase 5 — Elasticsearch & Kibana Dashboards](#phase-5--elasticsearch--kibana-dashboards)
  - [Phase 6 — Alerting System](#phase-6--alerting-system)
  - [Phase 7 — Kubernetes Deployment](#phase-7--kubernetes-deployment)
  - [Phase 8 — Integration Guide](#phase-8--integration-guide)
- [Advanced Features](#advanced-features)
- [Testing](#testing)
- [License](#license)

---

## Overview

This platform provides end-to-end API observability for microservice ecosystems. It captures every API request at the gateway level, publishes structured events to Kafka, processes and aggregates them in a dedicated analytics service, and persists results in Elasticsearch for real-time Kibana visualizations. Alerts are triggered automatically on anomalies such as error spikes or latency degradation.

### Key Capabilities

| Capability | Description |
|---|---|
| **API Interception** | Captures every request/response at the gateway via `GlobalFilter` |
| **Event Streaming** | Publishes structured analytics events to Apache Kafka |
| **Real-Time Aggregation** | Computes request counts, avg/p95/p99 latency, and error rates |
| **Observability Dashboards** | Kibana dashboards for traffic, latency, and error visualization |
| **Distributed Tracing** | End-to-end traces via OpenTelemetry + Jaeger |
| **Alerting** | Slack and email alerts for latency spikes, error surges, and traffic anomalies |
| **Multi-Tenancy** | Per-tenant traffic tracking, failure metrics, and quota enforcement |
| **Kubernetes-Native** | Full Helm chart and manifest suite with HPA, Ingress, and resource limits |

---

## Architecture

```
Client Requests
      │
      ▼
┌─────────────────┐
│  API Gateway    │  ← Spring Cloud Gateway + GlobalFilter
│  (gateway-svc)  │  ← Publishes events to Kafka
└────────┬────────┘
         │ Kafka Topic: api-events
         ▼
┌─────────────────┐
│ Analytics Svc   │  ← Kafka Consumer (with retries + DLQ)
│ (analytics-svc) │  ← Aggregates metrics → Elasticsearch
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────┐
│  Elasticsearch  │────▶│     Kibana        │
└─────────────────┘     └──────────────────┘

         │ Kafka Topic: analytics-events
         ▼
┌─────────────────┐
│  Alert Service  │  ← Detects anomalies → Slack / Email
│  (alert-svc)    │
└─────────────────┘

All services export traces to:
┌──────────────────────────────┐
│  OpenTelemetry Collector      │──▶ Jaeger
└──────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Language** | Java 21 |
| **Frameworks** | Spring Boot 3, Spring Cloud Gateway |
| **Messaging** | Apache Kafka, Zookeeper |
| **Storage** | Elasticsearch, PostgreSQL |
| **Observability** | OpenTelemetry, Jaeger, Kibana |
| **Containerization** | Docker, Docker Compose |
| **Orchestration** | Kubernetes, Helm |
| **Build Tool** | Gradle |
| **Schema Registry** | Avro / Protobuf (optional) |

---

## Project Structure

```
.
├── gateway-service/          # Spring Cloud Gateway with Kafka publisher
├── analytics-service/        # Kafka consumer + Elasticsearch aggregation
├── alert-service/            # Anomaly detection + Slack/email notifications
├── k8s/                      # Kubernetes manifests and Helm chart
│   ├── deployments/
│   ├── services/
│   ├── ingress/
│   ├── configmaps/
│   ├── secrets/
│   └── hpa/
├── docker/                   # Docker Compose + supporting configs
│   ├── docker-compose.yml
│   └── otel-collector-config.yml
├── kibana/                   # Index mappings + dashboard exports
└── docs/                     # Architecture diagrams and ADRs
```

---

## Getting Started

### Prerequisites

- Java 21
- Docker & Docker Compose
- kubectl + Helm (for Kubernetes deployment)

### Run Locally

```bash
# Clone the repository
git clone https://github.com/your-username/API-Gateway-Analytics-Platform-With-AI.git
cd API-Gateway-Analytics-Platform-With-AI

# Start all infrastructure services
docker-compose -f docker/docker-compose.yml up -d

# Verify services are healthy
docker-compose ps

# Start the gateway service
cd gateway-service && ./gradlew bootRun

# Start the analytics service
cd ../analytics-service && ./gradlew bootRun

# Start the alert service
cd ../alert-service && ./gradlew bootRun
```

### Verify the Stack

| Service | URL |
|---|---|
| Kibana | http://localhost:5601 |
| Jaeger UI | http://localhost:16686 |
| Gateway | http://localhost:8080 |
| Analytics API | http://localhost:8081 |

---

## Development Phases

### Phase 1 — Infrastructure Setup

**Goal:** Provision all backing services locally via Docker Compose.

**Services provisioned:**
- Apache Kafka + Zookeeper
- Elasticsearch + Kibana
- PostgreSQL
- OpenTelemetry Collector
- Jaeger

All containers include health checks, persistent volumes, restart policies, and optimized memory settings for local development.

---

### Phase 2 — API Gateway Service

**Goal:** Intercept all API traffic and publish structured analytics events to Kafka.

**Key implementation details:**
- Built on **Spring Cloud Gateway** and **Spring Boot 3**
- `GlobalFilter` intercepts every request to calculate latency and extract metadata
- Publishes JSON-structured `ApiAnalyticsEvent` to the `api-events` Kafka topic
- Supports `X-Correlation-ID` and `X-Tenant-ID` headers
- Configures retries, timeouts, and structured JSON logging

**Core dependencies (Gradle):**
```groovy
implementation 'org.springframework.cloud:spring-cloud-starter-gateway'
implementation 'org.springframework.kafka:spring-kafka'
implementation 'io.micrometer:micrometer-tracing-bridge-otel'
```

---

### Phase 3 — Analytics Service

**Goal:** Consume Kafka events and persist aggregated metrics to Elasticsearch.

**Capabilities:**
- Kafka consumer with retry logic and Dead Letter Queue (`api-events-dlq`)
- Computes per-endpoint and per-tenant metrics: request count, avg/p95/p99 latency, error rate
- Stores aggregated metrics in Elasticsearch with structured index mappings
- Exposes REST APIs for dashboard consumption
- Multi-tenant data isolation

---

### Phase 4 — Distributed Tracing (OpenTelemetry)

**Goal:** Enable end-to-end distributed tracing across all services with zero code changes.

**Approach:**
- Uses the **OpenTelemetry Java Agent** (`-javaagent:opentelemetry-javaagent.jar`)
- Auto-instruments HTTP, Kafka producers/consumers, and JDBC
- Exports traces to Jaeger via the OpenTelemetry Collector
- Correlates traces with `X-Correlation-ID` propagation

---

### Phase 5 — Elasticsearch & Kibana Dashboards

**Goal:** Surface API analytics through interactive, real-time Kibana dashboards.

**Dashboards include:**
- Request volume over time
- Error percentage by service and tenant
- p95 / p99 latency graphs
- Top APIs by traffic
- API traffic heatmap
- Failed request explorer
- Live monitoring view

---

### Phase 6 — Alerting System

**Goal:** Automatically detect and notify on API anomalies.

**Detection rules:**
- High latency threshold breach
- Error rate spike
- Unusual traffic volume (up or down)

**Notification channels:**
- Slack (webhook integration)
- Email (SMTP)

Features: configurable thresholds, alert rate limiting, Kafka consumer with DLQ support.

---

### Phase 7 — Kubernetes Deployment

**Goal:** Deploy the full platform to Kubernetes with production-grade configurations.

**Kubernetes resources generated:**
- `Deployment` manifests for all services
- `Service` and `Ingress` definitions
- `ConfigMap` and `Secret` resources
- `HorizontalPodAutoscaler` for gateway and analytics services
- Namespace isolation
- Helm chart for parameterized deployments

---

### Phase 8 — Integration Guide

**Goal:** Integrate this platform with any existing Spring Boot application in minutes.

**Step 1 — Add Kafka dependency:**
```groovy
implementation 'org.springframework.kafka:spring-kafka'
```

**Step 2 — Add the analytics filter:**
```java
@Component
public class ApiAnalyticsFilter extends OncePerRequestFilter {
    // Capture request metadata and publish to Kafka
}
```

**Step 3 — Publish events:**
```java
kafkaTemplate.send("api-events", analyticsEvent);
```

**Step 4 — Attach OpenTelemetry agent:**
```bash
-javaagent:opentelemetry-javaagent.jar \
-Dotel.exporter.otlp.endpoint=http://otel-collector:4317
```

Existing APIs will automatically appear in Kibana, Jaeger, and any connected alerting channels.

---

## Advanced Features

| Feature | Description |
|---|---|
| **Dead Letter Queue** | Failed events routed to `api-events-dlq` for replay and debugging |
| **Correlation IDs** | `X-Correlation-ID` propagated across all services and traces |
| **Multi-Tenant Analytics** | Per-tenant traffic, failure metrics, and configurable quotas |
| **Schema Registry** | Avro/Protobuf schema enforcement for Kafka event payloads |
| **Per-Tenant Rate Limiting** | Configurable request limits enforced at the gateway layer |
| **Kafka Lag Monitoring** | Consumer group lag tracked and exposed as a dashboard metric |

---

## Testing

### Local Testing Flow

```
Existing App → Gateway → Kafka → Analytics Service → Elasticsearch → Kibana
```

### Test Scenarios

| Scenario | Expected Result |
|---|---|
| Normal API call | Event published to Kafka, visible in Kibana |
| Slow API response | High latency recorded; p95/p99 metrics updated |
| API throws exception | Error event captured; error rate increases |
| Kafka unavailable | Producer retries; circuit breaker activates |
| Invalid event payload | Routed to DLQ; original topic unaffected |
| Requests from multiple tenants | Per-tenant dashboards updated independently |

---

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file included in this repository.
