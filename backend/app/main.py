import os
import re
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from dotenv import load_dotenv

from app.schemas.request_schema import AnalyzeRequest, IngestLogRequest
from app.services.ai_analysis_service import analyze_log_with_ai
from app.services.analyze_service import analyze_log
from app.services.alertmanager_service import (
    ingest_alertmanager_webhook,
    is_alertmanager_token_valid,
)
from app.services.ingest_service import ingest_log
from app.services.on_demand_log_ai_service import analyze_unified_log_record
from app.services.prometheus_client import get_prometheus_snapshot
from app.services.qwen_client import test_qwen_connection
from app.storage.history_store import (
    get_analysis_record_by_id,
    get_recent_analysis_records,
    init_db,
)
from app.storage.log_store import init_logs_db
from app.storage.log_store import (
    count_logs,
    get_log_record_by_id,
    get_log_statistics,
    get_recent_logs,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)

app = FastAPI(title="AI-OpsLog", version="0.1.0")


@app.on_event("startup")
def startup_init_db() -> None:
    try:
        init_db()
        init_logs_db()
    except Exception as exc:
        print(f"failed to initialize AI-OpsLog SQLite databases: {exc}")
        raise


@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard/logs", response_class=HTMLResponse)
def dashboard(
    source: str | None = None,
    host: str | None = None,
    log_level: str | None = None,
    time_from: str | None = None,
    time_to: str | None = None,
    recent_hours: str | None = "24",
    keyword: str | None = None,
    limit: str | None = "10",
    page: str | None = "1",
    stats_hours: str | None = "24",
) -> HTMLResponse:
    error_message = ""
    normalized_recent_hours = _parse_optional_positive_int(recent_hours)
    normalized_time_from = _effective_time_from(time_from, normalized_recent_hours)
    normalized_limit = _normalize_dashboard_limit(limit)
    normalized_page = max(_parse_optional_positive_int(page, default=1) or 1, 1)
    normalized_source = _normalize_history_filter(source)
    normalized_host = _normalize_history_filter(host)
    normalized_log_level = _normalize_history_filter(log_level)
    normalized_keyword = _normalize_history_filter(keyword)
    normalized_time_to = _normalize_history_filter(time_to)
    normalized_stats_hours = _normalize_stats_hours(stats_hours)
    total_count = 0
    stats = {"hours": normalized_stats_hours, "level_counts": {}, "source_counts": {}, "total": 0}
    prometheus_snapshot = {"configured": False, "metrics": []}
    try:
        stats = get_log_statistics(normalized_stats_hours)
        prometheus_snapshot = get_prometheus_snapshot()
        total_count = count_logs(
            source=normalized_source,
            host=normalized_host,
            log_level=normalized_log_level,
            time_from=normalized_time_from,
            time_to=normalized_time_to,
            keyword=normalized_keyword,
        )
        total_pages = max((total_count + normalized_limit - 1) // normalized_limit, 1)
        normalized_page = min(normalized_page, total_pages)
        offset = (normalized_page - 1) * normalized_limit
        records = get_recent_logs(
            limit=normalized_limit,
            source=normalized_source,
            host=normalized_host,
            log_level=normalized_log_level,
            time_from=normalized_time_from,
            time_to=normalized_time_to,
            keyword=normalized_keyword,
            offset=offset,
        )
    except Exception as exc:
        records = []
        error_message = f"统一日志查询失败：{exc}"

    table_body = _render_dashboard_rows(records, normalized_keyword)
    filter_form = _render_log_filter_form(
        source,
        host,
        log_level,
        time_from,
        time_to,
        normalized_recent_hours,
        keyword,
        normalized_limit,
        normalized_stats_hours,
    )
    pagination = _render_log_pagination(
        total_count=total_count,
        page=normalized_page,
        limit=normalized_limit,
        source=source,
        host=host,
        log_level=log_level,
        time_from=time_from,
        time_to=time_to,
        recent_hours=normalized_recent_hours,
        keyword=keyword,
        stats_hours=normalized_stats_hours,
    )
    stats_panel = _render_statistics_panel(
        stats,
        prometheus_snapshot,
        normalized_stats_hours,
        source=source,
        host=host,
        log_level=log_level,
        time_from=time_from,
        time_to=time_to,
        recent_hours=normalized_recent_hours,
        keyword=keyword,
        limit=normalized_limit,
    )
    error_block = ""
    if error_message:
        error_block = f'<div class="notice error">{escape(error_message)}</div>'

    html = f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI-OpsLog 运维日志分析助手</title>
  <style>
    body {{
      margin: 0;
      background: #f3f6fb;
      color: #1f2937;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      line-height: 1.55;
    }}
    .page {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 32px 20px 40px;
    }}
    .filters {{
      display: grid;
      grid-template-columns: repeat(6, minmax(150px, 1fr));
      gap: 12px;
      margin: 18px 0 22px;
      padding: 16px;
      border: 1px solid #d8e2ef;
      border-radius: 12px;
      background: #ffffff;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
      align-items: end;
      overflow: hidden;
    }}
    .filters > div {{
      min-width: 0;
    }}
    .filters label {{
      display: block;
      color: #374151;
      font-size: 12px;
      font-weight: 600;
      margin-bottom: 4px;
    }}
    .filters input, .filters select {{
      box-sizing: border-box;
      width: 100%;
      height: 40px;
      padding: 8px 10px;
      border: 1px solid #d8dee4;
      border-radius: 8px;
      background: #ffffff;
      color: #1f2937;
      font-size: 14px;
    }}
    .filters input:focus, .filters select:focus {{
      border-color: #2563eb;
      outline: 3px solid rgba(37, 99, 235, 0.14);
    }}
    .filter-actions {{
      align-self: end;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }}
    .filters button, .filters .reset-link {{
      align-self: end;
      min-height: 40px;
      border: 1px solid #1d4ed8;
      border-radius: 8px;
      background: #2563eb;
      color: #ffffff;
      cursor: pointer;
      font-size: 14px;
      padding: 0 16px;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      box-sizing: border-box;
    }}
    .filters button {{
      font-weight: 700;
      box-shadow: 0 8px 18px rgba(37, 99, 235, 0.16);
    }}
    .filters button:hover {{
      background: #1d4ed8;
    }}
    .filters .reset-link {{
      border-color: #d8dee4;
      background: #ffffff;
      color: #1f2937;
    }}
    .filters .wide {{
      grid-column: span 2;
    }}
    .filters .filter-limit {{
      max-width: 120px;
    }}
    .filters .filter-actions {{
      grid-column: span 2;
      justify-content: flex-end;
    }}
    .refresh-note {{
      margin: -8px 0 14px;
      color: #64748b;
      font-size: 12px;
    }}
    .pager {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin: 12px 0;
      padding: 10px 12px;
      border: 1px solid #d8e2ef;
      border-radius: 10px;
      background: #ffffff;
      color: #4b5563;
      font-size: 13px;
    }}
    .pager-controls {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
    }}
    .pager a, .pager .disabled {{
      display: inline-block;
      padding: 5px 10px;
      border: 1px solid #d8dee4;
      border-radius: 6px;
      background: #ffffff;
      color: #1f2937;
      text-decoration: none;
    }}
    .pager .disabled {{
      color: #9ca3af;
      background: #f3f4f6;
    }}
    .pager form {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin: 0;
    }}
    .pager input {{
      width: 58px;
      height: 30px;
      border: 1px solid #d8dee4;
      border-radius: 6px;
      padding: 0 8px;
    }}
    .pager button {{
      height: 32px;
      border: 1px solid #d8dee4;
      border-radius: 6px;
      background: #ffffff;
      cursor: pointer;
    }}
    .stats-toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
      padding: 14px 16px;
      border: 1px solid #d8e2ef;
      border-radius: 12px;
      background: linear-gradient(135deg, #eff6ff 0%, #ffffff 72%);
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
      color: #4b5563;
      font-size: 14px;
    }}
    .stats-summary {{
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      gap: 8px;
    }}
    .stats-total {{
      color: #0f172a;
      font-size: 24px;
      font-weight: 800;
    }}
    .stats-meta {{
      color: #64748b;
    }}
    .stats-toolbar select {{
      height: 36px;
      padding: 6px 9px;
      border: 1px solid #d8dee4;
      border-radius: 8px;
      background: #ffffff;
      color: #1f2937;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: minmax(360px, 1.15fr) minmax(360px, 0.85fr);
      gap: 18px;
      margin-bottom: 22px;
    }}
    .stat-panel {{
      background: #ffffff;
      border: 1px solid #d8e2ef;
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
      min-width: 0;
    }}
    .stat-panel h3 {{
      margin: 0 0 14px;
      font-size: 17px;
      line-height: 1.35;
    }}
    .stat-panel-scroll {{
      overflow-x: auto;
      padding-bottom: 2px;
    }}
    .bar-row {{
      display: grid;
      grid-template-columns: 128px minmax(180px, 1fr) 56px;
      gap: 12px;
      align-items: center;
      margin: 9px 0;
      padding: 6px 8px;
      border-radius: 8px;
      font-size: 13px;
      color: #1f2937;
      text-decoration: none;
    }}
    .bar-row:hover {{
      background: #f8fafc;
    }}
    .bar-track {{
      position: relative;
      height: 13px;
      overflow: hidden;
      border-radius: 999px;
      background: #e9eef6;
    }}
    .bar-fill {{
      height: 100%;
      min-width: 2px;
      border-radius: 999px;
      background: linear-gradient(90deg, rgba(37, 99, 235, 0.72), #2563eb);
    }}
    .bar-fill.level-critical {{
      background: linear-gradient(90deg, rgba(220, 38, 38, 0.65), #dc2626);
    }}
    .bar-fill.level-error {{
      background: linear-gradient(90deg, rgba(249, 115, 22, 0.68), #f97316);
    }}
    .bar-fill.level-warn {{
      background: linear-gradient(90deg, rgba(234, 179, 8, 0.72), #eab308);
    }}
    .bar-fill.level-info {{
      background: linear-gradient(90deg, rgba(22, 163, 74, 0.65), #16a34a);
    }}
    .bar-fill.level-debug {{
      background: linear-gradient(90deg, rgba(107, 114, 128, 0.65), #6b7280);
    }}
    .bar-fill.source-system {{
      background: #64748b;
    }}
    .bar-fill.source-zabbix {{
      background: #dc2626;
    }}
    .bar-fill.source-prometheus {{
      background: #f97316;
    }}
    .bar-fill.source-grafana {{
      background: #d97706;
    }}
    .bar-fill.source-ansible {{
      background: #2563eb;
    }}
    .bar-fill.source-docker {{
      background: #0891b2;
    }}
    .bar-fill.source-kubernetes {{
      background: #4f46e5;
    }}
    .bar-fill.source-nginx {{
      background: #16a34a;
    }}
    .bar-fill.source-redis {{
      background: #b91c1c;
    }}
    .bar-fill.source-mysql {{
      background: #0d9488;
    }}
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }}
    .metric-card {{
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      padding: 12px;
      background: #f8fafc;
    }}
    .metric-name {{
      margin: 0 0 6px;
      color: #475569;
      font-size: 12px;
      font-weight: 700;
    }}
    .metric-value {{
      margin: 0;
      color: #0f172a;
      font-size: 20px;
      font-weight: 800;
    }}
    .metric-desc {{
      margin: 6px 0 0;
      color: #64748b;
      font-size: 12px;
      line-height: 1.45;
    }}
    .metric-query {{
      margin-top: 8px;
      color: #64748b;
      font-size: 11px;
      overflow-wrap: anywhere;
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
    }}
    .metric-muted {{
      color: #64748b;
      font-size: 13px;
      line-height: 1.6;
    }}
    header {{
      margin-bottom: 26px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 32px;
      font-weight: 800;
      letter-spacing: 0;
      color: #0f172a;
    }}
    .subtitle {{
      margin: 0;
      color: #4b5563;
      font-size: 15px;
      line-height: 1.7;
    }}
    section {{
      margin-top: 28px;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 22px;
      line-height: 1.35;
      color: #0f172a;
    }}
    .table-wrap {{
      overflow-x: auto;
      background: #ffffff;
      border: 1px solid #d8e2ef;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      min-width: 1180px;
    }}
    th, td {{
      padding: 11px 12px;
      border-bottom: 1px solid #e5e7eb;
      text-align: left;
      vertical-align: middle;
      font-size: 14px;
      line-height: 20px;
    }}
    th {{
      background: #f3f4f6;
      color: #374151;
      font-weight: 600;
    }}
    tr:last-child td {{
      border-bottom: 0;
    }}
    .col-id {{
      width: 52px;
    }}
    .col-time {{
      width: 150px;
    }}
    .col-source {{
      width: 136px;
    }}
    .col-host {{
      width: 152px;
    }}
    .col-level {{
      width: 88px;
    }}
    .col-status {{
      width: 90px;
    }}
    .col-message {{
      width: auto;
    }}
    .col-action {{
      width: 108px;
    }}
    .message-cell {{
      max-width: 0;
    }}
    .message-text {{
      display: -webkit-box;
      overflow: hidden;
      white-space: normal;
      overflow-wrap: anywhere;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      cursor: pointer;
    }}
    .message-text.expanded {{
      display: block;
      -webkit-line-clamp: unset;
    }}
    .message-text mark {{
      padding: 0 2px;
      border-radius: 3px;
      background: #fde68a;
      color: #78350f;
    }}
    .row-risk-high td {{
      background: #fff5f5;
    }}
    .row-risk-high td:first-child {{
      border-left: 4px solid #dc2626;
    }}
    .row-risk-medium td {{
      background: #fffbeb;
    }}
    .row-risk-medium td:first-child {{
      border-left: 4px solid #d97706;
    }}
    .badge {{
      display: inline-block;
      min-width: 28px;
      padding: 3px 9px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 600;
      text-align: center;
      border: 1px solid #d8dee4;
      background: #f3f4f6;
      color: #374151;
    }}
    .badge-critical, .badge-high {{
      border-color: #f1b7b7;
      background: #fff5f5;
      color: #991b1b;
    }}
    .badge-error {{
      border-color: #fed7aa;
      background: #fff7ed;
      color: #9a3412;
    }}
    .badge-warn {{
      border-color: #fde68a;
      background: #fefce8;
      color: #854d0e;
    }}
    .badge-info {{
      border-color: #bbf7d0;
      background: #f0fdf4;
      color: #166534;
    }}
    .badge-debug {{
      border-color: #d1d5db;
      background: #f8fafc;
      color: #475569;
    }}
    .badge-medium {{
      border-color: #f2d28a;
      background: #fffbeb;
      color: #92400e;
    }}
    .badge-low {{
      border-color: #bbd7c0;
      background: #f0fdf4;
      color: #166534;
    }}
    .empty, .notice {{
      padding: 16px;
      background: #ffffff;
      border: 1px solid #d8dee4;
      border-radius: 8px;
      color: #4b5563;
    }}
    .error {{
      border-color: #f1b7b7;
      background: #fff5f5;
      color: #991b1b;
      margin-bottom: 16px;
    }}
    .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 8px;
    }}
    .links a, .endpoint {{
      display: inline-block;
      padding: 6px 10px;
      border: 1px solid #d8dee4;
      border-radius: 6px;
      background: #ffffff;
      color: #1f2937;
      text-decoration: none;
      font-size: 13px;
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
    }}
    .ai-button {{
      padding: 7px 10px;
      border: 1px solid #1d4ed8;
      border-radius: 8px;
      background: #eff6ff;
      color: #1d4ed8;
      cursor: pointer;
      font-size: 13px;
      font-weight: 700;
    }}
    .ai-button:hover {{
      border-color: #2563eb;
      color: #ffffff;
      background: #2563eb;
    }}
    .ai-button:disabled {{
      cursor: wait;
      border-color: #cbd5e1;
      background: #e5e7eb;
      color: #64748b;
    }}
    .ai-result {{
      margin-top: 18px;
      padding: 0;
      background: #ffffff;
      border: 1px solid #d8e2ef;
      border-radius: 12px;
      font-size: 14px;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
      overflow: hidden;
    }}
    .ai-result h3 {{
      margin: 0;
      font-size: 18px;
    }}
    .ai-result h4 {{
      margin: 0 0 8px;
      font-size: 15px;
    }}
    .ai-result p {{
      margin: 6px 0;
    }}
    .ai-result ul {{
      margin: 6px 0 0;
      padding-left: 20px;
    }}
    .ai-result pre {{
      overflow-x: auto;
      white-space: pre-wrap;
      background: #f6f8fa;
      border: 1px solid #d8dee4;
      border-radius: 6px;
      padding: 10px;
    }}
    .ai-placeholder {{
      padding: 16px;
      color: #64748b;
    }}
    .ai-card-header {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: center;
      padding: 16px;
      border-bottom: 1px solid #e5e7eb;
      background: #f8fafc;
    }}
    .ai-title-block {{
      min-width: 0;
    }}
    .ai-meta {{
      margin: 4px 0 0;
      color: #64748b;
      font-size: 13px;
    }}
    .ai-header-actions {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
    }}
    .ai-tool-button {{
      height: 30px;
      padding: 0 10px;
      border: 1px solid #d8dee4;
      border-radius: 8px;
      background: #ffffff;
      color: #1f2937;
      cursor: pointer;
      font-size: 12px;
      font-weight: 700;
    }}
    .ai-tool-button:hover {{
      border-color: #2563eb;
      color: #1d4ed8;
      background: #eff6ff;
    }}
    .copy-status {{
      color: #166534;
      font-size: 12px;
      font-weight: 700;
    }}
    .risk-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 800;
      border: 1px solid #d8dee4;
    }}
    .risk-critical, .risk-high {{
      border-color: #fecaca;
      background: #fef2f2;
      color: #991b1b;
    }}
    .risk-medium {{
      border-color: #fde68a;
      background: #fffbeb;
      color: #92400e;
    }}
    .risk-low {{
      border-color: #bbf7d0;
      background: #f0fdf4;
      color: #166534;
    }}
    .risk-unknown {{
      border-color: #d8dee4;
      background: #f8fafc;
      color: #475569;
    }}
    .ai-card-body {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      padding: 16px;
    }}
    .ai-section {{
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      padding: 13px;
      background: #ffffff;
    }}
    .ai-section.full {{
      grid-column: 1 / -1;
      background: #f8fafc;
    }}
    .ai-section summary {{
      cursor: pointer;
      font-weight: 700;
      color: #0f172a;
    }}
    .ai-section ul {{
      list-style: none;
      padding-left: 0;
    }}
    .ai-section li {{
      position: relative;
      padding-left: 22px;
      margin: 6px 0;
    }}
    .ai-section li::before {{
      content: "•";
      position: absolute;
      left: 7px;
      color: #2563eb;
      font-weight: 800;
    }}
    @media (max-width: 1180px) {{
      .filters {{
        grid-template-columns: repeat(3, minmax(160px, 1fr));
      }}
      .filters .wide {{
        grid-column: span 2;
      }}
      .filters .filter-actions {{
        grid-column: span 3;
        justify-content: flex-start;
      }}
    }}
    @media (max-width: 760px) {{
      .page {{
        padding: 22px 12px 32px;
      }}
      h1 {{
        font-size: 24px;
      }}
      .filters .wide {{
        grid-column: span 1;
      }}
      .filters {{
        grid-template-columns: 1fr;
      }}
      .filters .filter-limit,
      .filters .filter-actions {{
        grid-column: span 1;
        max-width: none;
      }}
      .stats-grid {{
        grid-template-columns: 1fr;
      }}
      .ai-card-body {{
        grid-template-columns: 1fr;
      }}
      .ai-card-header {{
        align-items: flex-start;
      }}
      .ai-header-actions {{
        justify-content: flex-start;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <header>
      <h1>AI-OpsLog 运维日志分析助手</h1>
      <p class="subtitle">集中日志收集、统一存储、按需 AI 分析 Demo</p>
    </header>

    <section>
      <h2>最近日志</h2>
      {error_block}
      {stats_panel}
      {filter_form}
      <div class="refresh-note">页面每 60 秒自动刷新一次，保留当前筛选条件。</div>
      {pagination}
      {table_body}
      {pagination}
      <div id="ai-result" class="ai-result"><div class="ai-placeholder">点击“AI 分析”后，分析结果会显示在这里。</div></div>
    </section>

    <section>
      <h2>API Endpoints</h2>
      <div class="links">
        <a href="/dashboard/logs">GET /dashboard/logs</a>
        <a href="/history/recent">GET /history/recent</a>
        <span class="endpoint">GET /history/{{id}}</span>
        <span class="endpoint">POST /logs/{{id}}/analyze</span>
        <span class="endpoint">POST /logs/ingest</span>
        <span class="endpoint">POST /alerts/alertmanager</span>
        <a href="/health">GET /health</a>
      </div>
    </section>
  </main>
  <script>
    function escapeHtml(value) {{
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }}

    function renderList(items) {{
      if (!Array.isArray(items) || items.length === 0) {{
        return "<p>-</p>";
      }}
      return "<ul>" + items.map(item => "<li>" + escapeHtml(item) + "</li>").join("") + "</ul>";
    }}

    function listText(items) {{
      if (!Array.isArray(items) || items.length === 0) {{
        return "-";
      }}
      return items.map((item, index) => `${{index + 1}}. ${{String(item)}}`).join("\\n");
    }}

    function displayRiskLevel(value) {{
      const mapping = {{
        critical: "严重",
        high: "高",
        medium: "中",
        low: "低",
        unknown: "未知"
      }};
      const raw = String(value || "").toLowerCase();
      return mapping[raw] || value || "-";
    }}

    function riskClass(value) {{
      const raw = String(value || "unknown").toLowerCase();
      if (raw === "critical" || raw === "high") return "risk-high";
      if (raw === "medium") return "risk-medium";
      if (raw === "low") return "risk-low";
      return "risk-unknown";
    }}

    let currentAnalysisData = null;

    function buildAnalysisText(data) {{
      const result = data?.analysis_result || {{}};
      const risk = result.risk_level || "unknown";
      return [
        `AI-OpsLog 日志 #${{data?.log_id ?? "-"}} AI 分析结果`,
        "",
        `风险等级：${{displayRiskLevel(risk)}}`,
        `参考 Runbook：${{result.runbook_used || "-"}}`,
        "",
        "问题摘要：",
        result.summary || "-",
        "",
        "关键报错：",
        result.key_error || "-",
        "",
        "关键证据：",
        listText(result.evidence),
        "",
        "根因假设：",
        result.root_cause_hypothesis || result.root_cause || result.possible_root_cause || "-",
        "",
        "命中关键词：",
        listText(result.matched_keywords),
        "",
        "可能原因：",
        listText(result.possible_causes),
        "",
        "排查建议：",
        listText(result.troubleshooting_steps || result.recommendations),
        "",
        "验证方法：",
        listText(result.verification_methods),
        "",
        "操作风险提示：",
        result.operation_risk || "-",
        "",
        "后续预防建议：",
        listText(result.prevention_suggestions),
        "",
        "补充说明：",
        result.notes || "-",
      ].join("\\n");
    }}

    async function copyAnalysisResult() {{
      if (!currentAnalysisData) {{
        return;
      }}
      const text = buildAnalysisText(currentAnalysisData);
      try {{
        await navigator.clipboard.writeText(text);
      }} catch (error) {{
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }}
      const status = document.getElementById("copy-status");
      if (status) {{
        status.textContent = "已复制";
        setTimeout(() => {{ status.textContent = ""; }}, 1800);
      }}
    }}

    function downloadAnalysisResult() {{
      if (!currentAnalysisData) {{
        return;
      }}
      const text = buildAnalysisText(currentAnalysisData);
      const blob = new Blob([text], {{ type: "text/plain;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "ai-opslog-analysis-log-" + (currentAnalysisData.log_id || "unknown") + ".txt";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }}

    function renderAnalysis(data) {{
      const result = data.analysis_result || {{}};
      if (result.error) {{
        return '<div class="ai-card-header"><h3>AI 分析失败</h3><span class="risk-pill risk-high">异常</span></div><div class="ai-card-body"><div class="ai-section full"><pre>' + escapeHtml(JSON.stringify(result, null, 2)) + "</pre></div></div>";
      }}
      const risk = result.risk_level || "unknown";
      return `
        <div class="ai-card-header">
          <div class="ai-title-block">
            <h3>日志 #${{escapeHtml(data.log_id)}} AI 分析结果</h3>
            <p class="ai-meta">参考 Runbook：${{escapeHtml(result.runbook_used || "-")}}</p>
          </div>
          <div class="ai-header-actions">
            <span class="risk-pill ${{riskClass(risk)}}">风险：${{escapeHtml(displayRiskLevel(risk))}}</span>
            <button class="ai-tool-button" type="button" onclick="copyAnalysisResult()">复制结果</button>
            <button class="ai-tool-button" type="button" onclick="downloadAnalysisResult()">导出文本</button>
            <span id="copy-status" class="copy-status"></span>
          </div>
        </div>
        <div class="ai-card-body">
          <div class="ai-section">
            <h4>问题摘要</h4>
            <p>${{escapeHtml(result.summary || "-")}}</p>
          </div>
          <div class="ai-section">
            <h4>关键报错</h4>
            <p>${{escapeHtml(result.key_error || "-")}}</p>
          </div>
          <div class="ai-section">
            <h4>参考 Runbook</h4>
            <p>${{escapeHtml(result.runbook_used || "-")}}</p>
          </div>
          <details class="ai-section full" open>
            <summary>关键证据</summary>
            ${{renderList(result.evidence)}}
          </details>
          <div class="ai-section full">
            <h4>根因假设</h4>
            <p>${{escapeHtml(result.root_cause_hypothesis || result.root_cause || result.possible_root_cause || "-")}}</p>
          </div>
          <details class="ai-section" open>
            <summary>命中关键词</summary>
            ${{renderList(result.matched_keywords)}}
          </details>
          <details class="ai-section">
            <summary>可能原因</summary>
            ${{renderList(result.possible_causes)}}
          </details>
          <details class="ai-section full">
            <summary>排查建议</summary>
            ${{renderList(result.troubleshooting_steps || result.recommendations)}}
          </details>
          <details class="ai-section full" open>
            <summary>验证方法</summary>
            ${{renderList(result.verification_methods)}}
          </details>
          <div class="ai-section full">
            <h4>操作风险提示</h4>
            <p>${{escapeHtml(result.operation_risk || "-")}}</p>
          </div>
          <details class="ai-section full">
            <summary>后续预防建议</summary>
            ${{renderList(result.prevention_suggestions)}}
          </details>
          <div class="ai-section full">
            <h4>补充说明</h4>
            <p>${{escapeHtml(result.notes || "-")}}</p>
          </div>
        </div>
      `;
    }}

    const activeAnalyses = new Set();

    async function analyzeLog(logId, button) {{
      if (activeAnalyses.has(logId)) {{
        return;
      }}
      activeAnalyses.add(logId);
      if (button) {{
        button.disabled = true;
        button.textContent = "分析中";
      }}
      const output = document.getElementById("ai-result");
      output.innerHTML = '<div class="ai-placeholder">正在分析日志 #' + escapeHtml(logId) + '...</div>';
      try {{
        const response = await fetch("/logs/" + logId + "/analyze", {{ method: "POST" }});
        if (!response.ok) {{
          throw new Error("HTTP " + response.status);
        }}
        const data = await response.json();
        currentAnalysisData = data;
        output.innerHTML = renderAnalysis(data);
      }} catch (error) {{
        currentAnalysisData = null;
        output.textContent = "AI 分析请求失败：" + error;
      }} finally {{
        activeAnalyses.delete(logId);
        if (button) {{
          button.disabled = false;
          button.textContent = "AI 分析";
        }}
      }}
    }}

    setInterval(() => {{
      if (!document.hidden && activeAnalyses.size === 0) {{
        window.location.reload();
      }}
    }}, 60000);
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


def _render_dashboard_rows(records: list[dict], keyword: str | None = None) -> str:
    if not records:
        return '<div class="empty">暂无日志记录</div>'

    rows = []
    for record in records:
        row_class = _log_row_class(record.get("log_level"))
        full_message = "" if record.get("message") is None else str(record.get("message"))
        message_html = _highlight_keyword(full_message, keyword)
        rows.append(
            f'<tr class="{row_class}">'
            f"<td>{_dashboard_value(record.get('id'))}</td>"
            f"<td>{_dashboard_value(format_datetime_for_display(record.get('timestamp') or record.get('created_at')))}</td>"
            f'<td class="col-source">{_dashboard_value(display_source(record.get("source")))}</td>'
            f'<td class="col-host">{_dashboard_value(record.get("host"))}</td>'
            f"<td>{_level_badge(record.get('log_level'))}</td>"
            f'<td class="message-cell" title="{_dashboard_value(full_message)}"><span class="message-text" onclick="this.classList.toggle(\'expanded\')">{message_html}</span></td>'
            f"<td>{_dashboard_value(_ai_status(record.get('AI_analysis_result')))}</td>"
            f'<td><button class="ai-button" onclick="analyzeLog({_dashboard_value(record.get("id"))}, this)">AI 分析</button></td>'
            "</tr>"
        )

    return (
        '<div class="table-wrap">'
        "<table>"
        "<thead>"
        "<tr>"
        '<th class="col-id">ID</th>'
        '<th class="col-time">时间</th>'
        '<th class="col-source">工具类型</th>'
        '<th class="col-host">主机</th>'
        '<th class="col-level">等级</th>'
        '<th class="col-message">日志内容</th>'
        '<th class="col-status">AI 结果</th>'
        '<th class="col-action">操作</th>'
        "</tr>"
        "</thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</div>"
    )


def _render_statistics_panel(
    stats: dict,
    prometheus_snapshot: dict,
    stats_hours: int,
    source: str | None,
    host: str | None,
    log_level: str | None,
    time_from: str | None,
    time_to: str | None,
    recent_hours: int | None,
    keyword: str | None,
    limit: int,
) -> str:
    period_label = "?? 24 ??" if stats_hours == 24 else "?? 7 ?"
    level_chart = _render_bar_chart(
        stats.get("level_counts") or {},
        display_log_level,
        _level_bar_class,
        filter_name="log_level",
        stats_hours=stats_hours,
    )
    source_chart = _render_bar_chart(
        stats.get("source_counts") or {},
        display_source,
        _source_bar_class,
        filter_name="source",
        stats_hours=stats_hours,
    )
    metrics_panel = _render_prometheus_metrics(prometheus_snapshot)
    hidden_inputs = _dashboard_hidden_inputs(
        source=source,
        host=host,
        log_level=log_level,
        time_from=time_from,
        time_to=time_to,
        recent_hours=recent_hours,
        keyword=keyword,
        limit=limit,
        page=1,
    )
    return f"""
      <div class="stats-toolbar">
        <div class="stats-summary">
          <span class="stats-total">{int(stats.get("total") or 0)}</span>
          <span class="stats-meta">??? ? {escape(period_label)}</span>
        </div>
        <form method="get" action="/dashboard/logs">
          {hidden_inputs}
          <label>?????
            <select name="stats_hours" onchange="this.form.submit()">
              <option value="24"{' selected' if stats_hours == 24 else ''}>?? 24 ??</option>
              <option value="168"{' selected' if stats_hours == 168 else ''}>?? 7 ?</option>
            </select>
          </label>
        </form>
      </div>
      <div class="stats-grid">
        <div class="stat-panel">
          <h3>??????</h3>
          {level_chart}
        </div>
        <div class="stat-panel">
          <h3>??????</h3>
          <div class="stat-panel-scroll">{source_chart}</div>
        </div>
        <div class="stat-panel">
          <h3>Prometheus ????</h3>
          {metrics_panel}
        </div>
      </div>
    """


def _render_prometheus_metrics(snapshot: dict) -> str:
    if not snapshot.get("configured"):
        return (
            '<div class="metric-muted">'
            "??? Prometheus??? <code>PROMETHEUS_BASE_URL</code> ??"
            "????????????"
            "</div>"
        )

    error = snapshot.get("error")
    error_block = f'<div class="notice error">Prometheus ???????{escape(str(error))}</div>' if error else ""
    cards = []
    for metric in snapshot.get("metrics") or []:
        value = _format_metric_value(metric.get("value"), metric.get("unit"))
        cards.append(
            '<div class="metric-card">'
            f'<p class="metric-name">{escape(str(metric.get("name") or "-"))}</p>'
            f'<p class="metric-value">{escape(value)}</p>'
            f'<p class="metric-desc">{escape(str(metric.get("description") or ""))}</p>'
            f'<div class="metric-query">{escape(str(metric.get("query") or ""))}</div>'
            "</div>"
        )

    if not cards:
        cards.append('<div class="metric-muted">?? Prometheus ?????</div>')

    return error_block + '<div class="metrics-grid">' + "".join(cards) + "</div>"


def _format_metric_value(value: object, unit: object) -> str:
    if value is None:
        return "-"

    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    unit_text = "" if unit is None else str(unit)
    if unit_text == "bytes":
        return _format_bytes(number)
    if number == 0:
        formatted = "0"
    elif abs(number) >= 100:
        formatted = f"{number:.0f}"
    elif abs(number) >= 10:
        formatted = f"{number:.1f}"
    else:
        formatted = f"{number:.3f}".rstrip("0").rstrip(".")
    return f"{formatted} {unit_text}".strip()


def _format_bytes(value: float) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    size = float(value)
    unit_index = 0
    while abs(size) >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{size:.0f} {units[unit_index]}"
    return f"{size:.1f} {units[unit_index]}"


def _render_bar_chart(
    counts: dict,
    label_func,
    css_class_func,
    filter_name: str | None = None,
    stats_hours: int = 24,
) -> str:
    if not counts:
        return '<div class="empty">暂无统计数据</div>'
    max_count = max((int(value or 0) for value in counts.values()), default=0)
    if max_count <= 0:
        return '<div class="empty">暂无统计数据</div>'

    rows = []
    total_count = sum(int(value or 0) for value in counts.values()) or 1
    for key, value in counts.items():
        count = int(value or 0)
        bar_percent = max(round((count / max_count) * 100), 2) if count else 0
        total_percent = round((count / total_count) * 100, 1) if count else 0
        label = label_func(key)
        title = f"{label}: {count} 条，占比 {total_percent}%"
        tag = "a" if filter_name else "div"
        href = ""
        if filter_name:
            params = {
                filter_name: str(key),
                "recent_hours": stats_hours,
                "stats_hours": stats_hours,
                "limit": 10,
                "page": 1,
            }
            href = f' href="/dashboard/logs?{urlencode(params)}"'
        rows.append(
            f'<{tag} class="bar-row"{href} title="{escape(title)}">'
            f'<span>{escape(label)}</span>'
            '<div class="bar-track">'
            f'<div class="bar-fill {escape(css_class_func(key))}" style="width: {bar_percent}%"></div>'
            '</div>'
            f'<strong>{count}</strong>'
            f'</{tag}>'
        )
    return "".join(rows)


def _level_bar_class(value: object) -> str:
    raw_value = "" if value is None else str(value).upper()
    return {
        "FATAL": "level-critical",
        "ERROR": "level-error",
        "WARN": "level-warn",
        "INFO": "level-info",
        "DEBUG": "level-debug",
    }.get(raw_value, "level-debug")


def _source_bar_class(value: object) -> str:
    raw_value = "" if value is None else str(value).lower()
    if raw_value.startswith("nginx"):
        return "source-nginx"
    return {
        "system": "source-system",
        "zabbix": "source-zabbix",
        "prometheus": "source-prometheus",
        "grafana": "source-grafana",
        "ansible": "source-ansible",
        "docker": "source-docker",
        "kubernetes": "source-kubernetes",
        "redis": "source-redis",
        "mysql": "source-mysql",
    }.get(raw_value, "source-system")


def _render_log_filter_form(
    source: str | None,
    host: str | None,
    log_level: str | None,
    time_from: str | None,
    time_to: str | None,
    recent_hours: int | None,
    keyword: str | None,
    limit: int,
    stats_hours: int,
) -> str:
    source_options = [
        "",
        "system",
        "zabbix",
        "prometheus",
        "grafana",
        "ansible",
        "docker",
        "kubernetes",
        "nginx_access",
        "nginx_error",
        "redis",
        "mysql",
    ]
    level_options = ["", "FATAL", "ERROR", "WARN", "INFO", "DEBUG"]
    recent_hour_options = ["", "1", "6", "12", "24", "72", "168"]
    return (
        '<form class="filters" method="get" action="/dashboard/logs">'
        f'<div><label>工具类型</label><select name="source">{_select_options(source_options, source, display_source)}</select></div>'
        f'<div><label>主机</label><input name="host" value="{_dashboard_value(host)}" placeholder="host / container"></div>'
        f'<div><label>日志等级</label><select name="log_level">{_select_options(level_options, log_level, display_log_level)}</select></div>'
        f'<div><label>最近 N 小时</label><select name="recent_hours">{_select_options(recent_hour_options, str(recent_hours) if recent_hours else None, _display_recent_hours)}</select></div>'
        f'<div><label>开始时间</label><input type="datetime-local" name="time_from" value="{_dashboard_value(_datetime_local_value(time_from))}"></div>'
        f'<div><label>结束时间</label><input type="datetime-local" name="time_to" value="{_dashboard_value(_datetime_local_value(time_to))}"></div>'
        f'<div class="wide filter-keyword"><label>消息关键字</label><input name="keyword" value="{_dashboard_value(keyword)}" placeholder="error / timeout / refused"></div>'
        f'<div class="filter-limit"><label>数量</label><input name="limit" value="{_dashboard_value(limit)}"></div>'
        '<input type="hidden" name="page" value="1">'
        f'<input type="hidden" name="stats_hours" value="{_dashboard_value(stats_hours)}">'
        '<div class="filter-actions"><button type="submit">筛选日志</button><a class="reset-link" href="/dashboard/logs">重置筛选</a></div>'
        "</form>"
    )


def _select_options(options: list[str], selected: str | None, display_func) -> str:
    rendered = []
    normalized_selected = selected or ""
    for option in options:
        label = "全部" if option == "" else display_func(option)
        selected_attr = " selected" if option == normalized_selected else ""
        rendered.append(f'<option value="{escape(option)}"{selected_attr}>{escape(label)}</option>')
    return "".join(rendered)


def _render_log_pagination(
    total_count: int,
    page: int,
    limit: int,
    source: str | None,
    host: str | None,
    log_level: str | None,
    time_from: str | None,
    time_to: str | None,
    recent_hours: int | None,
    keyword: str | None,
    stats_hours: int,
) -> str:
    if total_count <= 0:
        return '<div class="pager"><span>共 0 条日志</span></div>'

    total_pages = max((total_count + limit - 1) // limit, 1)
    current_page = min(max(page, 1), total_pages)
    start_index = (current_page - 1) * limit + 1
    end_index = min(current_page * limit, total_count)

    prev_link = '<span class="disabled">上一页</span>'
    next_link = '<span class="disabled">下一页</span>'
    if current_page > 1:
        prev_link = f'<a href="{_dashboard_page_url(current_page - 1, source, host, log_level, time_from, time_to, recent_hours, keyword, limit, stats_hours)}">上一页</a>'
    if current_page < total_pages:
        next_link = f'<a href="{_dashboard_page_url(current_page + 1, source, host, log_level, time_from, time_to, recent_hours, keyword, limit, stats_hours)}">下一页</a>'

    return (
        '<div class="pager">'
        f'<span class="pager-summary">共 {total_count} 条日志，当前第 {current_page}/{total_pages} 页，显示 {start_index}-{end_index}</span>'
        f'<div class="pager-controls">{prev_link}{next_link}{_render_page_jump_form(current_page, source, host, log_level, time_from, time_to, recent_hours, keyword, limit, stats_hours)}</div>'
        "</div>"
    )


def _render_page_jump_form(
    current_page: int,
    source: str | None,
    host: str | None,
    log_level: str | None,
    time_from: str | None,
    time_to: str | None,
    recent_hours: int | None,
    keyword: str | None,
    limit: int,
    stats_hours: int,
) -> str:
    hidden_inputs = _dashboard_hidden_inputs(
        source=source,
        host=host,
        log_level=log_level,
        time_from=time_from,
        time_to=time_to,
        recent_hours=recent_hours,
        keyword=keyword,
        limit=limit,
        page=None,
    )
    return (
        '<form method="get" action="/dashboard/logs">'
        f"{hidden_inputs}"
        f'<input type="hidden" name="stats_hours" value="{_dashboard_value(stats_hours)}">'
        f'<label>跳页 <input type="number" min="1" name="page" value="{_dashboard_value(current_page)}"></label>'
        '<button type="submit">跳转</button>'
        "</form>"
    )


def _dashboard_page_url(
    page: int,
    source: str | None,
    host: str | None,
    log_level: str | None,
    time_from: str | None,
    time_to: str | None,
    recent_hours: int | None,
    keyword: str | None,
    limit: int,
    stats_hours: int,
) -> str:
    params = {
        "source": _normalize_history_filter(source),
        "host": _normalize_history_filter(host),
        "log_level": _normalize_history_filter(log_level),
        "time_from": _normalize_history_filter(time_from),
        "time_to": _normalize_history_filter(time_to),
        "recent_hours": recent_hours if recent_hours and recent_hours > 0 else None,
        "keyword": _normalize_history_filter(keyword),
        "limit": limit,
        "page": max(page, 1),
        "stats_hours": stats_hours,
    }
    compact_params = {key: value for key, value in params.items() if value not in (None, "")}
    return "/dashboard/logs?" + urlencode(compact_params)


def _dashboard_hidden_inputs(
    source: str | None,
    host: str | None,
    log_level: str | None,
    time_from: str | None,
    time_to: str | None,
    recent_hours: int | None,
    keyword: str | None,
    limit: int,
    page: int | None,
) -> str:
    params = {
        "source": _normalize_history_filter(source),
        "host": _normalize_history_filter(host),
        "log_level": _normalize_history_filter(log_level),
        "time_from": _normalize_history_filter(time_from),
        "time_to": _normalize_history_filter(time_to),
        "recent_hours": recent_hours if recent_hours and recent_hours > 0 else None,
        "keyword": _normalize_history_filter(keyword),
        "limit": limit,
        "page": max(page, 1) if page is not None else None,
    }
    inputs = []
    for key, value in params.items():
        if value not in (None, ""):
            inputs.append(f'<input type="hidden" name="{escape(key)}" value="{_dashboard_value(value)}">')
    return "".join(inputs)


def _normalize_dashboard_limit(limit: object) -> int:
    parsed_limit = _parse_optional_positive_int(limit, default=10) or 10
    return min(max(parsed_limit, 1), 200)


def _parse_optional_positive_int(value: object, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed <= 0:
        return default
    return parsed


def _normalize_stats_hours(value: object) -> int:
    parsed_value = _parse_optional_positive_int(value, default=24) or 24
    return 168 if parsed_value == 168 else 24


def _display_recent_hours(value: object) -> str:
    if value is None or value == "":
        return "全部"
    return f"最近 {value} 小时"


def _datetime_local_value(value: str | None) -> str:
    normalized = _normalize_history_filter(value)
    if not normalized:
        return ""
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return normalized[:16]
    return parsed.strftime("%Y-%m-%dT%H:%M")


def _effective_time_from(time_from: str | None, recent_hours: int | None) -> str | None:
    normalized_time_from = _normalize_history_filter(time_from)
    if normalized_time_from:
        return normalized_time_from
    if recent_hours is None or recent_hours <= 0:
        return None
    return (datetime.now(timezone.utc) - timedelta(hours=recent_hours)).isoformat()


def _dashboard_value(value: object) -> str:
    if value is None:
        return ""
    return escape(str(value))


def _log_row_class(value: object) -> str:
    raw_value = "" if value is None else str(value).upper()
    if raw_value in {"FATAL", "ERROR"}:
        return "row-risk-high"
    if raw_value == "WARN":
        return "row-risk-medium"
    return ""


def _highlight_keyword(value: object, keyword: str | None) -> str:
    text = "" if value is None else str(value)
    normalized_keyword = _normalize_history_filter(keyword)
    if not normalized_keyword:
        return escape(text)

    pattern = re.compile(re.escape(normalized_keyword), re.IGNORECASE)
    parts = []
    last_index = 0
    for match in pattern.finditer(text):
        parts.append(escape(text[last_index : match.start()]))
        parts.append(f"<mark>{escape(match.group(0))}</mark>")
        last_index = match.end()
    parts.append(escape(text[last_index:]))
    return "".join(parts)


def format_datetime_for_display(value: object) -> str:
    if value is None or value == "":
        return "-"

    raw_value = str(value)
    try:
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return raw_value

    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def display_log_type(value: object) -> str:
    mapping = {
        "docker_log": "Docker 日志",
        "nginx_error": "Nginx 错误日志",
        "nginx_access": "Nginx 访问日志",
        "alertmanager_alert": "Alertmanager 告警",
    }
    return _mapped_display_value(value, mapping)


def display_risk_level(value: object) -> str:
    mapping = {
        "critical": "严重",
        "high": "高",
        "medium": "中",
        "low": "低",
        "unknown": "未知",
    }
    return _mapped_display_value(value, mapping)


def display_webhook_status(value: object) -> str:
    mapping = {
        "firing": "触发中",
        "resolved": "已恢复",
        "mixed": "混合状态",
    }
    return _mapped_display_value(value, mapping)


def display_service_name(value: object) -> str:
    mapping = {
        "HighCPUUsage": "CPU 使用率过高",
        "RedisDown": "Redis 服务异常",
        "NginxDown": "Nginx 服务异常",
        "DiskSpaceLow": "磁盘空间不足",
    }
    return _mapped_display_value(value, mapping)


def display_report_status(value: object) -> str:
    if value is None or value == "":
        return "-"
    return "已生成"


def display_source(value: object) -> str:
    mapping = {
        "system": "系统日志",
        "zabbix": "Zabbix",
        "prometheus": "Prometheus",
        "grafana": "Grafana",
        "ansible": "Ansible",
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "nginx_access": "Nginx 访问日志",
        "nginx_error": "Nginx 错误日志",
        "redis": "Redis",
        "mysql": "MySQL",
    }
    return _mapped_display_value(value, mapping)


def display_log_level(value: object) -> str:
    mapping = {
        "FATAL": "严重",
        "ERROR": "错误",
        "WARN": "警告",
        "INFO": "信息",
        "DEBUG": "调试",
    }
    return _mapped_display_value(value, mapping)


def _mapped_display_value(value: object, mapping: dict[str, str]) -> str:
    if value is None or value == "":
        return "-"
    raw_value = str(value)
    return mapping.get(raw_value, raw_value)


def _risk_badge(value: object) -> str:
    raw_value = "" if value is None else str(value)
    display_value = display_risk_level(raw_value)
    css_key = raw_value.lower() if raw_value else "unknown"
    css_class = f"badge badge-{escape(css_key)}"
    return f'<span class="{css_class}">{escape(display_value)}</span>'


def _level_badge(value: object) -> str:
    raw_value = "" if value is None else str(value).upper()
    display_value = display_log_level(raw_value)
    css_key = {
        "FATAL": "critical",
        "ERROR": "error",
        "WARN": "warn",
        "INFO": "info",
        "DEBUG": "debug",
    }.get(raw_value, "unknown")
    return f'<span class="badge badge-{css_key}">{escape(display_value)}</span>'


def _short_message(value: object, max_length: int = 180) -> str:
    if value is None:
        return "-"
    text = str(value).replace("\n", " ")
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def _ai_status(value: object) -> str:
    if value is None or value == "":
        return "待分析"
    return "已分析"


@app.get("/records/{record_id}", response_class=HTMLResponse)
def record_detail_page(record_id: int) -> HTMLResponse:
    try:
        record = get_analysis_record_by_id(record_id)
    except Exception as exc:
        return HTMLResponse(
            content=_render_record_error_page(
                title="历史记录查询失败",
                message=f"数据库查询失败：{exc}",
                status_code=500,
            ),
            status_code=500,
        )

    if record is None:
        return HTMLResponse(
            content=_render_record_error_page(
                title="历史记录不存在",
                message=f"未找到 ID 为 {record_id} 的历史记录。",
                status_code=404,
            ),
            status_code=404,
        )

    html = f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI-OpsLog 历史记录详情</title>
  {_record_page_style()}
</head>
<body>
  <main class="page">
    <header>
      <h1>AI-OpsLog 历史记录详情</h1>
      <p class="subtitle">查看 SQLite 中保存的单条分析元数据</p>
    </header>

    <section>
      <h2>基本信息</h2>
      <dl class="detail-grid">
        {_record_field("ID", record.get("id"))}
        {_record_field("创建时间", format_datetime_for_display(record.get("created_at")))}
        {_record_field("来源", record.get("source"))}
        {_record_display_field("服务名", record.get("service_name"), display_service_name)}
        {_record_field("环境", record.get("env"))}
        {_record_display_field("类型", record.get("log_type"), display_log_type)}
      </dl>
    </section>

    <section>
      <h2>风险信息</h2>
      <dl class="detail-grid">
        {_record_display_field("规则风险等级", record.get("rule_severity"), display_risk_level)}
        {_record_display_field("AI 风险等级", record.get("ai_risk_level"), display_risk_level)}
      </dl>
    </section>

    <section>
      <h2>分析信息</h2>
      <dl class="detail-grid">
        {_record_field("兼容字段 report_path", record.get("report_path"))}
        {_record_field("接口消息", record.get("message"))}
      </dl>
    </section>

    <section>
      <h2>告警信息</h2>
      <dl class="detail-grid">
        {_record_field("告警数量", record.get("alert_count"))}
        {_record_display_field("告警状态", record.get("webhook_status"), display_webhook_status)}
      </dl>
    </section>

    <section>
      <h2>相关入口</h2>
      <div class="links">
        <a href="/">返回首页</a>
        <a href="/history/{_record_detail_value(record.get("id"))}">查看 JSON API：/history/{_record_detail_value(record.get("id"))}</a>
      </div>
    </section>
  </main>
</body>
</html>
"""
    return HTMLResponse(content=html)


def _render_record_error_page(title: str, message: str, status_code: int) -> str:
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI-OpsLog {escape(title)}</title>
  {_record_page_style()}
</head>
<body>
  <main class="page">
    <header>
      <h1>AI-OpsLog 历史记录详情</h1>
      <p class="subtitle">HTTP {status_code}</p>
    </header>
    <section>
      <div class="notice error">
        <strong>{escape(title)}</strong>
        <p>{escape(message)}</p>
      </div>
      <div class="links">
        <a href="/">返回首页</a>
      </div>
    </section>
  </main>
</body>
</html>
"""


def _record_field(label: str, value: object) -> str:
    return (
        f"<dt>{escape(label)}</dt>"
        f"<dd>{_record_detail_value(value)}</dd>"
    )


def _record_display_field(label: str, value: object, display_func) -> str:
    return (
        f"<dt>{escape(label)}</dt>"
        f"<dd>{_record_display_with_raw(value, display_func)}</dd>"
    )


def _record_detail_value(value: object) -> str:
    if value is None or value == "":
        return "-"
    return escape(str(value))


def _record_display_with_raw(value: object, display_func) -> str:
    if value is None or value == "":
        return "-"

    raw_value = str(value)
    display_value = display_func(raw_value)
    if display_value == raw_value:
        return escape(raw_value)
    return f"{escape(display_value)}（{escape(raw_value)}）"


def _record_page_style() -> str:
    return """
  <style>
    body {
      margin: 0;
      background: #f6f8fa;
      color: #1f2937;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      line-height: 1.5;
    }
    .page {
      max-width: 900px;
      margin: 0 auto;
      padding: 32px 20px 40px;
    }
    header {
      margin-bottom: 24px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: 30px;
      font-weight: 700;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 20px;
    }
    section {
      margin-top: 24px;
    }
    .subtitle {
      margin: 0;
      color: #4b5563;
      font-size: 15px;
    }
    .detail-grid {
      display: grid;
      grid-template-columns: 180px minmax(0, 1fr);
      margin: 0;
      background: #ffffff;
      border: 1px solid #d8dee4;
      border-radius: 8px;
      overflow: hidden;
    }
    dt, dd {
      margin: 0;
      padding: 11px 14px;
      border-bottom: 1px solid #e5e7eb;
      font-size: 14px;
    }
    dt {
      background: #f3f4f6;
      color: #374151;
      font-weight: 600;
    }
    dd {
      overflow-wrap: anywhere;
    }
    dt:nth-last-of-type(1), dd:nth-last-of-type(1) {
      border-bottom: 0;
    }
    .notice {
      padding: 16px;
      background: #ffffff;
      border: 1px solid #d8dee4;
      border-radius: 8px;
      color: #4b5563;
    }
    .error {
      border-color: #f1b7b7;
      background: #fff5f5;
      color: #991b1b;
    }
    .links {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 8px;
    }
    .links a {
      display: inline-block;
      padding: 6px 10px;
      border: 1px solid #d8dee4;
      border-radius: 6px;
      background: #ffffff;
      color: #1f2937;
      text-decoration: none;
      font-size: 13px;
      font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono", monospace;
    }
  </style>
"""


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "ai-opslog",
    }


@app.post("/analyze")
def analyze(request: AnalyzeRequest) -> dict:
    return analyze_log(request.log_type, request.log_text)


@app.post("/analyze/ai")
def analyze_ai(request: AnalyzeRequest) -> dict:
    return analyze_log_with_ai(request.log_type, request.log_text)


@app.get("/config/check")
def config_check() -> dict:
    return {
        "dashscope_api_key_configured": bool(os.getenv("DASHSCOPE_API_KEY")),
        "dashscope_base_url": os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        "qwen_model": os.getenv("QWEN_MODEL", "qwen-plus"),
        "alertmanager_webhook_token_configured": bool(
            os.getenv("ALERTMANAGER_WEBHOOK_TOKEN", "").strip()
        ),
        "prometheus_base_url_configured": bool(os.getenv("PROMETHEUS_BASE_URL", "").strip()),
    }


@app.get("/qwen/test")
def qwen_test() -> dict:
    return test_qwen_connection()


@app.get("/metrics/prometheus")
def prometheus_metrics() -> dict:
    return get_prometheus_snapshot()


@app.get("/history/recent")
def history_recent(
    limit: int = 10,
    log_type: str | None = None,
    source: str | None = None,
    service_name: str | None = None,
    env: str | None = None,
    rule_severity: str | None = None,
    ai_risk_level: str | None = None,
    webhook_status: str | None = None,
) -> dict:
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be greater than 0")
    if limit > 100:
        raise HTTPException(status_code=400, detail="limit must be less than or equal to 100")

    try:
        records = get_recent_analysis_records(
            limit=limit,
            log_type=_normalize_history_filter(log_type),
            source=_normalize_history_filter(source),
            service_name=_normalize_history_filter(service_name),
            env=_normalize_history_filter(env),
            rule_severity=_normalize_history_filter(rule_severity),
            ai_risk_level=_normalize_history_filter(ai_risk_level),
            webhook_status=_normalize_history_filter(webhook_status),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to query history records: {exc}") from exc

    return {
        "records": records,
        "count": len(records),
    }


def _normalize_history_filter(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


@app.get("/history/{record_id}")
def history_record(record_id: int) -> dict:
    try:
        record = get_analysis_record_by_id(record_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to query history record: {exc}") from exc

    if record is None:
        raise HTTPException(status_code=404, detail="history record not found")

    return {"record": record}


@app.post("/logs/ingest")
def logs_ingest(request: IngestLogRequest) -> dict:
    return ingest_log(request)


@app.post("/logs/{log_id}/analyze")
def analyze_unified_log(log_id: int) -> dict:
    record = get_log_record_by_id(log_id)
    if record is None:
        raise HTTPException(status_code=404, detail="log record not found")

    result = analyze_unified_log_record(record)
    return {
        "log_id": log_id,
        "analysis_result": result,
    }


@app.post("/alerts/alertmanager")
def alerts_alertmanager(
    payload: dict,
    x_alertmanager_token: str | None = Header(default=None, alias="X-Alertmanager-Token"),
) -> dict:
    if not is_alertmanager_token_valid(x_alertmanager_token):
        return JSONResponse(
            status_code=401,
            content={"error": "invalid alertmanager webhook token"},
        )

    alerts = payload.get("alerts") if isinstance(payload, dict) else None
    if not alerts:
        return JSONResponse(
            status_code=400,
            content={"error": "no alerts found in alertmanager webhook"},
        )
    return ingest_alertmanager_webhook(payload)
