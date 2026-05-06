from fastapi import FastAPI

from app.schemas.request_schema import AnalyzeRequest
from app.services.analyze_service import analyze_log
from app.services.report_service import generate_markdown_report

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
