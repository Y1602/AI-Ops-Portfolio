def parse(log_text: str) -> dict:
    lines = [line for line in log_text.splitlines() if line.strip()]
    severities = _extract_fields(lines, "Severity")
    severity = _highest_alertmanager_severity(severities)
    alert_name = _extract_field(lines, "Alert Name") or "unknown"
    status = _extract_field(lines, "Status") or "unknown"
    instance = _extract_field(lines, "Instance") or "unknown"
    summary = _extract_field(lines, "Summary") or "No alert summary."
    description = _extract_field(lines, "Description") or "No alert description."

    sample_lines = lines[:20]

    return {
        "log_type": "alertmanager_alert",
        "total_lines": len(lines),
        "severity": severity,
        "matched_keywords": {
            "alertname": alert_name,
            "status": status,
            "severity": ", ".join(severities) if severities else "unknown",
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


def _extract_fields(lines: list[str], field_name: str) -> list[str]:
    prefix = f"{field_name}:"
    values = []
    for line in lines:
        if line.startswith(prefix):
            values.append(line[len(prefix) :].strip())
    return values


def _highest_alertmanager_severity(severities: list[str]) -> str:
    mapped = [_map_alertmanager_severity(severity) for severity in severities]
    if "high" in mapped:
        return "high"
    if "medium" in mapped:
        return "medium"
    return "low"


def _map_alertmanager_severity(severity: str) -> str:
    severity_lower = severity.lower()
    if severity_lower == "critical":
        return "high"
    if severity_lower == "warning":
        return "medium"
    if severity_lower == "info":
        return "low"
    return "low"
