def parse(log_text: str) -> dict:
    lines = [line for line in log_text.splitlines() if line.strip()]
    severity = _extract_field(lines, "Severity") or "unknown"
    alert_name = _extract_field(lines, "Alert Name") or "unknown"
    status = _extract_field(lines, "Status") or "unknown"
    instance = _extract_field(lines, "Instance") or "unknown"
    summary = _extract_field(lines, "Summary") or "No alert summary."
    description = _extract_field(lines, "Description") or "No alert description."

    mapped_severity = _map_alertmanager_severity(severity)
    sample_lines = lines[:20]

    return {
        "log_type": "alertmanager_alert",
        "total_lines": len(lines),
        "severity": mapped_severity,
        "matched_keywords": {
            "alertname": alert_name,
            "status": status,
            "severity": severity,
            "instance": instance,
        },
        "error_summary": f"{alert_name} on {instance}: {summary}. {description}",
        "sample_lines": sample_lines,
    }


def _extract_field(lines: list[str], field_name: str) -> str | None:
    prefix = f"{field_name}:"
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def _map_alertmanager_severity(severity: str) -> str:
    severity_lower = severity.lower()
    if severity_lower == "critical":
        return "high"
    if severity_lower == "warning":
        return "medium"
    if severity_lower == "info":
        return "low"
    return "unknown"
