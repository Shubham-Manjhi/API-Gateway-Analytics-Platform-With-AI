package com.platform.alert.service;

import com.platform.alert.model.AlertNotification;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

/**
 * Sends formatted alert notifications to a Slack incoming webhook.
 * Configure the webhook URL in config/common-config.yml:
 *   platform.slack.webhook-url
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SlackNotificationService {

    private final RestTemplate restTemplate;

    @Value("${platform.slack.webhook-url:}")
    private String webhookUrl;

    @Value("${platform.slack.enabled:true}")
    private boolean enabled;

    public void sendAlert(AlertNotification notification) {
        if (!enabled || webhookUrl.isBlank() || webhookUrl.contains("YOUR/SLACK")) {
            log.info("Slack disabled or not configured — skipping alert: {}", notification.getTitle());
            return;
        }

        String emoji = notification.getSeverity() == AlertNotification.Severity.CRITICAL ? ":rotating_light:" : ":warning:";
        String text = String.format(
                "%s *[%s] %s*\n>%s\n>• Tenant: `%s`\n>• Endpoint: `%s`\n>• Value: `%.2f` (threshold: `%.2f`)",
                emoji,
                notification.getSeverity(),
                notification.getTitle(),
                notification.getMessage(),
                notification.getTenantId(),
                notification.getEndpoint(),
                notification.getCurrentValue(),
                notification.getThresholdValue()
        );

        Map<String, String> payload = Map.of("text", text);
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);

        try {
            restTemplate.postForEntity(webhookUrl, new HttpEntity<>(payload, headers), String.class);
            log.info("Slack alert sent: {}", notification.getTitle());
        } catch (Exception ex) {
            log.error("Failed to send Slack alert '{}': {}", notification.getTitle(), ex.getMessage());
        }
    }
}
