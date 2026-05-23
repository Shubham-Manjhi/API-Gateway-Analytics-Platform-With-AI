package com.platform.demo.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;

@Configuration
@EnableAsync
public class AppConfig {
    // Enables @Async on ApiEventListener so event processing is non-blocking
}
