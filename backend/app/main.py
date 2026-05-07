import os
from datetime import datetime
from html import escape
from pathlib import Path

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
from app.services.qwen_client import test_qwen_connection
from app.services.report_service import (
    check_reports_dir,
    generate_ai_markdown_report,
    generate_markdown_report,
    save_report_to_file,
)
from app.storage.history_store import (
    get_analysis_record_by_id,
    get_recent_analysis_records,
    init_db,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)

app = FastAPI(title="AI-OpsLog", version="0.1.0")


@app.on_event("startup")
def startup_init_db() -> None:
    try:
        init_db()
    except Exception as exc:
        print(f"failed to initialize AI-OpsLog SQLite database: {exc}")
        raise


@app.get("/", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    error_message = ""
    try:
        records = get_recent_analysis_records(limit=10)
    except Exception as exc:
        records = []
        error_message = f"历史记录查询失败：{exc}"

    table_body = _render_dashboard_rows(records)
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
      background: #f6f8fa;
      color: #1f2937;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      line-height: 1.5;
    }}
    .page {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 32px 20px 40px;
    }}
    header {{
      margin-bottom: 24px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 30px;
      font-weight: 700;
    }}
    .subtitle {{
      margin: 0;
      color: #4b5563;
      font-size: 15px;
    }}
    section {{
      margin-top: 24px;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 20px;
    }}
    .table-wrap {{
      overflow-x: auto;
      background: #ffffff;
      border: 1px solid #d8dee4;
      border-radius: 8px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      min-width: 1180px;
    }}
    th, td {{
      padding: 10px 12px;
      border-bottom: 1px solid #e5e7eb;
      text-align: left;
      vertical-align: top;
      font-size: 14px;
      word-break: break-word;
      overflow-wrap: anywhere;
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
    .col-env {{
      width: 78px;
    }}
    .col-risk {{
      width: 88px;
    }}
    .col-status {{
      width: 90px;
    }}
    .col-report {{
      width: 78px;
    }}
    .col-action {{
      width: 92px;
    }}
    .badge {{
      display: inline-block;
      min-width: 28px;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 12px;
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
  </style>
</head>
<body>
  <main class="page">
    <header>
      <h1>AI-OpsLog 运维日志分析助手</h1>
      <p class="subtitle">基于规则分析与通义千问的运维日志 / 告警辅助分析 Demo</p>
    </header>

    <section>
      <h2>最近分析记录</h2>
      {error_block}
      {table_body}
    </section>

    <section>
      <h2>API Endpoints</h2>
      <div class="links">
        <a href="/history/recent">GET /history/recent</a>
        <span class="endpoint">GET /history/{{id}}</span>
        <span class="endpoint">POST /logs/ingest</span>
        <span class="endpoint">POST /alerts/alertmanager</span>
        <a href="/health">GET /health</a>
      </div>
    </section>
  </main>
</body>
</html>
"""
    return HTMLResponse(content=html)


def _render_dashboard_rows(records: list[dict]) -> str:
    if not records:
        return '<div class="empty">暂无历史记录</div>'

    rows = []
    for record in records:
        rows.append(
            "<tr>"
            f"<td>{_dashboard_value(record.get('id'))}</td>"
            f"<td>{_dashboard_value(format_datetime_for_display(record.get('created_at')))}</td>"
            f"<td>{_dashboard_value(record.get('source'))}</td>"
            f"<td>{_dashboard_value(display_service_name(record.get('service_name')))}</td>"
            f"<td>{_dashboard_value(record.get('env'))}</td>"
            f"<td>{_dashboard_value(display_log_type(record.get('log_type')))}</td>"
            f"<td>{_risk_badge(record.get('rule_severity'))}</td>"
            f"<td>{_risk_badge(record.get('ai_risk_level'))}</td>"
            f"<td>{_dashboard_value(display_webhook_status(record.get('webhook_status')))}</td>"
            f"<td>{_dashboard_value(display_report_status(record.get('report_path')))}</td>"
            f'<td><a href="/records/{_dashboard_value(record.get("id"))}">查看详情</a></td>'
            "</tr>"
        )

    return (
        '<div class="table-wrap">'
        "<table>"
        "<thead>"
        "<tr>"
        '<th class="col-id">ID</th>'
        '<th class="col-time">时间</th>'
        "<th>来源</th>"
        "<th>服务</th>"
        '<th class="col-env">环境</th>'
        "<th>类型</th>"
        '<th class="col-risk">规则风险</th>'
        '<th class="col-risk">AI 风险</th>'
        '<th class="col-status">告警状态</th>'
        '<th class="col-report">报告</th>'
        '<th class="col-action">操作</th>'
        "</tr>"
        "</thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</div>"
    )


def _dashboard_value(value: object) -> str:
    if value is None:
        return ""
    return escape(str(value))


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
      <h2>报告信息</h2>
      <dl class="detail-grid">
        {_record_field("报告路径 (report_path)", record.get("report_path"))}
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


@app.post("/analyze/report")
def analyze_report(request: AnalyzeRequest) -> dict:
    result = analyze_log(request.log_type, request.log_text)
    if "error" in result and "log_type" not in result:
        return result

    return {
        "log_type": result.get("log_type", request.log_type),
        "severity": result.get("severity", "unknown"),
        "markdown_report": generate_markdown_report(result),
    }


@app.post("/analyze/ai")
def analyze_ai(request: AnalyzeRequest) -> dict:
    return analyze_log_with_ai(request.log_type, request.log_text)


@app.post("/analyze/ai/report")
def analyze_ai_report(request: AnalyzeRequest) -> dict:
    result = analyze_log_with_ai(request.log_type, request.log_text)
    rule_result = result.get("rule_result") or {}
    ai_result = result.get("ai_result") or {}

    return {
        "log_type": result.get("log_type", request.log_type),
        "rule_severity": rule_result.get("severity", "unknown"),
        "ai_risk_level": ai_result.get("risk_level", "unknown"),
        "markdown_report": generate_ai_markdown_report(result),
    }


@app.post("/analyze/ai/report/save")
def analyze_ai_report_save(request: AnalyzeRequest) -> dict:
    result = analyze_log_with_ai(request.log_type, request.log_text)
    rule_result = result.get("rule_result") or {}
    ai_result = result.get("ai_result") or {}
    markdown_report = generate_ai_markdown_report(result)
    report_path = save_report_to_file(markdown_report, log_type=result.get("log_type", request.log_type))

    response = {
        "log_type": result.get("log_type", request.log_type),
        "rule_severity": rule_result.get("severity", "unknown"),
        "ai_risk_level": ai_result.get("risk_level", "unknown"),
        "report_path": report_path,
        "markdown_report": markdown_report,
    }

    if report_path.startswith("failed to save report:"):
        response["error"] = "failed to save report"

    return response


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
    }


@app.get("/qwen/test")
def qwen_test() -> dict:
    return test_qwen_connection()


@app.get("/reports/check")
def reports_check() -> dict:
    return check_reports_dir()


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
