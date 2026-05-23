package com.platform.alert.service;

import com.platform.alert.model.AlertNotification;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.stereotype.Service;

import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;

/**
 * Sends alert notifications via email using Spring's JavaMailSender.
 * Configure SMTP credentials in config/common-config.yml under spring.mail.*.
 * Enable email alerts by setting: platform.email.enabled=true
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class EmailNotificationService {

    private final JavaMailSender mailSender;

    @Value("${platform.email.from:alerts@your-domain.com}")
    private String from;

    @Value("${platform.email.to:team@your-domain.com}")
    private String to;

    @Value("${platform.email.enabled:false}")
    private boolean enabled;

    public void sendAlert(AlertNotification notification) {
        if (!enabled) {
            log.debug("Email notifications disabled — skipping alert: {}", notification.getTitle());
            return;
        }

        try {
            SimpleMailMessage message = new SimpleMailMessage();
            message.setFrom(from);
            message.setTo(to.split(","));
            message.setSubject(String.format("[API Alert][%s] %s",
                    notification.getSeverity(), notification.getTitle()));
            message.setText(buildEmailBody(notification));
            mailSender.send(message);
            log.info("Email alert sent to {} for alert: {}", to, notification.getTitle());
        } catch (Exception ex) {
            log.error("Failed to send email alert '{}': {}", notification.getTitle(), ex.getMessage());
        }
    }

    private String buildEmailBody(AlertNotification notification) {
        DateTimeFormatter fmt = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss").withZone(ZoneOffset.UTC);
        return String.format(
                "API Gateway Analytics Platform — Alert Notification\n" +
                "=========================================================\n\n" +
                "Severity  : %s\n" +
                "Alert Type: %s\n" +
                "Title     : %s\n\n" +
                "Details\n" +
                "-------\n" +
                "%s\n\n" +
                "Tenant    : %s\n" +
                "Endpoint  : %s\n" +
                "Value     : %.2f\n" +
                "Threshold : %.2f\n" +
                "Triggered : %s (UTC)\n\n" +
                "Please investigate via Kibana / Jaeger dashboards.\n",
                notification.getSeverity(),
                notification.getType(),
                notification.getTitle(),
                notification.getMessage(),
                notification.getTenantId(),
                notification.getEndpoint(),
                notification.getCurrentValue(),
                notification.getThresholdValue(),
                fmt.format(notification.getTriggeredAt())
        );
    }
}
