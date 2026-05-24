package com.platform.demo.model;

import lombok.Builder;
import lombok.Data;

@Data @Builder
public class AiAnalysisResponse {
    private String content;     // The full AI markdown response
    private String model;       // Model used
    private String provider;    // Provider name
    private boolean success;
    private String error;       // Non-null on failure
    private long latencyMs;     // How long the AI call took
}

