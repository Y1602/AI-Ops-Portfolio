import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = "data/ai_opslog.db"
DEFAULT_ARCHIVE_DIR = "data/archives"
DEFAULT_RETENTION_DAYS = 7


def get_db_path() -> Path:
    return Path(os.getenv("AI_OPSLOG_DB_PATH", DEFAULT_DB_PATH))


def init_logs_db() -> None:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                source TEXT,
                host TEXT,
                log_level TEXT,
                message TEXT,
                AI_analysis_result TEXT,
                created_at TEXT
            );
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_logs_created_at ON logs(created_at);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_logs_source ON logs(source);")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(log_level);")
        connection.commit()


def save_log_record(record: dict[str, Any]) -> int:
    return save_log_records([record])[0]


def save_log_records(records: list[dict[str, Any]]) -> list[int]:
    if not records:
        return []

    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_records = [_normalize_record(record) for record in records]

    with sqlite3.connect(db_path) as connection:
        inserted_ids = []
        for normalized_record in normalized_records:
            cursor = connection.execute(
                """
                INSERT INTO logs (
                    timestamp,
                    source,
                    host,
                    log_level,
                    message,
                    AI_analysis_result,
                    created_at
                )
                VALUES (
                    :timestamp,
                    :source,
                    :host,
                    :log_level,
                    :message,
                    :AI_analysis_result,
                    :created_at
                );
                """,
                normalized_record,
            )
            inserted_ids.append(int(cursor.lastrowid))
        connection.commit()
        return inserted_ids


def archive_old_logs(
    retention_days: int = DEFAULT_RETENTION_DAYS,
    archive_dir: str | Path = DEFAULT_ARCHIVE_DIR,
) -> int:
    db_path = get_db_path()
    archive_path = Path(archive_dir)
    archive_path.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    cutoff_text = cutoff.isoformat()

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                id,
                timestamp,
                source,
                host,
                log_level,
                message,
                AI_analysis_result,
                created_at
            FROM logs
            WHERE COALESCE(timestamp, created_at) < ?
            ORDER BY id ASC;
            """,
            (cutoff_text,),
        ).fetchall()

        if not rows:
            return 0

        archive_file = archive_path / f"logs_archive_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        with archive_file.open("a", encoding="utf-8") as file:
            for row in rows:
                file.write(json.dumps(dict(row), ensure_ascii=False) + "\n")

        connection.execute(
            """
            DELETE FROM logs
            WHERE COALESCE(timestamp, created_at) < ?;
            """,
            (cutoff_text,),
        )
        connection.commit()
        return len(rows)


def get_recent_logs(
    limit: int = 50,
    source: str | None = None,
    host: str | None = None,
    log_level: str | None = None,
    time_from: str | None = None,
    time_to: str | None = None,
) -> list[dict[str, Any]]:
    normalized_limit = min(max(limit, 1), 200)
    filters = {
        "source": source,
        "host": host,
        "log_level": log_level,
    }
    where_clauses = []
    params: list[Any] = []

    for column, value in filters.items():
        if value:
            where_clauses.append(f"{column} = ?")
            params.append(value)

    if time_from:
        where_clauses.append("COALESCE(timestamp, created_at) >= ?")
        params.append(time_from)
    if time_to:
        where_clauses.append("COALESCE(timestamp, created_at) <= ?")
        params.append(time_to)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    params.append(normalized_limit)
    db_path = get_db_path()

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"""
            SELECT
                id,
                timestamp,
                source,
                host,
                log_level,
                message,
                AI_analysis_result,
                created_at
            FROM logs
            {where_sql}
            ORDER BY id DESC
            LIMIT ?;
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]


def get_log_record_by_id(log_id: int) -> dict[str, Any] | None:
    db_path = get_db_path()

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT
                id,
                timestamp,
                source,
                host,
                log_level,
                message,
                AI_analysis_result,
                created_at
            FROM logs
            WHERE id = ?;
            """,
            (log_id,),
        ).fetchone()
        return dict(row) if row else None


def update_log_ai_analysis_result(log_id: int, analysis_result: str) -> bool:
    db_path = get_db_path()

    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE logs
            SET AI_analysis_result = ?
            WHERE id = ?;
            """,
            (analysis_result, log_id),
        )
        connection.commit()
        return cursor.rowcount > 0


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp": record.get("timestamp"),
        "source": record.get("source"),
        "host": record.get("host"),
        "log_level": record.get("log_level") or "INFO",
        "message": record.get("message"),
        "AI_analysis_result": record.get("AI_analysis_result"),
        "created_at": record.get("created_at") or datetime.now(timezone.utc).isoformat(),
    }
