#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import os
import queue
import socket
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.collectors.log_adapters import SUPPORTED_SOURCES, normalize_log_line  # noqa: E402
from app.storage.log_store import archive_old_logs, init_logs_db, save_log_records  # noqa: E402


@dataclass
class LogTarget:
    source: str
    path: Path
    host: str


def target_state_key(target: LogTarget) -> str:
    return f"{target.source}|{target.host}|{target.path}"


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


def start_archive_worker(retention_days: int, archive_dir: str) -> threading.Thread:
    thread = threading.Thread(
        target=run_archive_once,
        args=(retention_days, archive_dir),
        daemon=True,
    )
    thread.start()
    return thread


def run_archive_once(retention_days: int, archive_dir: str) -> None:
    try:
        archived_count = archive_old_logs(retention_days, archive_dir)
    except Exception as exc:
        print(f"[WARN] archive failed: {exc}")
        return
    if archived_count:
        print(f"[INFO] archived {archived_count} old log records")


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


def has_glob_pattern(path: Path) -> bool:
    return any(char in str(path) for char in ["*", "?", "["])


def expand_target_paths(target: LogTarget) -> list[LogTarget]:
    if not has_glob_pattern(target.path):
        return [target]

    matches = sorted(glob.glob(str(target.path)))
    if not matches:
        print(f"[WARN] glob target matched no files: {target.path}")
        return []

    return [
        LogTarget(source=target.source, path=Path(match), host=target.host)
        for match in matches
        if Path(match).is_file()
    ]


def expand_targets(targets: Iterable[LogTarget]) -> list[LogTarget]:
    expanded = []
    for target in targets:
        expanded.extend(expand_target_paths(target))
    return expanded


def read_last_lines(path: Path, line_count: int) -> list[str]:
    if line_count <= 0:
        return []
    with path.open("r", encoding="utf-8", errors="replace") as file:
        lines = file.readlines()
    return lines[-line_count:]


def read_from_offset(path: Path, offset: int) -> tuple[list[str], int]:
    with path.open("r", encoding="utf-8", errors="replace") as file:
        file.seek(offset)
        lines = file.readlines()
        return lines, file.tell()


def load_state(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    state = {}
    for key, value in data.items():
        try:
            state[str(key)] = int(value)
        except (TypeError, ValueError):
            continue
    return state


def save_state(path: Path, state: dict[str, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(state, file, ensure_ascii=False, indent=2, sort_keys=True)


def collect_once(
    targets: Iterable[LogTarget],
    writer: QueueLogWriter,
    lines: int,
    state: dict[str, int] | None = None,
) -> int:
    count = 0
    for target in expand_targets(targets):
        if not target.path.exists():
            print(f"[WARN] log file not found: {target.path}")
            continue
        target_count = 0
        current_size = target.path.stat().st_size
        state_key = target_state_key(target)
        previous_offset = state.get(state_key) if state is not None else None

        if previous_offset is not None and 0 <= previous_offset <= current_size:
            target_lines, next_offset = read_from_offset(target.path, previous_offset)
        else:
            target_lines = read_last_lines(target.path, lines)
            next_offset = current_size

        for line in target_lines:
            if line.strip():
                writer.put(normalize_log_line(line, target.source, target.host))
                count += 1
                target_count += 1
        if state is not None:
            state[state_key] = next_offset
        print(f"[INFO] target source={target.source} host={target.host} path={target.path} queued={target_count}")
    return count


def collect_tail(
    targets: list[LogTarget],
    writer: QueueLogWriter,
    interval: float,
    retention_days: int,
    archive_dir: str,
    archive_interval: float,
) -> None:
    targets = expand_targets(targets)
    offsets = {}
    last_archive = time.monotonic()
    archive_thread: threading.Thread | None = None
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
                            writer.put(normalize_log_line(line, target.source, target.host))
                    offsets[target.path] = file.tell()

        if time.monotonic() - last_archive >= archive_interval:
            if archive_thread is None or not archive_thread.is_alive():
                archive_thread = start_archive_worker(retention_days, archive_dir)
            last_archive = time.monotonic()

        time.sleep(interval)


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
    parser.add_argument("--state-file", default="data/collect_unified_logs_state.json")
    parser.add_argument("--no-state", action="store_true", help="Disable offset state in once mode.")
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
    archive_thread = start_archive_worker(args.retention_days, args.archive_dir)

    writer = QueueLogWriter(batch_size=args.batch_size, flush_interval=args.flush_interval)
    writer.start()
    try:
        if args.mode == "once":
            state_path = Path(args.state_file)
            state = None if args.no_state else load_state(state_path)
            collected = collect_once(targets, writer, args.lines, state)
            if state is not None:
                save_state(state_path, state)
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
        if args.mode == "once":
            archive_thread.join(timeout=5)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
