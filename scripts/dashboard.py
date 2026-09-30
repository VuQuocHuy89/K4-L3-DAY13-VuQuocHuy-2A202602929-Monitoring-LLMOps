from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from statistics import mean
from typing import Any
from urllib.parse import urlparse

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"

PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Monitoring &amp; LLMOps</title>
  <style>
    :root { color-scheme: light; --ink:#182230; --muted:#667085; --line:#e4eaf1; --blue:#3468f6; --teal:#16a394; --red:#dc5260; --amber:#c98213; }
    * { box-sizing:border-box }
    body { margin:0; background:#f4f7fb; color:var(--ink); font:14px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif }
    main { max-width:1440px; margin:auto; padding:28px 32px 40px }
    header { display:flex; justify-content:space-between; align-items:flex-end; gap:20px; margin-bottom:22px }
    h1 { margin:0 0 5px; font-size:25px; letter-spacing:-.035em }
    .subtitle,.muted { color:var(--muted) }
    .status { display:flex; align-items:center; gap:8px; white-space:nowrap; color:var(--muted); font-size:12px }
    .dot { width:8px; height:8px; border-radius:50%; background:var(--teal); box-shadow:0 0 0 4px #16a3941c }
    .grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px }
    article { min-height:285px; background:white; border:1px solid var(--line); border-radius:13px; padding:18px 19px; box-shadow:0 2px 8px #12233d06 }
    h2 { font-size:14px; margin:0; letter-spacing:-.01em }
    .panel-head { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:3px }
    .unit { color:var(--muted); font-size:11px; background:#f4f6f9; border-radius:5px; padding:3px 7px }
    .range { color:var(--muted); font-size:11px; margin-bottom:13px }
    .big { font-size:27px; line-height:1.1; font-weight:680; letter-spacing:-.04em }
    .big small { font-size:13px; color:var(--muted); font-weight:500; letter-spacing:0 }
    .stats { display:grid; grid-template-columns:repeat(2,1fr); gap:12px; margin:15px 0 8px }
    .stat-label { color:var(--muted); font-size:11px; margin-bottom:3px }
    .stat-value { font-size:17px; font-weight:630; font-variant-numeric:tabular-nums }
    .chart { width:100%; height:100px; display:block; overflow:visible; margin-top:7px }
    .chart text { fill:#8b96a7; font:10px ui-sans-serif,system-ui,sans-serif }
    .legend { display:flex; gap:15px; color:var(--muted); font-size:11px; margin-top:8px }
    .legend i { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:5px }
    .bar-row { display:grid; grid-template-columns:63px 52px 1fr; align-items:center; gap:8px; margin:10px 0 }
    .bar-label { color:var(--muted); font-size:11px }
    .bar-value { font-variant-numeric:tabular-nums; font-size:12px; font-weight:600; text-align:right }
    .track { height:7px; border-radius:9px; background:#edf1f6; overflow:hidden }
    .fill { height:100%; border-radius:9px; background:var(--blue) }
    .threshold { color:var(--muted); font-size:11px; margin-top:11px }
    .empty { color:var(--muted); padding:25px 0; text-align:center }
    footer { margin-top:15px; color:var(--muted); font-size:11px; display:flex; justify-content:space-between }
    @media(max-width:1000px) { .grid { grid-template-columns:repeat(2,minmax(0,1fr)) } }
    @media(max-width:650px) { main { padding:20px 14px } header { align-items:flex-start; flex-direction:column } .grid { grid-template-columns:1fr } article { min-height:260px } }
  </style>
</head>
<body>
<main>
  <header>
    <div><h1 id="title">Day 13 Monitoring &amp; LLMOps</h1><div class="subtitle">Request health, model usage and answer quality</div></div>
    <div class="status"><span class="dot"></span><span id="status">Loading log data…</span></div>
  </header>
  <section class="grid">
    <article><div class="panel-head"><h2>Latency percentiles and TTFT</h2><span class="unit">ms · last 60 min</span></div><div class="range">Request duration and time to first token</div><div id="latency"></div><div id="latency-chart"></div><div class="threshold" id="latency-threshold"></div></article>
    <article><div class="panel-head"><h2>Request traffic</h2><span class="unit">requests/min</span></div><div class="range">Requests received per minute</div><div class="big" id="traffic-total">—</div><div id="traffic-chart"></div><div class="threshold" id="traffic-threshold"></div></article>
    <article><div class="panel-head"><h2>Error rate and retrieval success</h2><span class="unit">percent</span></div><div class="range">Failed requests and retrieval outcomes</div><div class="stats"><div><div class="stat-label">Error rate</div><div class="stat-value" id="error-rate">—</div></div><div><div class="stat-label">Retrieval success</div><div class="stat-value" id="retrieval-success">—</div></div></div><div id="errors-chart"></div><div class="threshold" id="errors-threshold"></div></article>
    <article><div class="panel-head"><h2>Cost over time</h2><span class="unit">USD</span></div><div class="range">Estimated cost from fake model token usage</div><div class="big" id="cost-total">—</div><div id="cost-chart"></div><div class="threshold" id="cost-threshold"></div></article>
    <article><div class="panel-head"><h2>Input and output tokens</h2><span class="unit">tokens</span></div><div class="range">Token usage from completed generations</div><div class="stats"><div><div class="stat-label">Input</div><div class="stat-value" id="tokens-in">—</div></div><div><div class="stat-label">Output</div><div class="stat-value" id="tokens-out">—</div></div></div><div id="tokens-chart"></div><div class="threshold" id="tokens-threshold"></div></article>
    <article><div class="panel-head"><h2>Quality proxy</h2><span class="unit">score · 0–1</span></div><div class="range">Mean heuristic quality score</div><div class="big" id="quality-mean">—</div><div id="quality-chart"></div><div class="threshold" id="quality-threshold"></div></article>
  </section>
  <footer><span>Source: structured application logs · rolling 60-minute window</span><span id="updated">Waiting for data</span></footer>
</main>
<script>
const fmt=(n,d=0)=>Number(n||0).toLocaleString(undefined,{maximumFractionDigits:d,minimumFractionDigits:d});
const percent=n=>`${fmt(n,1)}%`;
const esc=Number;
function sparkline(target, series, keys, colors, threshold=null, maxOverride=null) {
  const el=document.getElementById(target), w=600,h=94,p=8;
  const vals=series.flatMap(row=>keys.map(k=>esc(row[k]||0)));
  const max=Math.max(maxOverride||0,threshold||0,...vals,1), min=0;
  const x=i=>p+(i/Math.max(series.length-1,1))*(w-2*p);
  const y=v=>h-p-((v-min)/(max-min))*(h-2*p);
  let svg=`<svg class="chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Metric history">`;
  for(let i=0;i<3;i++){const yy=p+i*(h-2*p)/2;svg+=`<line x1="${p}" y1="${yy}" x2="${w-p}" y2="${yy}" stroke="#edf1f6"/>`;}
  if(threshold!==null){const ty=y(threshold);svg+=`<line x1="${p}" y1="${ty}" x2="${w-p}" y2="${ty}" stroke="#dc5260" stroke-dasharray="5 5" opacity=".8"/>`;}
  keys.forEach((key,index)=>{const points=series.map((row,i)=>`${x(i)},${y(esc(row[key]||0))}`).join(" ");svg+=`<polyline points="${points}" fill="none" stroke="${colors[index]}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>`;});
  svg+=`<text x="${p}" y="${h-1}">${series[0]?.minute||""}</text><text x="${w-p}" y="${h-1}" text-anchor="end">${series.at(-1)?.minute||""}</text></svg>`;
  el.innerHTML=svg;
}
function panelThreshold(cfg,id,formatValue=null){
 const panel=cfg.dashboard.panels.find(p=>p.id===id); if(!panel)return "";
 const value=formatValue?formatValue(panel.threshold.value):`${fmt(panel.threshold.value)} ${panel.unit.replaceAll("_"," ")}`;
 return `${panel.threshold.operator==="lte"?"Target ≤":"Target ≥"} ${value}`;
}
function setBar(label,value,max,color){const width=Math.min(100,Math.max(0,(value/Math.max(max,1))*100));return `<div class="bar-row"><span class="bar-label">${label}</span><span class="bar-value">${fmt(value)} ms</span><div class="track"><div class="fill" style="width:${width}%;background:${color}"></div></div></div>`;}
async function refresh(){
 try{
  const response=await fetch("/api/metrics",{cache:"no-store"}); if(!response.ok)throw new Error(`HTTP ${response.status}`);
  const d=await response.json(), t=d.totals, cfg=d.config, s=d.series;
  document.getElementById("title").textContent=cfg.dashboard.title;
  document.getElementById("status").textContent=`Live · ${t.request_count} requests in ${cfg.dashboard.time_range_minutes} min`;
  const p=t.latency, limit=cfg.dashboard.panels.find(x=>x.id==="latency").threshold.value;
  document.getElementById("latency").innerHTML=setBar("P50",p.p50,limit,"#82a2ff")+setBar("P95",p.p95,limit,"#3468f6")+setBar("P99",p.p99,limit,"#6848d8")+setBar("TTFT P95",p.ttft_p95,limit,"#16a394");
  document.getElementById("latency-threshold").textContent=`P95 SLO ${panelThreshold(cfg,"latency",n=>`${fmt(n)} ms`)}`;
  sparkline("latency-chart",s,["latency_p95","ttft_p95"],["#3468f6","#16a394"],limit,limit);
  document.getElementById("traffic-total").innerHTML=`${fmt(t.request_count)} <small>requests</small>`;
  sparkline("traffic-chart",s,["traffic"],["#3468f6"]);
  document.getElementById("traffic-threshold").textContent=panelThreshold(cfg,"traffic");
  document.getElementById("error-rate").textContent=percent(t.error_rate_pct);
  document.getElementById("retrieval-success").textContent=percent(t.retrieval_success_pct);
  sparkline("errors-chart",s,["error_rate_pct"],["#dc5260"],cfg.dashboard.panels.find(x=>x.id==="errors").threshold.value);
  document.getElementById("errors-threshold").textContent=`Error rate ${panelThreshold(cfg,"errors",percent)} · retrieval target ≥ 90%`;
  document.getElementById("cost-total").innerHTML=`$${fmt(t.cost_usd,4)} <small>total</small>`;
  sparkline("cost-chart",s,["cost_usd"],["#c98213"]);
  document.getElementById("cost-threshold").textContent=panelThreshold(cfg,"cost",n=>`$${fmt(n,2)}`);
  document.getElementById("tokens-in").textContent=fmt(t.tokens_in);
  document.getElementById("tokens-out").textContent=fmt(t.tokens_out);
  sparkline("tokens-chart",s,["tokens_in","tokens_out"],["#3468f6","#16a394"]);
  document.getElementById("tokens-threshold").textContent=panelThreshold(cfg,"tokens");
  document.getElementById("quality-mean").innerHTML=`${fmt(t.quality_avg,2)} <small>/ 1.00</small>`;
  sparkline("quality-chart",s,["quality_avg"],["#16a394"],cfg.dashboard.panels.find(x=>x.id==="quality").threshold.value,1);
  document.getElementById("quality-threshold").textContent=panelThreshold(cfg,"quality");
  document.getElementById("updated").textContent=`Updated ${new Date(d.generated_at).toLocaleTimeString()}`;
  window.clearInterval(window.dashboardTimer); window.dashboardTimer=window.setInterval(refresh,cfg.dashboard.refresh_seconds*1000);
 }catch(error){document.getElementById("status").textContent=`Waiting for logs (${error.message})`;}
}
refresh();
</script>
</body>
</html>"""


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile / 100 * len(ordered)) - 1)
    return float(ordered[index])


def build_dashboard_data(
    log_path: Path = DEFAULT_LOG_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    now: datetime | None = None,
) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    window_minutes = int(config["dashboard"]["time_range_minutes"])
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = current - timedelta(minutes=window_minutes)
    records: list[tuple[datetime, dict[str, Any]]] = []
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            timestamp = _parse_timestamp(record.get("ts"))
            if timestamp is not None and start <= timestamp <= current:
                records.append((timestamp, record))

    minute_count = window_minutes
    buckets: dict[int, dict[str, Any]] = defaultdict(
        lambda: {
            "traffic": 0,
            "errors": 0,
            "latencies": [],
            "ttfts": [],
            "cost_usd": 0.0,
            "tokens_in": 0,
            "tokens_out": 0,
            "quality_scores": [],
        }
    )
    totals = {
        "request_count": 0,
        "failed_count": 0,
        "retrieval_attempts": 0,
        "retrieval_successes": 0,
        "latencies": [],
        "ttfts": [],
        "cost_usd": 0.0,
        "tokens_in": 0,
        "tokens_out": 0,
        "quality_scores": [],
    }

    for timestamp, record in records:
        bucket_index = int((timestamp - start).total_seconds() // 60)
        bucket_index = min(max(bucket_index, 0), minute_count - 1)
        bucket = buckets[bucket_index]
        event = record.get("event")
        if event == "request_received":
            totals["request_count"] += 1
            bucket["traffic"] += 1
        elif event == "request_failed":
            totals["failed_count"] += 1
            bucket["errors"] += 1
            if record.get("tool_name") == "retrieval":
                totals["retrieval_attempts"] += 1
        elif event == "response_sent":
            latency = record.get("latency_ms")
            ttft = record.get("ttft_ms")
            if isinstance(latency, (int, float)):
                totals["latencies"].append(float(latency))
                bucket["latencies"].append(float(latency))
            if isinstance(ttft, (int, float)):
                totals["ttfts"].append(float(ttft))
                bucket["ttfts"].append(float(ttft))
            cost = record.get("cost_usd")
            if isinstance(cost, (int, float)):
                totals["cost_usd"] += float(cost)
                bucket["cost_usd"] += float(cost)
            for field in ("tokens_in", "tokens_out"):
                value = record.get(field)
                if isinstance(value, (int, float)):
                    totals[field] += int(value)
                    bucket[field] += int(value)
            quality = record.get("quality_score")
            if isinstance(quality, (int, float)):
                totals["quality_scores"].append(float(quality))
                bucket["quality_scores"].append(float(quality))
            if record.get("tool_name") == "retrieval":
                totals["retrieval_attempts"] += 1
                if record.get("tool_success") is True:
                    totals["retrieval_successes"] += 1
        if event == "request_failed" and record.get("tool_success") is False:
            totals["retrieval_successes"] += 0

    series = []
    for index in range(minute_count):
        minute_start = start.replace(second=0, microsecond=0) + timedelta(minutes=index)
        bucket = buckets[index]
        series.append(
            {
                "minute": minute_start.strftime("%H:%M"),
                "traffic": bucket["traffic"],
                "error_count": bucket["errors"],
                "error_rate_pct": round(100 * bucket["errors"] / bucket["traffic"], 2)
                if bucket["traffic"]
                else 0.0,
                "latency_p95": _percentile(bucket["latencies"], 95),
                "ttft_p95": _percentile(bucket["ttfts"], 95),
                "cost_usd": round(bucket["cost_usd"], 6),
                "tokens_in": bucket["tokens_in"],
                "tokens_out": bucket["tokens_out"],
                "quality_avg": round(mean(bucket["quality_scores"]), 4)
                if bucket["quality_scores"]
                else 0.0,
            }
        )

    request_count = totals["request_count"]
    retrieval_attempts = totals["retrieval_attempts"]
    quality_values = totals["quality_scores"]
    return {
        "generated_at": current.isoformat(),
        "config": config,
        "totals": {
            "request_count": request_count,
            "failed_count": totals["failed_count"],
            "error_rate_pct": round(100 * totals["failed_count"] / request_count, 2)
            if request_count
            else 0.0,
            "retrieval_success_pct": round(
                100 * totals["retrieval_successes"] / retrieval_attempts, 2
            )
            if retrieval_attempts
            else 0.0,
            "latency": {
                "p50": _percentile(totals["latencies"], 50),
                "p95": _percentile(totals["latencies"], 95),
                "p99": _percentile(totals["latencies"], 99),
                "ttft_p95": _percentile(totals["ttfts"], 95),
            },
            "cost_usd": round(totals["cost_usd"], 6),
            "tokens_in": totals["tokens_in"],
            "tokens_out": totals["tokens_out"],
            "quality_avg": round(mean(quality_values), 4) if quality_values else 0.0,
        },
        "series": series,
    }


def make_handler(log_path: Path, config_path: Path) -> type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            route = urlparse(self.path).path
            if route == "/api/metrics":
                body = json.dumps(
                    build_dashboard_data(log_path, config_path), ensure_ascii=False
                ).encode("utf-8")
                content_type = "application/json; charset=utf-8"
            elif route == "/":
                body = PAGE.encode("utf-8")
                content_type = "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            return

    return DashboardHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the six-panel Day 13 dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--log-path", type=Path, default=DEFAULT_LOG_PATH)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()

    server = ThreadingHTTPServer(
        (args.host, args.port), make_handler(args.log_path, args.config)
    )
    print(f"Dashboard listening at http://{args.host}:{args.port}")
    print(f"Reading logs from {args.log_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
