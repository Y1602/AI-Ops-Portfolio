# AI-OpsLog 项目设计

## 项目背景

AI-OpsLog 是一个轻量级运维日志分析 Demo，用于接收外部服务日志，进行规则解析，调用通义千问辅助分析，并生成 Markdown 故障分析报告。

## 当前能力

- FastAPI 后端服务。
- `/logs/ingest` 外部日志接收接口。
- Nginx access、Nginx error、Docker log 三类规则解析器。
- 通义千问 AI 辅助分析。
- Markdown 报告生成与保存。
- `reports/` 目录沉淀典型故障报告。
- Docker Compose 部署。
- `scripts/send_log.py` 模拟外部服务发送日志。

## 报告持久化设计

AI-OpsLog 在 Docker Compose 模式下通过 volume 将宿主机 `reports/` 目录挂载到容器 `/app/reports`。

服务内部通过 `REPORTS_DIR` 环境变量指定报告输出目录，避免因相对路径导致报告保存位置不一致。

Docker Compose 推荐配置：

```text
REPORTS_DIR=/app/reports
./reports:/app/reports
```

本地直接运行时，如果不设置 `REPORTS_DIR`，默认保存到项目根目录 `reports/`。

`GET /reports/check` 用于检查当前报告目录是否存在、是否可写，以及当前 `.md` 报告数量。该接口不会读取报告正文，也不会返回任何 API Key。

## Docker 化部署

部署后服务监听 `8000` 端口，对外提供日志接收与分析接口。

环境变量通过 `.env` 文件传入，避免将 `DASHSCOPE_API_KEY` 写入代码或镜像。

## 暂不支持内容

- 不支持前端页面。
- 不支持数据库存储。
- 不支持自动修复。
- 不支持自动执行命令。
- 不支持生产环境日志采集 Agent。

## 后续计划

- 增加更多日志类型。
- 支持日志文件上传。
- 增加定时提交日志能力。
- 支持 `tail -f` 增量日志采集。
- 接入 Prometheus Alertmanager Webhook。
