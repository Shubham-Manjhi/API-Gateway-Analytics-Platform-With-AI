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
