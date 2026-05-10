# AI-OpsLog Backend

This directory contains the FastAPI backend for AI-OpsLog.

Current backend focus:

- Unified log storage in SQLite.
- Web dashboard at `GET /dashboard/logs`.
- Basic dashboard filters for source, host, log level, and time range.
- On-demand AI analysis for a single stored log via `POST /logs/{id}/analyze`.
- Compatibility endpoints for historical records and earlier ingest workflows.

## Local Run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Main Endpoints

- `GET /health`
- `GET /dashboard/logs`
- `POST /logs/{id}/analyze`
- `GET /history/recent`
- `GET /history/{id}`
- `POST /logs/ingest`
- `POST /alerts/alertmanager`
- `GET /qwen/test`

## Runtime Data

SQLite data is stored through `AI_OPSLOG_DB_PATH`, with the default path:

```text
data/ai_opslog.db
```

Runtime database files, archived logs, generated logs, and generated reports should not be committed.

## Safety Notes

- AI output is for manual troubleshooting reference only.
- The backend does not execute remediation commands returned by AI.
- API keys must be provided through `.env` or environment variables and must not be committed.
