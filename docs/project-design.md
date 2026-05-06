# AI-OpsLog 项目设计

## 1. 项目定位

AI-OpsLog 当前是一个日志接收与分析 Demo，面向运维/SRE 学习与项目展示场景。它不直接采集生产日志，不自动执行命令，也不替代人工决策。

项目主要用于辅助初级运维理解报错日志、生成排障报告、沉淀故障案例。

## 2. 当前架构

```text
External Service Logs
    ↓
scripts/send_log.py / HTTP POST
    ↓
POST /logs/ingest
    ↓
Rule Parser
    ↓
Qwen AI Analysis
    ↓
Markdown Report
    ↓
reports/
```

## 3. 核心模块

- `backend/app/main.py`: FastAPI 路由入口
- `backend/app/parsers/`: Nginx / Docker 规则解析器
- `backend/app/services/ai_analysis_service.py`: 规则解析与 AI 分析编排
- `backend/app/services/qwen_client.py`: 通义千问 OpenAI 兼容接口调用
- `backend/app/services/report_service.py`: Markdown 报告生成与保存
- `backend/app/services/ingest_service.py`: 外部日志接收流程
- `scripts/send_log.py`: 模拟外部服务器发送日志
- `reports/`: 运行时报告输出目录

## 4. 报告持久化设计

Docker Compose 模式下，宿主机 `reports/` 目录挂载到容器 `/app/reports`。

服务通过 `REPORTS_DIR` 指定报告输出目录，避免相对路径导致容器内外保存位置不一致。

```text
REPORTS_DIR=/app/reports
./reports:/app/reports
```

本地直接运行时，如果不设置 `REPORTS_DIR`，默认保存到项目根目录 `reports/`。

`GET /reports/check` 用于检查当前报告目录是否存在、是否可写，以及当前 `.md` 报告数量。该接口不会读取报告正文，也不会返回任何 API Key。

## 5. 能力边界

- 不自动执行任何系统命令。
- 不替代人工排障和生产操作决策。
- 不直接采集生产日志。
- 不保存历史记录到数据库。
- 不提供权限控制、多租户或审计能力。
- AI 输出的命令只作为人工排查参考。

## 6. 后续方向

- 增加 Redis / Linux 系统日志解析
- 增加定时日志采集
- 增加 `tail -f` 增量采集
- 接入 Prometheus Alertmanager Webhook
- 增加简单 Web 页面
- 增加历史记录数据库
- 增加更多故障案例样例
