package com.platform.alert.consumer;

import com.platform.alert.model.AnalyticsAggregation;
import com.platform.alert.service.AlertEvaluationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Component;

/**
 * Consumes aggregated metrics from the 'analytics-events' Kafka topic
 * and delegates anomaly detection to {@link AlertEvaluationService}.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AnalyticsEventConsumer {

    private final AlertEvaluationService alertEvaluationService;

    @KafkaListener(
            topics = "${platform.kafka.topics.analytics-events:analytics-events}",
            groupId = "${spring.kafka.consumer.group-id:alert-service-group}",
            containerFactory = "kafkaListenerContainerFactory"
    )
    public void consume(
            @Payload AnalyticsAggregation aggregation,
            @Header(KafkaHeaders.RECEIVED_TOPIC) String topic,
            @Header(KafkaHeaders.OFFSET) long offset) {

        log.debug("Received aggregation [topic={}, offset={}] tenant={}, endpoint={}",
                topic, offset, aggregation.getTenantId(), aggregation.getEndpoint());

        alertEvaluationService.evaluate(aggregation);
    }
}
