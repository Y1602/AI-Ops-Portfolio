import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = "data/ai_opslog.db"

ANALYSIS_RECORD_COLUMNS = """
    id,
    created_at,
    source,
    service_name,
    env,
    log_type,
    rule_severity,
    ai_risk_level,
    report_path,
    message,
    alert_count,
    webhook_status
"""


def get_db_path() -> Path:
    return Path(os.getenv("AI_OPSLOG_DB_PATH", DEFAULT_DB_PATH))


def init_db() -> None:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                source TEXT,
                service_name TEXT,
                env TEXT,
                log_type TEXT,
                rule_severity TEXT,
                ai_risk_level TEXT,
                report_path TEXT,
                message TEXT,
                alert_count INTEGER,
                webhook_status TEXT
            );
            """
        )
        connection.commit()


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def save_analysis_record(record: dict[str, Any]) -> int:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    created_at = record.get("created_at") or datetime.now(timezone.utc).isoformat()
    values = {
        "created_at": created_at,
        "source": record.get("source"),
        "service_name": record.get("service_name"),
        "env": record.get("env"),
        "log_type": record.get("log_type"),
        "rule_severity": record.get("rule_severity"),
        "ai_risk_level": record.get("ai_risk_level"),
        "report_path": record.get("report_path"),
        "message": record.get("message"),
        "alert_count": record.get("alert_count"),
        "webhook_status": record.get("webhook_status"),
    }

    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO analysis_records (
                created_at,
                source,
                service_name,
                env,
                log_type,
                rule_severity,
                ai_risk_level,
                report_path,
                message,
                alert_count,
                webhook_status
            )
            VALUES (
                :created_at,
                :source,
                :service_name,
                :env,
                :log_type,
                :rule_severity,
                :ai_risk_level,
                :report_path,
                :message,
                :alert_count,
                :webhook_status
            );
            """,
            values,
        )
        connection.commit()
        return int(cursor.lastrowid)


def get_recent_analysis_records(
    limit: int = 10,
    log_type: str | None = None,
    source: str | None = None,
    service_name: str | None = None,
    env: str | None = None,
    rule_severity: str | None = None,
    ai_risk_level: str | None = None,
    webhook_status: str | None = None,
) -> list[dict[str, Any]]:
    normalized_limit = min(max(limit, 1), 100)
    db_path = get_db_path()
    filters = {
        "log_type": log_type,
        "source": source,
        "service_name": service_name,
        "env": env,
        "rule_severity": rule_severity,
        "ai_risk_level": ai_risk_level,
        "webhook_status": webhook_status,
    }
    where_clauses = []
    params: list[Any] = []

    for column, value in filters.items():
        if value:
            where_clauses.append(f"{column} = ?")
            params.append(value)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    params.append(normalized_limit)

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"""
            SELECT
                {ANALYSIS_RECORD_COLUMNS}
            FROM analysis_records
            {where_sql}
            ORDER BY id DESC
            LIMIT ?;
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]


def get_analysis_record_by_id(record_id: int) -> dict[str, Any] | None:
    db_path = get_db_path()

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            f"""
            SELECT
                {ANALYSIS_RECORD_COLUMNS}
            FROM analysis_records
            WHERE id = ?;
            """,
            (record_id,),
        ).fetchone()
        return _row_to_dict(row)
