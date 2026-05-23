package com.platform.demo.controller;

import com.platform.demo.logging.InMemoryLogAppender;
import com.platform.demo.model.AlertNotification;
import com.platform.demo.model.LogEntry;
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
    /**
     * GET /demo/logs?limit=200&level=WARN
     * Returns captured service log entries (newest first).
     * level: optional filter — INFO | WARN | ERROR | DEBUG
     */
    @GetMapping("/logs")
    public ResponseEntity<List<LogEntry>> getLogs(
            @RequestParam(defaultValue = "200") int limit,
            @RequestParam(required = false) String level) {

        return ResponseEntity.ok(
                InMemoryLogAppender.getBuffer().stream()
                        .filter(l -> level == null || l.getLevel().equalsIgnoreCase(level))
                        .limit(limit)
                        .collect(Collectors.toList()));
    }

    /** DELETE /demo/logs — clears the in-memory log buffer. */
    @DeleteMapping("/logs")
    public ResponseEntity<Void> clearLogs() {
        InMemoryLogAppender.clear();
        return ResponseEntity.noContent().build();
    }

}
