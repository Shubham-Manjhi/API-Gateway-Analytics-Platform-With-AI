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
