package com.platform.demo.runner;

import com.platform.demo.model.ApiAnalyticsEvent;
import com.platform.demo.model.ApiAnalyticsEventMessage;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.util.List;
import java.util.Random;
import java.util.UUID;

/**
 * Simulates API gateway traffic by publishing ApiAnalyticsEvent via Spring ApplicationEvents.
 * In production this would be the Spring Cloud Gateway publishing to Kafka.
 *
 * Traffic pattern:
 *  - 3 tenants: tenant-alpha, tenant-beta, tenant-gamma
 *  - 8 endpoints across users/orders/products/payments/auth/reports
 *  - Normal latency: 40–400ms
 *  - Latency spike every 15 ticks: 3.5s–6.5s  (triggers LATENCY_HIGH alert)
 *  - Normal error rate: ~8%
 *  - Error spike every 20 ticks: ~40%          (triggers ERROR_RATE_HIGH alert)
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class SampleTrafficGenerator {

    private final ApplicationEventPublisher eventPublisher;
    private final Random random = new Random();

    private static final List<String> TENANTS = List.of("tenant-alpha", "tenant-beta", "tenant-gamma");
    private static final List<String> METHODS = List.of("GET","GET","GET","POST","PUT","DELETE");
    private static final List<String> PATHS   = List.of(
            "/api/users", "/api/users/{id}", "/api/orders",
            "/api/orders/{id}", "/api/products", "/api/payments",
            "/api/auth/login", "/api/reports/daily");
    private static final List<String> CLIENT_IPS = List.of(
            "10.0.1.10", "10.0.2.25", "192.168.1.42", "172.16.0.5");

    private int tick = 0;

    @Scheduled(fixedDelay = 600)
    public void generateTraffic() {
        tick++;
        int eventsThisTick = 1 + random.nextInt(3);

        for (int i = 0; i < eventsThisTick; i++) {
            String tenant = TENANTS.get(random.nextInt(TENANTS.size()));
            String path   = PATHS.get(random.nextInt(PATHS.size()));
            String method = METHODS.get(random.nextInt(METHODS.size()));

            // Latency spike every 15 ticks on first event
            boolean spiked = (tick % 15 == 0 && i == 0);
            long latency   = spiked ? 3500 + random.nextInt(2500) : 40 + random.nextInt(350);

            // Error spike every 20 ticks
            boolean errorSpike = (tick % 20 == 0);
            boolean isError    = random.nextDouble() < (errorSpike ? 0.45 : 0.08);
            int statusCode     = isError ? (random.nextBoolean() ? 500 : 503)
                                         : (method.equals("POST") ? 201 : 200);

            ApiAnalyticsEvent event = ApiAnalyticsEvent.builder()
                    .eventId(UUID.randomUUID().toString())
                    .timestamp(Instant.now())
                    .tenantId(tenant)
                    .correlationId(UUID.randomUUID().toString())
                    .method(method).path(path)
                    .statusCode(statusCode).latencyMs(latency)
                    .clientIp(CLIENT_IPS.get(random.nextInt(CLIENT_IPS.size())))
                    .error(isError)
                    .serviceName("gateway-service-[simulated]")
                    .endpoint(method + " " + path)
                    .build();

            // Publish to the "Kafka bus" (Spring ApplicationEvent)
            eventPublisher.publishEvent(new ApiAnalyticsEventMessage(this, event));
        }
    }
}
