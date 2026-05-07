import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.schemas.request_schema import AnalyzeRequest, IngestLogRequest
from app.services.ai_analysis_service import analyze_log_with_ai
from app.services.analyze_service import analyze_log
from app.services.alertmanager_service import ingest_alertmanager_webhook
from app.services.ingest_service import ingest_log
from app.services.qwen_client import test_qwen_connection
from app.services.report_service import (
    check_reports_dir,
    generate_ai_markdown_report,
    generate_markdown_report,
    save_report_to_file,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)

app = FastAPI(title="AI-OpsLog", version="0.1.0")


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
    }


@app.get("/qwen/test")
def qwen_test() -> dict:
    return test_qwen_connection()


@app.get("/reports/check")
def reports_check() -> dict:
    return check_reports_dir()


@app.post("/logs/ingest")
def logs_ingest(request: IngestLogRequest) -> dict:
    return ingest_log(request)


@app.post("/alerts/alertmanager")
def alerts_alertmanager(payload: dict) -> dict:
    alerts = payload.get("alerts") if isinstance(payload, dict) else None
    if not alerts:
        return JSONResponse(
            status_code=400,
            content={"error": "no alerts found in alertmanager webhook"},
        )
    return ingest_alertmanager_webhook(payload)
