package com.platform.demo.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.platform.demo.model.AiAnalysisRequest;
import com.platform.demo.model.AiAnalysisResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import java.util.*;

/**
 * AI Analysis Service — calls SambaNova (DeepSeek-V3) with rich, structured prompts.
 * Produces professional markdown responses with tables, code diffs, and suggestions.
 */
@Slf4j
@Service
public class AiService {

    // ── Provider config (SambaNova — has active key) ──────────────────────────
    private static final String SAMBANOVA_API_KEY  = "baa45cb0-722d-4269-8ed4-15d6bbda7351";
    private static final String SAMBANOVA_MODEL    = "Meta-Llama-3.3-70B-Instruct"; // Best available on SambaNova (DeepSeek-V3-0324 deprecated)
    private static final String SAMBANOVA_BASE_URL = "https://api.sambanova.ai/v1/chat/completions";
    private static final int    MAX_TOKENS         = 2048;
    private static final double TEMPERATURE        = 0.25;

    private final RestTemplate  restTemplate = new RestTemplate();
    private final ObjectMapper  mapper       = new ObjectMapper();

    // ═══════════════════════════════════════════════════════════════════════════
    //  PUBLIC ENTRY POINT
    // ═══════════════════════════════════════════════════════════════════════════
    public AiAnalysisResponse analyze(AiAnalysisRequest req) {
        long start = System.currentTimeMillis();
        try {
            String system = systemPrompt();
            String user   = buildUserPrompt(req);
            String content = callSambaNova(system, user);
            return AiAnalysisResponse.builder()
                    .content(content)
                    .model(SAMBANOVA_MODEL)
                    .provider("SambaNova")
                    .success(true)
                    .latencyMs(System.currentTimeMillis() - start)
                    .build();
        } catch (Exception e) {
            log.error("AI analysis failed for action={} contextType={}: {}",
                    req.getAction(), req.getContextType(), e.getMessage());
            return AiAnalysisResponse.builder()
                    .success(false)
                    .error("AI request failed: " + e.getMessage())
                    .latencyMs(System.currentTimeMillis() - start)
                    .build();
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  HTTP CALL
    // ═══════════════════════════════════════════════════════════════════════════
    private String callSambaNova(String systemPrompt, String userPrompt) throws Exception {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", SAMBANOVA_MODEL);
        body.put("stream", false);
        body.put("max_tokens", MAX_TOKENS);
        body.put("temperature", TEMPERATURE);
        body.put("messages", List.of(
                Map.of("role", "system", "content", systemPrompt),
                Map.of("role", "user",   "content", userPrompt)
        ));

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setBearerAuth(SAMBANOVA_API_KEY);

        try {
            ResponseEntity<String> resp = restTemplate.postForEntity(
                    SAMBANOVA_BASE_URL,
                    new HttpEntity<>(body, headers),
                    String.class);

            JsonNode root = mapper.readTree(resp.getBody());
            return root.path("choices").get(0).path("message").path("content").asText();
        } catch (HttpClientErrorException e) {
            log.warn("SambaNova HTTP {}: {}", e.getStatusCode(), e.getResponseBodyAsString());
            throw new RuntimeException("SambaNova API error " + e.getStatusCode() + ": " + e.getResponseBodyAsString());
        }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  SYSTEM PROMPT — defines AI persona + formatting rules
    // ═══════════════════════════════════════════════════════════════════════════
    private String systemPrompt() {
        return """
            You are a **Senior SRE and API Gateway Expert** embedded in an enterprise API observability platform.
            You analyze real-time metrics, logs, alerts, and events from a multi-tenant Java Spring Boot microservices platform.
            
            ## Your Expertise
            - Java Spring Boot, Spring Cloud Gateway, REST API design
            - Distributed systems observability: latency, error rates, SLOs/SLAs
            - Incident response, root cause analysis, post-mortem writing
            - Performance optimization and capacity planning
            - Security and reliability best practices
            
            ## Response Formatting Rules (STRICTLY FOLLOW ALL)
            1. **Always use Markdown** — headers (##, ###), bold, italics, code blocks
            2. **Tables required** — use markdown tables for any comparative or structured data
            3. **Fenced code blocks** — ALWAYS specify language: ```java  ```json  ```bash  ```yaml  ```xml
            4. **Emojis for scanning** — use ✅ ❌ ⚠️ 🔧 🚨 📊 💡 🔍 🌱 ⚡ 🛡️ 🔮 📋 📈 at section starts
            5. **Code diffs** — for any fix, show BEFORE and AFTER in separate labeled code blocks
            6. **Actionable** — every response must end with concrete next steps
            7. **Concise** — use bullet points over paragraphs; max ~650 words unless code requires more
            8. **Severity badges** — use `[CRITICAL]` `[WARNING]` `[INFO]` inline labels
            9. **Inline code** — use backticks for all endpoint paths, class names, method names, values
            
            ## Code Fix Pattern (ALWAYS USE THIS FORMAT)
            When showing code fixes, use this exact structure:
            > **📍 Root location:** `ClassName.java` → `methodName()`
            
            **❌ Before (problematic pattern):**
            ```java
            // code that causes the issue
            ```
            
            **✅ After (fixed implementation):**
            ```java
            // corrected code with comments
            ```
            """;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    //  USER PROMPT ROUTER
    // ═══════════════════════════════════════════════════════════════════════════
    private String buildUserPrompt(AiAnalysisRequest req) {
        Map<String, Object> d = req.getData() != null ? req.getData() : Map.of();
        return switch (req.getContextType()) {
            case "error"    -> endpointPrompt(req.getAction(), d, true);
            case "endpoint" -> endpointPrompt(req.getAction(), d, false);
            case "alert"    -> alertPrompt(req.getAction(), d);
            case "tenant"   -> tenantPrompt(req.getAction(), d);
            case "warn"     -> logPrompt(req.getAction(), d, "WARN");
            case "log"      -> logPrompt(req.getAction(), d, "INFO");
            default         -> genericPrompt(req.getAction(), d);
        };
    }

    // ── Endpoint / Error prompt ────────────────────────────────────────────────
    private String endpointPrompt(String action, Map<String, Object> d, boolean isError) {
        String errRateParsed = d.getOrDefault("errorRate", "0%").toString().replace("%", "");
        double errRate = parseDouble(errRateParsed);
        String severityLabel = errRate > 30 ? "[CRITICAL]" : errRate > 10 ? "[WARNING]" : "[INFO]";

        return """
            ## %s Endpoint Analysis Request

            **Requested Action:** `%s`
            **Severity:** `%s`

            ### 📊 Endpoint Context
            | Field            | Value                                  |
            |------------------|----------------------------------------|
            | Endpoint         | `%s`                                   |
            | Tenant           | `%s`                                   |
            | Error Rate       | **%s** (threshold: 10%% WARN / 30%% CRITICAL) |
            | Error Count      | **%s** errors out of **%s** requests (last 60s) |
            | Avg Latency      | `%sms`                                 |
            | p95 Latency      | `%sms`                                 |
            | p99 Latency      | `%sms`                                 |
            | Status           | %s                                     |

            ### 🔎 Analysis Required
            Provide a complete analysis with all of the following sections:

            1. **📊 Problem Summary** — Describe this error pattern and its impact on users/SLA
            2. **🔍 Root Cause Analysis** — List the top 3 likely causes ranked by probability with reasoning
            3. **📋 Diagnostic Checklist** — Exactly how to investigate this in a Java/Spring Boot microservice (commands, log patterns, tools)
            4. **🔧 Code Fix** — Show the most likely root cause as a concrete Java Spring Boot fix:
               - Identify the likely class/method that's failing
               - Show BEFORE (broken) and AFTER (fixed) code blocks with full comments
               - The fix must be realistic for a `%s` endpoint returning errors
            5. **🛡️ Prevention Plan** — Configuration, code patterns, and circuit-breaker/retry strategies to prevent recurrence
            6. **📈 Alert Rule Recommendation** — Suggest exact threshold values in YAML config format
            """.formatted(
                isError ? "🚨 Error" : "📊",
                action, severityLabel,
                d.getOrDefault("endpoint", "Unknown"), d.getOrDefault("tenant", "Unknown"),
                d.getOrDefault("errorRate", "0%"),
                d.getOrDefault("errors", "0"), d.getOrDefault("requests", "0"),
                d.getOrDefault("avgLatency", "?"), d.getOrDefault("p95Latency", "?"),
                d.getOrDefault("p99Latency", "?"),
                isError ? "❌ Elevated errors detected" : "✅ Monitoring",
                d.getOrDefault("endpoint", "POST /api/endpoint")
        );
    }

    // ── Alert prompt ──────────────────────────────────────────────────────────
    private String alertPrompt(String action, Map<String, Object> d) {
        return """
            ## 🚨 Alert Analysis Request

            **Requested Action:** `%s`

            ### Alert Details
            | Field           | Value                           |
            |-----------------|---------------------------------|
            | Alert Type      | `%s`                            |
            | Severity        | **`%s`**                        |
            | Current Value   | **%s** (threshold: **%s**)      |
            | Tenant          | `%s`                            |
            | Endpoint        | `%s`                            |
            | Triggered At    | `%s`                            |

            ### Alert Message
            > %s

            ### 🔎 Analysis Required
            Answer all sections below:

            1. **🚨 Plain-English Explanation** — What happened, why this alert fired, and what users are experiencing right now
            2. **📊 Business Impact** — Estimated impact on users/revenue/reliability (quantify where possible)
            3. **🔍 Root Cause Analysis** — Top 3 causes specific to this alert type in Java/Spring Boot microservices
            4. **⚡ Immediate Runbook** — Numbered, ordered steps to resolve this RIGHT NOW
            5. **🔧 Code Fix** — Show Java/Spring Boot fix for the most likely cause with BEFORE/AFTER code blocks
            6. **🔮 Recurrence Prevention** — Long-term fixes and architecture improvements
            7. **📋 Incident Report Snippet** — Ready-to-paste 5-line incident summary for stakeholders
            """.formatted(
                action,
                d.getOrDefault("type", "UNKNOWN"),
                d.getOrDefault("severity", "WARNING"),
                d.getOrDefault("currentValue", "N/A"), d.getOrDefault("thresholdValue", "N/A"),
                d.getOrDefault("tenant", "Unknown"), d.getOrDefault("endpoint", "Unknown"),
                d.getOrDefault("triggeredAt", "N/A"),
                d.getOrDefault("message", "No message")
        );
    }

    // ── Tenant prompt ─────────────────────────────────────────────────────────
    private String tenantPrompt(String action, Map<String, Object> d) {
        return """
            ## 🏢 Tenant Health Analysis Request

            **Requested Action:** `%s`

            ### Tenant Metrics
            | Metric              | Value                          |
            |---------------------|--------------------------------|
            | Tenant              | `%s`                           |
            | Total Requests/60s  | **%s**                         |
            | Overall Error Rate  | **%s%%**                       |
            | Total Errors        | **%s**                         |
            | Avg Latency         | `%sms`                         |
            | Active Endpoints    | `%s`                           |

            ### 🔎 Analysis Required

            1. **📊 Health Score** — Rate this tenant 1–10 with clear criteria table (errors, latency, throughput)
            2. **🔍 Anomaly Detection** — What patterns are statistically unusual or concerning?
            3. **🚨 Critical Issues** — List any SLA violations (`<1%% error`, `<500ms p99`) with specific remediation
            4. **🔧 Top 3 Recommended Fixes** — Show code and config fixes with BEFORE/AFTER examples
            5. **📈 Capacity Assessment** — Current load vs recommended limits; scaling trigger recommendations
            6. **📋 SLA Report Table** — Build a table showing metric | current | SLA target | status ✅/❌
            """.formatted(
                action,
                d.getOrDefault("tenant", "Unknown"),
                d.getOrDefault("totalRequests", "?"),
                d.getOrDefault("errorRate", "0"),
                d.getOrDefault("errors", "0"),
                d.getOrDefault("avgLatency", "?"),
                d.getOrDefault("endpoints", "?")
        );
    }

    // ── Log prompt ────────────────────────────────────────────────────────────
    private String logPrompt(String action, Map<String, Object> d, String level) {
        String msg     = d.getOrDefault("message", "(no message)").toString();
        boolean isAlert = msg.contains("🚨") || msg.contains("ALERT");
        boolean isApiEvent = msg.contains("→") && msg.contains("HTTP");
        String context  = isAlert ? "Alert/Warning" : isApiEvent ? "API Event" : "Application Log";

        return """
            ## 🗒️ Log Entry Deep-Dive Analysis

            **Requested Action:** `%s`
            **Log Level:** `%s`
            **Log Context:** `%s`

            ### Log Metadata
            | Field       | Value                              |
            |-------------|------------------------------------|
            | Level       | `%s`                               |
            | Logger      | `%s`                               |
            | Thread      | `%s`                               |
            | Timestamp   | `%s`                               |

            ### Full Log Message
            ```
            %s
            ```

            ### 🔎 Complete Analysis Required

            1. **🔍 Log Analysis** — What exactly does this log entry mean? Is this normal behavior or a symptom?
            2. **📊 Severity Assessment** — How critical is this in production? What breaks if ignored?
            3. **🌱 Root Cause** — The most likely Java Spring Boot code path that generated this message
            4. **🔧 Code Fix** — Show the exact code pattern causing this issue and the corrected version:
               - Identify the probable class and method (`ServiceName.java → methodName()`)
               - **BEFORE (problematic):** code block with issue highlighted in comments
               - **AFTER (fixed):** corrected implementation with improvement comments
            5. **⚡ Resolution Steps** — Step-by-step numbered actions to resolve this now
            6. **📈 Observability Improvement** — What log message, metric, or alert to add to detect this faster next time
            """.formatted(
                action, level, context,
                d.getOrDefault("level", level),
                d.getOrDefault("logger", "Unknown"),
                d.getOrDefault("thread", "Unknown"),
                d.getOrDefault("timestamp", "Unknown"),
                msg
        );
    }

    // ── Generic fallback prompt ───────────────────────────────────────────────
    private String genericPrompt(String action, Map<String, Object> d) {
        return """
            ## 📊 API Gateway Analysis Request

            **Action:** `%s`

            **Context:**
            ```json
            %s
            ```

            Provide:
            1. **📊 Summary** — Key findings
            2. **🔍 Root Cause Analysis** — What is the likely underlying issue?
            3. **🔧 Code Fix** — Realistic Java Spring Boot fix with BEFORE/AFTER code blocks
            4. **🛡️ Prevention** — How to prevent this in future
            5. **📈 Monitoring** — What metrics/alerts to add
            """.formatted(action, d.toString());
    }

    // ─── Utility ─────────────────────────────────────────────────────────────
    private double parseDouble(String s) {
        try { return Double.parseDouble(s.trim()); } catch (Exception e) { return 0.0; }
    }
}



