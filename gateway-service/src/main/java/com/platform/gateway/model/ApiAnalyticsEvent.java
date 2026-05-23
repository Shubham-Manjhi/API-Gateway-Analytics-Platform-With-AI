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
