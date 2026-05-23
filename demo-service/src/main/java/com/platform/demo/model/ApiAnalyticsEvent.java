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
