from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_PROMETHEUS_TIMEOUT_SECONDS = 3.0

PROMETHEUS_QUERIES = [
    {
        "key": "target_up",
        "name": "存活目标",
        "query": "sum(up)",
        "unit": "个",
        "description": "Prometheus 当前可见的 up 目标数量。",
    },
    {
        "key": "http_5xx_rate",
        "name": "HTTP 5xx 速率",
        "query": 'sum(rate(http_requests_total{status=~"5.."}[5m]))',
        "unit": "次/秒",
        "description": "最近 5 分钟 HTTP 5xx 请求速率。指标不存在时会显示为空。",
    },
    {
        "key": "process_cpu_rate",
        "name": "进程 CPU 速率",
        "query": "sum(rate(process_cpu_seconds_total[5m]))",
        "unit": "核",
        "description": "最近 5 分钟进程 CPU 使用速率。指标不存在时会显示为空。",
    },
    {
        "key": "process_memory",
        "name": "进程内存",
        "query": "sum(process_resident_memory_bytes)",
        "unit": "bytes",
        "description": "进程常驻内存总量。指标不存在时会显示为空。",
    },
]


def get_prometheus_base_url() -> str | None:
    base_url = os.getenv("PROMETHEUS_BASE_URL", "").strip()
    return base_url.rstrip("/") if base_url else None


def get_prometheus_timeout() -> float:
    raw_value = os.getenv("PROMETHEUS_TIMEOUT_SECONDS", "").strip()
    if not raw_value:
        return DEFAULT_PROMETHEUS_TIMEOUT_SECONDS
    try:
        return max(float(raw_value), 0.5)
    except ValueError:
        return DEFAULT_PROMETHEUS_TIMEOUT_SECONDS


def get_prometheus_snapshot() -> dict[str, Any]:
    base_url = get_prometheus_base_url()
    if not base_url:
        return {
            "configured": False,
            "error": None,
            "metrics": [],
        }

    metrics = []
    errors = []
    for item in PROMETHEUS_QUERIES:
        try:
            value = query_prometheus_instant(base_url, item["query"])
        except Exception as exc:
            value = None
            errors.append(f"{item['key']}: {exc}")

        metrics.append(
            {
                "key": item["key"],
                "name": item["name"],
                "query": item["query"],
                "unit": item["unit"],
                "description": item["description"],
                "value": value,
            }
        )

    return {
        "configured": True,
        "base_url": base_url,
        "error": "; ".join(errors) if errors else None,
        "metrics": metrics,
    }


def query_prometheus_instant(base_url: str, query: str) -> float | None:
    params = urllib.parse.urlencode({"query": query})
    url = f"{base_url}/api/v1/query?{params}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})

    with urllib.request.urlopen(request, timeout=get_prometheus_timeout()) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("status") != "success":
        raise RuntimeError(payload.get("error") or "prometheus query failed")

    result = payload.get("data", {}).get("result", [])
    if not result:
        return None

    values = []
    for item in result:
        raw_value = item.get("value", [None, None])[1]
        try:
            values.append(float(raw_value))
        except (TypeError, ValueError):
            continue

    if not values:
        return None
    return sum(values)
