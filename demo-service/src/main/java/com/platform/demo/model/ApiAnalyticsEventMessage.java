package com.platform.demo.model;

import org.springframework.context.ApplicationEvent;

/**
 * Spring ApplicationEvent wrapper — acts as the "Kafka message bus"
 * in this demo. In production the gateway publishes to a real Kafka topic.
 */
public class ApiAnalyticsEventMessage extends ApplicationEvent {
    private final ApiAnalyticsEvent analyticsEvent;

    public ApiAnalyticsEventMessage(Object source, ApiAnalyticsEvent event) {
        super(source);
        this.analyticsEvent = event;
    }

    public ApiAnalyticsEvent getAnalyticsEvent() {
        return analyticsEvent;
    }
}
