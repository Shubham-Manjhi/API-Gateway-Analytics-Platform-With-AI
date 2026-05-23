package com.platform.alert.service;

import com.platform.alert.config.AlertProperties;
import com.platform.alert.model.AlertNotification;
import com.platform.alert.model.AlertNotification.AlertType;
import com.platform.alert.model.AlertNotification.Severity;
import com.platform.alert.model.AnalyticsAggregation;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Evaluates incoming {@link AnalyticsAggregation} against configured thresholds
 * and fires alert notifications via Slack and/or email.
 *
 * Alert cooldown prevents repeated notifications for the same tenant+endpoint key.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AlertEvaluationService {

    private final AlertProperties properties;
    private final SlackNotificationService slackService;
    private final EmailNotificationService emailService;

    /** Tracks the last alert time per "tenantId|endpoint|alertType" to enforce cooldown. */
    private final ConcurrentHashMap<String, Instant> lastAlertTime = new ConcurrentHashMap<>();

    public void evaluate(AnalyticsAggregation agg) {
        if (agg.getRequestCount() < properties.getMinSampleSize()) {
            log.debug("Skipping alert evaluation: sample size {} < minimum {}",
                    agg.getRequestCount(), properties.getMinSampleSize());
            return;
        }

        checkLatency(agg);
        checkErrorRate(agg);
    }

    private void checkLatency(AnalyticsAggregation agg) {
        double threshold = properties.getLatencyThresholdMs();
        if (agg.getAvgLatencyMs() > threshold) {
            Severity severity = agg.getAvgLatencyMs() > threshold * 2 ? Severity.CRITICAL : Severity.WARNING;
            String alertKey = alertKey(agg, AlertType.LATENCY_HIGH);

            if (isCooledDown(alertKey)) {
                AlertNotification notification = AlertNotification.builder()
                        .alertId(UUID.randomUUID().toString())
                        .type(AlertType.LATENCY_HIGH)
                        .severity(severity)
                        .title(severity + ": High Latency Detected")
                        .message(String.format(
                                "Average latency %.0f ms exceeds threshold %.0f ms on endpoint '%s'",
                                agg.getAvgLatencyMs(), threshold, agg.getEndpoint()))
                        .tenantId(agg.getTenantId())
                        .endpoint(agg.getEndpoint())
                        .currentValue(agg.getAvgLatencyMs())
                        .thresholdValue(threshold)
                        .triggeredAt(Instant.now())
                        .build();

                sendAlert(notification, alertKey);
            }
        }
    }

    private void checkErrorRate(AnalyticsAggregation agg) {
        double threshold = properties.getErrorRateThreshold();
        if (agg.getErrorRate() > threshold) {
            Severity severity = agg.getErrorRate() > threshold * 2 ? Severity.CRITICAL : Severity.WARNING;
            String alertKey = alertKey(agg, AlertType.ERROR_RATE_HIGH);

            if (isCooledDown(alertKey)) {
                AlertNotification notification = AlertNotification.builder()
                        .alertId(UUID.randomUUID().toString())
                        .type(AlertType.ERROR_RATE_HIGH)
                        .severity(severity)
                        .title(severity + ": Error Rate Spike Detected")
                        .message(String.format(
                                "Error rate %.1f%% exceeds threshold %.1f%% on endpoint '%s'",
                                agg.getErrorRate() * 100, threshold * 100, agg.getEndpoint()))
                        .tenantId(agg.getTenantId())
                        .endpoint(agg.getEndpoint())
                        .currentValue(agg.getErrorRate())
                        .thresholdValue(threshold)
                        .triggeredAt(Instant.now())
                        .build();

                sendAlert(notification, alertKey);
            }
        }
    }

    private void sendAlert(AlertNotification notification, String alertKey) {
        log.warn("ALERT FIRED [{}] tenant={}, endpoint={}: {}",
                notification.getSeverity(), notification.getTenantId(),
                notification.getEndpoint(), notification.getMessage());

        slackService.sendAlert(notification);
        emailService.sendAlert(notification);
        lastAlertTime.put(alertKey, Instant.now());
    }

    private boolean isCooledDown(String alertKey) {
        Instant last = lastAlertTime.get(alertKey);
        if (last == null) return true;
        return Instant.now().isAfter(last.plus(properties.getCooldownMinutes(), ChronoUnit.MINUTES));
    }

    private String alertKey(AnalyticsAggregation agg, AlertType type) {
        return agg.getTenantId() + "|" + agg.getEndpoint() + "|" + type.name();
    }
}
