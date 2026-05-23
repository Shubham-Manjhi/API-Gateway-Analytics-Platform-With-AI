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
