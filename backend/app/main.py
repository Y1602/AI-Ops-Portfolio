import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
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
