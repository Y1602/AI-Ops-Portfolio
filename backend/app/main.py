from fastapi import FastAPI

from app.schemas.request_schema import AnalyzeRequest
from app.services.analyze_service import analyze_log

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

