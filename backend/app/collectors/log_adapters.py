import json
import re
from datetime import datetime, timezone
from typing import Any


SUPPORTED_SOURCES = {
    "system",
    "zabbix",
    "prometheus",
    "grafana",
    "ansible",
    "docker",
    "kubernetes",
    "nginx_access",
    "nginx_error",
    "redis",
    "mysql",
}

LOG_LEVELS = {"FATAL", "ERROR", "WARN", "INFO", "DEBUG"}

LEVEL_ALIASES = {
    "fatal": "FATAL",
    "panic": "FATAL",
    "critical": "FATAL",
    "crit": "FATAL",
    "emerg": "FATAL",
    "alert": "FATAL",
    "error": "ERROR",
    "err": "ERROR",
    "eror": "ERROR",
    "warning": "WARN",
    "warn": "WARN",
    "notice": "INFO",
    "info": "INFO",
    "information": "INFO",
    "debug": "DEBUG",
    "trace": "DEBUG",
}

JSON_LEVEL_KEYS = ("level", "severity", "log_level", "log.level", "lvl", "levelname")
JSON_TIME_KEYS = ("timestamp", "time", "ts", "@timestamp", "datetime", "date")
JSON_MESSAGE_KEYS = ("message", "msg", "log", "event", "error")


def normalize_log_line(line: str, source: str, host: str) -> dict[str, Any]:
    stripped_line = line.rstrip("\n")
    parsed_json = _parse_json_line(stripped_line)
    timestamp = extract_timestamp(stripped_line, source, parsed_json)
    level = extract_level(stripped_line, source, parsed_json)
    message = extract_message(stripped_line, parsed_json)

    return {
        "timestamp": timestamp,
        "source": source,
        "host": host,
        "log_level": level,
        "message": message,
        "AI_analysis_result": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def extract_message(line: str, parsed_json: dict[str, Any] | None = None) -> str:
    if parsed_json:
        for key in JSON_MESSAGE_KEYS:
            value = _get_nested_value(parsed_json, key)
            if value not in (None, ""):
                return str(value).rstrip("\n")
    return line.rstrip("\n")


def extract_timestamp(
    line: str,
    source: str = "",
    parsed_json: dict[str, Any] | None = None,
) -> str | None:
    if parsed_json:
        for key in JSON_TIME_KEYS:
            value = _get_nested_value(parsed_json, key)
            if value not in (None, ""):
                return _normalize_timestamp(str(value))

    logfmt_time_match = re.search(r'(?:^|\s)(?:ts|time|timestamp)=["\']?([^"\'\s]+)', line)
    if logfmt_time_match:
        return _normalize_timestamp(logfmt_time_match.group(1))

    iso_match = re.search(
        r"(\d{4}-\d{2}-\d{2}[T ][0-9:.]+(?:Z|[+-]\d{2}:?\d{2})?)",
        line,
    )
    if iso_match:
        return _normalize_timestamp(iso_match.group(1))

    nginx_match = re.search(r"\[(\d{2}/[A-Za-z]{3}/\d{4}:[0-9:]+ [+-]\d{4})\]", line)
    if nginx_match:
        try:
            parsed = datetime.strptime(nginx_match.group(1), "%d/%b/%Y:%H:%M:%S %z")
            return parsed.isoformat()
        except ValueError:
            return nginx_match.group(1)

    redis_match = re.search(r"\b(\d{1,2} [A-Za-z]{3} \d{4} [0-9:]{8}\.\d{3})\b", line)
    if source == "redis" and redis_match:
        try:
            parsed = datetime.strptime(redis_match.group(1), "%d %b %Y %H:%M:%S.%f")
            return parsed.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            return redis_match.group(1)

    zabbix_match = re.match(r"\s*\d+:(\d{8}:\d{6}\.\d+)", line)
    if source == "zabbix" and zabbix_match:
        try:
            parsed = datetime.strptime(zabbix_match.group(1), "%Y%m%d:%H%M%S.%f")
            return parsed.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            return zabbix_match.group(1)

    syslog_match = re.match(r"([A-Z][a-z]{2}\s+\d{1,2}\s+[0-9:]{8})", line)
    if syslog_match:
        try:
            parsed = datetime.strptime(
                f"{datetime.now().year} {syslog_match.group(1)}",
                "%Y %b %d %H:%M:%S",
            )
            return parsed.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            return syslog_match.group(1)

    return None


def extract_level(
    line: str,
    source: str = "",
    parsed_json: dict[str, Any] | None = None,
) -> str:
    if source == "nginx_access":
        status_match = re.search(r'"\s+(\d{3})\s+', line)
        if status_match:
            return _level_from_http_status(int(status_match.group(1)))

    if parsed_json:
        for key in JSON_LEVEL_KEYS:
            value = _get_nested_value(parsed_json, key)
            mapped = normalize_level(value)
            if mapped:
                return mapped

        status = _get_nested_value(parsed_json, "status") or _get_nested_value(parsed_json, "status_code")
        if status is not None:
            try:
                return _level_from_http_status(int(status))
            except (TypeError, ValueError):
                pass

    key_value_level = re.search(r'(?:^|\s)(?:level|lvl|severity|log_level)=["\']?([A-Za-z]+)', line, re.IGNORECASE)
    if key_value_level:
        mapped = normalize_level(key_value_level.group(1))
        if mapped:
            return mapped

    bracket_level = re.search(r"\[([A-Za-z]+)\]", line)
    if bracket_level:
        mapped = normalize_level(bracket_level.group(1))
        if mapped:
            return mapped

    for token in re.findall(r"[A-Za-z]+", line):
        mapped = normalize_level(token)
        if mapped:
            return mapped

    return "INFO"


def normalize_level(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().strip('"').strip("'").lower()
    return LEVEL_ALIASES.get(normalized)


def _level_from_http_status(status: int) -> str:
    if status >= 500:
        return "ERROR"
    if status >= 400:
        return "WARN"
    return "INFO"


def _normalize_timestamp(value: str) -> str:
    normalized = value.strip().replace(" ", "T", 1)
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized).isoformat()
    except ValueError:
        return value


def _parse_json_line(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped.startswith("{"):
        return None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _get_nested_value(data: dict[str, Any], key: str) -> Any:
    if key in data:
        return data[key]
    if "." not in key:
        return None

    current: Any = data
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current
