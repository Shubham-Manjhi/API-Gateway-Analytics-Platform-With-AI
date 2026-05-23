package com.platform.alert.model;

import lombok.Builder;
import lombok.Data;

import java.time.Instant;

/** Represents a triggered alert notification sent to Slack / email. */
@Data
@Builder
public class AlertNotification {

    public enum AlertType { LATENCY_HIGH, ERROR_RATE_HIGH, TRAFFIC_SPIKE }
    public enum Severity  { WARNING, CRITICAL }

    private String alertId;
    private AlertType type;
    private Severity severity;
    private String title;
    private String message;
    private String tenantId;
    private String endpoint;
    private double currentValue;
    private double thresholdValue;
    private Instant triggeredAt;
}
