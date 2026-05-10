import json
import re
from typing import Any

from app.services.qwen_client import call_qwen_model


ERROR_PATTERNS = [
    r"\b(fatal|panic|critical|crit|error|err|exception|failed|failure|timeout|refused|denied|unavailable|down)\b",
    r"\b(5\d{2}|4\d{2})\b",
    r"\b(OOMKilled|CrashLoopBackOff|ImagePullBackOff|BackOff|Evicted)\b",
    r"\b(no space left|out of memory|address already in use|connection reset|connection refused)\b",
]


def analyze_unified_log_record(record: dict[str, Any]) -> dict[str, Any]:
    log_summary = extract_log_summary(record)
    prompt = _build_prompt(record, log_summary)
    ai_result = call_qwen_model(prompt)

    if not isinstance(ai_result, dict):
        return {
            "summary": log_summary["summary"],
            "key_error": log_summary["key_error"],
            "risk_level": _fallback_risk_level(record),
            "root_cause": "AI response is not a JSON object.",
            "possible_causes": [],
            "troubleshooting_steps": ["Check Qwen response format and service configuration."],
            "notes": str(ai_result),
        }

    ai_result.setdefault("summary", log_summary["summary"])
    ai_result.setdefault("key_error", log_summary["key_error"])
    ai_result.setdefault("matched_keywords", log_summary["matched_keywords"])
    ai_result.setdefault("source", record.get("source"))
    ai_result.setdefault("host", record.get("host"))
    ai_result.setdefault("log_level", record.get("log_level"))
    return ai_result


def extract_log_summary(record: dict[str, Any]) -> dict[str, Any]:
    message = str(record.get("message") or "").strip()
    compact_message = _compact_whitespace(message)
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    candidate_lines = [line for line in lines if _contains_error_signal(line)]
    key_error = candidate_lines[0] if candidate_lines else compact_message
    key_error = _truncate(key_error, 500)
    matched_keywords = _extract_matched_keywords(message)

    source = record.get("source") or "unknown"
    host = record.get("host") or "unknown"
    level = record.get("log_level") or "INFO"
    summary = f"{source} on {host} reported {level}: {_truncate(key_error, 180)}"

    return {
        "summary": summary,
        "key_error": key_error,
        "matched_keywords": matched_keywords,
        "context": _truncate(compact_message, 1600),
    }


def _build_prompt(record: dict[str, Any], log_summary: dict[str, Any]) -> str:
    payload = {
        "timestamp": record.get("timestamp"),
        "source": record.get("source"),
        "host": record.get("host"),
        "log_level": record.get("log_level"),
        "created_at": record.get("created_at"),
        "log_summary": log_summary,
        "raw_message": _truncate(str(record.get("message") or ""), 3000),
    }

    return f"""
请作为运维/SRE 日志分析助手，只返回严格 JSON，不要返回 Markdown，不要输出额外解释。

请基于下面的单条日志和已提取的关键报错摘要进行按需分析。不要执行系统命令，不要假设已经执行过任何操作。

日志数据：
{json.dumps(payload, ensure_ascii=False, indent=2)}

返回 JSON 结构必须包含：
{{
  "summary": "一句话说明日志含义",
  "key_error": "最关键的报错片段",
  "root_cause": "最可能的问题原因",
  "risk_level": "critical/high/medium/low/unknown",
  "possible_causes": ["可能原因1", "可能原因2"],
  "troubleshooting_steps": ["排查建议1", "排查建议2"],
  "notes": "必要的补充说明"
}}
""".strip()


def _contains_error_signal(line: str) -> bool:
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in ERROR_PATTERNS)


def _extract_matched_keywords(message: str) -> list[str]:
    keywords = set()
    for pattern in ERROR_PATTERNS:
        for match in re.findall(pattern, message, re.IGNORECASE):
            if isinstance(match, tuple):
                keywords.update(item.lower() for item in match if item)
            else:
                keywords.add(str(match).lower())
    return sorted(keywords)[:12]


def _fallback_risk_level(record: dict[str, Any]) -> str:
    level = str(record.get("log_level") or "").upper()
    if level == "FATAL":
        return "critical"
    if level == "ERROR":
        return "high"
    if level == "WARN":
        return "medium"
    if level in {"INFO", "DEBUG"}:
        return "low"
    return "unknown"


def _compact_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."
