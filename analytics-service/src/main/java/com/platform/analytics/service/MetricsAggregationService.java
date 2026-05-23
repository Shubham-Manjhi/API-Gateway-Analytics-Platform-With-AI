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

        // Retrieve events in the time window across all tenants
        List<ApiEventDocument> events = eventRepository.findByTimestampBetween(windowStart, windowEnd);

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
            String[] parts = key.split("[|]", 2);
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
