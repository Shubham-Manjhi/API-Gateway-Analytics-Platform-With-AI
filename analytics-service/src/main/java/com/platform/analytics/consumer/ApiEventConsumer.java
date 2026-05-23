package com.platform.analytics.consumer;

import com.platform.analytics.model.ApiAnalyticsEvent;
import com.platform.analytics.service.MetricsAggregationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Component;

/**
 * Kafka consumer that receives API analytics events from the gateway
 * and delegates to {@link MetricsAggregationService} for persistence.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ApiEventConsumer {

    private final MetricsAggregationService metricsAggregationService;

    @KafkaListener(
            topics = "${platform.kafka.topics.api-events:api-events}",
            groupId = "${spring.kafka.consumer.group-id:analytics-service-group}",
            containerFactory = "kafkaListenerContainerFactory"
    )
    public void consume(
            @Payload ApiAnalyticsEvent event,
            @Header(KafkaHeaders.RECEIVED_TOPIC) String topic,
            @Header(KafkaHeaders.RECEIVED_PARTITION) int partition,
            @Header(KafkaHeaders.OFFSET) long offset) {

        log.debug("Received event [topic={}, partition={}, offset={}] eventId={}",
                topic, partition, offset, event.getEventId());

        try {
            metricsAggregationService.processEvent(event);
        } catch (Exception ex) {
            log.error("Error processing event eventId={}: {}", event.getEventId(), ex.getMessage(), ex);
            throw ex; // Re-throw so DLQ error handler can route to api-events-dlq
        }
    }
}
