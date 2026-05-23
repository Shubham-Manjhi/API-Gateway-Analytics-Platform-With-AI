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
