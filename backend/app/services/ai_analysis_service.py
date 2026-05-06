from app.prompts.log_analysis_prompt import build_log_analysis_prompt
from app.services.analyze_service import analyze_log
from app.services.qwen_client import call_qwen_model


def analyze_log_with_ai(log_type: str, log_text: str) -> dict:
    parsed_result = analyze_log(log_type, log_text)

    if "error" in parsed_result and "log_type" not in parsed_result:
        return {
            "log_type": log_type,
            "error": parsed_result.get("error"),
            "rule_result": parsed_result,
            "ai_result": None,
        }

    try:
        prompt = build_log_analysis_prompt(log_type, log_text, parsed_result)
        ai_result = call_qwen_model(prompt)

        return {
            "log_type": parsed_result.get("log_type", log_type),
            "rule_result": parsed_result,
            "ai_result": ai_result,
        }
    except Exception as exc:
        return {
            "log_type": parsed_result.get("log_type", log_type),
            "rule_result": parsed_result,
            "ai_result": {
                "error": "AI analysis failed",
                "detail": str(exc),
            },
        }
