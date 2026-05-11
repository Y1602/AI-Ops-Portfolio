from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.services.qwen_client import call_qwen_model


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNBOOK_DIR = PROJECT_ROOT / "docs" / "runbooks"

ERROR_PATTERNS = [
    r"\b(fatal|panic|critical|crit|error|err|exception|failed|failure|timeout|refused|denied|unavailable|down)\b",
    r"\b(5\d{2}|4\d{2})\b",
    r"\b(OOMKilled|CrashLoopBackOff|ImagePullBackOff|BackOff|Evicted)\b",
    r"\b(no space left|out of memory|address already in use|connection reset|connection refused)\b",
]


def analyze_unified_log_record(record: dict[str, Any]) -> dict[str, Any]:
    log_summary = extract_log_summary(record)
    runbook = select_runbook(record, log_summary)
    prompt = _build_prompt(record, log_summary, runbook)
    ai_result = call_qwen_model(prompt)

    if not isinstance(ai_result, dict):
        return {
            "summary": log_summary["summary"],
            "key_error": log_summary["key_error"],
            "risk_level": _fallback_risk_level(record),
            "root_cause": "AI response is not a JSON object.",
            "root_cause_hypothesis": "AI response is not a JSON object.",
            "evidence": _fallback_evidence(record, log_summary),
            "possible_causes": [],
            "troubleshooting_steps": ["Check Qwen response format and service configuration."],
            "verification_methods": ["Confirm Qwen API configuration and response format."],
            "operation_risk": "Do not execute remediation commands based on this failed analysis.",
            "prevention_suggestions": [],
            "runbook_used": runbook.get("name"),
            "notes": str(ai_result),
        }

    ai_result.setdefault("summary", log_summary["summary"])
    ai_result.setdefault("key_error", log_summary["key_error"])
    ai_result.setdefault("matched_keywords", log_summary["matched_keywords"])
    ai_result.setdefault("evidence", _fallback_evidence(record, log_summary))
    ai_result.setdefault(
        "root_cause_hypothesis",
        ai_result.get("root_cause") or ai_result.get("possible_root_cause") or "当前证据不足，不能确认唯一根因。",
    )
    ai_result.setdefault("verification_methods", _fallback_verification_methods(record))
    ai_result.setdefault("operation_risk", _fallback_operation_risk(record))
    ai_result.setdefault("prevention_suggestions", [])
    ai_result.setdefault("runbook_used", runbook.get("name"))
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


def select_runbook(record: dict[str, Any], log_summary: dict[str, Any]) -> dict[str, str | None]:
    source = str(record.get("source") or "").lower()
    message = str(record.get("message") or "").lower()
    keywords = " ".join(str(item).lower() for item in log_summary.get("matched_keywords") or [])

    filename = None
    if "no space left" in message or "disk" in message or "disk" in keywords:
        filename = "disk-space-low.md"
    elif source.startswith("nginx") or any(token in message for token in ["502", "upstream", "bad gateway"]):
        filename = "nginx-502.md"
    elif source == "redis" or "redis" in message:
        filename = "redis-connection-error.md"
    elif source == "mysql" or "mysql" in message or "innodb" in message:
        filename = "mysql-connection-error.md"
    elif source in {"system", "docker", "kubernetes"}:
        filename = "system-service-error.md"

    if not filename:
        return {"name": None, "content": None}

    path = RUNBOOK_DIR / filename
    if not path.exists():
        return {"name": filename, "content": None}

    return {
        "name": filename,
        "content": _truncate(path.read_text(encoding="utf-8", errors="replace"), 2400),
    }


def _build_prompt(record: dict[str, Any], log_summary: dict[str, Any], runbook: dict[str, str | None]) -> str:
    payload = {
        "timestamp": record.get("timestamp"),
        "source": record.get("source"),
        "host": record.get("host"),
        "log_level": record.get("log_level"),
        "created_at": record.get("created_at"),
        "log_summary": log_summary,
        "selected_runbook": runbook.get("name"),
        "raw_message": _truncate(str(record.get("message") or ""), 3000),
    }
    runbook_text = runbook.get("content") or "未匹配到可用 Runbook。"

    return f"""
请作为运维/SRE 日志分析助手，只返回严格 JSON，不要返回 Markdown，不要输出额外解释。

请基于下面的单条日志、已提取的关键报错摘要，以及可选 Runbook 进行按需分析。
要求：
1. 不要执行系统命令。
2. 不要假设已经执行过任何操作。
3. 每个结论都尽量基于日志字段、日志等级、关键报错、命中关键词或 Runbook 形成证据。
4. 如果证据不足，必须明确说明“当前证据不足，不能确认唯一根因”。
5. 排查步骤和验证方法只能作为人工参考，不要写成已经执行完成。
6. Runbook 只能作为经验参考，不能覆盖当前日志证据。

日志数据：
{json.dumps(payload, ensure_ascii=False, indent=2)}

可参考 Runbook：
{runbook_text}

返回 JSON 结构必须包含：
{{
  "summary": "一句话说明日志含义",
  "key_error": "最关键的报错片段",
  "evidence": ["证据1，例如日志等级/关键报错/命中关键词/Runbook 判断依据", "证据2"],
  "root_cause_hypothesis": "基于当前证据的根因假设；证据不足时明确说明不能确认唯一根因",
  "root_cause": "兼容字段，内容可与 root_cause_hypothesis 一致",
  "risk_level": "critical/high/medium/low/unknown",
  "possible_causes": ["可能原因1", "可能原因2"],
  "troubleshooting_steps": ["排查步骤1", "排查步骤2"],
  "verification_methods": ["验证方法1", "验证方法2"],
  "operation_risk": "操作风险提示，例如不要直接重启/删除/扩缩容或修改生产配置",
  "prevention_suggestions": ["后续预防建议1", "后续预防建议2"],
  "runbook_used": "{runbook.get("name") or ""}",
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


def _fallback_evidence(record: dict[str, Any], log_summary: dict[str, Any]) -> list[str]:
    evidence = []
    source = record.get("source")
    host = record.get("host")
    level = record.get("log_level")
    key_error = log_summary.get("key_error")
    matched_keywords = log_summary.get("matched_keywords") or []

    if source:
        evidence.append(f"日志来源：{source}")
    if host:
        evidence.append(f"主机/实例：{host}")
    if level:
        evidence.append(f"日志等级：{level}")
    if key_error:
        evidence.append(f"关键报错：{_truncate(str(key_error), 220)}")
    if matched_keywords:
        evidence.append(f"命中关键词：{', '.join(str(item) for item in matched_keywords[:8])}")
    return evidence


def _fallback_verification_methods(record: dict[str, Any]) -> list[str]:
    source = str(record.get("source") or "")
    if source.startswith("nginx"):
        return [
            "检查 Nginx access/error 日志中同一时间段是否持续出现同类错误。",
            "确认后端服务健康状态、端口监听和 upstream 配置是否正常。",
        ]
    if source == "redis":
        return [
            "检查 Redis 服务状态、端口监听和连接数是否异常。",
            "结合 Redis 日志确认是否存在连接拒绝、内存不足或持久化失败。",
        ]
    if source == "mysql":
        return [
            "检查 MySQL 服务状态、连接数、慢查询和错误日志。",
            "确认应用侧数据库连接配置和账号权限是否正确。",
        ]
    if source in {"docker", "kubernetes"}:
        return [
            "检查容器或 Pod 状态是否为 Running/Ready。",
            "查看同一实例附近时间段是否存在重启、OOM 或镜像拉取失败事件。",
        ]
    return [
        "检查同一时间段是否还有相同来源、相同主机的 ERROR/WARN 日志。",
        "结合服务状态、最近变更和监控指标确认问题是否仍在持续。",
    ]


def _fallback_operation_risk(record: dict[str, Any]) -> str:
    level = str(record.get("log_level") or "").upper()
    if level in {"FATAL", "ERROR"}:
        return "风险较高。建议先收集证据并人工确认，不要直接执行重启、删除、扩缩容或配置变更。"
    if level == "WARN":
        return "存在潜在风险。建议先验证影响范围，再决定是否变更配置或重启服务。"
    return "当前日志风险较低。建议作为观察和趋势分析依据，不需要直接执行高风险操作。"


def _compact_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."
