package com.platform.demo.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/** A single captured log line exposed via /demo/logs. */
@Data @Builder @NoArgsConstructor @AllArgsConstructor
public class LogEntry {
    /** ISO-8601 timestamp (UTC). */
    private String timestamp;
    /** Log level: INFO | WARN | ERROR | DEBUG. */
    private String level;
    /** Short class name. */
    private String logger;
    /** Thread name. */
    private String thread;
    /** Formatted log message (may include stack trace first line). */
    private String message;
}
