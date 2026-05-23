#!/usr/bin/env python3
"""
Generates the entire API Gateway Analytics Platform project structure.
Run from the project root: python3 scripts/generate_project.py
"""

import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def write(rel_path, content):
    full_path = os.path.join(BASE, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  + {rel_path}")

print(f"Generating project at: {BASE}\n")

# ==============================================================
# COMMON CONFIG
# ==============================================================
write("config/common-config.yml", """\
# ==============================================================
#  COMMON CONFIGURATION - API Gateway Analytics Platform
#  All shared credentials and settings live here.
#  Each microservice imports this file via spring.config.import.
#
#  TO USE: update the placeholder values or set the environment
#  variables listed in ${...} expressions.
#
#  For local dev, run from each service directory so the
#  relative path ../config/common-config.yml resolves correctly.
# ==============================================================

# ---------------------------------------------------------------
# Apache Kafka
# ---------------------------------------------------------------
spring:
  kafka:
    bootstrap-servers: ${KAFKA_BOOTSTRAP_SERVERS:localhost:9092}

  # ---------------------------------------------------------------
  # Elasticsearch
  # ---------------------------------------------------------------
  elasticsearch:
    uris: ${ELASTICSEARCH_URIS:http://localhost:9200}
    username: ${ELASTICSEARCH_USERNAME:elastic}
    password: ${ELASTICSEARCH_PASSWORD:changeme}
    connection-timeout: 5s
    socket-timeout: 30s

  # ---------------------------------------------------------------
  # PostgreSQL (analytics-service raw event storage)
  # ---------------------------------------------------------------
  datasource:
    url: jdbc:postgresql://${POSTGRES_HOST:localhost}:${POSTGRES_PORT:5432}/${POSTGRES_DB:analytics_db}
    username: ${POSTGRES_USERNAME:analytics_user}
    password: ${POSTGRES_PASSWORD:analytics_pass}
    driver-class-name: org.postgresql.Driver

  # ---------------------------------------------------------------
  # Email / SMTP (alert-service notifications)
  # ---------------------------------------------------------------
  mail:
    host: ${SMTP_HOST:smtp.gmail.com}
    port: ${SMTP_PORT:587}
    username: ${SMTP_USERNAME:your-email@gmail.com}
    password: ${SMTP_PASSWORD:your-app-password}
    properties:
      mail.smtp.auth: true
      mail.smtp.starttls.enable: true

# ---------------------------------------------------------------
# Platform - Kafka Topic Names
# ---------------------------------------------------------------
platform:
  kafka:
    topics:
      api-events: ${KAFKA_TOPIC_API_EVENTS:api-events}
      api-events-dlq: ${KAFKA_TOPIC_API_EVENTS_DLQ:api-events-dlq}
      analytics-events: ${KAFKA_TOPIC_ANALYTICS_EVENTS:analytics-events}

  # ---------------------------------------------------------------
  # Slack Notifications (alert-service)
  # ---------------------------------------------------------------
  slack:
    webhook-url: ${SLACK_WEBHOOK_URL:https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK}
    enabled: ${SLACK_NOTIFICATIONS_ENABLED:true}

  # ---------------------------------------------------------------
  # Email Notifications (alert-service)
  # ---------------------------------------------------------------
  email:
    from: ${EMAIL_FROM:alerts@your-domain.com}
    to: ${EMAIL_RECIPIENTS:team@your-domain.com}
    enabled: ${EMAIL_NOTIFICATIONS_ENABLED:false}

  # ---------------------------------------------------------------
  # Alert Thresholds
  # ---------------------------------------------------------------
  alert:
    latency-threshold-ms: ${ALERT_LATENCY_THRESHOLD_MS:5000}
    error-rate-threshold: ${ALERT_ERROR_RATE_THRESHOLD:0.10}
    traffic-spike-multiplier: ${ALERT_TRAFFIC_SPIKE_MULTIPLIER:3.0}
    min-sample-size: ${ALERT_MIN_SAMPLE_SIZE:10}
    cooldown-minutes: ${ALERT_COOLDOWN_MINUTES:5}

  # ---------------------------------------------------------------
  # OpenTelemetry Collector
  # ---------------------------------------------------------------
  otel:
    endpoint: ${OTEL_EXPORTER_OTLP_ENDPOINT:http://localhost:4317}
    service-name: ${OTEL_SERVICE_NAME:api-gateway-platform}

  # ---------------------------------------------------------------
  # Multi-Tenancy
  # ---------------------------------------------------------------
  multi-tenancy:
    default-tenant-id: ${DEFAULT_TENANT_ID:default}
    rate-limit-enabled: ${RATE_LIMIT_ENABLED:true}
    default-rate-limit-per-minute: ${DEFAULT_RATE_LIMIT_PER_MINUTE:1000}
""")

# ==============================================================
# DOCKER COMPOSE
# ==============================================================
write("docker/docker-compose.yml", """\
version: '3.8'

# All credentials/ports are sourced from config/common-config.yml
# at the application level. Docker Compose uses matching env vars.

services:

  # --------------------------------------------------------
  # Apache ZooKeeper
  # --------------------------------------------------------
  zookeeper:
    image: confluentinc/cp-zookeeper:7.6.0
    container_name: zookeeper
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"
    healthcheck:
      test: ["CMD", "bash", "-c", "echo ruok | nc localhost 2181"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # --------------------------------------------------------
  # Apache Kafka
  # --------------------------------------------------------
  kafka:
    image: confluentinc/cp-kafka:7.6.0
    container_name: kafka
    depends_on:
      zookeeper:
        condition: service_healthy
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
      KAFKA_LOG_RETENTION_HOURS: 168
      KAFKA_HEAP_OPTS: "-Xmx512m -Xms256m"
    healthcheck:
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9092"]
      interval: 15s
      timeout: 10s
      retries: 10
    restart: unless-stopped

  # --------------------------------------------------------
  # Elasticsearch
  # --------------------------------------------------------
  elasticsearch:
    image: elasticsearch:8.13.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=true
      - ELASTIC_PASSWORD=${ELASTICSEARCH_PASSWORD:-changeme}
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    ports:
      - "9200:9200"
    volumes:
      - es-data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -s -u elastic:${ELASTICSEARCH_PASSWORD:-changeme} http://localhost:9200/_cluster/health | grep -qv '\"status\":\"red\"'"]
      interval: 15s
      timeout: 10s
      retries: 10
    restart: unless-stopped

  # --------------------------------------------------------
  # Kibana
  # --------------------------------------------------------
  kibana:
    image: kibana:8.13.0
    container_name: kibana
    depends_on:
      elasticsearch:
        condition: service_healthy
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
      - ELASTICSEARCH_USERNAME=elastic
      - ELASTICSEARCH_PASSWORD=${ELASTICSEARCH_PASSWORD:-changeme}
    restart: unless-stopped

  # --------------------------------------------------------
  # PostgreSQL
  # --------------------------------------------------------
  postgres:
    image: postgres:16-alpine
    container_name: postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-analytics_db}
      POSTGRES_USER: ${POSTGRES_USERNAME:-analytics_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-analytics_pass}
    ports:
      - "5432:5432"
    volumes:
      - pg-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USERNAME:-analytics_user} -d ${POSTGRES_DB:-analytics_db}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # --------------------------------------------------------
  # Jaeger (Distributed Tracing)
  # --------------------------------------------------------
  jaeger:
    image: jaegertracing/all-in-one:1.57
    container_name: jaeger
    ports:
      - "16686:16686"   # Jaeger UI
      - "14250:14250"   # gRPC collector
      - "14268:14268"   # HTTP collector
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    restart: unless-stopped

  # --------------------------------------------------------
  # OpenTelemetry Collector
  # --------------------------------------------------------
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.100.0
    container_name: otel-collector
    command: ["--config=/etc/otel-collector-config.yml"]
    volumes:
      - ./otel-collector-config.yml:/etc/otel-collector-config.yml:ro
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
      - "8888:8888"   # Prometheus metrics
    depends_on:
      - jaeger
    restart: unless-stopped

volumes:
  es-data:
    driver: local
  pg-data:
    driver: local
""")

write("docker/otel-collector-config.yml", """\
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 1024
  memory_limiter:
    check_interval: 1s
    limit_mib: 300

exporters:
  otlp/jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true
  logging:
    verbosity: detailed

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/jaeger, logging]
""")

# ==============================================================
# GATEWAY SERVICE
# ==============================================================
write("gateway-service/build.gradle", """\
plugins {
    id 'org.springframework.boot'
    id 'io.spring.dependency-management'
}

dependencies {
    implementation 'org.springframework.cloud:spring-cloud-starter-gateway'
    implementation 'org.springframework.boot:spring-boot-starter-actuator'
    implementation 'org.springframework.kafka:spring-kafka'
    implementation 'io.micrometer:micrometer-tracing-bridge-otel'
    implementation 'io.opentelemetry:opentelemetry-exporter-otlp'
    implementation 'net.logstash.logback:logstash-logback-encoder:7.4'
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
    testImplementation 'org.springframework.kafka:spring-kafka-test'
    testImplementation 'io.projectreactor:reactor-test'
}

dependencyManagement {
    imports {
        mavenBom "org.springframework.cloud:spring-cloud-dependencies:2023.0.2"
    }
}
""")

write("gateway-service/src/main/java/com/platform/gateway/GatewayApplication.java", """\
package com.platform.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class GatewayApplication {
    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }
}
""")

write("gateway-service/src/main/java/com/platform/gateway/model/ApiAnalyticsEvent.java", """\
package com.platform.gateway.model;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * Structured analytics event published to the Kafka 'api-events' topic
 * for every request intercepted by the gateway.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ApiAnalyticsEvent {

    /** Unique event identifier (UUID). */
    private String eventId;

    /** Time the request was completed. */
    @JsonFormat(shape = JsonFormat.Shape.STRING)
    private Instant timestamp;

    /** Tenant identifier from X-Tenant-ID header. */
    private String tenantId;

    /** Correlation ID from X-Correlation-ID header (generated if absent). */
    private String correlationId;

    /** HTTP method (GET, POST, PUT, DELETE, etc.). */
    private String method;

    /** Request path. */
    private String path;

    /** Request host. */
    private String host;

    /** HTTP response status code. */
    private int statusCode;

    /** End-to-end latency in milliseconds. */
    private long latencyMs;

    /** Originating client IP address. */
    private String clientIp;

    /** User-Agent header value. */
    private String userAgent;

    /** Request Content-Length (null if not present). */
    private Long requestSize;

    /** Response Content-Length (null if not present). */
    private Long responseSize;

    /** True if the response status code is 4xx or 5xx. */
    private boolean error;

    /** Error message or exception detail (if available). */
    private String errorMessage;

    /** Name of the originating service. */
    private String serviceName;
}
""")

write("gateway-service/src/main/java/com/platform/gateway/config/KafkaProducerConfig.java", """\
package com.platform.gateway.config;

import com.platform.gateway.model.ApiAnalyticsEvent;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.DefaultKafkaProducerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;
import org.springframework.kafka.support.serializer.JsonSerializer;

import java.util.HashMap;
import java.util.Map;

@Configuration
public class KafkaProducerConfig {

    @Value("${spring.kafka.bootstrap-servers:localhost:9092}")
    private String bootstrapServers;

    @Bean
    public ProducerFactory<String, ApiAnalyticsEvent> producerFactory() {
        Map<String, Object> props = new HashMap<>();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, JsonSerializer.class);
        props.put(ProducerConfig.ACKS_CONFIG, "1");
        props.put(ProducerConfig.RETRIES_CONFIG, 3);
        props.put(ProducerConfig.RETRY_BACKOFF_MS_CONFIG, 500);
        props.put(ProducerConfig.COMPRESSION_TYPE_CONFIG, "snappy");
        props.put(JsonSerializer.ADD_TYPE_INFO_HEADERS, false);
        return new DefaultKafkaProducerFactory<>(props);
    }

    @Bean
    public KafkaTemplate<String, ApiAnalyticsEvent> kafkaTemplate(
            ProducerFactory<String, ApiAnalyticsEvent> producerFactory) {
        return new KafkaTemplate<>(producerFactory);
    }
}
""")

write("gateway-service/src/main/java/com/platform/gateway/filter/AnalyticsGlobalFilter.java", """\
package com.platform.gateway.filter;

import com.platform.gateway.model.ApiAnalyticsEvent;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.net.InetSocketAddress;
import java.time.Instant;
import java.util.UUID;

/**
 * Global reactive filter that intercepts every inbound request,
 * measures end-to-end latency, and publishes a structured
 * {@link ApiAnalyticsEvent} to the Kafka 'api-events' topic.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AnalyticsGlobalFilter implements GlobalFilter, Ordered {

    private final KafkaTemplate<String, ApiAnalyticsEvent> kafkaTemplate;

    @Value("${platform.kafka.topics.api-events:api-events}")
    private String apiEventsTopic;

    @Value("${platform.multi-tenancy.default-tenant-id:default}")
    private String defaultTenantId;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        final long startTime = System.currentTimeMillis();

        // Ensure correlation ID is present in the request
        String incomingCorrelationId = exchange.getRequest().getHeaders().getFirst("X-Correlation-ID");
        final String correlationId = (incomingCorrelationId != null && !incomingCorrelationId.isBlank())
                ? incomingCorrelationId
                : UUID.randomUUID().toString();

        ServerHttpRequest mutatedRequest = exchange.getRequest()
                .mutate()
                .header("X-Correlation-ID", correlationId)
                .build();

        ServerWebExchange mutatedExchange = exchange.mutate()
                .request(mutatedRequest)
                .build();

        return chain.filter(mutatedExchange)
                .doFinally(signalType -> {
                    try {
                        long latencyMs = System.currentTimeMillis() - startTime;
                        publishAnalyticsEvent(mutatedExchange, latencyMs, correlationId);
                    } catch (Exception ex) {
                        log.error("Failed to publish analytics event: {}", ex.getMessage(), ex);
                    }
                });
    }

    private void publishAnalyticsEvent(ServerWebExchange exchange, long latencyMs, String correlationId) {
        ServerHttpRequest request = exchange.getRequest();
        ServerHttpResponse response = exchange.getResponse();

        int statusCode = response.getStatusCode() != null ? response.getStatusCode().value() : 0;
        boolean isError = statusCode >= 400;

        String tenantId = request.getHeaders().getFirst("X-Tenant-ID");
        if (tenantId == null || tenantId.isBlank()) {
            tenantId = defaultTenantId;
        }

        long reqContentLength = request.getHeaders().getContentLength();
        Long requestSize = reqContentLength > 0 ? reqContentLength : null;

        ApiAnalyticsEvent event = ApiAnalyticsEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .timestamp(Instant.now())
                .tenantId(tenantId)
                .correlationId(correlationId)
                .method(request.getMethod().name())
                .path(request.getPath().value())
                .host(request.getURI().getHost())
                .statusCode(statusCode)
                .latencyMs(latencyMs)
                .clientIp(extractClientIp(request))
                .userAgent(request.getHeaders().getFirst("User-Agent"))
                .requestSize(requestSize)
                .error(isError)
                .serviceName("gateway-service")
                .build();

        kafkaTemplate.send(apiEventsTopic, tenantId, event)
                .whenComplete((result, ex) -> {
                    if (ex != null) {
                        log.error("Kafka publish failed [topic={}]: {}", apiEventsTopic, ex.getMessage());
                    } else {
                        log.debug("Event published [eventId={}, path={}, status={}, latency={}ms]",
                                event.getEventId(), event.getPath(), event.getStatusCode(), event.getLatencyMs());
                    }
                });
    }

    private String extractClientIp(ServerHttpRequest request) {
        String xForwardedFor = request.getHeaders().getFirst("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isBlank()) {
            return xForwardedFor.split(",")[0].trim();
        }
        InetSocketAddress remote = request.getRemoteAddress();
        return remote != null ? remote.getAddress().getHostAddress() : "unknown";
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }
}
""")

write("gateway-service/src/main/resources/application.yml", """\
spring:
  application:
    name: gateway-service

  # ---------------------------------------------------------------
  # Import the shared credentials/config from the common config file.
  # Path is relative to the working directory (the service root when
  # running via ./gradlew bootRun from gateway-service/).
  # Override at runtime with:
  #   SPRING_CONFIG_IMPORT=optional:file:/config/common-config.yml
  # ---------------------------------------------------------------
  config:
    import: "optional:file:../config/common-config.yml"

  cloud:
    gateway:
      default-filters:
        - DedupeResponseHeader=Access-Control-Allow-Credentials Access-Control-Allow-Origin
      globalcors:
        cors-configurations:
          '[/**]':
            allowedOrigins: "*"
            allowedMethods: "*"
            allowedHeaders: "*"

      # Add your backend service routes below.
      # Example:
      routes:
        # - id: sample-backend
        #   uri: ${SAMPLE_BACKEND_URI:http://localhost:8090}
        #   predicates:
        #     - Path=/api/sample/**
        #   filters:
        #     - StripPrefix=2

server:
  port: ${GATEWAY_PORT:8080}

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
  endpoint:
    health:
      show-details: always
  tracing:
    sampling:
      probability: 1.0

logging:
  level:
    com.platform: DEBUG
    org.springframework.cloud.gateway: INFO
  pattern:
    console: "%d{ISO8601} [%thread] %-5level [%X{traceId}/%X{spanId}] %logger{36} - %msg%n"
""")

print("\nGateway service created.")

# ==============================================================
# ANALYTICS SERVICE
# ==============================================================
write("analytics-service/build.gradle", """\
plugins {
    id 'org.springframework.boot'
    id 'io.spring.dependency-management'
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-actuator'
    implementation 'org.springframework.boot:spring-boot-starter-data-elasticsearch'
    implementation 'org.springframework.kafka:spring-kafka'
    implementation 'io.micrometer:micrometer-tracing-bridge-otel'
    implementation 'io.opentelemetry:opentelemetry-exporter-otlp'
    implementation 'net.logstash.logback:logstash-logback-encoder:7.4'
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
    testImplementation 'org.springframework.kafka:spring-kafka-test'
}
""")

write("analytics-service/src/main/java/com/platform/analytics/AnalyticsApplication.java", """\
package com.platform.analytics;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class AnalyticsApplication {
    public static void main(String[] args) {
        SpringApplication.run(AnalyticsApplication.class, args);
    }
}
""")

write("analytics-service/src/main/java/com/platform/analytics/model/ApiAnalyticsEvent.java", """\
package com.platform.analytics.model;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/** Mirrors the gateway's ApiAnalyticsEvent schema (received from Kafka). */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class ApiAnalyticsEvent {
    private String eventId;
    @JsonFormat(shape = JsonFormat.Shape.STRING)
    private Instant timestamp;
    private String tenantId;
    private String correlationId;
    private String method;
    private String path;
    private String host;
    private int statusCode;
    private long latencyMs;
    private String clientIp;
    private String userAgent;
    private Long requestSize;
    private Long responseSize;
    private boolean error;
    private String errorMessage;
    private String serviceName;
}
""")

write("analytics-service/src/main/java/com/platform/analytics/model/ApiEventDocument.java", """\
package com.platform.analytics.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.elasticsearch.annotations.*;

import java.time.Instant;

/** Elasticsearch document stored in the 'api-events' index for every API call. */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(indexName = "api-events")
@Setting(settingPath = "elasticsearch/settings.json")
public class ApiEventDocument {

    @Id
    private String id;

    @Field(type = FieldType.Date, format = DateFormat.date_time)
    private Instant timestamp;

    @Field(type = FieldType.Keyword)
    private String tenantId;

    @Field(type = FieldType.Keyword)
    private String correlationId;

    @Field(type = FieldType.Keyword)
    private String method;

    @Field(type = FieldType.Keyword)
    private String path;

    @Field(type = FieldType.Keyword)
    private String host;

    @Field(type = FieldType.Integer)
    private int statusCode;

    @Field(type = FieldType.Long)
    private long latencyMs;

    @Field(type = FieldType.Keyword)
    private String clientIp;

    @Field(type = FieldType.Text)
    private String userAgent;

    @Field(type = FieldType.Boolean)
    private boolean error;

    @Field(type = FieldType.Text)
    private String errorMessage;

    @Field(type = FieldType.Keyword)
    private String serviceName;

    /** Composite field: "METHOD /path" for easy aggregation. */
    @Field(type = FieldType.Keyword)
    private String endpoint;
}
""")

write("analytics-service/src/main/java/com/platform/analytics/model/AnalyticsAggregation.java", """\
package com.platform.analytics.model;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * Aggregated metrics for a single tenant+endpoint window,
 * published to the Kafka 'analytics-events' topic and consumed
 * by the alert-service.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AnalyticsAggregation {
    private String tenantId;
    private String endpoint;

    @JsonFormat(shape = JsonFormat.Shape.STRING)
    private Instant windowStart;

    @JsonFormat(shape = JsonFormat.Shape.STRING)
    private Instant windowEnd;

    private long requestCount;
    private double avgLatencyMs;
    private double p95LatencyMs;
    private double p99LatencyMs;
    private long errorCount;
    private double errorRate;
    private String service;
}
""")

write("analytics-service/src/main/java/com/platform/analytics/repository/ApiEventRepository.java", """\
package com.platform.analytics.repository;

import com.platform.analytics.model.ApiEventDocument;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.elasticsearch.repository.ElasticsearchRepository;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;

@Repository
public interface ApiEventRepository extends ElasticsearchRepository<ApiEventDocument, String> {

    Page<ApiEventDocument> findByTenantId(String tenantId, Pageable pageable);

    List<ApiEventDocument> findByTenantIdAndTimestampBetween(String tenantId, Instant from, Instant to);

    Page<ApiEventDocument> findByTenantIdAndTimestampBetween(
            String tenantId, Instant from, Instant to, Pageable pageable);

    Page<ApiEventDocument> findByTenantIdAndErrorIsTrue(String tenantId, Pageable pageable);

    long countByTenantIdAndTimestampBetween(String tenantId, Instant from, Instant to);

    long countByTenantIdAndErrorIsTrueAndTimestampBetween(String tenantId, Instant from, Instant to);
}
""")

write("analytics-service/src/main/java/com/platform/analytics/config/KafkaConfig.java", """\
package com.platform.analytics.config;

import com.platform.analytics.model.ApiAnalyticsEvent;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.*;
import org.springframework.kafka.listener.DeadLetterPublishingRecoverer;
import org.springframework.kafka.listener.DefaultErrorHandler;
import org.springframework.kafka.support.serializer.ErrorHandlingDeserializer;
import org.springframework.kafka.support.serializer.JsonDeserializer;
import org.springframework.kafka.support.serializer.JsonSerializer;
import org.springframework.util.backoff.FixedBackOff;

import java.util.HashMap;
import java.util.Map;

@Configuration
public class KafkaConfig {

    @Value("${spring.kafka.bootstrap-servers:localhost:9092}")
    private String bootstrapServers;

    @Value("${spring.kafka.consumer.group-id:analytics-service-group}")
    private String groupId;

    // ----------------------------------------------------------
    // Producer (for DLQ publishing and analytics-events topic)
    // ----------------------------------------------------------
    @Bean
    public ProducerFactory<String, Object> producerFactory() {
        Map<String, Object> props = new HashMap<>();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, JsonSerializer.class);
        props.put(ProducerConfig.ACKS_CONFIG, "1");
        props.put(ProducerConfig.RETRIES_CONFIG, 3);
        props.put(JsonSerializer.ADD_TYPE_INFO_HEADERS, false);
        return new DefaultKafkaProducerFactory<>(props);
    }

    @Bean
    public KafkaTemplate<String, Object> kafkaTemplate(ProducerFactory<String, Object> pf) {
        return new KafkaTemplate<>(pf);
    }

    // ----------------------------------------------------------
    // Consumer (for api-events topic)
    // ----------------------------------------------------------
    @Bean
    public ConsumerFactory<String, ApiAnalyticsEvent> consumerFactory() {
        Map<String, Object> props = new HashMap<>();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, groupId);
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        props.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, 500);
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, ErrorHandlingDeserializer.class);
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, ErrorHandlingDeserializer.class);
        props.put(ErrorHandlingDeserializer.KEY_DESERIALIZER_CLASS, StringDeserializer.class);
        props.put(ErrorHandlingDeserializer.VALUE_DESERIALIZER_CLASS, JsonDeserializer.class);
        props.put(JsonDeserializer.VALUE_DEFAULT_TYPE, ApiAnalyticsEvent.class.getName());
        props.put(JsonDeserializer.TRUSTED_PACKAGES,
                "com.platform.gateway.model,com.platform.analytics.model");
        return new DefaultKafkaConsumerFactory<>(props);
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, ApiAnalyticsEvent> kafkaListenerContainerFactory(
            ConsumerFactory<String, ApiAnalyticsEvent> cf,
            KafkaTemplate<String, Object> kafkaTemplate) {

        ConcurrentKafkaListenerContainerFactory<String, ApiAnalyticsEvent> factory =
                new ConcurrentKafkaListenerContainerFactory<>();
        factory.setConsumerFactory(cf);
        factory.setConcurrency(3);

        // Dead Letter Queue: failed messages go to <topic>-dlq
        DeadLetterPublishingRecoverer recoverer = new DeadLetterPublishingRecoverer(kafkaTemplate);
        DefaultErrorHandler errorHandler = new DefaultErrorHandler(recoverer, new FixedBackOff(1000L, 3));
        factory.setCommonErrorHandler(errorHandler);

        return factory;
    }
}
""")

write("analytics-service/src/main/java/com/platform/analytics/consumer/ApiEventConsumer.java", """\
package com.platform.analytics.consumer;

import com.platform.analytics.model.ApiAnalyticsEvent;
import com.platform.analytics.service.MetricsAggregationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Component;

/**
 * Kafka consumer that receives API analytics events from the gateway
 * and delegates to {@link MetricsAggregationService} for persistence.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ApiEventConsumer {

    private final MetricsAggregationService metricsAggregationService;

    @KafkaListener(
            topics = "${platform.kafka.topics.api-events:api-events}",
            groupId = "${spring.kafka.consumer.group-id:analytics-service-group}",
            containerFactory = "kafkaListenerContainerFactory"
    )
    public void consume(
            @Payload ApiAnalyticsEvent event,
            @Header(KafkaHeaders.RECEIVED_TOPIC) String topic,
            @Header(KafkaHeaders.RECEIVED_PARTITION) int partition,
            @Header(KafkaHeaders.OFFSET) long offset) {

        log.debug("Received event [topic={}, partition={}, offset={}] eventId={}",
                topic, partition, offset, event.getEventId());

        try {
            metricsAggregationService.processEvent(event);
        } catch (Exception ex) {
            log.error("Error processing event eventId={}: {}", event.getEventId(), ex.getMessage(), ex);
            throw ex; // Re-throw so DLQ error handler can route to api-events-dlq
        }
    }
}
""")

write("analytics-service/src/main/java/com/platform/analytics/service/MetricsAggregationService.java", """\
package com.platform.analytics.service;

import com.platform.analytics.model.AnalyticsAggregation;
import com.platform.analytics.model.ApiAnalyticsEvent;
import com.platform.analytics.model.ApiEventDocument;
import com.platform.analytics.repository.ApiEventRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Core analytics service:
 * <ul>
 *   <li>Persists each {@link ApiAnalyticsEvent} as an {@link ApiEventDocument} in Elasticsearch.</li>
 *   <li>Every 60 s, computes per-tenant/endpoint aggregations and publishes to the
 *       analytics-events Kafka topic for the alert-service.</li>
 * </ul>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class MetricsAggregationService {

    private final ApiEventRepository eventRepository;
    private final KafkaTemplate<String, Object> kafkaTemplate;

    @Value("${platform.kafka.topics.analytics-events:analytics-events}")
    private String analyticsEventsTopic;

    /** Persist an inbound API event to Elasticsearch. */
    public void processEvent(ApiAnalyticsEvent event) {
        ApiEventDocument doc = ApiEventDocument.builder()
                .id(event.getEventId())
                .timestamp(event.getTimestamp())
                .tenantId(event.getTenantId())
                .correlationId(event.getCorrelationId())
                .method(event.getMethod())
                .path(event.getPath())
                .host(event.getHost())
                .statusCode(event.getStatusCode())
                .latencyMs(event.getLatencyMs())
                .clientIp(event.getClientIp())
                .userAgent(event.getUserAgent())
                .error(event.isError())
                .errorMessage(event.getErrorMessage())
                .serviceName(event.getServiceName())
                .endpoint(event.getMethod() + " " + event.getPath())
                .build();

        eventRepository.save(doc);
        log.debug("Saved event {} to Elasticsearch", event.getEventId());
    }

    /**
     * Runs every 60 seconds. Queries Elasticsearch for the past minute's events,
     * computes aggregations per tenant+endpoint, and publishes them to Kafka.
     */
    @Scheduled(fixedDelayString = "${platform.aggregation.interval-ms:60000}")
    public void computeAndPublishAggregations() {
        Instant windowEnd = Instant.now();
        Instant windowStart = windowEnd.minus(1, ChronoUnit.MINUTES);

        log.debug("Computing aggregations for window [{} → {}]", windowStart, windowEnd);

        // Retrieve all events in the window (across all tenants)
        // In production, paginate or use ES aggregation API for large volumes
        List<ApiEventDocument> events = eventRepository.findAll()
                .stream()
                .filter(e -> e.getTimestamp() != null
                        && !e.getTimestamp().isBefore(windowStart)
                        && !e.getTimestamp().isAfter(windowEnd))
                .collect(Collectors.toList());

        if (events.isEmpty()) {
            log.debug("No events in aggregation window — skipping publish.");
            return;
        }

        // Group by tenantId + endpoint
        Map<String, List<ApiEventDocument>> grouped = events.stream()
                .collect(Collectors.groupingBy(
                        e -> e.getTenantId() + "|" + e.getEndpoint()
                ));

        grouped.forEach((key, docs) -> {
            String[] parts = key.split("\\|", 2);
            String tenantId = parts[0];
            String endpoint = parts.length > 1 ? parts[1] : "unknown";

            List<Long> latencies = docs.stream()
                    .map(ApiEventDocument::getLatencyMs)
                    .sorted()
                    .collect(Collectors.toList());

            long errorCount = docs.stream().filter(ApiEventDocument::isError).count();
            double errorRate = docs.isEmpty() ? 0.0 : (double) errorCount / docs.size();

            AnalyticsAggregation agg = AnalyticsAggregation.builder()
                    .tenantId(tenantId)
                    .endpoint(endpoint)
                    .windowStart(windowStart)
                    .windowEnd(windowEnd)
                    .requestCount(docs.size())
                    .avgLatencyMs(latencies.stream().mapToLong(Long::longValue).average().orElse(0))
                    .p95LatencyMs(percentile(latencies, 95))
                    .p99LatencyMs(percentile(latencies, 99))
                    .errorCount(errorCount)
                    .errorRate(errorRate)
                    .service("analytics-service")
                    .build();

            kafkaTemplate.send(analyticsEventsTopic, tenantId, agg);
            log.debug("Published aggregation [tenant={}, endpoint={}, requests={}, errRate={:.2f}]",
                    tenantId, endpoint, docs.size(), errorRate);
        });
    }

    /** Compute the Nth percentile from a sorted list of values. */
    private double percentile(List<Long> sortedValues, int percentile) {
        if (sortedValues.isEmpty()) return 0.0;
        int index = (int) Math.ceil(percentile / 100.0 * sortedValues.size()) - 1;
        return sortedValues.get(Math.max(0, Math.min(index, sortedValues.size() - 1)));
    }

    // ----------------------------------------------------------
    // Summary queries (used by AnalyticsController)
    // ----------------------------------------------------------

    public long countEvents(String tenantId, Instant from, Instant to) {
        return eventRepository.countByTenantIdAndTimestampBetween(tenantId, from, to);
    }

    public long countErrors(String tenantId, Instant from, Instant to) {
        return eventRepository.countByTenantIdAndErrorIsTrueAndTimestampBetween(tenantId, from, to);
    }
}
""")

write("analytics-service/src/main/java/com/platform/analytics/controller/AnalyticsController.java", """\
package com.platform.analytics.controller;

import com.platform.analytics.model.ApiEventDocument;
import com.platform.analytics.repository.ApiEventRepository;
import com.platform.analytics.service.MetricsAggregationService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Map;

/**
 * REST API for accessing analytics data stored in Elasticsearch.
 * Base URL: http://localhost:8081/api/analytics
 */
@RestController
@RequestMapping("/api/analytics")
@RequiredArgsConstructor
public class AnalyticsController {

    private final ApiEventRepository eventRepository;
    private final MetricsAggregationService aggregationService;

    /**
     * GET /api/analytics/events?tenantId=X&from=ISO&to=ISO&page=0&size=20
     * Returns paginated raw events for a tenant in the given time range.
     */
    @GetMapping("/events")
    public ResponseEntity<Page<ApiEventDocument>> getEvents(
            @RequestParam String tenantId,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) Instant to,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {

        Instant effectiveTo = (to != null) ? to : Instant.now();
        Instant effectiveFrom = (from != null) ? from : effectiveTo.minus(1, ChronoUnit.HOURS);

        PageRequest pageRequest = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "timestamp"));
        Page<ApiEventDocument> result = eventRepository.findByTenantIdAndTimestampBetween(
                tenantId, effectiveFrom, effectiveTo, pageRequest);

        return ResponseEntity.ok(result);
    }

    /**
     * GET /api/analytics/summary?tenantId=X
     * Returns a 24-hour summary of request count, error count, and error rate.
     */
    @GetMapping("/summary")
    public ResponseEntity<Map<String, Object>> getSummary(@RequestParam String tenantId) {
        Instant to = Instant.now();
        Instant from = to.minus(24, ChronoUnit.HOURS);

        long total = aggregationService.countEvents(tenantId, from, to);
        long errors = aggregationService.countErrors(tenantId, from, to);
        double errorRate = total > 0 ? (double) errors / total : 0.0;

        return ResponseEntity.ok(Map.of(
                "tenantId", tenantId,
                "from", from.toString(),
                "to", to.toString(),
                "totalRequests", total,
                "errorCount", errors,
                "errorRate", String.format("%.2f%%", errorRate * 100)
        ));
    }

    /**
     * GET /api/analytics/errors?tenantId=X&page=0&size=20
     * Returns the most recent error events for a tenant.
     */
    @GetMapping("/errors")
    public ResponseEntity<Page<ApiEventDocument>> getErrors(
            @RequestParam String tenantId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {

        PageRequest pageRequest = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "timestamp"));
        return ResponseEntity.ok(eventRepository.findByTenantIdAndErrorIsTrue(tenantId, pageRequest));
    }

    /** GET /api/analytics/health — simple liveness check. */
    @GetMapping("/health")
    public ResponseEntity<Map<String, String>> health() {
        return ResponseEntity.ok(Map.of("status", "UP", "service", "analytics-service"));
    }
}
""")

write("analytics-service/src/main/resources/application.yml", """\
spring:
  application:
    name: analytics-service

  config:
    import: "optional:file:../config/common-config.yml"

  kafka:
    consumer:
      group-id: analytics-service-group
      auto-offset-reset: earliest

server:
  port: ${ANALYTICS_PORT:8081}

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
  endpoint:
    health:
      show-details: always
  tracing:
    sampling:
      probability: 1.0

platform:
  aggregation:
    interval-ms: ${AGGREGATION_INTERVAL_MS:60000}

logging:
  level:
    com.platform: DEBUG
    org.springframework.data.elasticsearch: INFO
  pattern:
    console: "%d{ISO8601} [%thread] %-5level [%X{traceId}/%X{spanId}] %logger{36} - %msg%n"
""")

write("analytics-service/src/main/resources/elasticsearch/settings.json", """\
{
  "index": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "refresh_interval": "5s"
  }
}
""")

print("\nAnalytics service created.")

# ==============================================================
# ALERT SERVICE
# ==============================================================
write("alert-service/build.gradle", """\
plugins {
    id 'org.springframework.boot'
    id 'io.spring.dependency-management'
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-actuator'
    implementation 'org.springframework.boot:spring-boot-starter-mail'
    implementation 'org.springframework.kafka:spring-kafka'
    implementation 'io.micrometer:micrometer-tracing-bridge-otel'
    implementation 'io.opentelemetry:opentelemetry-exporter-otlp'
    implementation 'net.logstash.logback:logstash-logback-encoder:7.4'
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
    testImplementation 'org.springframework.kafka:spring-kafka-test'
}
""")

write("alert-service/src/main/java/com/platform/alert/AlertApplication.java", """\
package com.platform.alert;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class AlertApplication {
    public static void main(String[] args) {
        SpringApplication.run(AlertApplication.class, args);
    }
}
""")

write("alert-service/src/main/java/com/platform/alert/config/AlertProperties.java", """\
package com.platform.alert.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * Strongly-typed binding for all 'platform.alert.*' properties
 * defined in config/common-config.yml.
 */
@Data
@Component
@ConfigurationProperties(prefix = "platform.alert")
public class AlertProperties {

    /** Maximum acceptable average latency in milliseconds. */
    private long latencyThresholdMs = 5000;

    /** Maximum acceptable error rate (0.0 – 1.0). */
    private double errorRateThreshold = 0.10;

    /** Multiplier above baseline traffic that triggers a spike alert. */
    private double trafficSpikeMultiplier = 3.0;

    /** Minimum number of requests to consider an alert valid. */
    private int minSampleSize = 10;

    /** How many minutes to suppress repeated alerts for the same key. */
    private int cooldownMinutes = 5;
}
""")

write("alert-service/src/main/java/com/platform/alert/config/KafkaConsumerConfig.java", """\
package com.platform.alert.config;

import com.platform.alert.model.AnalyticsAggregation;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.support.serializer.ErrorHandlingDeserializer;
import org.springframework.kafka.support.serializer.JsonDeserializer;

import java.util.HashMap;
import java.util.Map;

@Configuration
public class KafkaConsumerConfig {

    @Value("${spring.kafka.bootstrap-servers:localhost:9092}")
    private String bootstrapServers;

    @Value("${spring.kafka.consumer.group-id:alert-service-group}")
    private String groupId;

    @Bean
    public ConsumerFactory<String, AnalyticsAggregation> consumerFactory() {
        Map<String, Object> props = new HashMap<>();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, groupId);
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, ErrorHandlingDeserializer.class);
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, ErrorHandlingDeserializer.class);
        props.put(ErrorHandlingDeserializer.KEY_DESERIALIZER_CLASS, StringDeserializer.class);
        props.put(ErrorHandlingDeserializer.VALUE_DESERIALIZER_CLASS, JsonDeserializer.class);
        props.put(JsonDeserializer.VALUE_DEFAULT_TYPE, AnalyticsAggregation.class.getName());
        props.put(JsonDeserializer.TRUSTED_PACKAGES,
                "com.platform.analytics.model,com.platform.alert.model");
        return new DefaultKafkaConsumerFactory<>(props);
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, AnalyticsAggregation> kafkaListenerContainerFactory(
            ConsumerFactory<String, AnalyticsAggregation> cf) {
        ConcurrentKafkaListenerContainerFactory<String, AnalyticsAggregation> factory =
                new ConcurrentKafkaListenerContainerFactory<>();
        factory.setConsumerFactory(cf);
        factory.setConcurrency(2);
        return factory;
    }
}
""")

write("alert-service/src/main/java/com/platform/alert/model/AnalyticsAggregation.java", """\
package com.platform.alert.model;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/** Mirrors the analytics-service AnalyticsAggregation (received from Kafka). */
@Data
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class AnalyticsAggregation {
    private String tenantId;
    private String endpoint;
    @JsonFormat(shape = JsonFormat.Shape.STRING)
    private Instant windowStart;
    @JsonFormat(shape = JsonFormat.Shape.STRING)
    private Instant windowEnd;
    private long requestCount;
    private double avgLatencyMs;
    private double p95LatencyMs;
    private double p99LatencyMs;
    private long errorCount;
    private double errorRate;
    private String service;
}
""")

write("alert-service/src/main/java/com/platform/alert/model/AlertNotification.java", """\
package com.platform.alert.model;

import lombok.Builder;
import lombok.Data;

import java.time.Instant;

/** Represents a triggered alert notification sent to Slack / email. */
@Data
@Builder
public class AlertNotification {

    public enum AlertType { LATENCY_HIGH, ERROR_RATE_HIGH, TRAFFIC_SPIKE }
    public enum Severity  { WARNING, CRITICAL }

    private String alertId;
    private AlertType type;
    private Severity severity;
    private String title;
    private String message;
    private String tenantId;
    private String endpoint;
    private double currentValue;
    private double thresholdValue;
    private Instant triggeredAt;
}
""")

write("alert-service/src/main/java/com/platform/alert/consumer/AnalyticsEventConsumer.java", """\
package com.platform.alert.consumer;

import com.platform.alert.model.AnalyticsAggregation;
import com.platform.alert.service.AlertEvaluationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Component;

/**
 * Consumes aggregated metrics from the 'analytics-events' Kafka topic
 * and delegates anomaly detection to {@link AlertEvaluationService}.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AnalyticsEventConsumer {

    private final AlertEvaluationService alertEvaluationService;

    @KafkaListener(
            topics = "${platform.kafka.topics.analytics-events:analytics-events}",
            groupId = "${spring.kafka.consumer.group-id:alert-service-group}",
            containerFactory = "kafkaListenerContainerFactory"
    )
    public void consume(
            @Payload AnalyticsAggregation aggregation,
            @Header(KafkaHeaders.RECEIVED_TOPIC) String topic,
            @Header(KafkaHeaders.OFFSET) long offset) {

        log.debug("Received aggregation [topic={}, offset={}] tenant={}, endpoint={}",
                topic, offset, aggregation.getTenantId(), aggregation.getEndpoint());

        alertEvaluationService.evaluate(aggregation);
    }
}
""")

write("alert-service/src/main/java/com/platform/alert/service/AlertEvaluationService.java", """\
package com.platform.alert.service;

import com.platform.alert.config.AlertProperties;
import com.platform.alert.model.AlertNotification;
import com.platform.alert.model.AlertNotification.AlertType;
import com.platform.alert.model.AlertNotification.Severity;
import com.platform.alert.model.AnalyticsAggregation;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Evaluates incoming {@link AnalyticsAggregation} against configured thresholds
 * and fires alert notifications via Slack and/or email.
 *
 * Alert cooldown prevents repeated notifications for the same tenant+endpoint key.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AlertEvaluationService {

    private final AlertProperties properties;
    private final SlackNotificationService slackService;
    private final EmailNotificationService emailService;

    /** Tracks the last alert time per "tenantId|endpoint|alertType" to enforce cooldown. */
    private final ConcurrentHashMap<String, Instant> lastAlertTime = new ConcurrentHashMap<>();

    public void evaluate(AnalyticsAggregation agg) {
        if (agg.getRequestCount() < properties.getMinSampleSize()) {
            log.debug("Skipping alert evaluation: sample size {} < minimum {}",
                    agg.getRequestCount(), properties.getMinSampleSize());
            return;
        }

        checkLatency(agg);
        checkErrorRate(agg);
    }

    private void checkLatency(AnalyticsAggregation agg) {
        double threshold = properties.getLatencyThresholdMs();
        if (agg.getAvgLatencyMs() > threshold) {
            Severity severity = agg.getAvgLatencyMs() > threshold * 2 ? Severity.CRITICAL : Severity.WARNING;
            String alertKey = alertKey(agg, AlertType.LATENCY_HIGH);

            if (isCooledDown(alertKey)) {
                AlertNotification notification = AlertNotification.builder()
                        .alertId(UUID.randomUUID().toString())
                        .type(AlertType.LATENCY_HIGH)
                        .severity(severity)
                        .title(severity + ": High Latency Detected")
                        .message(String.format(
                                "Average latency %.0f ms exceeds threshold %.0f ms on endpoint '%s'",
                                agg.getAvgLatencyMs(), threshold, agg.getEndpoint()))
                        .tenantId(agg.getTenantId())
                        .endpoint(agg.getEndpoint())
                        .currentValue(agg.getAvgLatencyMs())
                        .thresholdValue(threshold)
                        .triggeredAt(Instant.now())
                        .build();

                sendAlert(notification, alertKey);
            }
        }
    }

    private void checkErrorRate(AnalyticsAggregation agg) {
        double threshold = properties.getErrorRateThreshold();
        if (agg.getErrorRate() > threshold) {
            Severity severity = agg.getErrorRate() > threshold * 2 ? Severity.CRITICAL : Severity.WARNING;
            String alertKey = alertKey(agg, AlertType.ERROR_RATE_HIGH);

            if (isCooledDown(alertKey)) {
                AlertNotification notification = AlertNotification.builder()
                        .alertId(UUID.randomUUID().toString())
                        .type(AlertType.ERROR_RATE_HIGH)
                        .severity(severity)
                        .title(severity + ": Error Rate Spike Detected")
                        .message(String.format(
                                "Error rate %.1f%% exceeds threshold %.1f%% on endpoint '%s'",
                                agg.getErrorRate() * 100, threshold * 100, agg.getEndpoint()))
                        .tenantId(agg.getTenantId())
                        .endpoint(agg.getEndpoint())
                        .currentValue(agg.getErrorRate())
                        .thresholdValue(threshold)
                        .triggeredAt(Instant.now())
                        .build();

                sendAlert(notification, alertKey);
            }
        }
    }

    private void sendAlert(AlertNotification notification, String alertKey) {
        log.warn("ALERT FIRED [{}] tenant={}, endpoint={}: {}",
                notification.getSeverity(), notification.getTenantId(),
                notification.getEndpoint(), notification.getMessage());

        slackService.sendAlert(notification);
        emailService.sendAlert(notification);
        lastAlertTime.put(alertKey, Instant.now());
    }

    private boolean isCooledDown(String alertKey) {
        Instant last = lastAlertTime.get(alertKey);
        if (last == null) return true;
        return Instant.now().isAfter(last.plus(properties.getCooldownMinutes(), ChronoUnit.MINUTES));
    }

    private String alertKey(AnalyticsAggregation agg, AlertType type) {
        return agg.getTenantId() + "|" + agg.getEndpoint() + "|" + type.name();
    }
}
""")

write("alert-service/src/main/java/com/platform/alert/service/SlackNotificationService.java", """\
package com.platform.alert.service;

import com.platform.alert.model.AlertNotification;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

/**
 * Sends formatted alert notifications to a Slack incoming webhook.
 * Configure the webhook URL in config/common-config.yml:
 *   platform.slack.webhook-url
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SlackNotificationService {

    private final RestTemplate restTemplate;

    @Value("${platform.slack.webhook-url:}")
    private String webhookUrl;

    @Value("${platform.slack.enabled:true}")
    private boolean enabled;

    public void sendAlert(AlertNotification notification) {
        if (!enabled || webhookUrl.isBlank() || webhookUrl.contains("YOUR/SLACK")) {
            log.info("Slack disabled or not configured — skipping alert: {}", notification.getTitle());
            return;
        }

        String emoji = notification.getSeverity() == AlertNotification.Severity.CRITICAL ? ":rotating_light:" : ":warning:";
        String text = String.format(
                "%s *[%s] %s*\\n>%s\\n>• Tenant: `%s`\\n>• Endpoint: `%s`\\n>• Value: `%.2f` (threshold: `%.2f`)",
                emoji,
                notification.getSeverity(),
                notification.getTitle(),
                notification.getMessage(),
                notification.getTenantId(),
                notification.getEndpoint(),
                notification.getCurrentValue(),
                notification.getThresholdValue()
        );

        Map<String, String> payload = Map.of("text", text);
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        try {
            restTemplate.postForEntity(webhookUrl, new HttpEntity<>(payload, headers), String.class);
            log.info("Slack alert sent: {}", notification.getTitle());
        } catch (Exception ex) {
            log.error("Failed to send Slack alert '{}': {}", notification.getTitle(), ex.getMessage());
        }
    }
}
""")

write("alert-service/src/main/java/com/platform/alert/service/EmailNotificationService.java", """\
package com.platform.alert.service;

import com.platform.alert.model.AlertNotification;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;

import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;

/**
 * Sends alert notifications via email using Spring's JavaMailSender.
 * Configure SMTP credentials in config/common-config.yml under spring.mail.*.
 * Enable email alerts by setting: platform.email.enabled=true
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class EmailNotificationService {

    private final JavaMailSender mailSender;

    @Value("${platform.email.from:alerts@your-domain.com}")
    private String from;

    @Value("${platform.email.to:team@your-domain.com}")
    private String to;

    @Value("${platform.email.enabled:false}")
    private boolean enabled;

    public void sendAlert(AlertNotification notification) {
        if (!enabled) {
            log.debug("Email notifications disabled — skipping alert: {}", notification.getTitle());
            return;
        }

        try {
            SimpleMailMessage message = new SimpleMailMessage();
            message.setFrom(from);
            message.setTo(to.split(","));
            message.setSubject(String.format("[API Alert][%s] %s",
                    notification.getSeverity(), notification.getTitle()));
            message.setText(buildEmailBody(notification));
            mailSender.send(message);
            log.info("Email alert sent to {} for alert: {}", to, notification.getTitle());
        } catch (Exception ex) {
            log.error("Failed to send email alert '{}': {}", notification.getTitle(), ex.getMessage());
        }
    }

    private String buildEmailBody(AlertNotification notification) {
        DateTimeFormatter fmt = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss").withZone(ZoneOffset.UTC);
        return String.format(
                "API Gateway Analytics Platform — Alert Notification\\n" +
                "=========================================================\\n\\n" +
                "Severity  : %s\\n" +
                "Alert Type: %s\\n" +
                "Title     : %s\\n\\n" +
                "Details\\n" +
                "-------\\n" +
                "%s\\n\\n" +
                "Tenant    : %s\\n" +
                "Endpoint  : %s\\n" +
                "Value     : %.2f\\n" +
                "Threshold : %.2f\\n" +
                "Triggered : %s (UTC)\\n\\n" +
                "Please investigate via Kibana / Jaeger dashboards.\\n",
                notification.getSeverity(),
                notification.getType(),
                notification.getTitle(),
                notification.getMessage(),
                notification.getTenantId(),
                notification.getEndpoint(),
                notification.getCurrentValue(),
                notification.getThresholdValue(),
                fmt.format(notification.getTriggeredAt())
        );
    }
}
""")

write("alert-service/src/main/java/com/platform/alert/config/AppConfig.java", """\
package com.platform.alert.config;

import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

@Configuration
@EnableConfigurationProperties(AlertProperties.class)
public class AppConfig {

    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}
""")

write("alert-service/src/main/resources/application.yml", """\
spring:
  application:
    name: alert-service

  config:
    import: "optional:file:../config/common-config.yml"

  kafka:
    consumer:
      group-id: alert-service-group
      auto-offset-reset: earliest

server:
  port: ${ALERT_PORT:8082}

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
  endpoint:
    health:
      show-details: always
  tracing:
    sampling:
      probability: 1.0

logging:
  level:
    com.platform: DEBUG
  pattern:
    console: "%d{ISO8601} [%thread] %-5level [%X{traceId}/%X{spanId}] %logger{36} - %msg%n"
""")

print("\nAlert service created.")

# ==============================================================
# KUBERNETES MANIFESTS
# ==============================================================
write("k8s/namespace.yml", """\
apiVersion: v1
kind: Namespace
metadata:
  name: api-analytics
  labels:
    app: api-gateway-analytics-platform
""")

write("k8s/configmaps/platform-configmap.yml", """\
apiVersion: v1
kind: ConfigMap
metadata:
  name: platform-config
  namespace: api-analytics
data:
  KAFKA_BOOTSTRAP_SERVERS: "kafka:9092"
  ELASTICSEARCH_URIS: "http://elasticsearch:9200"
  ELASTICSEARCH_USERNAME: "elastic"
  POSTGRES_HOST: "postgres"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "analytics_db"
  POSTGRES_USERNAME: "analytics_user"
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://otel-collector:4317"
  KAFKA_TOPIC_API_EVENTS: "api-events"
  KAFKA_TOPIC_API_EVENTS_DLQ: "api-events-dlq"
  KAFKA_TOPIC_ANALYTICS_EVENTS: "analytics-events"
  ALERT_LATENCY_THRESHOLD_MS: "5000"
  ALERT_ERROR_RATE_THRESHOLD: "0.10"
  ALERT_COOLDOWN_MINUTES: "5"
  SLACK_NOTIFICATIONS_ENABLED: "true"
  EMAIL_NOTIFICATIONS_ENABLED: "false"
""")

write("k8s/secrets/platform-secrets.yml", """\
# WARNING: Do NOT commit real secret values to version control.
# Use kubectl create secret or a secrets manager (Vault, AWS Secrets Manager, etc.)
apiVersion: v1
kind: Secret
metadata:
  name: platform-secrets
  namespace: api-analytics
type: Opaque
stringData:
  ELASTICSEARCH_PASSWORD: "changeme"
  POSTGRES_PASSWORD: "analytics_pass"
  SMTP_USERNAME: "your-email@gmail.com"
  SMTP_PASSWORD: "your-app-password"
  SLACK_WEBHOOK_URL: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
""")

write("k8s/deployments/gateway-deployment.yml", """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway-service
  namespace: api-analytics
  labels:
    app: gateway-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: gateway-service
  template:
    metadata:
      labels:
        app: gateway-service
    spec:
      containers:
        - name: gateway-service
          image: platform/gateway-service:1.0.0
          ports:
            - containerPort: 8080
          envFrom:
            - configMapRef:
                name: platform-config
            - secretRef:
                name: platform-secrets
          env:
            - name: SPRING_CONFIG_IMPORT
              value: "optional:file:/config/common-config.yml"
            - name: OTEL_SERVICE_NAME
              value: "gateway-service"
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "1Gi"
              cpu: "500m"
          readinessProbe:
            httpGet:
              path: /actuator/health
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /actuator/health
              port: 8080
            initialDelaySeconds: 60
            periodSeconds: 15
""")

write("k8s/deployments/analytics-deployment.yml", """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: analytics-service
  namespace: api-analytics
  labels:
    app: analytics-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: analytics-service
  template:
    metadata:
      labels:
        app: analytics-service
    spec:
      containers:
        - name: analytics-service
          image: platform/analytics-service:1.0.0
          ports:
            - containerPort: 8081
          envFrom:
            - configMapRef:
                name: platform-config
            - secretRef:
                name: platform-secrets
          env:
            - name: SPRING_CONFIG_IMPORT
              value: "optional:file:/config/common-config.yml"
            - name: OTEL_SERVICE_NAME
              value: "analytics-service"
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "1Gi"
              cpu: "500m"
          readinessProbe:
            httpGet:
              path: /actuator/health
              port: 8081
            initialDelaySeconds: 30
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /actuator/health
              port: 8081
            initialDelaySeconds: 60
            periodSeconds: 15
""")

write("k8s/deployments/alert-deployment.yml", """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alert-service
  namespace: api-analytics
  labels:
    app: alert-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: alert-service
  template:
    metadata:
      labels:
        app: alert-service
    spec:
      containers:
        - name: alert-service
          image: platform/alert-service:1.0.0
          ports:
            - containerPort: 8082
          envFrom:
            - configMapRef:
                name: platform-config
            - secretRef:
                name: platform-secrets
          env:
            - name: SPRING_CONFIG_IMPORT
              value: "optional:file:/config/common-config.yml"
            - name: OTEL_SERVICE_NAME
              value: "alert-service"
          resources:
            requests:
              memory: "256Mi"
              cpu: "125m"
            limits:
              memory: "512Mi"
              cpu: "250m"
          readinessProbe:
            httpGet:
              path: /actuator/health
              port: 8082
            initialDelaySeconds: 30
            periodSeconds: 10
""")

write("k8s/services/gateway-service.yml", """\
apiVersion: v1
kind: Service
metadata:
  name: gateway-service
  namespace: api-analytics
spec:
  selector:
    app: gateway-service
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: ClusterIP
""")

write("k8s/services/analytics-service.yml", """\
apiVersion: v1
kind: Service
metadata:
  name: analytics-service
  namespace: api-analytics
spec:
  selector:
    app: analytics-service
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8081
  type: ClusterIP
""")

write("k8s/services/alert-service.yml", """\
apiVersion: v1
kind: Service
metadata:
  name: alert-service
  namespace: api-analytics
spec:
  selector:
    app: alert-service
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8082
  type: ClusterIP
""")

write("k8s/ingress/platform-ingress.yml", """\
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: platform-ingress
  namespace: api-analytics
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
    - host: api-gateway.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: gateway-service
                port:
                  number: 80
    - host: analytics.example.com
      http:
        paths:
          - path: /api/analytics
            pathType: Prefix
            backend:
              service:
                name: analytics-service
                port:
                  number: 80
""")

write("k8s/hpa/gateway-hpa.yml", """\
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: gateway-hpa
  namespace: api-analytics
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gateway-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
""")

write("k8s/hpa/analytics-hpa.yml", """\
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: analytics-hpa
  namespace: api-analytics
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: analytics-service
  minReplicas: 2
  maxReplicas: 8
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
""")

# ==============================================================
# KIBANA INDEX MAPPINGS
# ==============================================================
write("kibana/index-mappings/api-events-mapping.json", """\
{
  "mappings": {
    "properties": {
      "id":            { "type": "keyword" },
      "timestamp":     { "type": "date", "format": "strict_date_optional_time" },
      "tenantId":      { "type": "keyword" },
      "correlationId": { "type": "keyword" },
      "method":        { "type": "keyword" },
      "path":          { "type": "keyword" },
      "host":          { "type": "keyword" },
      "statusCode":    { "type": "integer" },
      "latencyMs":     { "type": "long" },
      "clientIp":      { "type": "ip" },
      "userAgent":     { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
      "error":         { "type": "boolean" },
      "errorMessage":  { "type": "text" },
      "serviceName":   { "type": "keyword" },
      "endpoint":      { "type": "keyword" }
    }
  },
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "refresh_interval": "5s"
  }
}
""")

write("kibana/index-mappings/analytics-aggregations-mapping.json", """\
{
  "mappings": {
    "properties": {
      "tenantId":      { "type": "keyword" },
      "endpoint":      { "type": "keyword" },
      "windowStart":   { "type": "date", "format": "strict_date_optional_time" },
      "windowEnd":     { "type": "date", "format": "strict_date_optional_time" },
      "requestCount":  { "type": "long" },
      "avgLatencyMs":  { "type": "double" },
      "p95LatencyMs":  { "type": "double" },
      "p99LatencyMs":  { "type": "double" },
      "errorCount":    { "type": "long" },
      "errorRate":     { "type": "double" },
      "service":       { "type": "keyword" }
    }
  }
}
""")

write("kibana/dashboards/README.md", """\
# Kibana Dashboards

## Import Order

1. Apply index mappings first:
   ```
   curl -X PUT http://localhost:9200/api-events \\
        -u elastic:changeme \\
        -H 'Content-Type: application/json' \\
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
""")

# ==============================================================
# SCRIPTS
# ==============================================================
write("scripts/setup.sh", """\
#!/usr/bin/env bash
# Run once after cloning to generate the Gradle wrapper
set -euo pipefail

cd "$(dirname "$0")/.."

if command -v gradle &>/dev/null; then
    echo "Generating Gradle wrapper..."
    gradle wrapper --gradle-version 8.7
    echo "Done. You can now use ./gradlew"
else
    echo "ERROR: 'gradle' not found. Install Gradle 8.x first."
    echo "  macOS: brew install gradle"
    exit 1
fi
""")

write("scripts/start-infra.sh", """\
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
""")

write("scripts/stop-infra.sh", """\
#!/usr/bin/env bash
# Stop all infrastructure services
set -euo pipefail

cd "$(dirname "$0")/../docker"
docker compose down

echo "Infrastructure stopped."
""")

os.chmod(os.path.join(BASE, "scripts/setup.sh"), 0o755)
os.chmod(os.path.join(BASE, "scripts/start-infra.sh"), 0o755)
os.chmod(os.path.join(BASE, "scripts/stop-infra.sh"), 0o755)

# ==============================================================
# DOCS
# ==============================================================
write("docs/architecture.md", """\
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
""")

print("\nAll project files created successfully!")
print(f"\nProject structure generated at: {BASE}")
print("\nNext steps:")
print("  1. cd <project-root> && bash scripts/setup.sh   # generate gradlew")
print("  2. bash scripts/start-infra.sh                  # start Docker services")
print("  3. cd gateway-service && ../gradlew bootRun")
print("  4. cd analytics-service && ../gradlew bootRun")
print("  5. cd alert-service && ../gradlew bootRun")
PYEOF
