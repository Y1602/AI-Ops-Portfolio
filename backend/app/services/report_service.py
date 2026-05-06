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

    lines.extend(
        [
            "",
            "## 3. 异常摘要",
            "",
        ]
    )

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

    lines.extend(
        [
            "",
            "## 4. 样例日志",
            "",
        ]
    )

    if "sample_lines" in result:
        sample_lines = result.get("sample_lines") or []
        if sample_lines:
            for sample in sample_lines:
                lines.append(f"- `{sample}`")
        else:
            lines.append("无样例日志。")
    elif "parsed_samples" in result:
        parsed_samples = result.get("parsed_samples") or []
        if parsed_samples:
            for sample in parsed_samples[:3]:
                lines.append(f"- `{sample}`")
        else:
            lines.append("无解析样例。")
    else:
        lines.append("无样例日志。")

    lines.extend(
        [
            "",
            "## 5. 初步建议",
            "",
            _get_advice(severity),
            "",
        ]
    )

    return "\n".join(lines)


def _format_dict_items(data: dict, empty_message: str) -> list[str]:
    if not data:
        return [empty_message]

    return [f"- {key}: {value}" for key, value in data.items()]


def _get_advice(severity: str) -> str:
    if severity == "high":
        return "当前日志存在较明显异常，建议优先检查相关服务状态、端口占用、反向代理配置或依赖连接情况。"
    if severity == "medium":
        return "当前日志存在一定异常，需要结合服务状态、端口监听、容器状态进一步排查。"
    if severity == "low":
        return "当前日志未发现明显高风险异常，建议继续观察服务运行状态。"
    return "当前日志风险等级未知，建议先确认日志类型和解析结果是否完整。"
