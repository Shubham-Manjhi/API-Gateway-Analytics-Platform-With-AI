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
