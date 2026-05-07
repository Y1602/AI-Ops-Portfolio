# AI-OpsLog

## 1. 项目简介

AI-OpsLog 是一个面向运维/SRE 场景的 AI 日志分析助手。它支持通过 HTTP 接口接收 Docker、Nginx 等服务日志，结合规则解析与通义千问大模型生成故障摘要、风险等级、可能原因、排查步骤、修复建议，并保存 Markdown 故障分析报告。

当前项目定位为 Demo / 学习项目，用于展示 AI 辅助运维日志分析的最小可运行闭环。

## 2. 当前阶段能力

- 支持 Docker 日志分析
- 支持 Nginx Error 日志分析
- 支持 Nginx Access 日志基础分析
- 支持规则解析
- 支持通义千问 AI 辅助分析
- 支持 Markdown 报告生成
- 支持报告保存到 `reports/`
- 支持 SQLite 历史记录存储
- 支持 Docker Compose 部署
- 支持 `scripts/send_log.py` 模拟外部日志发送

## 3. 项目架构

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

## 4. 技术栈

- Python
- FastAPI
- Docker / Docker Compose
- 阿里云百炼 / 通义千问 Qwen
- Markdown Report
- Shell / curl 测试

## 5. 快速开始

1. 克隆项目并进入目录。

2. 配置环境变量：

```bash
cp .env.example .env
```

编辑 `.env`，填入自己的通义千问 API Key：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
REPORTS_DIR=/app/reports
AI_OPSLOG_DB_PATH=data/ai_opslog.db
```

3. 使用 Docker Compose 启动：

```bash
docker compose up -d --build
```

4. 健康检查：

```bash
curl -s http://127.0.0.1:8000/health | python -m json.tool
```

5. Qwen 连通性测试：

```bash
curl -s http://127.0.0.1:8000/qwen/test | python -m json.tool
```

6. 安装客户端依赖并发送测试日志：

```bash
pip install -r requirements-client.txt
python scripts/send_log.py \
  --server http://127.0.0.1:8000 \
  --source docker-host-01 \
  --service-name redis-container \
  --env dev \
  --log-type docker_log \
  --file examples/docker_port_conflict.log
```

7. 查看生成报告：

```bash
ls -lh reports/
```

## 第二阶段：最近日志采集脚本

AI-OpsLog 第二阶段新增了 `scripts/collect_recent_logs.py`，用于读取指定日志文件最后 N 行内容，并发送到已有的 `POST /logs/ingest` 接口。后端收到日志后，会继续完成规则分析、通义千问 AI 分析，并生成 Markdown 故障分析报告。

使用示例：

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source nginx-web-01 \
  --service-name nginx \
  --env dev \
  --log-type nginx_error \
  --file examples/nginx_error_502.log \
  --lines 50
```

执行成功后，控制台会返回 `/logs/ingest` 接口响应结果，并在 `reports/` 目录下生成新的 Markdown 故障分析报告。

如果需要使用 cron 定时执行最近日志采集脚本，可以参考：[docs/cron-guide.md](docs/cron-guide.md)。

### dry-run 预览模式

`--dry-run` 是预览模式，用于在真正发送日志到 `/logs/ingest` 之前，先确认脚本读取到的日志内容是否正确。

dry-run 模式下：

- 会解析参数
- 会检查日志文件路径
- 会执行敏感文件拦截
- 会读取指定日志文件最后 N 行
- 会在终端打印读取到的日志内容
- 不会请求 `/logs/ingest`
- 不会触发 AI 分析
- 不会生成 `reports/` 报告

示例命令：

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source nginx-web-01 \
  --service-name nginx \
  --env dev \
  --log-type nginx_error \
  --file examples/nginx_error_502.log \
  --lines 10 \
  --dry-run
```

示例输出：

```text
[DRY-RUN] Read last 10 lines from examples/nginx_error_502.log
[DRY-RUN] The following log content will not be sent to server:
...
```

### output-log 运行日志

`--output-log` 用于记录 `collect_recent_logs.py` 每次运行结果，适合配合 cron 查看采集任务是否执行成功。

需要区分：

- `reports/` 是 AI 分析生成的 Markdown 故障报告目录
- `logs/` 是采集脚本自身的运行日志目录
- 两者不要混淆

示例命令：

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source nginx-web-01 \
  --service-name nginx \
  --env dev \
  --log-type nginx_error \
  --file examples/nginx_error_502.log \
  --lines 50 \
  --output-log logs/collect_recent_logs.log
```

示例运行日志：

```text
[2026-05-06 23:21:14] status=success source=nginx-web-01 service=nginx env=dev log_type=nginx_error file=examples/nginx_error_502.log lines=50 max_chars=20000 dry_run=false truncated=false report_path=app/reports/ai_opslog_nginx_error_nginx-web-01_nginx_report_xxx.md
```

### max-chars 内容长度限制

`--max-chars` 用于限制最终发送给后端或 dry-run 展示的日志内容长度，默认值为 `20000`。

如果日志内容超过 `max_chars`，脚本会保留最后 `max_chars` 个字符，并在日志内容前添加 `[TRUNCATED]` 提示。

保留末尾内容是因为日志排障通常更关注最近发生的错误，最新日志一般位于文件末尾。

示例命令：

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source nginx-web-01 \
  --service-name nginx \
  --env dev \
  --log-type nginx_error \
  --file examples/nginx_error_502.log \
  --lines 50 \
  --max-chars 5000 \
  --output-log logs/collect_recent_logs.log
```

当前能力边界：

- 当前只支持手动执行一次采集
- 当前不是实时日志采集器
- 当前不做 tail -f
- 当前不做定时任务
- 当前不做断点续读
- 当前不做日志去重
- 当前不做多文件批量采集
- 当前不执行任何系统命令
- 当前 AI 返回的命令只作为人工排查建议
- 当前会拦截敏感文件，例如 `.env`、`id_rsa`、`/etc/passwd`、`/etc/shadow`、`*.pem`、`*.key`

## 第三阶段：Alertmanager Webhook 接入

第三阶段新增 Alertmanager Webhook 接入能力，用于接收 Alertmanager 告警事件，并复用现有规则分析、通义千问 AI 分析和 Markdown 报告生成链路。

当前支持单条告警样例、多条 alerts 合并为一份报告、字段缺省处理；空 `alerts` 会返回错误。

当前支持 firing 和 resolved 告警事件的基础识别，resolved 事件会生成恢复告警分析报告，但不做告警生命周期追踪。

`alertmanager_alert` 会生成偏向监控告警排查的 Markdown 报告。

Alertmanager Webhook 支持可选 Token 校验，只保护 `POST /alerts/alertmanager`，不影响 `/logs/ingest`，详细说明见接入文档。

新增接口：

```text
POST /alerts/alertmanager
```

示例命令：

```bash
curl -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -d @examples/alertmanager_webhook_high_cpu.json
```

详细说明见：[docs/alertmanager-webhook.md](docs/alertmanager-webhook.md)、[docs/alertmanager-config-example.md](docs/alertmanager-config-example.md)、[docs/stage-3-plan.md](docs/stage-3-plan.md) 和 [docs/stage-3-summary.md](docs/stage-3-summary.md)。

## 第四阶段：SQLite 历史记录存储

第四阶段新增 SQLite 历史记录存储能力。成功的日志分析和 Alertmanager 告警分析会将关键元数据写入 `analysis_records` 表，便于后续增加查询接口和简单展示。

默认数据库路径为 `data/ai_opslog.db`。详细说明见：[docs/stage-4-plan.md](docs/stage-4-plan.md)。

### 历史记录查询

第四阶段第二步新增基础历史记录查询接口：

- `GET /history/recent`：查询最近分析记录
- `GET /history/recent?limit=5`：限制返回数量，`limit` 范围为 1 到 100
- `GET /history/{id}`：查询单条分析记录

当前查询接口只返回 SQLite 中保存的分析元数据，不返回完整原始日志，也不读取 Markdown 报告正文。详细说明见：[docs/history-api.md](docs/history-api.md)。

## 6. API 接口说明

- `GET /health`: 健康检查
- `GET /config/check`: 检查 DashScope 配置是否已加载，不返回 API Key 原文
- `GET /qwen/test`: 测试通义千问连接
- `GET /reports/check`: 检查报告目录状态
- `GET /history/recent`: 查询最近分析记录
- `GET /history/{id}`: 查询单条分析记录
- `POST /analyze`: 规则解析接口
- `POST /analyze/report`: 规则 Markdown 报告接口
- `POST /analyze/ai`: 通义千问辅助分析接口
- `POST /analyze/ai/report`: AI Markdown 报告接口
- `POST /analyze/ai/report/save`: 生成并保存 AI Markdown 报告
- `POST /logs/ingest`: 当前主要日志接收接口，用于接收外部服务日志并生成分析报告
- `POST /alerts/alertmanager`: 接收 Alertmanager Webhook 告警事件并生成分析报告

`POST /logs/ingest` 示例：

```bash
curl -s -X POST "http://127.0.0.1:8000/logs/ingest" \
  -H "Content-Type: application/json" \
  -d @examples/ingest_payload_docker.json \
  | python -m json.tool
```

## 7. 示例报告

`reports/` 目录用于保存运行时生成的 Markdown 报告。自动生成的 `reports/*.md` 默认不提交到 GitHub。

示例报告可查看：

- [Docker 端口冲突分析报告](docs/sample-reports/docker_port_conflict_report.md)

报告片段示例：

```text
- 日志类型：docker_log
- 规则风险等级：high
- AI 风险等级：high
- AI 故障摘要：Docker 容器启动失败，端口已被占用。
- 建议排查命令：ss -lntp, docker ps -a
```

## 8. 安全边界

- 本系统不会自动执行任何系统命令。
- AI 输出的命令只作为人工排查参考。
- AI 分析结果不能直接作为生产环境操作依据。
- API Key 通过环境变量或 `.env` 注入，不应提交到 GitHub。
- 当前项目定位为 Demo / 学习项目，不是完整 AIOps 系统。

## 9. 后续规划

- 增加 Redis / Linux 系统日志解析
- 增加定时日志采集
- 增加 `tail -f` 增量采集
- 接入 Prometheus Alertmanager Webhook
- 增加简单 Web 页面
- 增加历史记录数据库
- 增加更多故障案例样例
