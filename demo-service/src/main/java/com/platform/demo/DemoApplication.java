package com.platform.demo;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Self-contained demo of the API Gateway Analytics Platform.
 *
 * Simulates the FULL event pipeline in a single JVM:
 *
 *   SampleTrafficGenerator ─── ApplicationEvent ──▶ ApiEventListener
 *       (simulates Gateway)          (Kafka-like bus)   (simulates Analytics-Service)
 *                                                              │
 *                                                     InMemoryMetricsStore
 *                                                      (replaces Elasticsearch)
 *                                                              │
 *                                                     AlertEvaluationService
 *                                                      (simulates Alert-Service)
 *
 * REST API at http://localhost:8888:
 *   GET /demo/dashboard  ─ full live view
 *   GET /demo/metrics    ─ per-endpoint stats (last 60 s)
 *   GET /demo/summary    ─ platform-wide totals
 *   GET /demo/alerts     ─ fired alerts
 *   GET /demo/events     ─ recent raw events
 *   POST /demo/inject    ─ inject a custom event
 */
@SpringBootApplication
@EnableScheduling
public class DemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoApplication.class, args);
    }
}
