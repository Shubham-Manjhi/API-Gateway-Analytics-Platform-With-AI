#!/usr/bin/env python3
"""Generates the professional 3D analytics dashboard HTML."""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def write(rel, content):
    p = os.path.join(BASE, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"  + {rel}")

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>API Gateway Analytics Platform</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css" rel="stylesheet"/>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
<style>
:root{
  --bg:#06090f;--bg2:#0c1120;--bg3:#111827;
  --glass:rgba(255,255,255,0.04);--glass2:rgba(255,255,255,0.07);
  --border:rgba(255,255,255,0.09);--border2:rgba(255,255,255,0.15);
  --ind:#6366f1;--ind2:#818cf8;
  --blue:#3b82f6;--cyan:#06b6d4;--green:#10b981;
  --yellow:#f59e0b;--red:#ef4444;--orange:#f97316;
  --purple:#a855f7;--pink:#ec4899;
  --txt:#f1f5f9;--muted:#64748b;--muted2:#94a3b8;
  --r:14px;--r2:10px;
  --shadow:0 25px 60px rgba(0,0,0,0.6);
  --glow-ind:0 0 40px rgba(99,102,241,0.25);
  --glow-red:0 0 40px rgba(239,68,68,0.25);
  --glow-green:0 0 40px rgba(16,185,129,0.2);
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--txt);min-height:100vh;overflow-x:hidden}
canvas#bg{position:fixed;top:0;left:0;z-index:0;opacity:.35;pointer-events:none}
.wrap{position:relative;z-index:1;padding:20px 24px;max-width:1800px;margin:0 auto}

/* ─── HEADER ─── */
header{display:flex;align-items:center;justify-content:space-between;padding:16px 24px;
  background:rgba(6,9,15,0.85);backdrop-filter:blur(20px);
  border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100;
  box-shadow:0 4px 30px rgba(0,0,0,0.5)}
.logo{display:flex;align-items:center;gap:12px}
.logo-icon{width:40px;height:40px;border-radius:10px;
  background:linear-gradient(135deg,#6366f1,#a855f7);
  display:flex;align-items:center;justify-content:center;font-size:18px;
  box-shadow:0 0 20px rgba(99,102,241,0.5)}
.logo-text h1{font-size:16px;font-weight:700;letter-spacing:.5px}
.logo-text p{font-size:11px;color:var(--muted2);letter-spacing:1px;text-transform:uppercase}
.header-center{display:flex;gap:8px}
.status-pill{display:flex;align-items:center;gap:6px;padding:6px 12px;
  border-radius:20px;font-size:12px;font-weight:500;border:1px solid var(--border)}
.pulse{width:8px;height:8px;border-radius:50%;background:var(--green);
  animation:pulse 1.5s infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(16,185,129,0.7)}50%{box-shadow:0 0 0 6px rgba(16,185,129,0)}}
.header-right{display:flex;align-items:center;gap:16px}
#clock{font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--muted2)}
.refresh-badge{padding:5px 10px;border-radius:6px;background:var(--glass2);
  border:1px solid var(--border);font-size:11px;color:var(--muted2)}

/* ─── SECTION TITLE ─── */
.section-title{font-size:11px;font-weight:600;text-transform:uppercase;
  letter-spacing:2px;color:var(--muted2);margin:24px 0 12px;
  display:flex;align-items:center;gap:8px}
.section-title::after{content:'';flex:1;height:1px;background:var(--border)}

/* ─── KPI GRID ─── */
.kpi-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:14px;margin-bottom:20px}
@media(max-width:1400px){.kpi-grid{grid-template-columns:repeat(3,1fr)}}
.kpi{position:relative;background:var(--glass);border:1px solid var(--border);
  border-radius:var(--r);padding:18px 20px;overflow:hidden;
  cursor:default;transition:transform .3s,box-shadow .3s;
  transform-style:preserve-3d;perspective:800px}
.kpi:hover{transform:translateY(-4px) rotateY(3deg) rotateX(-2deg);
  box-shadow:var(--shadow),0 0 30px rgba(99,102,241,0.15)}
.kpi-accent{position:absolute;bottom:0;left:0;right:0;height:2px}
.kpi-icon{width:38px;height:38px;border-radius:10px;display:flex;align-items:center;
  justify-content:center;font-size:16px;margin-bottom:12px;flex-shrink:0}
.kpi-label{font-size:11px;color:var(--muted2);text-transform:uppercase;letter-spacing:1px;font-weight:500;margin-bottom:6px}
.kpi-value{font-size:28px;font-weight:800;line-height:1;margin-bottom:8px;
  font-variant-numeric:tabular-nums}
.kpi-sub{font-size:11px;color:var(--muted2);display:flex;align-items:center;gap:4px}
.kpi-trend{font-size:11px;padding:2px 6px;border-radius:4px}
.kpi-spark{position:absolute;bottom:0;right:0;width:80px;height:40px;opacity:.4}

/* ─── CHARTS LAYOUT ─── */
.charts-row{display:grid;gap:14px;margin-bottom:14px}
.r2{grid-template-columns:8fr 4fr}
.r3{grid-template-columns:7fr 5fr}
.r4{grid-template-columns:1fr}
.r5{grid-template-columns:6fr 6fr}
@media(max-width:1200px){.r2,.r3,.r5{grid-template-columns:1fr}}

/* ─── CARD ─── */
.card{background:var(--glass);border:1px solid var(--border);border-radius:var(--r);
  padding:20px;overflow:hidden;transition:border-color .3s,box-shadow .3s}
.card:hover{border-color:var(--border2);box-shadow:var(--shadow)}
.card-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.card-title{font-size:13px;font-weight:600;display:flex;align-items:center;gap:8px}
.card-title i{opacity:.8}
.card-badge{font-size:10px;padding:3px 8px;border-radius:12px;font-weight:600;
  background:var(--glass2);border:1px solid var(--border)}
.chart-wrap{position:relative}
.chart-wrap canvas{display:block}

/* ─── GAUGE SECTION ─── */
.gauges{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.gauge-card{background:var(--glass2);border:1px solid var(--border);border-radius:var(--r2);
  padding:16px;text-align:center}
.gauge-wrap{position:relative;width:120px;height:66px;margin:0 auto 6px}
.gauge-center{position:absolute;bottom:-2px;left:0;right:0;text-align:center}
.gauge-val{font-size:20px;font-weight:800}
.gauge-unit{font-size:10px;color:var(--muted2)}
.gauge-label{font-size:11px;color:var(--muted2);font-weight:500;margin-top:2px}

/* ─── ALERT FEED ─── */
.alert-list{display:flex;flex-direction:column;gap:8px;max-height:320px;overflow-y:auto}
.alert-list::-webkit-scrollbar{width:4px}
.alert-list::-webkit-scrollbar-track{background:transparent}
.alert-list::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px}
.alert-item{display:flex;align-items:flex-start;gap:10px;padding:10px 12px;
  border-radius:8px;border:1px solid;animation:fadeIn .4s ease}
@keyframes fadeIn{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:none}}
.alert-item.CRITICAL{background:rgba(239,68,68,0.08);border-color:rgba(239,68,68,0.3)}
.alert-item.WARNING{background:rgba(245,158,11,0.08);border-color:rgba(245,158,11,0.3)}
.alert-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;margin-top:4px}
.alert-item.CRITICAL .alert-dot{background:var(--red);box-shadow:0 0 8px var(--red);animation:alertPulse 1s infinite}
.alert-item.WARNING .alert-dot{background:var(--yellow);box-shadow:0 0 8px var(--yellow)}
@keyframes alertPulse{0%,100%{opacity:1}50%{opacity:.4}}
.alert-msg{font-size:12px;line-height:1.5;color:var(--txt)}
.alert-meta{font-size:10px;color:var(--muted2);margin-top:3px;font-family:'JetBrains Mono',monospace}
.sev-badge{font-size:9px;padding:2px 6px;border-radius:4px;font-weight:700;white-space:nowrap;flex-shrink:0;margin-top:2px}
.sev-badge.CRITICAL{background:rgba(239,68,68,.25);color:var(--red);border:1px solid rgba(239,68,68,.4)}
.sev-badge.WARNING{background:rgba(245,158,11,.25);color:var(--yellow);border:1px solid rgba(245,158,11,.4)}

/* ─── EVENT STREAM ─── */
#event-stream{display:flex;flex-direction:column;gap:5px;max-height:320px;overflow-y:auto;
  font-family:'JetBrains Mono',monospace}
#event-stream::-webkit-scrollbar{width:4px}
#event-stream::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px}
.ev-row{display:grid;grid-template-columns:55px 80px 55px auto 60px 55px;
  gap:6px;align-items:center;padding:5px 8px;border-radius:6px;
  font-size:11px;transition:background .15s;animation:fadeIn .3s ease}
.ev-row:hover{background:var(--glass2)}
.ev-status{width:32px;height:20px;border-radius:4px;display:inline-flex;align-items:center;
  justify-content:center;font-size:10px;font-weight:700}
.s2xx{background:rgba(16,185,129,.2);color:var(--green);border:1px solid rgba(16,185,129,.3)}
.s4xx{background:rgba(245,158,11,.2);color:var(--yellow);border:1px solid rgba(245,158,11,.3)}
.s5xx{background:rgba(239,68,68,.2);color:var(--red);border:1px solid rgba(239,68,68,.3)}
.ev-lat{text-align:right}
.lat-ok{color:var(--green)}
.lat-warn{color:var(--yellow)}
.lat-crit{color:var(--red)}
.ev-tenant{color:var(--ind2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ev-path{color:var(--muted2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:10px}

/* ─── ENDPOINT TABLE ─── */
.ep-table-wrap{overflow-x:auto;max-height:300px;overflow-y:auto}
.ep-table-wrap::-webkit-scrollbar{width:4px;height:4px}
.ep-table-wrap::-webkit-scrollbar-thumb{background:var(--border2);border-radius:2px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--muted2);
  padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);font-weight:600;
  position:sticky;top:0;background:var(--bg3)}
td{padding:8px 12px;border-bottom:1px solid rgba(255,255,255,0.04);vertical-align:middle}
tr:hover td{background:var(--glass2)}
.err-bar-wrap{display:flex;align-items:center;gap:6px;min-width:80px}
.err-bar{height:5px;border-radius:3px;flex:1;background:rgba(255,255,255,0.08);overflow:hidden}
.err-bar-fill{height:100%;border-radius:3px;transition:width .5s}
.lat-pill{padding:2px 7px;border-radius:4px;font-weight:600;font-size:11px}
.rank-badge{width:20px;height:20px;border-radius:5px;display:inline-flex;
  align-items:center;justify-content:center;font-size:10px;font-weight:700;
  background:var(--glass2);border:1px solid var(--border)}
.method-badge{padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700;font-family:'JetBrains Mono',monospace}
.GET{background:rgba(6,182,212,.15);color:var(--cyan);border:1px solid rgba(6,182,212,.3)}
.POST{background:rgba(16,185,129,.15);color:var(--green);border:1px solid rgba(16,185,129,.3)}
.PUT{background:rgba(245,158,11,.15);color:var(--yellow);border:1px solid rgba(245,158,11,.3)}
.DELETE{background:rgba(239,68,68,.15);color:var(--red);border:1px solid rgba(239,68,68,.3)}

/* ─── 3D GLOBE CONTAINER ─── */
#globe-container{display:flex;align-items:center;justify-content:center;
  height:100%;min-height:200px;flex:1}
#globe-canvas{border-radius:50%;box-shadow:0 0 60px rgba(99,102,241,0.3)}

/* ─── MINI SPARKLINES ─── */
.sparkline{position:absolute;bottom:12px;right:12px;opacity:.5}

/* ─── MISC ─── */
.no-data{text-align:center;color:var(--muted2);padding:30px;font-size:13px}
.live-tag{display:inline-flex;align-items:center;gap:5px;font-size:10px;
  color:var(--green);font-weight:600}
.live-dot{width:6px;height:6px;border-radius:50%;background:var(--green);
  animation:pulse 1.5s infinite}
.trend-up{color:var(--red)}
.trend-down{color:var(--green)}
.count-animated{transition:all .5s}
</style>
</head>
<body>
<!-- ── PARTICLE CANVAS ── -->
<canvas id="bg"></canvas>

<!-- ── HEADER ── -->
<header>
  <div class="logo">
    <div class="logo-icon">⚡</div>
    <div class="logo-text">
      <h1>API Gateway Analytics</h1>
      <p>Enterprise Observability Platform</p>
    </div>
  </div>
  <div class="header-center">
    <div class="status-pill">
      <span class="pulse"></span>
      <span style="color:var(--green)">Live</span>
    </div>
    <div class="status-pill" id="event-count-badge">— events</div>
    <div class="status-pill" id="alert-count-badge">— alerts</div>
  </div>
  <div class="header-right">
    <span class="live-tag"><span class="live-dot"></span>Auto-refresh 3s</span>
    <span id="clock"></span>
    <div class="refresh-badge">
      <i class="fa fa-rotate" id="refresh-icon"></i> Polling /demo/dashboard
    </div>
  </div>
</header>

<!-- ── MAIN WRAP ── -->
<div class="wrap">

<!-- ── KPI CARDS ── -->
<div class="section-title"><i class="fa fa-gauge-high" style="color:var(--ind)"></i> Key Performance Indicators</div>
<div class="kpi-grid">

  <div class="kpi" id="kpi-events">
    <div class="kpi-accent" style="background:linear-gradient(90deg,var(--blue),var(--ind))"></div>
    <div class="kpi-icon" style="background:rgba(59,130,246,.15);border:1px solid rgba(59,130,246,.3)">
      <i class="fa fa-bolt" style="color:var(--blue)"></i>
    </div>
    <div class="kpi-label">Total Events</div>
    <div class="kpi-value" id="v-events">—</div>
    <div class="kpi-sub" id="s-events"><i class="fa fa-database" style="font-size:10px"></i> buffered in memory</div>
  </div>

  <div class="kpi" id="kpi-err">
    <div class="kpi-accent" id="err-accent" style="background:linear-gradient(90deg,var(--red),var(--orange))"></div>
    <div class="kpi-icon" style="background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.3)">
      <i class="fa fa-triangle-exclamation" style="color:var(--red)"></i>
    </div>
    <div class="kpi-label">Error Rate</div>
    <div class="kpi-value" id="v-err" style="color:var(--red)">—</div>
    <div class="kpi-sub" id="s-err"><i class="fa fa-xmark" style="font-size:10px;color:var(--red)"></i> <span id="v-errcount">—</span> errors total</div>
  </div>

  <div class="kpi" id="kpi-lat">
    <div class="kpi-accent" style="background:linear-gradient(90deg,var(--yellow),var(--orange))"></div>
    <div class="kpi-icon" style="background:rgba(245,158,11,.15);border:1px solid rgba(245,158,11,.3)">
      <i class="fa fa-stopwatch" style="color:var(--yellow)"></i>
    </div>
    <div class="kpi-label">Avg Latency</div>
    <div class="kpi-value" id="v-lat" style="color:var(--yellow)">—</div>
    <div class="kpi-sub"><i class="fa fa-clock" style="font-size:10px"></i> milliseconds</div>
  </div>

  <div class="kpi" id="kpi-alerts">
    <div class="kpi-accent" style="background:linear-gradient(90deg,var(--orange),var(--red))"></div>
    <div class="kpi-icon" style="background:rgba(249,115,22,.15);border:1px solid rgba(249,115,22,.3)">
      <i class="fa fa-bell" style="color:var(--orange)"></i>
    </div>
    <div class="kpi-label">Alerts Fired</div>
    <div class="kpi-value" id="v-alerts" style="color:var(--orange)">—</div>
    <div class="kpi-sub" id="s-alerts"><i class="fa fa-shield-halved" style="font-size:10px"></i> anomalies detected</div>
  </div>

  <div class="kpi" id="kpi-tenants">
    <div class="kpi-accent" style="background:linear-gradient(90deg,var(--purple),var(--pink))"></div>
    <div class="kpi-icon" style="background:rgba(168,85,247,.15);border:1px solid rgba(168,85,247,.3)">
      <i class="fa fa-building" style="color:var(--purple)"></i>
    </div>
    <div class="kpi-label">Active Tenants</div>
    <div class="kpi-value" id="v-tenants" style="color:var(--purple)">—</div>
    <div class="kpi-sub"><i class="fa fa-users" style="font-size:10px"></i> tenants tracked</div>
  </div>

  <div class="kpi" id="kpi-eps">
    <div class="kpi-accent" style="background:linear-gradient(90deg,var(--cyan),var(--blue))"></div>
    <div class="kpi-icon" style="background:rgba(6,182,212,.15);border:1px solid rgba(6,182,212,.3)">
      <i class="fa fa-route" style="color:var(--cyan)"></i>
    </div>
    <div class="kpi-label">Endpoints Tracked</div>
    <div class="kpi-value" id="v-eps" style="color:var(--cyan)">—</div>
    <div class="kpi-sub"><i class="fa fa-code-branch" style="font-size:10px"></i> unique routes</div>
  </div>
</div>

<!-- ── ROW 2: TRAFFIC + GAUGES ── -->
<div class="section-title"><i class="fa fa-chart-line" style="color:var(--blue)"></i> Real-Time Traffic & Error Analysis</div>
<div class="charts-row r2">
  <div class="card">
    <div class="card-header">
      <span class="card-title"><i class="fa fa-wave-square" style="color:var(--blue)"></i> Request Traffic Timeline</span>
      <div style="display:flex;gap:8px;align-items:center">
        <span class="card-badge" style="color:var(--blue);border-color:rgba(59,130,246,.3)">Last 60s window</span>
        <span class="live-tag"><span class="live-dot"></span>LIVE</span>
      </div>
    </div>
    <div class="chart-wrap" style="height:220px"><canvas id="trafficChart"></canvas></div>
  </div>

  <div class="card" style="display:flex;flex-direction:column;gap:14px">
    <div class="card-header">
      <span class="card-title"><i class="fa fa-gauge" style="color:var(--red)"></i> Live Gauges</span>
    </div>
    <div class="gauges" style="flex:1">
      <div class="gauge-card">
        <div class="gauge-wrap">
          <canvas id="errGauge" width="120" height="66"></canvas>
          <div class="gauge-center">
            <div class="gauge-val" id="gauge-err-val" style="color:var(--red)">—</div>
            <div class="gauge-unit">%</div>
          </div>
        </div>
        <div class="gauge-label">Error Rate</div>
        <div style="font-size:10px;color:var(--muted2);margin-top:4px">Threshold 30%</div>
      </div>
      <div class="gauge-card">
        <div class="gauge-wrap">
          <canvas id="latGauge" width="120" height="66"></canvas>
          <div class="gauge-center">
            <div class="gauge-val" id="gauge-lat-val" style="color:var(--yellow)">—</div>
            <div class="gauge-unit">ms</div>
          </div>
        </div>
        <div class="gauge-label">Avg Latency</div>
        <div style="font-size:10px;color:var(--muted2);margin-top:4px">Threshold 3 000ms</div>
      </div>
    </div>
    <div class="card" style="background:var(--glass2);border:none;padding:12px">
      <div class="card-header" style="margin-bottom:10px">
        <span class="card-title" style="font-size:12px">
          <i class="fa fa-chart-pie" style="color:var(--purple)"></i> Error Rate Trend
        </span>
      </div>
      <div class="chart-wrap" style="height:80px"><canvas id="errTrendChart"></canvas></div>
    </div>
  </div>
</div>

<!-- ── ROW 3: LATENCY + TENANT ── -->
<div class="section-title"><i class="fa fa-chart-bar" style="color:var(--yellow)"></i> Latency Benchmark &amp; Tenant Distribution</div>
<div class="charts-row r3">
  <div class="card">
    <div class="card-header">
      <span class="card-title"><i class="fa fa-timer" style="color:var(--yellow)"></i> Latency Profile — Top Endpoints</span>
      <span class="card-badge" style="color:var(--yellow);border-color:rgba(245,158,11,.3)">avg / p95 / p99</span>
    </div>
    <div class="chart-wrap" style="height:240px"><canvas id="latencyChart"></canvas></div>
  </div>

  <div class="card" style="display:flex;flex-direction:column">
    <div class="card-header">
      <span class="card-title"><i class="fa fa-building-columns" style="color:var(--purple)"></i> Tenant Traffic Share</span>
    </div>
    <div style="flex:1;display:flex;flex-direction:column;justify-content:center">
      <div class="chart-wrap" style="height:180px"><canvas id="tenantChart"></canvas></div>
      <div id="tenant-legend" style="margin-top:12px;display:flex;flex-wrap:wrap;gap:8px;justify-content:center"></div>
    </div>
  </div>
</div>

<!-- ── ROW 4: ENDPOINT TABLE ── -->
<div class="section-title"><i class="fa fa-table" style="color:var(--cyan)"></i> Endpoint Metrics — Last 60 Seconds</div>
<div class="card">
  <div class="card-header">
    <span class="card-title"><i class="fa fa-list" style="color:var(--cyan)"></i> All Tracked Endpoints</span>
    <div style="display:flex;gap:8px;align-items:center">
      <span class="card-badge" id="ep-count-badge">— endpoints</span>
      <span class="live-tag"><span class="live-dot"></span>Updates every 3s</span>
    </div>
  </div>
  <div class="ep-table-wrap">
    <table>
      <thead>
        <tr>
          <th>#</th><th>Tenant</th><th>Method</th><th>Endpoint</th>
          <th style="text-align:right">Req/60s</th>
          <th style="text-align:right">Avg ms</th>
          <th style="text-align:right">p95 ms</th>
          <th style="text-align:right">p99 ms</th>
          <th>Error Rate</th>
        </tr>
      </thead>
      <tbody id="ep-table-body">
        <tr><td colspan="9" class="no-data">Loading...</td></tr>
      </tbody>
    </table>
  </div>
</div>

<!-- ── ROW 5: ALERTS + EVENTS ── -->
<div class="section-title"><i class="fa fa-bell" style="color:var(--orange)"></i> Alerts &amp; Live Event Stream</div>
<div class="charts-row r5">
  <div class="card">
    <div class="card-header">
      <span class="card-title"><i class="fa fa-triangle-exclamation" style="color:var(--orange)"></i> Active Alert Feed</span>
      <span class="card-badge" id="alert-total" style="color:var(--orange);border-color:rgba(249,115,22,.4)">0 alerts</span>
    </div>
    <div class="alert-list" id="alert-feed">
      <div class="no-data">No alerts yet — waiting for anomalies...</div>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <span class="card-title"><i class="fa fa-satellite-dish" style="color:var(--cyan)"></i> Live Event Stream</span>
      <span class="live-tag"><span class="live-dot"></span>LIVE</span>
    </div>
    <!-- Column headers -->
    <div style="display:grid;grid-template-columns:55px 80px 55px auto 60px 55px;
      gap:6px;padding:4px 8px;font-size:9px;text-transform:uppercase;
      letter-spacing:1px;color:var(--muted2);border-bottom:1px solid var(--border);margin-bottom:6px">
      <span>Status</span><span>Tenant</span><span>Method</span>
      <span>Endpoint</span><span style="text-align:right">Latency</span><span style="text-align:right">Time</span>
    </div>
    <div id="event-stream"></div>
  </div>
</div>

<!-- ── ROW 6: ERROR BAR CHART ── -->
<div class="section-title"><i class="fa fa-chart-area" style="color:var(--red)"></i> Error Analysis</div>
<div class="card">
  <div class="card-header">
    <span class="card-title"><i class="fa fa-xmark" style="color:var(--red)"></i> Error Rate by Endpoint — Top 10</span>
    <span class="card-badge" style="color:var(--red);border-color:rgba(239,68,68,.3)">% errors in last 60s</span>
  </div>
  <div class="chart-wrap" style="height:200px"><canvas id="errorBarChart"></canvas></div>
</div>

<div style="height:40px"></div>
</div><!-- /wrap -->

<script>
// ═══════════════════════════════════════════════════════
//  PARTICLE BACKGROUND
// ═══════════════════════════════════════════════════════
(function(){
  const c = document.getElementById('bg');
  const ctx = c.getContext('2d');
  let W,H,pts=[];
  function resize(){W=c.width=innerWidth;H=c.height=innerHeight;}
  resize();
  window.addEventListener('resize',resize);
  for(let i=0;i<120;i++) pts.push({
    x:Math.random()*10000%1,y:Math.random(),
    vx:(Math.random()-.5)*0.0003,vy:(Math.random()-.5)*0.0003,
    s:Math.random()*2+1
  });
  function draw(){
    ctx.clearRect(0,0,W,H);
    pts.forEach(p=>{
      p.x+=p.vx; p.y+=p.vy;
      if(p.x<0||p.x>1)p.vx*=-1;
      if(p.y<0||p.y>1)p.vy*=-1;
      const px=p.x*W, py=p.y*H;
      ctx.beginPath();
      ctx.arc(px,py,p.s,0,Math.PI*2);
      ctx.fillStyle='rgba(99,102,241,0.5)';
      ctx.fill();
      pts.forEach(q=>{
        const d=Math.hypot((p.x-q.x)*W,(p.y-q.y)*H);
        if(d<130&&d>0){
          ctx.beginPath();
          ctx.moveTo(px,py);
          ctx.lineTo(q.x*W,q.y*H);
          ctx.strokeStyle=`rgba(99,102,241,${0.12*(1-d/130)})`;
          ctx.lineWidth=1;
          ctx.stroke();
        }
      });
    });
    requestAnimationFrame(draw);
  }
  draw();
})();

// ═══════════════════════════════════════════════════════
//  CLOCK
// ═══════════════════════════════════════════════════════
function updateClock(){
  document.getElementById('clock').textContent =
    new Date().toLocaleTimeString('en-US',{hour12:false});
}
setInterval(updateClock,1000); updateClock();

// ═══════════════════════════════════════════════════════
//  CHART GLOBALS
// ═══════════════════════════════════════════════════════
Chart.defaults.color='#64748b';
Chart.defaults.font.family="'Inter',sans-serif";
const PALETTE=['#6366f1','#06b6d4','#10b981','#f59e0b','#ef4444','#a855f7','#3b82f6','#ec4899','#f97316'];
const MAX_POINTS=20;
let prevTotal=0,prevErrors=0;
const tlLabels=[], tlData=[], errTlData=[];

// ─── Traffic Timeline ───
const trafficCtx=document.getElementById('trafficChart').getContext('2d');
const tGrad=trafficCtx.createLinearGradient(0,0,0,220);
tGrad.addColorStop(0,'rgba(99,102,241,0.4)');
tGrad.addColorStop(1,'rgba(99,102,241,0.0)');
const trafficChart=new Chart(trafficCtx,{
  type:'line',
  data:{labels:[], datasets:[{
    label:'Events/sample',data:[],
    borderColor:'#6366f1',backgroundColor:tGrad,fill:true,
    tension:0.45,pointRadius:3,pointBackgroundColor:'#6366f1',
    pointHoverRadius:5,borderWidth:2.5
  }]},
  options:{responsive:true,maintainAspectRatio:false,
    interaction:{intersect:false,mode:'index'},
    scales:{
      x:{grid:{color:'rgba(255,255,255,0.04)'},ticks:{color:'#64748b',font:{size:10},maxTicksLimit:10}},
      y:{grid:{color:'rgba(255,255,255,0.04)'},ticks:{color:'#64748b',font:{size:10}},min:0}
    },
    plugins:{legend:{display:false},
      tooltip:{backgroundColor:'rgba(15,20,40,0.95)',borderColor:'rgba(99,102,241,0.4)',
        borderWidth:1,titleColor:'#f1f5f9',bodyColor:'#94a3b8',padding:10,cornerRadius:8}}
  }
});

// ─── Error Rate Trend ───
const errTrendCtx=document.getElementById('errTrendChart').getContext('2d');
const eGrad=errTrendCtx.createLinearGradient(0,0,0,80);
eGrad.addColorStop(0,'rgba(239,68,68,0.4)');
eGrad.addColorStop(1,'rgba(239,68,68,0.0)');
const errTrendChart=new Chart(errTrendCtx,{
  type:'line',
  data:{labels:[], datasets:[{
    label:'Error %',data:[],
    borderColor:'#ef4444',backgroundColor:eGrad,fill:true,
    tension:0.4,pointRadius:0,borderWidth:2
  }]},
  options:{responsive:true,maintainAspectRatio:false,
    scales:{
      x:{display:false},
      y:{grid:{color:'rgba(255,255,255,0.04)'},ticks:{color:'#64748b',font:{size:9}},min:0}
    },
    plugins:{legend:{display:false}}
  }
});

// ─── Error Rate Gauge ───
let errGaugeChart=new Chart(document.getElementById('errGauge'),{
  type:'doughnut',
  data:{datasets:[{data:[0,100],backgroundColor:['#ef4444','rgba(255,255,255,0.05)'],borderWidth:0,cutout:'78%'}]},
  options:{rotation:-90,circumference:180,responsive:false,plugins:{legend:{display:false},tooltip:{enabled:false}}}
});
// ─── Latency Gauge ───
let latGaugeChart=new Chart(document.getElementById('latGauge'),{
  type:'doughnut',
  data:{datasets:[{data:[0,100],backgroundColor:['#f59e0b','rgba(255,255,255,0.05)'],borderWidth:0,cutout:'78%'}]},
  options:{rotation:-90,circumference:180,responsive:false,plugins:{legend:{display:false},tooltip:{enabled:false}}}
});

// ─── Latency Benchmark ───
const latencyChart=new Chart(document.getElementById('latencyChart'),{
  type:'bar',
  data:{labels:[], datasets:[
    {label:'Avg',data:[],backgroundColor:'rgba(59,130,246,0.7)',borderRadius:4,borderSkipped:false},
    {label:'p95',data:[],backgroundColor:'rgba(245,158,11,0.7)',borderRadius:4,borderSkipped:false},
    {label:'p99',data:[],backgroundColor:'rgba(239,68,68,0.7)',borderRadius:4,borderSkipped:false}
  ]},
  options:{responsive:true,maintainAspectRatio:false,
    indexAxis:'y',
    scales:{
      x:{grid:{color:'rgba(255,255,255,0.04)'},ticks:{color:'#64748b',font:{size:10}}},
      y:{grid:{display:false},ticks:{color:'#94a3b8',font:{size:10},maxTicksLimit:8}}
    },
    plugins:{legend:{labels:{color:'#94a3b8',font:{size:11},pointStyle:'rectRounded',usePointStyle:true}},
      tooltip:{backgroundColor:'rgba(15,20,40,0.95)',borderColor:'rgba(245,158,11,.3)',
        borderWidth:1,callbacks:{label:ctx=>`${ctx.dataset.label}: ${ctx.raw} ms`}}}
  }
});

// ─── Tenant Doughnut ───
const tenantChart=new Chart(document.getElementById('tenantChart'),{
  type:'doughnut',
  data:{labels:[], datasets:[{data:[],backgroundColor:PALETTE,borderWidth:0,
    hoverOffset:8,spacing:2}]},
  options:{responsive:true,maintainAspectRatio:false,cutout:'65%',
    plugins:{legend:{display:false},
      tooltip:{backgroundColor:'rgba(15,20,40,0.95)',borderColor:'rgba(255,255,255,.1)',
        borderWidth:1,callbacks:{label:ctx=>`${ctx.label}: ${ctx.raw} req`}}}
  }
});

// ─── Error Bar Chart ───
const errorBarChart=new Chart(document.getElementById('errorBarChart'),{
  type:'bar',
  data:{labels:[], datasets:[{label:'Error %',data:[],
    backgroundColor:ctx=>{
      const v=ctx.raw||0;
      return v>50?'rgba(239,68,68,0.8)':v>30?'rgba(249,115,22,0.8)':v>10?'rgba(245,158,11,0.8)':'rgba(16,185,129,0.6)';
    },borderRadius:5,borderSkipped:false}]},
  options:{responsive:true,maintainAspectRatio:false,indexAxis:'y',
    scales:{
      x:{grid:{color:'rgba(255,255,255,0.04)'},ticks:{color:'#64748b',font:{size:10}},
        max:100,title:{display:true,text:'Error Rate %',color:'#64748b'}},
      y:{grid:{display:false},ticks:{color:'#94a3b8',font:{size:10},maxTicksLimit:10}}
    },
    plugins:{legend:{display:false},
      tooltip:{callbacks:{label:ctx=>`Error rate: ${ctx.raw.toFixed(1)}%`}}}
  }
});

// ═══════════════════════════════════════
//  HELPERS
// ═══════════════════════════════════════
function addPoint(chart,label,value){
  chart.data.labels.push(label);
  chart.data.datasets[0].data.push(value);
  if(chart.data.labels.length>MAX_POINTS){
    chart.data.labels.shift();
    chart.data.datasets[0].data.shift();
  }
  chart.update('none');
}
function addErrPoint(label,val){
  errTrendChart.data.labels.push(label);
  errTrendChart.data.datasets[0].data.push(val);
  if(errTrendChart.data.labels.length>MAX_POINTS){
    errTrendChart.data.labels.shift();
    errTrendChart.data.datasets[0].data.shift();
  }
  errTrendChart.update('none');
}
function updateGauge(chart,val,max){
  const pct=Math.min(100,val/max*100);
  chart.data.datasets[0].data=[pct,100-pct];
  chart.update('none');
}
function animateNum(elId,val){
  const el=document.getElementById(elId);
  if(el) el.textContent=val;
}
function latClass(ms){
  if(ms>3000)return 'lat-crit';
  if(ms>800)return 'lat-warn';
  return 'lat-ok';
}
function statusClass(code){
  if(code>=500)return 's5xx';
  if(code>=400)return 's4xx';
  return 's2xx';
}
function methodBadge(m){
  const cls={'GET':'GET','POST':'POST','PUT':'PUT','DELETE':'DELETE'}[m]||'GET';
  return `<span class="method-badge ${cls}">${m}</span>`;
}
function errColor(pct){
  if(pct>50)return'var(--red)';
  if(pct>30)return'var(--orange)';
  if(pct>10)return'var(--yellow)';
  return'var(--green)';
}
function since(ts){
  const d=Math.round((Date.now()-new Date(ts))/1000);
  if(d<2)return'just now';
  if(d<60)return d+'s ago';
  return Math.round(d/60)+'m ago';
}

// ═══════════════════════════════════════
//  MAIN UPDATE
// ═══════════════════════════════════════
async function updateDashboard(){
  const ri=document.getElementById('refresh-icon');
  ri.style.transform='rotate(360deg)';
  ri.style.transition='transform .6s linear';
  setTimeout(()=>{ri.style.transform='';ri.style.transition='';},700);

  let data;
  try{
    const [dash,allMetrics,allAlerts]= await Promise.all([
      fetch('/demo/dashboard').then(r=>r.json()),
      fetch('/demo/metrics').then(r=>r.json()),
      fetch('/demo/alerts?limit=30').then(r=>r.json())
    ]);
    data=dash; data.allMetrics=allMetrics; data.allAlerts=allAlerts;
  }catch(e){console.error('Fetch error',e); return;}

  const s=data.summary;
  const now=new Date().toLocaleTimeString('en-US',{hour12:false,second:'2-digit'});

  // ── KPI updates ──
  animateNum('v-events', s.totalEventsBuffered.toLocaleString());
  animateNum('v-err', s.errorRate);
  animateNum('v-errcount', s.errorCount.toLocaleString());
  animateNum('v-lat', s.avgLatencyMs + 'ms');
  animateNum('v-alerts', s.alertsFired);
  animateNum('v-tenants', s.tenantsActive);
  animateNum('v-eps', s.endpointsTracked);
  document.getElementById('event-count-badge').textContent=s.totalEventsBuffered.toLocaleString()+' events';
  document.getElementById('alert-count-badge').textContent=s.alertsFired+' alerts';
  document.getElementById('alert-total').textContent=data.allAlerts.length+' alerts';
  document.getElementById('ep-count-badge').textContent=(data.allMetrics||[]).length+' endpoints';

  // ── Gauge updates ──
  const errNum=parseFloat(s.errorRate)||0;
  const latNum=s.avgLatencyMs||0;
  animateNum('gauge-err-val', s.errorRate.replace('%',''));
  animateNum('gauge-lat-val', latNum);
  updateGauge(errGaugeChart, errNum, 100);
  updateGauge(latGaugeChart, Math.min(latNum,3000), 3000);

  // ── Traffic timeline ──
  const delta=Math.max(0, s.totalEventsBuffered-prevTotal);
  prevTotal=s.totalEventsBuffered;
  addPoint(trafficChart, now, delta);

  // ── Error trend ──
  addErrPoint(now, errNum);

  // ── Latency benchmark (top 8) ──
  const top8=(data.allMetrics||[]).slice(0,8);
  latencyChart.data.labels=top8.map(m=>{
    const p=m.key.split(' | ');
    const ep=p[1]||p[0];
    return ep.length>22?ep.slice(0,22)+'…':ep;
  });
  latencyChart.data.datasets[0].data=top8.map(m=>m.avgLatencyMs);
  latencyChart.data.datasets[1].data=top8.map(m=>m.p95LatencyMs);
  latencyChart.data.datasets[2].data=top8.map(m=>m.p99LatencyMs);
  latencyChart.update('none');

  // ── Tenant distribution ──
  const tenants={};
  (data.allMetrics||[]).forEach(m=>{
    const t=m.key.split(' | ')[0];
    tenants[t]=(tenants[t]||0)+m.requests_60s;
  });
  const tNames=Object.keys(tenants);
  tenantChart.data.labels=tNames;
  tenantChart.data.datasets[0].data=tNames.map(t=>tenants[t]);
  tenantChart.update('none');
  // Render legend
  const leg=document.getElementById('tenant-legend');
  leg.innerHTML=tNames.map((t,i)=>`
    <div style="display:flex;align-items:center;gap:5px;font-size:11px">
      <span style="width:10px;height:10px;border-radius:50%;background:${PALETTE[i%PALETTE.length]};flex-shrink:0"></span>
      <span style="color:var(--muted2)">${t}: <b style="color:var(--txt)">${tenants[t]}</b></span>
    </div>`).join('');

  // ── Error bar chart ──
  const withErrors=(data.allMetrics||[]).filter(m=>m.errors>0)
    .sort((a,b)=>b.errors/b.requests_60s-a.errors/a.requests_60s).slice(0,10);
  errorBarChart.data.labels=withErrors.map(m=>{
    const k=m.key; return k.length>35?k.slice(0,35)+'…':k;
  });
  errorBarChart.data.datasets[0].data=withErrors.map(m=>
    parseFloat(m.errorRate.replace('%',''))||0);
  errorBarChart.update('none');

  // ── Endpoint table ──
  const tbody=document.getElementById('ep-table-body');
  const rows=(data.allMetrics||[]);
  if(!rows.length){tbody.innerHTML='<tr><td colspan="9" class="no-data">No endpoint data yet…</td></tr>';return;}
  tbody.innerHTML=rows.map((m,i)=>{
    const parts=m.key.split(' | ');
    const tenant=parts[0], ep=parts[1]||parts[0];
    const epParts=ep.match(/^(\w+)\s+(.+)$/)||['',ep,ep];
    const method=epParts[1],path=epParts[2];
    const errPct=parseFloat(m.errorRate.replace('%',''))||0;
    const lClass=m.avgLatencyMs>3000?'var(--red)':m.avgLatencyMs>800?'var(--yellow)':'var(--green)';
    return `<tr>
      <td><span class="rank-badge">${i+1}</span></td>
      <td style="color:var(--purple);font-size:11px">${tenant}</td>
      <td>${methodBadge(method)}</td>
      <td style="color:var(--muted2);font-size:11px;font-family:'JetBrains Mono',monospace">${path}</td>
      <td style="text-align:right;font-weight:700">${m.requests_60s}</td>
      <td style="text-align:right"><span class="lat-pill" style="background:rgba(0,0,0,.3);color:${lClass}">${m.avgLatencyMs}</span></td>
      <td style="text-align:right;color:var(--yellow)">${m.p95LatencyMs}</td>
      <td style="text-align:right;color:var(--red)">${m.p99LatencyMs}</td>
      <td>
        <div class="err-bar-wrap">
          <div class="err-bar">
            <div class="err-bar-fill" style="width:${errPct}%;background:${errColor(errPct)}"></div>
          </div>
          <span style="color:${errColor(errPct)};font-size:11px;font-weight:600;width:35px;text-align:right">${m.errorRate}</span>
        </div>
      </td>
    </tr>`;
  }).join('');

  // ── Alert feed ──
  const feed=document.getElementById('alert-feed');
  const alerts=data.allAlerts||[];
  if(!alerts.length){
    feed.innerHTML='<div class="no-data">No alerts — all systems nominal ✅</div>';
  } else {
    feed.innerHTML=alerts.slice(0,15).map(a=>`
      <div class="alert-item ${a.severity}">
        <span class="alert-dot"></span>
        <div style="flex:1;min-width:0">
          <div class="alert-msg">${a.message}</div>
          <div class="alert-meta">
            ${a.type} &nbsp;|&nbsp; ${since(a.triggeredAt)}
            &nbsp;|&nbsp; val=${typeof a.currentValue==='number'?a.currentValue.toFixed(2):a.currentValue}
            &nbsp;threshold=${typeof a.thresholdValue==='number'?a.thresholdValue.toFixed(2):a.thresholdValue}
          </div>
        </div>
        <span class="sev-badge ${a.severity}">${a.severity}</span>
      </div>`).join('');
  }

  // ── Event stream ──
  const stream=document.getElementById('event-stream');
  const evts=(data.recentEvents||[]).slice(0,20);
  const evHtml=evts.map(e=>{
    const t=new Date(e.timestamp).toLocaleTimeString('en-US',{hour12:false});
    const sc=statusClass(e.statusCode);
    const lc=latClass(e.latencyMs);
    const tenant=(e.tenantId||'').replace('tenant-','');
    const mParts=(e.endpoint||'').match(/^(\w+)\s*(.*)$/)||['','?',''];
    return `<div class="ev-row">
      <span class="ev-status ${sc}">${e.statusCode}</span>
      <span class="ev-tenant">${tenant}</span>
      <span>${methodBadge(mParts[1])}</span>
      <span class="ev-path">${mParts[2]||e.path||'/'}</span>
      <span class="ev-lat ${lc}" style="text-align:right">${e.latencyMs}ms</span>
      <span style="text-align:right;color:var(--muted2);font-size:10px">${t}</span>
    </div>`;
  }).join('');
  stream.innerHTML=evHtml||'<div class="no-data">Waiting for events…</div>';
}

// ─── initial load + poll ───
updateDashboard();
setInterval(updateDashboard, 3000);
</script>
</body>
</html>
"""

write("demo-service/src/main/resources/static/index.html", DASHBOARD_HTML)
print("\nDashboard generated!")
print("Access it at: http://localhost:8888/")

