#!/usr/bin/env python3
"""Regenerates the demo service using Spring ApplicationEvents (no Kafka needed)."""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def write(rel, content):
    p = os.path.join(BASE, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write(content)
    print(f"  + {rel}")

# ── build.gradle (simpler — no Kafka at all in demo) ──────────
write("demo-service/build.gradle",
"plugins {\n"
"    id 'org.springframework.boot'\n"
"    id 'io.spring.dependency-management'\n"
"}\n\n"
"dependencies {\n"
"    implementation 'org.springframework.boot:spring-boot-starter-web'\n"
"    implementation 'org.springframework.boot:spring-boot-starter-actuator'\n"
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
 * Simulates the FULL event pipeline in a single JVM:
 *
 *   SampleTrafficGenerator ─── ApplicationEvent ──▶ ApiEventListener
 *       (simulates Gateway)          (Kafka-like bus)   (simulates Analytics-Service)
 *                                                              │
 *                                                     InMemoryMetricsStore
 *                                                      (replaces Elasticsearch)
 *                                                              │
 *                                                     AlertEvaluationService
 *                                                      (simulates Alert-Service)
 *
 * REST API at http://localhost:8888:
 *   GET /demo/dashboard  ─ full live view
 *   GET /demo/metrics    ─ per-endpoint stats (last 60 s)
 *   GET /demo/summary    ─ platform-wide totals
 *   GET /demo/alerts     ─ fired alerts
 *   GET /demo/events     ─ recent raw events
 *   POST /demo/inject    ─ inject a custom event
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

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.Instant;

/** Structured event representing a single captured API request. */
@Data @Builder @NoArgsConstructor @AllArgsConstructor
public class ApiAnalyticsEvent {
    private String eventId;
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

# ── ApiAnalyticsEventMessage ──────────────────────────────────
write("demo-service/src/main/java/com/platform/demo/model/ApiAnalyticsEventMessage.java", """\
package com.platform.demo.model;

import org.springframework.context.ApplicationEvent;

/**
 * Spring ApplicationEvent wrapper — acts as the "Kafka message bus"
 * in this demo. In production the gateway publishes to a real Kafka topic.
 */
public class ApiAnalyticsEventMessage extends ApplicationEvent {
    private final ApiAnalyticsEvent analyticsEvent;

    public ApiAnalyticsEventMessage(Object source, ApiAnalyticsEvent event) {
        super(source);
        this.analyticsEvent = event;
    }

    public ApiAnalyticsEvent getAnalyticsEvent() {
        return analyticsEvent;
    }
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
 * In-memory store replacing Elasticsearch + Alert-Service for this demo.
 * Keeps the last MAX_EVENTS events and all fired alerts in memory.
 */
@Slf4j
@Service
public class InMemoryMetricsStore {

    private static final int MAX_EVENTS = 1000;

    @Getter
    private final Deque<ApiAnalyticsEvent> events = new ConcurrentLinkedDeque<>();
    @Getter
    private final Deque<AlertNotification> alerts = new ConcurrentLinkedDeque<>();

    @Value("${platform.alert.latency-threshold-ms:3000}")
    private long latencyThreshold;

    @Value("${platform.alert.error-rate-threshold:0.30}")
    private double errorRateThreshold;

    private final Map<String, Instant> cooldown = new HashMap<>();

    public void recordEvent(ApiAnalyticsEvent event) {
        events.addFirst(event);
        if (events.size() > MAX_EVENTS) events.removeLast();
        evaluateAlerts(event);
    }

    private void evaluateAlerts(ApiAnalyticsEvent latest) {
        Instant since = Instant.now().minusSeconds(60);
        List<ApiAnalyticsEvent> window = events.stream()
                .filter(e -> e.getTenantId().equals(latest.getTenantId())
                          && e.getEndpoint().equals(latest.getEndpoint())
                          && e.getTimestamp().isAfter(since))
                .collect(Collectors.toList());

        if (window.size() < 3) return;

        double avgLatency = window.stream().mapToLong(ApiAnalyticsEvent::getLatencyMs).average().orElse(0);
        long errorCount   = window.stream().filter(ApiAnalyticsEvent::isError).count();
        double errorRate  = (double) errorCount / window.size();

        if (avgLatency > latencyThreshold) {
            String key = latest.getTenantId() + "|" + latest.getEndpoint() + "|LAT";
            if (canAlert(key)) {
                AlertNotification.Severity sev = avgLatency > latencyThreshold * 2
                        ? AlertNotification.Severity.CRITICAL : AlertNotification.Severity.WARNING;
                AlertNotification alert = AlertNotification.builder()
                        .type(AlertNotification.AlertType.LATENCY_HIGH).severity(sev)
                        .message(String.format("[%s] Avg latency %.0f ms > threshold %d ms  →  %s",
                                latest.getTenantId(), avgLatency, latencyThreshold, latest.getEndpoint()))
                        .tenantId(latest.getTenantId()).endpoint(latest.getEndpoint())
                        .currentValue(avgLatency).thresholdValue(latencyThreshold)
                        .triggeredAt(Instant.now()).build();
                alerts.addFirst(alert);
                log.warn("🚨 ALERT [{}] {}", sev, alert.getMessage());
            }
        }

        if (errorRate > errorRateThreshold) {
            String key = latest.getTenantId() + "|" + latest.getEndpoint() + "|ERR";
            if (canAlert(key)) {
                AlertNotification.Severity sev = errorRate > errorRateThreshold * 2
                        ? AlertNotification.Severity.CRITICAL : AlertNotification.Severity.WARNING;
                AlertNotification alert = AlertNotification.builder()
                        .type(AlertNotification.AlertType.ERROR_RATE_HIGH).severity(sev)
                        .message(String.format("[%s] Error rate %.1f%% > threshold %.1f%%  →  %s",
                                latest.getTenantId(), errorRate * 100,
                                errorRateThreshold * 100, latest.getEndpoint()))
                        .tenantId(latest.getTenantId()).endpoint(latest.getEndpoint())
                        .currentValue(errorRate).thresholdValue(errorRateThreshold)
                        .triggeredAt(Instant.now()).build();
                alerts.addFirst(alert);
                log.warn("🚨 ALERT [{}] {}", sev, alert.getMessage());
            }
        }
    }

    private boolean canAlert(String key) {
        Instant last = cooldown.get(key);
        if (last == null || Instant.now().isAfter(last.plusSeconds(30))) {
            cooldown.put(key, Instant.now());
            return true;
        }
        return false;
    }

    public List<Map<String, Object>> getMetrics() {
        Instant since = Instant.now().minusSeconds(60);
        Map<String, List<ApiAnalyticsEvent>> grouped = events.stream()
                .filter(e -> e.getTimestamp().isAfter(since))
                .collect(Collectors.groupingBy(e -> e.getTenantId() + " | " + e.getEndpoint()));

        return grouped.entrySet().stream().map(entry -> {
            List<ApiAnalyticsEvent> g = entry.getValue();
            List<Long> lats = g.stream().map(ApiAnalyticsEvent::getLatencyMs).sorted().collect(Collectors.toList());
            long errs = g.stream().filter(ApiAnalyticsEvent::isError).count();
            long p95 = lats.isEmpty() ? 0 : lats.get(Math.max(0, (int)(lats.size() * 0.95) - 1));
            long p99 = lats.isEmpty() ? 0 : lats.get(Math.max(0, (int)(lats.size() * 0.99) - 1));
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("key", entry.getKey());
            m.put("requests_60s", g.size());
            m.put("errors", errs);
            m.put("errorRate", String.format("%.1f%%", g.isEmpty() ? 0 : 100.0 * errs / g.size()));
            m.put("avgLatencyMs", (long) g.stream().mapToLong(ApiAnalyticsEvent::getLatencyMs).average().orElse(0));
            m.put("p95LatencyMs", p95);
            m.put("p99LatencyMs", p99);
            return m;
        }).sorted(Comparator.comparingInt(m -> -((Integer)m.get("requests_60s")))).collect(Collectors.toList());
    }

    public Map<String, Object> getSummary() {
        long total = events.size();
        long errs  = events.stream().filter(ApiAnalyticsEvent::isError).count();
        OptionalDouble avg = events.stream().mapToLong(ApiAnalyticsEvent::getLatencyMs).average();
        Map<String, Object> s = new LinkedHashMap<>();
        s.put("totalEventsBuffered", total);
        s.put("errorCount", errs);
        s.put("errorRate", total > 0 ? String.format("%.1f%%", 100.0 * errs / total) : "0%");
        s.put("avgLatencyMs", avg.isPresent() ? (long) avg.getAsDouble() : 0);
        s.put("alertsFired", alerts.size());
        s.put("tenantsActive", events.stream().map(ApiAnalyticsEvent::getTenantId).distinct().count());
        s.put("endpointsTracked", events.stream().map(ApiAnalyticsEvent::getEndpoint).distinct().count());
        return s;
    }
}
""")

# ── ApiEventListener ──────────────────────────────────────────
write("demo-service/src/main/java/com/platform/demo/consumer/ApiEventListener.java", """\
package com.platform.demo.consumer;

import com.platform.demo.model.ApiAnalyticsEventMessage;
import com.platform.demo.service.InMemoryMetricsStore;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

/**
 * Simulates the analytics-service Kafka consumer.
 * Listens for ApiAnalyticsEventMessage (Spring App events = Kafka in this demo)
 * and stores them in the InMemoryMetricsStore.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ApiEventListener {

    private final InMemoryMetricsStore metricsStore;

    @Async
    @EventListener
    public void onEvent(ApiAnalyticsEventMessage message) {
        var event = message.getAnalyticsEvent();
        metricsStore.recordEvent(event);
        String icon = event.isError() ? "❌" : "✅";
        log.info("{} tenant={} | {} → {}ms | HTTP {}",
                icon, event.getTenantId(), event.getEndpoint(),
                event.getLatencyMs(), event.getStatusCode());
    }
}
""")

# ── SampleTrafficGenerator ────────────────────────────────────
write("demo-service/src/main/java/com/platform/demo/runner/SampleTrafficGenerator.java", """\
package com.platform.demo.runner;

import com.platform.demo.model.ApiAnalyticsEvent;
import com.platform.demo.model.ApiAnalyticsEventMessage;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.List;
import java.util.Random;
import java.util.UUID;

/**
 * Simulates API gateway traffic by publishing ApiAnalyticsEvent via Spring ApplicationEvents.
 * In production this would be the Spring Cloud Gateway publishing to Kafka.
 *
 * Traffic pattern:
 *  - 3 tenants: tenant-alpha, tenant-beta, tenant-gamma
 *  - 8 endpoints across users/orders/products/payments/auth/reports
 *  - Normal latency: 40–400ms
 *  - Latency spike every 15 ticks: 3.5s–6.5s  (triggers LATENCY_HIGH alert)
 *  - Normal error rate: ~8%
 *  - Error spike every 20 ticks: ~40%          (triggers ERROR_RATE_HIGH alert)
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class SampleTrafficGenerator {

    private final ApplicationEventPublisher eventPublisher;
    private final Random random = new Random();

    private static final List<String> TENANTS = List.of("tenant-alpha", "tenant-beta", "tenant-gamma");
    private static final List<String> METHODS = List.of("GET","GET","GET","POST","PUT","DELETE");
    private static final List<String> PATHS   = List.of(
            "/api/users", "/api/users/{id}", "/api/orders",
            "/api/orders/{id}", "/api/products", "/api/payments",
            "/api/auth/login", "/api/reports/daily");
    private static final List<String> CLIENT_IPS = List.of(
            "10.0.1.10", "10.0.2.25", "192.168.1.42", "172.16.0.5");

    private int tick = 0;

    @Scheduled(fixedDelay = 600)
    public void generateTraffic() {
        tick++;
        int eventsThisTick = 1 + random.nextInt(3);

        for (int i = 0; i < eventsThisTick; i++) {
            String tenant = TENANTS.get(random.nextInt(TENANTS.size()));
            String path   = PATHS.get(random.nextInt(PATHS.size()));
            String method = METHODS.get(random.nextInt(METHODS.size()));

            // Latency spike every 15 ticks on first event
            boolean spiked = (tick % 15 == 0 && i == 0);
            long latency   = spiked ? 3500 + random.nextInt(2500) : 40 + random.nextInt(350);

            // Error spike every 20 ticks
            boolean errorSpike = (tick % 20 == 0);
            boolean isError    = random.nextDouble() < (errorSpike ? 0.45 : 0.08);
            int statusCode     = isError ? (random.nextBoolean() ? 500 : 503)
                                         : (method.equals("POST") ? 201 : 200);

            ApiAnalyticsEvent event = ApiAnalyticsEvent.builder()
                    .eventId(UUID.randomUUID().toString())
                    .timestamp(Instant.now())
                    .tenantId(tenant)
                    .correlationId(UUID.randomUUID().toString())
                    .method(method).path(path)
                    .statusCode(statusCode).latencyMs(latency)
                    .clientIp(CLIENT_IPS.get(random.nextInt(CLIENT_IPS.size())))
                    .error(isError)
                    .serviceName("gateway-service-[simulated]")
                    .endpoint(method + " " + path)
                    .build();

            // Publish to the "Kafka bus" (Spring ApplicationEvent)
            eventPublisher.publishEvent(new ApiAnalyticsEventMessage(this, event));
        }
    }
}
""")

# ── DemoController ────────────────────────────────────────────
write("demo-service/src/main/java/com/platform/demo/controller/DemoController.java", """\
package com.platform.demo.controller;

import com.platform.demo.model.AlertNotification;
import com.platform.demo.model.ApiAnalyticsEvent;
import com.platform.demo.model.ApiAnalyticsEventMessage;
import com.platform.demo.service.InMemoryMetricsStore;
import lombok.RequiredArgsConstructor;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Live analytics REST API for the demo.
 *
 * Open http://localhost:8888/demo/dashboard in your browser (or curl) to see live data.
 */
@RestController
@RequestMapping("/demo")
@RequiredArgsConstructor
public class DemoController {

    private final InMemoryMetricsStore store;
    private final ApplicationEventPublisher eventPublisher;

    /** Full live dashboard in one call. */
    @GetMapping("/dashboard")
    public ResponseEntity<Map<String, Object>> dashboard() {
        Map<String, Object> d = new LinkedHashMap<>();
        d.put("_info", "Live data — refreshes every request. Traffic auto-generated every 600ms.");
        d.put("summary", store.getSummary());
        d.put("metricsPerEndpoint_last60s", store.getMetrics());
        d.put("recentAlerts", store.getAlerts().stream().limit(10).collect(Collectors.toList()));
        d.put("recentEvents", store.getEvents().stream().limit(15).collect(Collectors.toList()));
        return ResponseEntity.ok(d);
    }

    /** Aggregated per-endpoint stats for the last 60 seconds. */
    @GetMapping("/metrics")
    public ResponseEntity<List<Map<String, Object>>> metrics() {
        return ResponseEntity.ok(store.getMetrics());
    }

    /** Platform-wide totals. */
    @GetMapping("/summary")
    public ResponseEntity<Map<String, Object>> summary() {
        return ResponseEntity.ok(store.getSummary());
    }

    /** Fired alerts. */
    @GetMapping("/alerts")
    public ResponseEntity<List<AlertNotification>> alerts(
            @RequestParam(defaultValue = "20") int limit) {
        return ResponseEntity.ok(store.getAlerts().stream().limit(limit).collect(Collectors.toList()));
    }

    /** Recent raw events. */
    @GetMapping("/events")
    public ResponseEntity<List<ApiAnalyticsEvent>> events(
            @RequestParam(defaultValue = "20") int limit,
            @RequestParam(required = false) String tenantId) {
        return ResponseEntity.ok(
                store.getEvents().stream()
                        .filter(e -> tenantId == null || e.getTenantId().equals(tenantId))
                        .limit(limit)
                        .collect(Collectors.toList()));
    }

    /**
     * Inject a custom event to manually test thresholds.
     * Example:
     *   curl -X POST "http://localhost:8888/demo/inject?latencyMs=6000&status=500"
     */
    @PostMapping("/inject")
    public ResponseEntity<Map<String, Object>> inject(
            @RequestParam(defaultValue = "tenant-alpha") String tenant,
            @RequestParam(defaultValue = "GET") String method,
            @RequestParam(defaultValue = "/api/orders") String path,
            @RequestParam(defaultValue = "200") int status,
            @RequestParam(defaultValue = "150") long latencyMs) {

        ApiAnalyticsEvent event = ApiAnalyticsEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .timestamp(Instant.now())
                .tenantId(tenant).correlationId(UUID.randomUUID().toString())
                .method(method).path(path)
                .statusCode(status).latencyMs(latencyMs)
                .clientIp("127.0.0.1")
                .error(status >= 400)
                .serviceName("demo-inject")
                .endpoint(method + " " + path)
                .build();

        eventPublisher.publishEvent(new ApiAnalyticsEventMessage(this, event));

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("status", "injected");
        response.put("eventId", event.getEventId());
        response.put("tenant", tenant);
        response.put("endpoint", event.getEndpoint());
        response.put("latencyMs", latencyMs);
        response.put("httpStatus", status);
        response.put("isError", status >= 400);
        return ResponseEntity.ok(response);
    }
}
""")

# ── AppConfig (enable async) ──────────────────────────────────
write("demo-service/src/main/java/com/platform/demo/config/AppConfig.java", """\
package com.platform.demo.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;

@Configuration
@EnableAsync
public class AppConfig {
    // Enables @Async on ApiEventListener so event processing is non-blocking
}
""")

# ── application.yml ────────────────────────────────────────────
write("demo-service/src/main/resources/application.yml", """\
spring:
  application:
    name: api-gateway-analytics-demo

  # Import common credentials — optional for this demo
  config:
    import: "optional:file:../config/common-config.yml"

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

# Alert thresholds used by InMemoryMetricsStore
platform:
  alert:
    latency-threshold-ms: 3000    # 3 s  (lower than prod to easily trigger alerts)
    error-rate-threshold:  0.30   # 30%

logging:
  level:
    com.platform.demo: INFO
    org.springframework: WARN
  pattern:
    console: "%d{HH:mm:ss.SSS} %-5level %msg%n"
""")

# ── banner.txt ─────────────────────────────────────────────────
write("demo-service/src/main/resources/banner.txt", """\

  ___  ___ ___   ___       _           _   _
 / _ \\/ __/ __| / _ \\ __ _| |_ _____ _| |_| |_   _
| (_) \\__ \\__ \\| (_) / _' |  _/ -_) V / / _| || |
 \\__\\_\\___/___/ \\__,_\\__,_|\\__\\___|\\_/|_\\__|\\_, |
    _          _      _   _         _         |__/
   /_\\  _ _  __ _| |_  _| |_(_)__ ___ | |___
  / _ \\| ' \\/ _` | | || |  _| / _(_-<| |__ /
 /_/ \\_\\_||_\\__,_|_|\\_, |\\__|_\\__/__/|_|___/
                    |__/
  Platform Demo — port 8888 — /demo/dashboard
""")

print("\nDemo service regenerated (no Kafka required!).")

