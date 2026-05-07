from app.schemas.request_schema import IngestLogRequest
from app.services.ingest_service import ingest_log


def ingest_alertmanager_webhook(payload: dict) -> dict:
    alerts = payload.get("alerts") or []
    if not alerts:
        return {"error": "no alerts found in alertmanager webhook"}

    alert_text = alertmanager_payload_to_text(payload)
    first_alert = _first_alert(payload)
    labels = first_alert.get("labels") or {}

    source = labels.get("instance") or "alertmanager"
    service_name = labels.get("alertname") or "alertmanager-alert"

    request = IngestLogRequest(
        source=source,
        service_name=service_name,
        env="monitoring",
        log_type="alertmanager_alert",
        log_text=alert_text,
    )
    response = ingest_log(request)
    response["alert_count"] = len(alerts)
    response["webhook_status"] = payload.get("status", "unknown")

    if not response.get("error"):
        response["message"] = "alertmanager webhook ingested and report generated"

    return response


def alertmanager_payload_to_text(payload: dict) -> str:
    alerts = payload.get("alerts") or []
    common_labels = payload.get("commonLabels") or {}
    lines = [
        "Alertmanager Webhook Event",
        "",
        "Event Summary:",
        f"- Receiver: {payload.get('receiver', 'alertmanager')}",
        f"- Webhook Status: {payload.get('status', 'unknown')}",
        f"- Event Type: {_event_type(payload, alerts)}",
        f"- Alert Count: {len(alerts)}",
        f"- Common Severity: {common_labels.get('severity') or _highest_raw_severity(alerts)}",
        f"- Common Alert Name: {common_labels.get('alertname', 'mixed')}",
        f"- External URL: {payload.get('externalURL', 'unknown')}",
        "",
        "Alert Details:",
        "",
    ]

    for index, alert in enumerate(alerts, start=1):
        labels = alert.get("labels") or {}
        annotations = alert.get("annotations") or {}
        lines.extend(
            [
                f"Alert #{index}",
                f"- Alert Name: {labels.get('alertname', 'alertmanager-alert')}",
                f"- Status: {alert.get('status', 'unknown')}",
                f"- Severity: {labels.get('severity', 'unknown')}",
                f"- Instance: {labels.get('instance', 'alertmanager')}",
                f"- Job: {labels.get('job', 'unknown')}",
                f"- Summary: {annotations.get('summary', 'no summary')}",
                f"- Description: {annotations.get('description', 'no description')}",
                f"- Starts At: {alert.get('startsAt', 'unknown')}",
                f"- Ends At: {alert.get('endsAt', 'unknown')}",
                f"- Generator URL: {alert.get('generatorURL', 'unknown')}",
                "",
            ]
        )

    return "\n".join(lines).strip()


def _first_alert(payload: dict) -> dict:
    alerts = payload.get("alerts") or []
    if alerts and isinstance(alerts[0], dict):
        return alerts[0]
    return {}


def _highest_raw_severity(alerts: list[dict]) -> str:
    severities = []
    for alert in alerts:
        labels = alert.get("labels") or {}
        severities.append(str(labels.get("severity", "unknown")).lower())
    if "critical" in severities:
        return "critical"
    if "warning" in severities:
        return "warning"
    if "info" in severities:
        return "info"
    return "unknown"


def _event_type(payload: dict, alerts: list[dict]) -> str:
    webhook_status = str(payload.get("status", "")).lower()
    alert_statuses = [str(alert.get("status", "")).lower() for alert in alerts]
    if webhook_status == "resolved" or (
        alert_statuses and alert_statuses.count("resolved") >= alert_statuses.count("firing")
    ):
        return "alert_resolved"
    return "alert_firing"
