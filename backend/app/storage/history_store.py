import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = "data/ai_opslog.db"


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
