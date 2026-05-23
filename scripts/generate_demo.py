#!/usr/bin/env python3
"""Generates the demo-service — a single-JVM demo of the full platform."""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(BASE, "demo-service/src/main/java/com/platform/demo")

def write(rel, content):
    p = os.path.join(BASE, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write(content)
    print(f"  + {rel}")

# ── Add demo-service to settings.gradle ─────────────────────
settings_path = os.path.join(BASE, "settings.gradle")
with open(settings_path) as f:
    settings = f.read()
if "demo-service" not in settings:
    with open(settings_path, 'w') as f:
        f.write(settings.rstrip() + "\ninclude 'demo-service'\n")
    print("  + settings.gradle (added demo-service)")

# ── build.gradle ──────────────────────────────────────────────
write("demo-service/build.gradle",
"plugins {\n"
"    id 'org.springframework.boot'\n"
"    id 'io.spring.dependency-management'\n"
"}\n\n"
"dependencies {\n"
"    // Web for REST + Kafka for messaging + embedded Kafka for no-Docker demo\n"
"    implementation 'org.springframework.boot:spring-boot-starter-web'\n"
"    implementation 'org.springframework.boot:spring-boot-starter-actuator'\n"
"    implementation 'org.springframework.kafka:spring-kafka'\n"
"    // Embedded Kafka broker (normally a test dep, used here for self-contained demo)\n"
"    implementation 'org.springframework.kafka:spring-kafka-test'\n"
"    implementation 'net.logstash.logback:logstash-logback-encoder:8.0'\n"
"}\n")

# ── DemoApplication ───────────────────────────────────────────
write("demo-service/src/main/java/com/platform/demo/DemoApplication.java", """\
package com.platform.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Self-contained demo of the API Gateway Analytics Platform.
 *
 * Runs the FULL event pipeline in a single JVM with embedded Kafka:
 *
 *   SampleTrafficGenerator
 *       → Kafka topic "api-events"          (simulates gateway capturing requests)
 *            → ApiEventConsumer             (simulates analytics-service)
 *                 → InMemoryMetricsStore    (replaces Elasticsearch)
 *                      → AlertEvaluationService (simulates alert-service)
 *
 * REST API:  http://localhost:8888/demo/metrics
 *            http://localhost:8888/demo/summary
 *            http://localhost:8888/demo/alerts
 *            http://localhost:8888/demo/events
 */
@SpringBootApplication
@EnableScheduling
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}
""")

# ── ApiAnalyticsEvent ─────────────────────────────────────────
write("demo-service/src/main/java/com/platform/demo/model/ApiAnalyticsEvent.java", """\
package com.platform.demo.model;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.Instant;

@Data @Builder @NoArgsConstructor @AllArgsConstructor
public class ApiAnalyticsEvent {
    private String eventId;
    @JsonFormat(shape = JsonFormat.Shape.STRING)
    private Instant timestamp;
    private String tenantId;
    private String correlationId;
    private String method;
    private String path;
    private int statusCode;
    private long latencyMs;
    private String clientIp;
    private boolean error;
    private String serviceName;
    private String endpoint; // "METHOD /path"
}
""")

# ── AlertNotification ─────────────────────────────────────────
write("demo-service/src/main/java/com/platform/demo/model/AlertNotification.java", """\
package com.platform.demo.model;

import lombok.Builder;
import lombok.Data;
import java.time.Instant;

@Data @Builder
public class AlertNotification {
    public enum AlertType { LATENCY_HIGH, ERROR_RATE_HIGH }
    public enum Severity  { WARNING, CRITICAL }

    private AlertType type;
    private Severity severity;
    private String message;
    private String tenantId;
    private String endpoint;
    private double currentValue;
    private double thresholdValue;
    private Instant triggeredAt;
}
""")

# ── EmbeddedKafkaConfig ───────────────────────────────────────
write("demo-service/src/main/java/com/platform/demo/config/EmbeddedKafkaConfig.java", """\
package com.platform.demo.config;

import com.platform.demo.model.ApiAnalyticsEvent;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.annotation.EnableKafka;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.*;
import org.springframework.kafka.support.serializer.JsonDeserializer;
import org.springframework.kafka.support.serializer.JsonSerializer;
import org.springframework.kafka.test.EmbeddedKafkaBroker;

import java.util.HashMap;
import java.util.Map;

@EnableKafka
@Configuration
public class EmbeddedKafkaConfig {

    /** Spin up a single-broker embedded Kafka inside this JVM process. */
    @Bean
    public EmbeddedKafkaBroker embeddedKafkaBroker() {
        return new EmbeddedKafkaBroker(1, true, 1, "api-events", "api-events-dlq", "analytics-events")
                .brokerListProperty("spring.kafka.bootstrap-servers");
    }

    @Bean
    public ProducerFactory<String, ApiAnalyticsEvent> producerFactory(EmbeddedKafkaBroker broker) {
        Map<String, Object> props = new HashMap<>();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, broker.getBrokersAsString());
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, JsonSerializer.class);
        props.put(JsonSerializer.ADD_TYPE_INFO_HEADERS, false);
        return new DefaultKafkaProducerFactory<>(props);
    }

    @Bean
    public KafkaTemplate<String, ApiAnalyticsEvent> kafkaTemplate(
            ProducerFactory<String, ApiAnalyticsEvent> pf) {
        return new KafkaTemplate<>(pf);
    }

    @Bean
    public ConsumerFactory<String, ApiAnalyticsEvent> consumerFactory(EmbeddedKafkaBroker broker) {
        Map<String, Object> props = new HashMap<>();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, broker.getBrokersAsString());
        props.put(ConsumerConfig.GROUP_ID_CONFIG, "demo-analytics-group");
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class);
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, JsonDeserializer.class);
        props.put(JsonDeserializer.VALUE_DEFAULT_TYPE, ApiAnalyticsEvent.class.getName());
        props.put(JsonDeserializer.TRUSTED_PACKAGES, "com.platform.demo.model");
        return new DefaultKafkaConsumerFactory<>(props);
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, ApiAnalyticsEvent> kafkaListenerContainerFactory(
            ConsumerFactory<String, ApiAnalyticsEvent> cf) {
        var factory = new ConcurrentKafkaListenerContainerFactory<String, ApiAnalyticsEvent>();
        factory.setConsumerFactory(cf);
        return factory;
    }
}
""")

# ── InMemoryMetricsStore ──────────────────────────────────────
write("demo-service/src/main/java/com/platform/demo/service/InMemoryMetricsStore.java", """\
package com.platform.demo.service;

import com.platform.demo.model.AlertNotification;
import com.platform.demo.model.ApiAnalyticsEvent;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentLinkedDeque;
import java.util.stream.Collectors;

/**
 * In-memory replacement for Elasticsearch.
 * Keeps a rolling window of the last 500 events and all fired alerts.
 */
@Slf4j
@Service
public class InMemoryMetricsStore {

    private static final int MAX_EVENTS = 500;

    @Getter
    private final Deque<ApiAnalyticsEvent> events = new ConcurrentLinkedDeque<>();

    @Getter
    private final Deque<AlertNotification> alerts = new ConcurrentLinkedDeque<>();

    @Value("${platform.alert.latency-threshold-ms:3000}")
    private long latencyThreshold;

    @Value("${platform.alert.error-rate-threshold:0.3}")
    private double errorRateThreshold;

    private final Map<String, Instant> lastAlertTime = new HashMap<>();

    public void recordEvent(ApiAnalyticsEvent event) {
        events.addFirst(event);
        if (events.size() > MAX_EVENTS) events.removeLast();
        checkThresholds(event);
    }

    private void checkThresholds(ApiAnalyticsEvent event) {
        // Compute stats for this tenant+endpoint over last 60s
        Instant since = Instant.now().minusSeconds(60);
        List<ApiAnalyticsEvent> window = events.stream()
                .filter(e -> e.getTenantId().equals(event.getTenantId())
                        && e.getEndpoint().equals(event.getEndpoint())
                        && e.getTimestamp().isAfter(since))
                .collect(Collectors.toList());

        if (window.size() < 3) return; // need a minimum sample

        double avgLatency = window.stream().mapToLong(ApiAnalyticsEvent::getLatencyMs).average().orElse(0);
        long errors = window.stream().filter(ApiAnalyticsEvent::isError).count();
        double errorRate = (double) errors / window.size();

        if (avgLatency > latencyThreshold) {
            String key = event.getTenantId() + "|" + event.getEndpoint() + "|LATENCY";
            if (canAlert(key)) {
                AlertNotification alert = AlertNotification.builder()
                        .type(AlertNotification.AlertType.LATENCY_HIGH)
                        .severity(avgLatency > latencyThreshold * 2
                                ? AlertNotification.Severity.CRITICAL
                                : AlertNotification.Severity.WARNING)
                        .message(String.format("[%s] Avg latency %.0f ms > threshold %d ms on %s",
                                event.getTenantId(), avgLatency, latencyThreshold, event.getEndpoint()))
                        .tenantId(event.getTenantId())
                        .endpoint(event.getEndpoint())
                        .currentValue(avgLatency)
                        .thresholdValue(latencyThreshold)
                        .triggeredAt(Instant.now())
                        .build();
                alerts.addFirst(alert);
                log.warn("🚨 ALERT [{}] {}", alert.getSeverity(), alert.getMessage());
            }
        }

        if (errorRate > errorRateThreshold) {
            String key = event.getTenantId() + "|" + event.getEndpoint() + "|ERROR_RATE";
            if (canAlert(key)) {
                AlertNotification alert = AlertNotification.builder()
                        .type(AlertNotification.AlertType.ERROR_RATE_HIGH)
                        .severity(errorRate > errorRateThreshold * 2
                                ? AlertNotification.Severity.CRITICAL
                                : AlertNotification.Severity.WARNING)
                        .message(String.format("[%s] Error rate %.1f%% > threshold %.1f%% on %s",
                                event.getTenantId(), errorRate * 100,
                                errorRateThreshold * 100, event.getEndpoint()))
                        .tenantId(event.getTenantId())
                        .endpoint(event.getEndpoint())
                        .currentValue(errorRate)
                        .thresholdValue(errorRateThreshold)
                        .triggeredAt(Instant.now())
                        .build();
                alerts.addFirst(alert);
                log.warn("🚨 ALERT [{}] {}", alert.getSeverity(), alert.getMessage());
            }
        }
    }

    private boolean canAlert(String key) {
        Instant last = lastAlertTime.get(key);
        if (last == null || Instant.now().isAfter(last.plusSeconds(30))) {
            lastAlertTime.put(key, Instant.now());
            return true;
        }
        return false;
    }

    /** Returns aggregated stats per tenant+endpoint for the last 60 seconds. */
    public List<Map<String, Object>> getMetrics() {
        Instant since = Instant.now().minusSeconds(60);
        Map<String, List<ApiAnalyticsEvent>> grouped = events.stream()
                .filter(e -> e.getTimestamp().isAfter(since))
                .collect(Collectors.groupingBy(
                        e -> e.getTenantId() + " | " + e.getEndpoint()));

        return grouped.entrySet().stream().map(entry -> {
            List<ApiAnalyticsEvent> g = entry.getValue();
            List<Long> latencies = g.stream().map(ApiAnalyticsEvent::getLatencyMs)
                    .sorted().collect(Collectors.toList());
            long errors = g.stream().filter(ApiAnalyticsEvent::isError).count();
            double p95 = latencies.isEmpty() ? 0 : latencies.get((int)(latencies.size() * 0.95));
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("key", entry.getKey());
            m.put("requests", g.size());
            m.put("errors", errors);
            m.put("errorRate", String.format("%.1f%%", g.isEmpty() ? 0 : 100.0 * errors / g.size()));
            m.put("avgLatencyMs", (long) g.stream().mapToLong(ApiAnalyticsEvent::getLatencyMs).average().orElse(0));
            m.put("p95LatencyMs", p95);
            m.put("windowSeconds", 60);
            return m;
        }).sorted(Comparator.comparingInt(m -> -((Integer) m.get("requests")))).collect(Collectors.toList());
    }

    /** Returns a summary across all events stored (up to last 500). */
    public Map<String, Object> getSummary() {
        long total = events.size();
        long errors = events.stream().filter(ApiAnalyticsEvent::isError).count();
        OptionalDouble avgLat = events.stream().mapToLong(ApiAnalyticsEvent::getLatencyMs).average();
        Map<String, Object> s = new LinkedHashMap<>();
        s.put("totalEventsInMemory", total);
        s.put("errorCount", errors);
        s.put("errorRate", total > 0 ? String.format("%.1f%%", 100.0 * errors / total) : "0%");
        s.put("avgLatencyMs", avgLat.isPresent() ? (long) avgLat.getAsDouble() : 0);
        s.put("alertsFired", alerts.size());
        s.put("tenantsActive", events.stream().map(ApiAnalyticsEvent::getTenantId).distinct().count());
        return s;
    }
}
""")

# ── ApiEventConsumer ──────────────────────────────────────────
write("demo-service/src/main/java/com/platform/demo/consumer/ApiEventConsumer.java", """\
package com.platform.demo.consumer;

import com.platform.demo.model.ApiAnalyticsEvent;
import com.platform.demo.service.InMemoryMetricsStore;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Component;

/**
 * Simulates the analytics-service Kafka consumer.
 * Receives ApiAnalyticsEvent from embedded Kafka and stores in memory.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ApiEventConsumer {

    private final InMemoryMetricsStore metricsStore;

    @KafkaListener(topics = "api-events", groupId = "demo-analytics-group",
                   containerFactory = "kafkaListenerContainerFactory")
    public void consume(@Payload ApiAnalyticsEvent event,
                        @Header(KafkaHeaders.OFFSET) long offset) {
        metricsStore.recordEvent(event);
        String statusIcon = event.isError() ? "❌" : "✅";
        log.info("{} [offset={}] tenant={} | {} → {}ms | status={}",
                statusIcon, offset,
                event.getTenantId(), event.getEndpoint(),
                event.getLatencyMs(), event.getStatusCode());
    }
}
""")

# ── SampleTrafficGenerator ────────────────────────────────────
write("demo-service/src/main/java/com/platform/demo/runner/SampleTrafficGenerator.java", """\
package com.platform.demo.runner;

import com.platform.demo.model.ApiAnalyticsEvent;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.List;
import java.util.Random;
import java.util.UUID;

/**
 * Simulates real API traffic by publishing ApiAnalyticsEvent to Kafka
 * on a schedule. Includes intentional latency spikes and errors to
 * trigger the alerting system.
 *
 * Runs every 800ms to generate a realistic traffic stream.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class SampleTrafficGenerator {

    private final KafkaTemplate<String, ApiAnalyticsEvent> kafkaTemplate;
    private final Random random = new Random();

    private static final List<String> TENANTS   = List.of("tenant-alpha", "tenant-beta", "tenant-gamma");
    private static final List<String> METHODS   = List.of("GET", "GET", "GET", "POST", "PUT", "DELETE");
    private static final List<String> ENDPOINTS = List.of(
            "/api/users", "/api/users/{id}", "/api/orders",
            "/api/orders/{id}", "/api/products", "/api/payments",
            "/api/auth/login", "/api/reports/daily");

    private int tick = 0;

    @Scheduled(fixedDelay = 800)
    public void generateTraffic() {
        tick++;

        // Generate 1-3 events per tick
        int count = 1 + random.nextInt(3);
        for (int i = 0; i < count; i++) {
            String tenant   = TENANTS.get(random.nextInt(TENANTS.size()));
            String path     = ENDPOINTS.get(random.nextInt(ENDPOINTS.size()));
            String method   = METHODS.get(random.nextInt(METHODS.size()));

            // Normal latency 40-400ms; spike every 15 ticks
            long latency;
            boolean isSpikedLatency = (tick % 15 == 0) && (i == 0);
            if (isSpikedLatency) {
                latency = 3500 + random.nextInt(3000); // 3.5s–6.5s spike
            } else {
                latency = 40 + random.nextInt(360);
            }

            // ~10% error rate; 30% error spike every 20 ticks
            boolean isError;
            int statusCode;
            if (tick % 20 == 0) {
                isError = random.nextDouble() < 0.4;
            } else {
                isError = random.nextDouble() < 0.08;
            }
            if (isError) {
                statusCode = random.nextBoolean() ? 500 : 503;
            } else {
                statusCode = method.equals("POST") ? 201 : 200;
            }

            ApiAnalyticsEvent event = ApiAnalyticsEvent.builder()
                    .eventId(UUID.randomUUID().toString())
                    .timestamp(Instant.now())
                    .tenantId(tenant)
                    .correlationId(UUID.randomUUID().toString())
                    .method(method)
                    .path(path)
                    .statusCode(statusCode)
                    .latencyMs(latency)
                    .clientIp("10.0." + random.nextInt(10) + "." + random.nextInt(255))
                    .error(isError)
                    .serviceName("gateway-service")
                    .endpoint(method + " " + path)
                    .build();

            kafkaTemplate.send("api-events", tenant, event);
        }

        // Log a tick summary every 10 ticks
        if (tick % 10 == 0) {
            log.info("── Traffic generator tick {} ── {} events published so far",
                    tick, tick * 2);
        }
    }
}
""")

# ── DemoController ────────────────────────────────────────────
write("demo-service/src/main/java/com/platform/demo/controller/DemoController.java", """\
package com.platform.demo.controller;

import com.platform.demo.model.AlertNotification;
import com.platform.demo.model.ApiAnalyticsEvent;
import com.platform.demo.service.InMemoryMetricsStore;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;
import java.util.stream.Collectors;

/**
 * REST API to inspect the live analytics data in this demo.
 *
 * GET /demo/metrics   — aggregated per-endpoint stats (last 60 s)
 * GET /demo/summary   — platform-wide summary
 * GET /demo/alerts    — list of fired alerts
 * GET /demo/events    — recent raw events (last 20)
 * GET /demo/dashboard — all data in one call
 */
@RestController
@RequestMapping("/demo")
@RequiredArgsConstructor
public class DemoController {

    private final InMemoryMetricsStore store;

    @GetMapping("/metrics")
    public ResponseEntity<List<Map<String, Object>>> metrics() {
        return ResponseEntity.ok(store.getMetrics());
    }

    @GetMapping("/summary")
    public ResponseEntity<Map<String, Object>> summary() {
        return ResponseEntity.ok(store.getSummary());
    }

    @GetMapping("/alerts")
    public ResponseEntity<List<AlertNotification>> alerts(
            @RequestParam(defaultValue = "20") int limit) {
        List<AlertNotification> result = store.getAlerts().stream()
                .limit(limit).collect(Collectors.toList());
        return ResponseEntity.ok(result);
    }

    @GetMapping("/events")
    public ResponseEntity<List<ApiAnalyticsEvent>> events(
            @RequestParam(defaultValue = "20") int limit,
            @RequestParam(required = false) String tenantId) {
        List<ApiAnalyticsEvent> result = store.getEvents().stream()
                .filter(e -> tenantId == null || e.getTenantId().equals(tenantId))
                .limit(limit)
                .collect(Collectors.toList());
        return ResponseEntity.ok(result);
    }

    @GetMapping("/dashboard")
    public ResponseEntity<Map<String, Object>> dashboard() {
        Map<String, Object> dash = new LinkedHashMap<>();
        dash.put("summary", store.getSummary());
        dash.put("metricsPerEndpoint", store.getMetrics());
        dash.put("recentAlerts", store.getAlerts().stream().limit(5).collect(Collectors.toList()));
        dash.put("recentEvents", store.getEvents().stream().limit(10).collect(Collectors.toList()));
        return ResponseEntity.ok(dash);
    }

    /** POST /demo/inject — manually inject a custom event */
    @PostMapping("/inject")
    public ResponseEntity<Map<String, String>> injectEvent(
            @RequestParam(defaultValue = "tenant-alpha") String tenant,
            @RequestParam(defaultValue = "GET") String method,
            @RequestParam(defaultValue = "/api/custom") String path,
            @RequestParam(defaultValue = "200") int status,
            @RequestParam(defaultValue = "100") long latencyMs) {

        com.platform.demo.model.ApiAnalyticsEvent event =
                com.platform.demo.model.ApiAnalyticsEvent.builder()
                        .eventId(UUID.randomUUID().toString())
                        .timestamp(java.time.Instant.now())
                        .tenantId(tenant)
                        .method(method)
                        .path(path)
                        .statusCode(status)
                        .latencyMs(latencyMs)
                        .error(status >= 400)
                        .serviceName("demo-inject")
                        .endpoint(method + " " + path)
                        .build();

        store.recordEvent(event);
        return ResponseEntity.ok(Map.of("injected", event.getEventId(), "status", "ok"));
    }
}
""")

# ── application.yml ────────────────────────────────────────────
write("demo-service/src/main/resources/application.yml", """\
spring:
  application:
    name: demo-service

  # Import common credentials (optional — demo runs fully embedded)
  config:
    import: "optional:file:../config/common-config.yml"

  # Kafka bootstrap-servers is set dynamically by EmbeddedKafkaBroker
  # via the brokerListProperty. No external Kafka needed.
  kafka:
    consumer:
      auto-offset-reset: earliest

server:
  port: 8888

management:
  endpoints:
    web:
      exposure:
        include: health,info
  endpoint:
    health:
      show-details: always

platform:
  alert:
    latency-threshold-ms: 3000   # 3 s (lower than prod to easily see alerts)
    error-rate-threshold: 0.30   # 30%

logging:
  level:
    com.platform.demo: INFO
    org.apache.kafka: WARN
    org.springframework.kafka: WARN
  pattern:
    console: "%d{HH:mm:ss.SSS} %-5level [demo] %msg%n"
""")

print("\nDemo service generated.")
print("Run it with:")
print("  cd demo-service && ../gradlew bootRun")

