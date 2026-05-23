package com.platform.demo.logging;

import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.AppenderBase;
import com.platform.demo.model.LogEntry;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentLinkedDeque;

/**
 * A Logback appender that stores the most recent log entries in an
 * in-memory ring buffer. The buffer is exposed via /demo/logs REST endpoint.
 *
 * Configured in logback-spring.xml; this class is instantiated by Logback
 * (not Spring) so the buffer is static.
 */
public class InMemoryLogAppender extends AppenderBase<ILoggingEvent> {

    private static final int MAX_SIZE = 500;
    private static final ConcurrentLinkedDeque<LogEntry> BUFFER = new ConcurrentLinkedDeque<>();

    @Override
    protected void append(ILoggingEvent event) {
        // Keep buffer bounded
        while (BUFFER.size() >= MAX_SIZE) {
            BUFFER.pollLast();
        }

        String msg = event.getFormattedMessage();

        // Append first line of stack trace if present
        if (event.getThrowableProxy() != null) {
            msg += "  →  " + event.getThrowableProxy().getClassName()
                    + ": " + event.getThrowableProxy().getMessage();
        }

        BUFFER.addFirst(LogEntry.builder()
                .timestamp(Instant.ofEpochMilli(event.getTimeStamp()).toString())
                .level(event.getLevel().toString())
                .logger(shortName(event.getLoggerName()))
                .thread(event.getThreadName())
                .message(msg)
                .build());
    }

    /** Returns a snapshot of all buffered log entries (newest first). */
    public static List<LogEntry> getBuffer() {
        return new ArrayList<>(BUFFER);
    }

    /** Clears the in-memory buffer. */
    public static void clear() {
        BUFFER.clear();
    }

    private static String shortName(String fqn) {
        if (fqn == null || fqn.isBlank()) return "?";
        int dot = fqn.lastIndexOf('.');
        return dot >= 0 ? fqn.substring(dot + 1) : fqn;
    }
}
