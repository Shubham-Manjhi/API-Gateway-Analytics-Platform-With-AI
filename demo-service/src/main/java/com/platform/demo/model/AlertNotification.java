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
