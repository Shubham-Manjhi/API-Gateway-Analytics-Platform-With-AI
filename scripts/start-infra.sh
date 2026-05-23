#!/usr/bin/env bash
# Start all infrastructure services (Kafka, Elasticsearch, Kibana, PostgreSQL, Jaeger, OTel)
set -euo pipefail

cd "$(dirname "$0")/../docker"

echo "Starting infrastructure services..."
docker compose up -d

echo ""
echo "Waiting for services to be healthy..."
sleep 10
docker compose ps

echo ""
echo "Infrastructure ready. Service URLs:"
echo "  Kafka:          localhost:9092"
echo "  Elasticsearch:  http://localhost:9200"
echo "  Kibana:         http://localhost:5601"
echo "  Jaeger UI:      http://localhost:16686"
echo "  PostgreSQL:     localhost:5432"
echo "  OTel Collector: localhost:4317"
