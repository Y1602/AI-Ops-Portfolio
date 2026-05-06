import re
from datetime import datetime
from pathlib import Path


DANGEROUS_COMMAND_KEYWORDS = [
    "rm -rf",
    "mkfs",
    "dd if=",
    "shutdown",
    "reboot",
    "init 0",
    "halt",
    "poweroff",
    "iptables -f",
    "systemctl stop firewalld",
    "drop database",
    "truncate table",
    "docker system prune -a",
]


def generate_markdown_report(result: dict) -> str:
    log_type = result.get("log_type", "unknown")
    total_lines = result.get("total_lines", 0)
    severity = result.get("severity", "unknown")

    lines = [
        "# AI-OpsLog 日志分析报告",
        "",
        "## 1. 基本信息",
        "",
        f"- 日志类型：{log_type}",
        f"- 总日志行数：{total_lines}",
        f"- 风险等级：{severity}",
        "",
        "## 2. 命中关键词 / 状态码统计",
        "",
    ]

    if "matched_keywords" in result:
        lines.extend(_format_dict_items(result.get("matched_keywords"), "未命中已知错误关键词。"))
    elif "status_code_count" in result:
        lines.extend(_format_dict_items(result.get("status_code_count"), "未解析到状态码统计。"))
    else:
        lines.append("未提供关键词或状态码统计。")

    lines.extend(["", "## 3. 异常摘要", ""])

    if "error_summary" in result:
        lines.append(str(result.get("error_summary") or "无异常摘要。"))
    elif log_type == "nginx_access":
        suspicious_paths = result.get("suspicious_paths") or []
        lines.extend(
            [
                f"- error_count：{result.get('error_count', 0)}",
                f"- error_rate：{result.get('error_rate', 0)}",
                "- suspicious_paths："
                + (", ".join(map(str, suspicious_paths)) if suspicious_paths else "无"),
            ]
        )
    else:
        lines.append("无异常摘要。")

    lines.extend(["", "## 4. 样例日志", ""])
    lines.extend(_format_samples(result))
    lines.extend(["", "## 5. 初步建议", "", _get_advice(severity), ""])

    return "\n".join(lines)


def generate_ai_markdown_report(result: dict) -> str:
    try:
        log_type = result.get("log_type", "unknown")
        rule_result = result.get("rule_result") or {}
        ai_result = result.get("ai_result") or {}
        rule_severity = rule_result.get("severity", "unknown")
        ai_risk_level = ai_result.get("risk_level", "unknown")
        need_manual_intervention = ai_result.get("need_manual_intervention", "unknown")

        lines = [
            "# AI-OpsLog 智能日志分析报告",
            "",
            "## 1. 基本信息",
            "",
            f"- 日志类型：{log_type}",
            f"- 规则风险等级：{rule_severity}",
            f"- AI 风险等级：{ai_risk_level}",
            f"- 是否需要人工介入：{need_manual_intervention}",
            "",
            "## 2. 规则解析结果",
            "",
        ]

        lines.extend(_format_rule_result(rule_result))
        lines.extend(["", "## 3. AI 故障摘要", ""])

        if isinstance(ai_result, dict) and ai_result.get("error"):
            lines.append(f"- AI 调用失败：{ai_result.get('error')}")
            if ai_result.get("detail"):
                lines.append(f"- 错误详情：{ai_result.get('detail')}")
            lines.append("- 当前报告仅包含规则分析结果。")
        else:
            lines.append(str(ai_result.get("summary") or "AI 未返回故障摘要。"))

        lines.extend(["", "## 4. 可能原因", ""])
        lines.extend(_format_list(ai_result.get("possible_causes"), "AI 未返回可能原因。"))

        lines.extend(["", "## 5. 排查步骤", ""])
        lines.extend(_format_list(ai_result.get("troubleshooting_steps"), "AI 未返回排查步骤。"))

        lines.extend(["", "## 6. 修复建议", ""])
        lines.extend(_format_list(ai_result.get("fix_suggestions"), "AI 未返回修复建议。"))

        lines.extend(["", "## 7. 建议排查命令", ""])
        safe_commands = _filter_safe_commands(ai_result.get("related_commands"))
        if safe_commands:
            for command in safe_commands:
                lines.append(f"- `{command}`")
        else:
            lines.append("无安全的建议排查命令。")
        lines.append("")
        lines.append("以上命令仅作为人工排查参考，本系统不会自动执行任何命令。")

        lines.extend(["", "## 8. 样例日志", ""])
        lines.extend(_format_samples(rule_result))

        lines.extend(
            [
                "",
                "## 9. 安全说明",
                "",
                "本报告由规则解析与大模型辅助分析生成，仅用于运维排障参考。  ",
                "AI 分析结果需要结合实际环境人工确认。  ",
                "本系统不会自动执行任何系统命令。",
                "",
            ]
        )

        return "\n".join(lines)
    except Exception as exc:
        return "\n".join(
            [
                "# AI-OpsLog 智能日志分析报告",
                "",
                "## 报告生成失败",
                "",
                f"- 错误信息：{exc}",
                "- 本系统不会自动执行任何系统命令。",
                "",
            ]
        )


def save_report_to_file(
    markdown_report: str,
    log_type: str = "unknown",
    output_dir: str = "reports",
) -> str:
    try:
        project_root = Path(__file__).resolve().parents[3]
        output_path = Path(output_dir)
        if not output_path.is_absolute():
            output_path = project_root / output_path

        output_path.mkdir(parents=True, exist_ok=True)

        safe_log_type = _safe_filename_part(log_type)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"ai_opslog_{safe_log_type}_report_{timestamp}"
        report_path = output_path / f"{base_name}.md"

        counter = 1
        while report_path.exists():
            report_path = output_path / f"{base_name}_{counter:02d}.md"
            counter += 1

        report_path.write_text(markdown_report, encoding="utf-8")
        return _to_project_relative_path(project_root, report_path)
    except Exception as exc:
        return f"failed to save report: {exc}"


def _format_rule_result(rule_result: dict) -> list[str]:
    lines = []

    if rule_result.get("matched_keywords"):
        lines.extend(["| 关键词 | 命中次数 |", "|---|---|"])
        for keyword, count in rule_result.get("matched_keywords", {}).items():
            lines.append(f"| {keyword} | {count} |")

    if rule_result.get("status_code_count"):
        if lines:
            lines.append("")
        lines.extend(["| 状态码 | 次数 |", "|---|---|"])
        for status_code, count in rule_result.get("status_code_count", {}).items():
            lines.append(f"| {status_code} | {count} |")

    if "error_summary" in rule_result:
        lines.append(f"- 异常摘要：{rule_result.get('error_summary') or '无'}")

    if "error_count" in rule_result:
        lines.append(f"- error_count：{rule_result.get('error_count')}")

    if "error_rate" in rule_result:
        lines.append(f"- error_rate：{rule_result.get('error_rate')}")

    if "suspicious_paths" in rule_result:
        suspicious_paths = rule_result.get("suspicious_paths") or []
        lines.append(
            "- 可疑路径："
            + (", ".join(map(str, suspicious_paths)) if suspicious_paths else "无")
        )

    return lines or ["无规则解析结果。"]


def _format_samples(result: dict) -> list[str]:
    if "sample_lines" in result:
        sample_lines = result.get("sample_lines") or []
        if sample_lines:
            return [f"- `{sample}`" for sample in sample_lines]
        return ["无样例日志。"]

    if "parsed_samples" in result:
        parsed_samples = result.get("parsed_samples") or []
        if parsed_samples:
            return [f"- `{sample}`" for sample in parsed_samples[:3]]
        return ["无解析样例。"]

    return ["无样例日志。"]


def _format_dict_items(data: dict, empty_message: str) -> list[str]:
    if not data:
        return [empty_message]

    return [f"- {key}: {value}" for key, value in data.items()]


def _format_list(items, empty_message: str) -> list[str]:
    if not items:
        return [empty_message]

    return [f"- {item}" for item in items]


def _filter_safe_commands(commands) -> list[str]:
    if not commands:
        return []

    safe_commands = []
    for command in commands:
        command_text = str(command).strip()
        command_lower = command_text.lower()
        if any(keyword in command_lower for keyword in DANGEROUS_COMMAND_KEYWORDS):
            continue
        safe_commands.append(command_text)

    return safe_commands


def _safe_filename_part(value: str) -> str:
    safe_value = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value).strip())
    return safe_value.strip("_") or "unknown"


def _to_project_relative_path(project_root: Path, report_path: Path) -> str:
    try:
        return report_path.relative_to(project_root).as_posix()
    except ValueError:
        return str(report_path)


def _get_advice(severity: str) -> str:
    if severity == "high":
        return "当前日志存在较明显异常，建议优先检查相关服务状态、端口占用、反向代理配置或依赖连接情况。"
    if severity == "medium":
        return "当前日志存在一定异常，需要结合服务状态、端口监听、容器状态进一步排查。"
    if severity == "low":
        return "当前日志未发现明显高风险异常，建议继续观察服务运行状态。"
    return "当前日志风险等级未知，建议先确认日志类型和解析结果是否完整。"
