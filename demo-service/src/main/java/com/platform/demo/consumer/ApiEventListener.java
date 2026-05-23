package com.platform.demo.consumer;

import com.platform.demo.model.ApiAnalyticsEventMessage;
import com.platform.demo.service.InMemoryMetricsStore;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

/**
 * Simulates the analytics-service Kafka consumer.
 * Listens for ApiAnalyticsEventMessage (Spring App events = Kafka in this demo)
 * and stores them in the InMemoryMetricsStore.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ApiEventListener {

    private final InMemoryMetricsStore metricsStore;

    @Async
    @EventListener
    public void onEvent(ApiAnalyticsEventMessage message) {
        var event = message.getAnalyticsEvent();
        metricsStore.recordEvent(event);
        String icon = event.isError() ? "❌" : "✅";
        log.info("{} tenant={} | {} → {}ms | HTTP {}",
                icon, event.getTenantId(), event.getEndpoint(),
                event.getLatencyMs(), event.getStatusCode());
    }
}
