#!/usr/bin/env python3
"""Adds live service logs feature: backend log capture + dashboard logs panel."""
import os, re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def write(rel, content):
    p = os.path.join(BASE, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  + {rel}")

def append_file(rel, new_content, before_marker):
    """Insert new_content just before before_marker in the file."""
    p = os.path.join(BASE, rel)
    with open(p, 'r', encoding='utf-8') as f:
        content = f.read()
    idx = content.rfind(before_marker)
    if idx == -1:
        print(f"  ⚠ marker not found in {rel}, appending")
        with open(p, 'a', encoding='utf-8') as f:
            f.write(new_content)
    else:
        updated = content[:idx] + new_content + content[idx:]
        with open(p, 'w', encoding='utf-8') as f:
            f.write(updated)
    print(f"  ✎ {rel}")

# ── 1. LogEntry model ─────────────────────────────────────────
write("demo-service/src/main/java/com/platform/demo/model/LogEntry.java", """\
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
""")

# ── 2. InMemoryLogAppender ────────────────────────────────────
write("demo-service/src/main/java/com/platform/demo/logging/InMemoryLogAppender.java", """\
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
""")

# ── 3. logback-spring.xml ─────────────────────────────────────
write("demo-service/src/main/resources/logback-spring.xml", """\
<?xml version="1.0" encoding="UTF-8"?>
<configuration>

  <!-- ── Console appender (keep standard output) ── -->
  <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
    <encoder>
      <pattern>%d{HH:mm:ss.SSS} %-5level [demo] %msg%n</pattern>
    </encoder>
  </appender>

  <!-- ── In-memory appender (captured by /demo/logs API) ── -->
  <appender name="IN_MEMORY"
            class="com.platform.demo.logging.InMemoryLogAppender"/>

  <!-- Application code: DEBUG and up, goes to both outputs -->
  <logger name="com.platform.demo" level="DEBUG" additivity="false">
    <appender-ref ref="CONSOLE"/>
    <appender-ref ref="IN_MEMORY"/>
  </logger>

  <!-- Spring framework: INFO and up -->
  <logger name="org.springframework" level="INFO" additivity="false">
    <appender-ref ref="CONSOLE"/>
    <appender-ref ref="IN_MEMORY"/>
  </logger>

  <!-- Root: WARN and up (reduce noise from 3rd-party libs) -->
  <root level="WARN">
    <appender-ref ref="CONSOLE"/>
    <appender-ref ref="IN_MEMORY"/>
  </root>

</configuration>
""")

# ── 4. Update DemoController — add /demo/logs endpoint ────────
controller_path = os.path.join(
    BASE, "demo-service/src/main/java/com/platform/demo/controller/DemoController.java")

with open(controller_path, 'r') as f:
    ctrl = f.read()

# Add import for InMemoryLogAppender and LogEntry if not present
if "InMemoryLogAppender" not in ctrl:
    ctrl = ctrl.replace(
        "import com.platform.demo.model.AlertNotification;",
        "import com.platform.demo.logging.InMemoryLogAppender;\n"
        "import com.platform.demo.model.AlertNotification;\n"
        "import com.platform.demo.model.LogEntry;"
    )

# Add /demo/logs and /demo/logs DELETE endpoints before the last closing brace
logs_endpoints = '''
    /**
     * GET /demo/logs?limit=200&level=WARN
     * Returns captured service log entries (newest first).
     * level: optional filter — INFO | WARN | ERROR | DEBUG
     */
    @GetMapping("/logs")
    public ResponseEntity<List<LogEntry>> getLogs(
            @RequestParam(defaultValue = "200") int limit,
            @RequestParam(required = false) String level) {

        return ResponseEntity.ok(
                InMemoryLogAppender.getBuffer().stream()
                        .filter(l -> level == null || l.getLevel().equalsIgnoreCase(level))
                        .limit(limit)
                        .collect(Collectors.toList()));
    }

    /** DELETE /demo/logs — clears the in-memory log buffer. */
    @DeleteMapping("/logs")
    public ResponseEntity<Void> clearLogs() {
        InMemoryLogAppender.clear();
        return ResponseEntity.noContent().build();
    }
'''

if "/demo/logs" not in ctrl:
    # Insert before final closing brace of the class
    last_brace = ctrl.rfind('\n}')
    ctrl = ctrl[:last_brace] + logs_endpoints + ctrl[last_brace:]

with open(controller_path, 'w') as f:
    f.write(ctrl)
print("  ✎ DemoController.java  (added /demo/logs)")

# ── 5. Regenerate index.html with logs panel ──────────────────
# Read current dashboard and inject logs panel before </div><!-- /wrap -->
dashboard_path = os.path.join(
    BASE, "demo-service/src/main/resources/static/index.html")
with open(dashboard_path, 'r', encoding='utf-8') as f:
    html = f.read()

LOGS_CSS = """
/* ─── LOGS PANEL ─── */
.log-viewer{height:380px;overflow-y:auto;font-family:'JetBrains Mono',monospace;
  font-size:11px;line-height:1.6;background:#06080e;border-radius:8px;
  padding:8px 4px;border:1px solid rgba(255,255,255,0.06)}
.log-viewer::-webkit-scrollbar{width:5px}
.log-viewer::-webkit-scrollbar-track{background:transparent}
.log-viewer::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.15);border-radius:3px}
.log-row{display:grid;grid-template-columns:145px 52px 115px 170px 1fr;
  gap:8px;align-items:start;padding:3px 8px;border-radius:4px;
  transition:background .1s;word-break:break-word}
.log-row:hover{background:rgba(255,255,255,0.04)}
.log-row.ERROR{background:rgba(239,68,68,0.06);border-left:2px solid rgba(239,68,68,0.5)}
.log-row.WARN{background:rgba(245,158,11,0.05);border-left:2px solid rgba(245,158,11,0.4)}
.log-row.ALERT{background:rgba(239,68,68,0.1);border-left:2px solid var(--red);
  animation:logAlert .5s ease}
@keyframes logAlert{0%{background:rgba(239,68,68,0.3)}100%{background:rgba(239,68,68,0.1)}}
.log-ts{color:#475569;font-size:10px;white-space:nowrap;padding-top:1px}
.log-lvl{padding:1px 5px;border-radius:3px;font-weight:700;font-size:9px;
  text-align:center;white-space:nowrap;display:inline-block;margin-top:2px}
.ll-INFO{background:rgba(6,182,212,.15);color:#06b6d4;border:1px solid rgba(6,182,212,.25)}
.ll-WARN{background:rgba(245,158,11,.15);color:#f59e0b;border:1px solid rgba(245,158,11,.25)}
.ll-ERROR{background:rgba(239,68,68,.2);color:#ef4444;border:1px solid rgba(239,68,68,.3)}
.ll-DEBUG{background:rgba(148,163,184,.1);color:#64748b;border:1px solid rgba(148,163,184,.15)}
.log-thread{color:#4b5563;font-size:10px;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap;padding-top:1px}
.log-logger{color:#6366f1;font-size:10.5px;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap;padding-top:1px}
.log-msg{color:#cbd5e1;font-size:11px;word-break:break-word}
.log-msg.has-alert{color:#fca5a5}

/* ─── LOG CONTROLS ─── */
.log-controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.lf-btn{padding:4px 10px;border-radius:6px;border:1px solid var(--border);
  background:var(--glass);color:var(--muted2);font-size:11px;font-weight:600;
  cursor:pointer;transition:all .2s;letter-spacing:.5px}
.lf-btn:hover{border-color:var(--border2);color:var(--txt)}
.lf-btn.active{background:rgba(99,102,241,.2);border-color:rgba(99,102,241,.5);color:var(--ind2)}
.lf-btn.lf-WARN.active{background:rgba(245,158,11,.2);border-color:rgba(245,158,11,.5);color:var(--yellow)}
.lf-btn.lf-ERROR.active{background:rgba(239,68,68,.2);border-color:rgba(239,68,68,.5);color:var(--red)}
.lf-btn.lf-DEBUG.active{background:rgba(148,163,184,.15);border-color:rgba(148,163,184,.3);color:var(--muted2)}
.lf-btn.lf-INFO.active{background:rgba(6,182,212,.15);border-color:rgba(6,182,212,.4);color:var(--cyan)}
.log-search-box{flex:1;max-width:260px;padding:5px 10px;
  background:var(--glass2);border:1px solid var(--border);border-radius:6px;
  color:var(--txt);font-size:12px;font-family:'JetBrains Mono',monospace;
  outline:none;transition:border-color .2s}
.log-search-box:focus{border-color:rgba(99,102,241,.5)}
.log-search-box::placeholder{color:var(--muted)}
.log-ctrl-btn{padding:4px 10px;border-radius:6px;border:1px solid var(--border);
  background:var(--glass);color:var(--muted2);font-size:11px;cursor:pointer;
  display:flex;align-items:center;gap:5px;transition:all .2s}
.log-ctrl-btn:hover{border-color:var(--border2);color:var(--txt)}
.log-ctrl-btn.active{border-color:rgba(16,185,129,.4);color:var(--green);background:rgba(16,185,129,.1)}
.log-stat-badge{padding:3px 8px;border-radius:5px;font-size:10px;font-weight:600;
  font-family:'JetBrains Mono',monospace;border:1px solid var(--border)}
.log-header-row{display:grid;grid-template-columns:145px 52px 115px 170px 1fr;
  gap:8px;padding:4px 8px;font-size:9px;text-transform:uppercase;letter-spacing:1px;
  color:var(--muted);border-bottom:1px solid var(--border);margin-bottom:4px}
"""

LOGS_HTML = """
<!-- ── SERVICE LOGS ── -->
<div class="section-title" style="margin-top:6px">
  <i class="fa fa-terminal" style="color:var(--green)"></i>
  Live Service Logs
</div>
<div class="card" id="logs-card">
  <div class="card-header">
    <span class="card-title">
      <i class="fa fa-scroll" style="color:var(--green)"></i>
      Application Log Stream
    </span>
    <div style="display:flex;gap:8px;align-items:center">
      <span class="live-tag"><span class="live-dot"></span>LIVE</span>
      <button class="log-ctrl-btn" id="pause-logs">
        <i class="fa fa-pause" id="pause-icon"></i> <span id="pause-label">Pause</span>
      </button>
      <button class="log-ctrl-btn" id="clear-log-btn" style="border-color:rgba(239,68,68,.3);color:var(--red)">
        <i class="fa fa-trash"></i> Clear
      </button>
    </div>
  </div>

  <!-- Controls row -->
  <div class="log-controls">
    <button class="lf-btn active" data-lvl="">ALL</button>
    <button class="lf-btn lf-INFO" data-lvl="INFO">INFO</button>
    <button class="lf-btn lf-WARN" data-lvl="WARN">WARN</button>
    <button class="lf-btn lf-ERROR" data-lvl="ERROR">ERROR</button>
    <button class="lf-btn lf-DEBUG" data-lvl="DEBUG">DEBUG</button>
    <input class="log-search-box" id="log-search" placeholder="🔍  Search logs…" type="text"/>
    <button class="log-ctrl-btn active" id="auto-scroll-btn">
      <i class="fa fa-arrow-down"></i> Auto-scroll
    </button>
    <span class="log-stat-badge" id="lstat-total" style="color:var(--muted2)">— entries</span>
    <span class="log-stat-badge" id="lstat-info"  style="color:var(--cyan)">— INFO</span>
    <span class="log-stat-badge" id="lstat-warn"  style="color:var(--yellow)">— WARN</span>
    <span class="log-stat-badge" id="lstat-error" style="color:var(--red)">— ERROR</span>
  </div>

  <!-- Column headers -->
  <div class="log-header-row">
    <span>Timestamp (UTC)</span>
    <span>Level</span>
    <span>Thread</span>
    <span>Logger</span>
    <span>Message</span>
  </div>

  <!-- Log entries -->
  <div class="log-viewer" id="log-viewer">
    <div style="text-align:center;color:var(--muted);padding:20px;font-family:'JetBrains Mono'">
      Waiting for log entries…
    </div>
  </div>
</div>

<div style="height:40px"></div>
"""

LOGS_JS = """
// ═══════════════════════════════════════════════════════
//  LOGS PANEL
// ═══════════════════════════════════════════════════════
let logsPaused = false;
let logsAutoScroll = true;
let activeLogLevel = '';
let logSearchTerm = '';
let allLogs = [];

document.getElementById('pause-logs').addEventListener('click', function(){
  logsPaused = !logsPaused;
  const icon = document.getElementById('pause-icon');
  const label = document.getElementById('pause-label');
  if (logsPaused) {
    icon.className = 'fa fa-play'; label.textContent = 'Resume';
    this.style.color = 'var(--yellow)'; this.style.borderColor = 'rgba(245,158,11,.4)';
  } else {
    icon.className = 'fa fa-pause'; label.textContent = 'Pause';
    this.style.color = ''; this.style.borderColor = '';
  }
});

document.getElementById('auto-scroll-btn').addEventListener('click', function(){
  logsAutoScroll = !logsAutoScroll;
  this.classList.toggle('active', logsAutoScroll);
});

document.getElementById('clear-log-btn').addEventListener('click', async () => {
  await fetch('/demo/logs', {method:'DELETE'}).catch(()=>{});
  allLogs = [];
  renderLogs([]);
});

document.getElementById('log-search').addEventListener('input', function(){
  logSearchTerm = this.value.toLowerCase();
  renderLogs(allLogs);
});

document.querySelectorAll('.lf-btn').forEach(btn => {
  btn.addEventListener('click', function(){
    document.querySelectorAll('.lf-btn').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    activeLogLevel = this.dataset.lvl || '';
    renderLogs(allLogs);
  });
});

function renderLogs(logs) {
  const viewer = document.getElementById('log-viewer');
  const scrolledToBottom = viewer.scrollHeight - viewer.clientHeight - viewer.scrollTop < 30;

  // Filter
  let filtered = logs;
  if (activeLogLevel) filtered = filtered.filter(l => l.level === activeLogLevel);
  if (logSearchTerm)  filtered = filtered.filter(l =>
    l.message.toLowerCase().includes(logSearchTerm) ||
    l.logger.toLowerCase().includes(logSearchTerm) ||
    l.thread.toLowerCase().includes(logSearchTerm));

  if (!filtered.length) {
    viewer.innerHTML = '<div style="text-align:center;color:var(--muted);padding:20px;' +
      'font-family:JetBrains Mono">No log entries match the current filter.</div>';
    return;
  }

  // Newest-first for display (already newest-first from API)
  // Render rows
  viewer.innerHTML = filtered.map(l => {
    const ts = l.timestamp ? l.timestamp.replace('T',' ').replace('Z','').substring(0,23) : '';
    const lvlClass = 'll-' + (l.level || 'INFO');
    const rowClass = l.level === 'ERROR' ? 'log-row ERROR'
                   : l.level === 'WARN'  ? 'log-row WARN'
                   : l.message && l.message.includes('🚨') ? 'log-row ALERT'
                   : 'log-row';
    const msgClass = l.message && (l.level === 'ERROR' || l.message.includes('🚨')) ? 'log-msg has-alert' : 'log-msg';
    const escaped = (l.message || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    return `<div class="${rowClass}">
      <span class="log-ts">${ts}</span>
      <span class="log-lvl ${lvlClass}">${l.level||'?'}</span>
      <span class="log-thread" title="${l.thread||''}">${(l.thread||'').substring(0,18)}</span>
      <span class="log-logger" title="${l.logger||''}">${(l.logger||'').substring(0,22)}</span>
      <span class="${msgClass}">${escaped}</span>
    </div>`;
  }).join('');

  // Update stats
  document.getElementById('lstat-total').textContent = logs.length + ' entries';
  document.getElementById('lstat-info').textContent  = logs.filter(l=>l.level==='INFO').length + ' INFO';
  document.getElementById('lstat-warn').textContent  = logs.filter(l=>l.level==='WARN').length + ' WARN';
  document.getElementById('lstat-error').textContent = logs.filter(l=>l.level==='ERROR').length + ' ERROR';

  // Auto-scroll to bottom (latest = bottom since viewer shows them newest-first in DOM reversed)
  if (logsAutoScroll) {
    viewer.scrollTop = 0; // newest is at top since API returns newest-first
  }
}

async function updateLogs() {
  if (logsPaused) return;
  try {
    const logs = await fetch('/demo/logs?limit=300').then(r => r.json());
    allLogs = logs;
    renderLogs(logs);
  } catch(e) {
    // silent
  }
}

// Poll logs every 2 seconds
setInterval(updateLogs, 2000);
updateLogs();
"""

# ── Inject CSS into <style> block ─────────────────────────────
if "log-viewer" not in html:
    html = html.replace("</style>", LOGS_CSS + "\n</style>")
    print("  ✎ index.html  (injected logs CSS)")

# ── Inject HTML section before </div><!-- /wrap --> ───────────
WRAP_CLOSE = "<div style=\"height:40px\"></div>\n</div><!-- /wrap -->"
if WRAP_CLOSE in html and "logs-card" not in html:
    html = html.replace(WRAP_CLOSE, LOGS_HTML + "\n</div><!-- /wrap -->")
    print("  ✎ index.html  (injected logs HTML section)")
elif "logs-card" not in html:
    # Try a looser marker
    last_wrap = html.rfind("\n</div><!-- /wrap -->")
    if last_wrap != -1:
        html = html[:last_wrap] + "\n" + LOGS_HTML + html[last_wrap:]
        print("  ✎ index.html  (injected logs HTML at wrap end)")
    else:
        print("  ⚠ Could not find </div><!-- /wrap --> — appending logs HTML before </body>")
        html = html.replace("</body>", LOGS_HTML + "\n</body>")

# ── Inject JS before closing </script> ────────────────────────
if "updateLogs" not in html:
    html = html.replace("</script>\n</body>", LOGS_JS + "\n</script>\n</body>")
    print("  ✎ index.html  (injected logs JS)")

with open(dashboard_path, 'w', encoding='utf-8') as f:
    f.write(html)

print("\n✅ All files created/updated.")
print("Next: rebuild demo-service and restart to activate the Logback appender.")

