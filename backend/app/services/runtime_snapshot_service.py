from __future__ import annotations

import os
import subprocess
from typing import Any


DEFAULT_RUNTIME_TIMEOUT_SECONDS = 3.0
DEFAULT_MAX_ITEMS = 8


def get_runtime_snapshot() -> dict[str, Any]:
    return {
        "docker": get_docker_snapshot(),
        "kubernetes": get_kubernetes_snapshot(),
    }


def get_docker_snapshot() -> dict[str, Any]:
    if not _is_enabled("AI_OPSLOG_ENABLE_DOCKER_SNAPSHOT", default=True):
        return {"enabled": False, "available": False, "error": "Docker snapshot disabled.", "containers": []}

    command = [
        _env_or_default("DOCKER_BIN", "docker"),
        "ps",
        "--format",
        "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}",
    ]
    result = _run_readonly_command(command)
    if not result["ok"]:
        return {"enabled": True, "available": False, "error": result["error"], "containers": []}

    containers = []
    for line in result["stdout"].splitlines()[: _max_items()]:
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        containers.append(
            {
                "id": parts[0],
                "name": parts[1],
                "image": parts[2],
                "status": parts[3],
            }
        )

    return {
        "enabled": True,
        "available": True,
        "error": None,
        "containers": containers,
    }


def get_kubernetes_snapshot() -> dict[str, Any]:
    if not _is_enabled("AI_OPSLOG_ENABLE_KUBERNETES_SNAPSHOT", default=True):
        return {"enabled": False, "available": False, "error": "Kubernetes snapshot disabled.", "pods": [], "events": []}

    kubectl = _env_or_default("KUBECTL_BIN", "kubectl")
    pods_result = _run_readonly_command(
        [
            kubectl,
            "get",
            "pods",
            "-A",
            "--no-headers",
        ]
    )
    events_result = _run_readonly_command(
        [
            kubectl,
            "get",
            "events",
            "-A",
            "--sort-by=.lastTimestamp",
            "--no-headers",
        ]
    )

    errors = []
    if not pods_result["ok"]:
        errors.append(f"pods: {pods_result['error']}")
    if not events_result["ok"]:
        errors.append(f"events: {events_result['error']}")

    return {
        "enabled": True,
        "available": pods_result["ok"] or events_result["ok"],
        "error": "; ".join(errors) if errors else None,
        "pods": _parse_kubectl_pods(pods_result["stdout"]) if pods_result["ok"] else [],
        "events": _parse_kubectl_events(events_result["stdout"]) if events_result["ok"] else [],
    }


def _parse_kubectl_pods(output: str) -> list[dict[str, str]]:
    pods = []
    for line in output.splitlines()[: _max_items()]:
        parts = line.split()
        if len(parts) < 5:
            continue
        pods.append(
            {
                "namespace": parts[0],
                "name": parts[1],
                "ready": parts[2],
                "status": parts[3],
                "restarts": parts[4],
                "age": parts[5] if len(parts) > 5 else "",
            }
        )
    return pods


def _parse_kubectl_events(output: str) -> list[dict[str, str]]:
    events = []
    lines = output.splitlines()
    for line in lines[-_max_items():]:
        parts = line.split(maxsplit=6)
        if len(parts) < 6:
            continue
        events.append(
            {
                "namespace": parts[0],
                "last_seen": parts[1],
                "type": parts[2],
                "reason": parts[3],
                "object": parts[4],
                "message": parts[6] if len(parts) > 6 else "",
            }
        )
    return events


def _run_readonly_command(command: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            timeout=_timeout(),
        )
    except FileNotFoundError:
        return {"ok": False, "stdout": "", "error": f"command not found: {command[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stdout": "", "error": f"command timeout after {_timeout()}s: {command[0]}"}
    except Exception as exc:
        return {"ok": False, "stdout": "", "error": str(exc)}

    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip()
        return {"ok": False, "stdout": completed.stdout, "error": stderr or f"exit code {completed.returncode}"}

    return {"ok": True, "stdout": completed.stdout, "error": None}


def _timeout() -> float:
    raw_value = os.getenv("RUNTIME_SNAPSHOT_TIMEOUT_SECONDS", "").strip()
    if not raw_value:
        return DEFAULT_RUNTIME_TIMEOUT_SECONDS
    try:
        return max(float(raw_value), 0.5)
    except ValueError:
        return DEFAULT_RUNTIME_TIMEOUT_SECONDS


def _max_items() -> int:
    raw_value = os.getenv("RUNTIME_SNAPSHOT_MAX_ITEMS", "").strip()
    if not raw_value:
        return DEFAULT_MAX_ITEMS
    try:
        return min(max(int(raw_value), 1), 50)
    except ValueError:
        return DEFAULT_MAX_ITEMS


def _env_or_default(name: str, default: str) -> str:
    return os.getenv(name, "").strip() or default


def _is_enabled(name: str, default: bool) -> bool:
    raw_value = os.getenv(name, "").strip().lower()
    if not raw_value:
        return default
    return raw_value not in {"0", "false", "no", "off"}
