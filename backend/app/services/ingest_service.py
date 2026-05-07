from app.schemas.request_schema import IngestLogRequest
from app.services.ai_analysis_service import analyze_log_with_ai
from app.services.report_service import generate_ai_markdown_report, save_report_to_file
from app.storage.history_store import save_analysis_record


def ingest_log(request_data: IngestLogRequest, save_history: bool = True) -> dict:
    try:
        source = request_data.source
        service_name = request_data.service_name
        log_type = request_data.log_type
        env = request_data.env
        log_text = request_data.log_text

        result = analyze_log_with_ai(log_type, log_text)
        if result.get("error"):
            return {
                "source": source,
                "service_name": service_name,
                "env": env,
                "log_type": log_type,
                "error": result.get("error"),
                "rule_result": result.get("rule_result"),
            }

        metadata = {
            "source": source,
            "service_name": service_name,
            "env": env,
        }
        markdown_report = generate_ai_markdown_report(result, metadata=metadata)
        report_path = save_report_to_file(
            markdown_report,
            log_type=log_type,
            source=source,
            service_name=service_name,
        )

        rule_result = result.get("rule_result") or {}
        ai_result = result.get("ai_result") or {}
        response = {
            "source": source,
            "service_name": service_name,
            "env": env,
            "log_type": log_type,
            "rule_severity": rule_result.get("severity", "unknown"),
            "ai_risk_level": ai_result.get("risk_level", "unknown"),
            "report_path": report_path,
            "message": "log ingested and report generated",
        }

        if report_path.startswith("failed to save report:"):
            response["error"] = "failed to save report"
        elif save_history:
            try:
                save_analysis_record(
                    {
                        "source": response.get("source"),
                        "service_name": response.get("service_name"),
                        "env": response.get("env"),
                        "log_type": response.get("log_type"),
                        "rule_severity": response.get("rule_severity"),
                        "ai_risk_level": response.get("ai_risk_level"),
                        "report_path": response.get("report_path"),
                        "message": response.get("message"),
                        "alert_count": None,
                        "webhook_status": None,
                    }
                )
            except Exception as exc:
                print(f"failed to save analysis history record: {exc}")

        return response
    except Exception as exc:
        return {
            "error": "log ingest failed",
            "detail": str(exc),
        }
