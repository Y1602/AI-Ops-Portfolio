#!/usr/bin/env python3
import argparse
import os
import queue
import re
import socket
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.storage.log_store import archive_old_logs, init_logs_db, save_log_records  # noqa: E402


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
    "error": "ERROR",
    "err": "ERROR",
    "warning": "WARN",
    "warn": "WARN",
    "notice": "INFO",
    "info": "INFO",
    "debug": "DEBUG",
}


@dataclass
class LogTarget:
    source: str
    path: Path
    host: str


class QueueLogWriter:
    def __init__(self, batch_size: int = 100, flush_interval: float = 2.0) -> None:
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._queue: queue.Queue[dict | None] = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._errors: list[str] = []

    def start(self) -> None:
        self._thread.start()

    def put(self, record: dict) -> None:
        self._queue.put(record)

    def stop(self) -> None:
        self._queue.put(None)
        self._thread.join()
        if self._errors:
            raise RuntimeError("; ".join(self._errors))

    def _run(self) -> None:
        batch = []
        last_flush = time.monotonic()
        while True:
            timeout = max(0.1, self.flush_interval - (time.monotonic() - last_flush))
            try:
                item = self._queue.get(timeout=timeout)
            except queue.Empty:
                item = "flush"

            if item is None:
                self._flush(batch)
                return

            if item != "flush":
                batch.append(item)

            if len(batch) >= self.batch_size or time.monotonic() - last_flush >= self.flush_interval:
                self._flush(batch)
                last_flush = time.monotonic()

    def _flush(self, batch: list[dict]) -> None:
        if not batch:
            return
        try:
            save_log_records(batch)
        except Exception as exc:
            self._errors.append(str(exc))
        finally:
            batch.clear()


def parse_target(raw_target: str, default_host: str) -> LogTarget:
    parts = {}
    for item in raw_target.split(","):
        if "=" not in item:
            raise ValueError(f"invalid target segment: {item}")
        key, value = item.split("=", 1)
        parts[key.strip()] = value.strip()

    source = parts.get("source", "")
    path = parts.get("path", "")
    host = parts.get("host") or default_host

    if source not in SUPPORTED_SOURCES:
        raise ValueError(f"unsupported source: {source}")
    if not path:
        raise ValueError("target path is required")

    return LogTarget(source=source, path=Path(path), host=host)


def normalize_log_line(line: str, target: LogTarget) -> dict:
    timestamp = extract_timestamp(line)
    level = extract_level(line, target.source)
    return {
        "timestamp": timestamp,
        "source": target.source,
        "host": target.host,
        "log_level": level,
        "message": line.rstrip("\n"),
        "AI_analysis_result": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def extract_timestamp(line: str) -> str | None:
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


def extract_level(line: str, source: str) -> str:
    if source == "nginx_access":
        status_match = re.search(r'"\s+(\d{3})\s+', line)
        if status_match:
            status = int(status_match.group(1))
            if status >= 500:
                return "ERROR"
            if status >= 400:
                return "WARN"
            return "INFO"

    for token in re.findall(r"[A-Za-z]+", line):
        mapped = LEVEL_ALIASES.get(token.lower())
        if mapped:
            return mapped

    return "INFO"


def read_last_lines(path: Path, line_count: int) -> list[str]:
    if line_count <= 0:
        return []
    with path.open("r", encoding="utf-8", errors="replace") as file:
        lines = file.readlines()
    return lines[-line_count:]


def collect_once(targets: Iterable[LogTarget], writer: QueueLogWriter, lines: int) -> int:
    count = 0
    for target in targets:
        if not target.path.exists():
            print(f"[WARN] log file not found: {target.path}")
            continue
        for line in read_last_lines(target.path, lines):
            if line.strip():
                writer.put(normalize_log_line(line, target))
                count += 1
    return count


def collect_tail(
    targets: list[LogTarget],
    writer: QueueLogWriter,
    interval: float,
    retention_days: int,
    archive_dir: str,
    archive_interval: float,
) -> None:
    offsets = {}
    last_archive = time.monotonic()
    for target in targets:
        if target.path.exists():
            offsets[target.path] = target.path.stat().st_size
        else:
            offsets[target.path] = 0

    while True:
        for target in targets:
            if not target.path.exists():
                continue

            current_size = target.path.stat().st_size
            offset = offsets.get(target.path, 0)
            if current_size < offset:
                offset = 0

            if current_size > offset:
                with target.path.open("r", encoding="utf-8", errors="replace") as file:
                    file.seek(offset)
                    for line in file:
                        if line.strip():
                            writer.put(normalize_log_line(line, target))
                    offsets[target.path] = file.tell()

        if time.monotonic() - last_archive >= archive_interval:
            archived_count = archive_old_logs(retention_days, archive_dir)
            if archived_count:
                print(f"[INFO] archived {archived_count} old log records")
            last_archive = time.monotonic()

        time.sleep(interval)


def _normalize_timestamp(value: str) -> str:
    normalized = value.replace(" ", "T", 1)
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized).isoformat()
    except ValueError:
        return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect and store unified AI-OpsLog log records.")
    parser.add_argument(
        "--target",
        action="append",
        required=True,
        help="Log target in source=<type>,path=<file>,host=<host> format. host is optional.",
    )
    parser.add_argument("--mode", choices=["once", "tail"], default="once")
    parser.add_argument("--interval", type=float, default=60.0, help="Polling interval in seconds.")
    parser.add_argument("--lines", type=int, default=200, help="Lines to read per target in once mode.")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--flush-interval", type=float, default=2.0)
    parser.add_argument("--retention-days", type=int, default=7)
    parser.add_argument("--archive-dir", default="data/archives")
    parser.add_argument("--archive-interval", type=float, default=86400.0, help="Archive check interval in seconds.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    default_host = socket.gethostname()
    targets = [parse_target(raw_target, default_host) for raw_target in args.target]

    if args.dry_run:
        for target in targets:
            print(f"[DRY-RUN] source={target.source} host={target.host} path={target.path}")
        return 0

    os.environ.setdefault("AI_OPSLOG_DB_PATH", "data/ai_opslog.db")
    init_logs_db()
    archived_count = archive_old_logs(args.retention_days, args.archive_dir)
    if archived_count:
        print(f"[INFO] archived {archived_count} old log records")

    writer = QueueLogWriter(batch_size=args.batch_size, flush_interval=args.flush_interval)
    writer.start()
    try:
        if args.mode == "once":
            collected = collect_once(targets, writer, args.lines)
            print(f"[INFO] queued {collected} log records")
        else:
            print("[INFO] tail mode started; press Ctrl+C to stop")
            collect_tail(
                targets,
                writer,
                args.interval,
                args.retention_days,
                args.archive_dir,
                args.archive_interval,
            )
    except KeyboardInterrupt:
        print("[INFO] stopping collector")
    finally:
        writer.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
