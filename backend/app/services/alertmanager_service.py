from app.schemas.request_schema import IngestLogRequest
from app.services.ingest_service import ingest_log


def ingest_alertmanager_webhook(payload: dict) -> dict:
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
    response["alert_count"] = len(payload.get("alerts") or [])

    if not response.get("error"):
        response["message"] = "alertmanager webhook ingested and report generated"

    return response


def alertmanager_payload_to_text(payload: dict) -> str:
    alerts = payload.get("alerts") or []
    lines = [
        "Alertmanager Webhook Event",
        "",
        f"Receiver: {payload.get('receiver', 'unknown')}",
        f"Webhook Status: {payload.get('status', 'unknown')}",
        f"Alert Count: {len(alerts)}",
        "",
    ]

    for index, alert in enumerate(alerts, start=1):
        labels = alert.get("labels") or {}
        annotations = alert.get("annotations") or {}
        lines.extend(
            [
                f"Alert #{index}",
                f"Alert Name: {labels.get('alertname', 'unknown')}",
                f"Status: {alert.get('status', 'unknown')}",
                f"Severity: {labels.get('severity', 'unknown')}",
                f"Instance: {labels.get('instance', 'unknown')}",
                f"Job: {labels.get('job', 'unknown')}",
                f"Summary: {annotations.get('summary', 'No alert summary.')}",
                f"Description: {annotations.get('description', 'No alert description.')}",
                f"Starts At: {alert.get('startsAt', 'unknown')}",
                f"Ends At: {alert.get('endsAt', 'unknown')}",
                f"Generator URL: {alert.get('generatorURL', 'unknown')}",
                "",
            ]
        )

    return "\n".join(lines).strip()


def _first_alert(payload: dict) -> dict:
    alerts = payload.get("alerts") or []
    if alerts and isinstance(alerts[0], dict):
        return alerts[0]
    return {}
