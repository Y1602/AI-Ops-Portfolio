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

## 6. API 接口说明

- `GET /health`: 健康检查
- `GET /config/check`: 检查 DashScope 配置是否已加载，不返回 API Key 原文
- `GET /qwen/test`: 测试通义千问连接
- `GET /reports/check`: 检查报告目录状态
- `POST /analyze`: 规则解析接口
- `POST /analyze/report`: 规则 Markdown 报告接口
- `POST /analyze/ai`: 通义千问辅助分析接口
- `POST /analyze/ai/report`: AI Markdown 报告接口
- `POST /analyze/ai/report/save`: 生成并保存 AI Markdown 报告
- `POST /logs/ingest`: 当前主要日志接收接口，用于接收外部服务日志并生成分析报告

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
