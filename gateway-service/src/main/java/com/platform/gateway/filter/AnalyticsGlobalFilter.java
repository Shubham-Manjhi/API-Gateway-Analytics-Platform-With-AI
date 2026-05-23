package com.platform.gateway.filter;

import com.platform.gateway.model.ApiAnalyticsEvent;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.net.InetSocketAddress;
import java.time.Instant;
import java.util.UUID;

/**
 * Global reactive filter that intercepts every inbound request,
 * measures end-to-end latency, and publishes a structured
 * {@link ApiAnalyticsEvent} to the Kafka 'api-events' topic.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class AnalyticsGlobalFilter implements GlobalFilter, Ordered {

    private final KafkaTemplate<String, ApiAnalyticsEvent> kafkaTemplate;

    @Value("${platform.kafka.topics.api-events:api-events}")
    private String apiEventsTopic;

    @Value("${platform.multi-tenancy.default-tenant-id:default}")
    private String defaultTenantId;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        final long startTime = System.currentTimeMillis();

        // Ensure correlation ID is present in the request
        String incomingCorrelationId = exchange.getRequest().getHeaders().getFirst("X-Correlation-ID");
        final String correlationId = (incomingCorrelationId != null && !incomingCorrelationId.isBlank())
                ? incomingCorrelationId
                : UUID.randomUUID().toString();

        ServerHttpRequest mutatedRequest = exchange.getRequest()
                .mutate()
                .header("X-Correlation-ID", correlationId)
                .build();

        ServerWebExchange mutatedExchange = exchange.mutate()
                .request(mutatedRequest)
                .build();

        return chain.filter(mutatedExchange)
                .doFinally(signalType -> {
                    try {
                        long latencyMs = System.currentTimeMillis() - startTime;
                        publishAnalyticsEvent(mutatedExchange, latencyMs, correlationId);
                    } catch (Exception ex) {
                        log.error("Failed to publish analytics event: {}", ex.getMessage(), ex);
                    }
                });
    }

    private void publishAnalyticsEvent(ServerWebExchange exchange, long latencyMs, String correlationId) {
        ServerHttpRequest request = exchange.getRequest();
        ServerHttpResponse response = exchange.getResponse();

        int statusCode = response.getStatusCode() != null ? response.getStatusCode().value() : 0;
        boolean isError = statusCode >= 400;

        String tenantId = request.getHeaders().getFirst("X-Tenant-ID");
        if (tenantId == null || tenantId.isBlank()) {
            tenantId = defaultTenantId;
        }

        long reqContentLength = request.getHeaders().getContentLength();
        Long requestSize = reqContentLength > 0 ? reqContentLength : null;

        ApiAnalyticsEvent event = ApiAnalyticsEvent.builder()
                .eventId(UUID.randomUUID().toString())
                .timestamp(Instant.now())
                .tenantId(tenantId)
                .correlationId(correlationId)
                .method(request.getMethod().name())
                .path(request.getPath().value())
                .host(request.getURI().getHost())
                .statusCode(statusCode)
                .latencyMs(latencyMs)
                .clientIp(extractClientIp(request))
                .userAgent(request.getHeaders().getFirst("User-Agent"))
                .requestSize(requestSize)
                .error(isError)
                .serviceName("gateway-service")
                .build();

        kafkaTemplate.send(apiEventsTopic, tenantId, event)
                .whenComplete((result, ex) -> {
                    if (ex != null) {
                        log.error("Kafka publish failed [topic={}]: {}", apiEventsTopic, ex.getMessage());
                    } else {
                        log.debug("Event published [eventId={}, path={}, status={}, latency={}ms]",
                                event.getEventId(), event.getPath(), event.getStatusCode(), event.getLatencyMs());
                    }
                });
    }

    private String extractClientIp(ServerHttpRequest request) {
        String xForwardedFor = request.getHeaders().getFirst("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isBlank()) {
            return xForwardedFor.split(",")[0].trim();
        }
        InetSocketAddress remote = request.getRemoteAddress();
        return remote != null ? remote.getAddress().getHostAddress() : "unknown";
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE;
    }
}
