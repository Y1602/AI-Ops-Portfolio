# AI-OpsLog 后端说明

本目录是 AI-OpsLog 的 FastAPI 后端服务代码。

当前后端主要负责：

- 使用 SQLite 统一存储采集后的日志数据。
- 提供 Web 看板：`GET /dashboard/logs`。
- 支持按工具类型、主机、日志等级、时间范围和关键字筛选日志。
- 可选接入 Prometheus，只读展示指标快照。
- 支持单条日志按需 AI 分析：`POST /logs/{id}/analyze`。
- 保留历史记录接口和早期日志/告警接入接口，保证兼容性。

## 本地运行

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 主要接口

- `GET /health`
- `GET /dashboard/logs`
- `GET /metrics/prometheus`
- `POST /logs/{id}/analyze`
- `GET /history/recent`
- `GET /history/{id}`
- `POST /logs/ingest`
- `POST /alerts/alertmanager`
- `GET /qwen/test`

## 运行时数据

SQLite 数据库路径通过 `AI_OPSLOG_DB_PATH` 配置，默认路径为：

```text
data/ai_opslog.db
```

运行时数据库文件、归档日志和采集日志不应提交到 Git。

## 安全说明

- AI 输出只作为人工排查参考。
- 后端不会执行 AI 返回的修复命令。
- API Key 应通过 `.env` 或环境变量提供，不应提交到仓库。
