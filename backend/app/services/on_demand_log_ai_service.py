from app.services.qwen_client import call_qwen_model


def analyze_unified_log_record(record: dict) -> dict:
    prompt = _build_prompt(record)
    return call_qwen_model(prompt)


def _build_prompt(record: dict) -> str:
    return f"""
请作为运维/SRE 日志分析助手，只返回 JSON，不要返回 Markdown。

请分析以下单条日志，给出问题原因和排查建议。不要生成系统执行命令，不要假设已经执行过任何操作。

日志标准字段：
- timestamp: {record.get("timestamp")}
- source: {record.get("source")}
- host: {record.get("host")}
- log_level: {record.get("log_level")}
- created_at: {record.get("created_at")}

日志内容：
{record.get("message")}

请严格返回如下 JSON 结构：
{{
  "summary": "一句话说明日志含义",
  "root_cause": "最可能的问题原因",
  "risk_level": "critical/high/medium/low/unknown",
  "possible_causes": ["可能原因1", "可能原因2"],
  "troubleshooting_steps": ["排查建议1", "排查建议2"],
  "notes": "必要的补充说明"
}}
""".strip()
