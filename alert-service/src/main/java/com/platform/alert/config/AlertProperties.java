package com.platform.alert.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * Strongly-typed binding for all 'platform.alert.*' properties
 * defined in config/common-config.yml.
 */
@Data
@Component
@ConfigurationProperties(prefix = "platform.alert")
public class AlertProperties {

    /** Maximum acceptable average latency in milliseconds. */
    private long latencyThresholdMs = 5000;

    /** Maximum acceptable error rate (0.0 – 1.0). */
    private double errorRateThreshold = 0.10;

    /** Multiplier above baseline traffic that triggers a spike alert. */
    private double trafficSpikeMultiplier = 3.0;

    /** Minimum number of requests to consider an alert valid. */
    private int minSampleSize = 10;

    /** How many minutes to suppress repeated alerts for the same key. */
    private int cooldownMinutes = 5;
}
