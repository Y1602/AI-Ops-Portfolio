# AI-OpsLog Backend

这是 AI-OpsLog 的 FastAPI 后端 Demo。当前提供日志接收、规则解析、规则 Markdown 报告、通义千问辅助分析、AI Markdown 报告、AI 报告保存和 Qwen 连通性测试能力。

当前后端不包含前端和数据库，不会自动执行任何系统命令。

## 本地启动

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Docker 镜像

后端 Dockerfile 位于 `backend/Dockerfile`，只复制 `requirements.txt` 和 `app/` 目录，不复制 `.env`。

推荐在项目根目录使用 Docker Compose 启动：

```bash
cp .env.example .env
docker compose up -d --build
```

## 接口

- `GET /health`: 健康检查
- `GET /config/check`: 检查 DashScope 配置是否已加载，不返回 API Key 原文
- `GET /qwen/test`: 测试通义千问连接
- `POST /analyze`: 规则解析接口
- `POST /analyze/report`: 规则解析 Markdown 报告接口
- `POST /analyze/ai`: 通义千问辅助分析接口
- `POST /analyze/ai/report`: AI Markdown 报告接口
- `POST /analyze/ai/report/save`: 生成 AI 日志分析报告，并保存到 `reports/` 目录
- `POST /logs/ingest`: 接收外部服务日志，自动完成规则解析、通义千问分析、Markdown 报告生成和保存

## 测试日志接收

```bash
curl -s -X POST "http://127.0.0.1:8000/logs/ingest" \
  -H "Content-Type: application/json" \
  -d @examples/ingest_payload_docker.json \
  | python -m json.tool
```

## 使用日志发送脚本模拟外部服务接入

安装客户端依赖：

```bash
pip install -r requirements-client.txt
```

发送 Docker 日志：

```bash
python scripts/send_log.py \
  --server http://127.0.0.1:8000 \
  --source docker-host-01 \
  --service-name redis-container \
  --env dev \
  --log-type docker_log \
  --file examples/docker_port_conflict.log
```

发送 Nginx Error 日志：

```bash
python scripts/send_log.py \
  --server http://127.0.0.1:8000 \
  --source nginx-web-01 \
  --service-name nginx \
  --env dev \
  --log-type nginx_error \
  --file examples/nginx_error_502.log
```

说明：

- 该脚本用于模拟外部服务器向 AI-OpsLog 发送日志。
- 当前不是实时采集。
- 后续可以扩展为定时读取日志或 `tail -f` 增量采集。
- AI-OpsLog 只负责接收、分析、生成报告，不会自动执行任何系统命令。

## 安全说明

- 本项目不会自动执行任何系统命令。
- AI 返回的 `related_commands` 只作为人工排查建议。
- AI 分析结果不能直接作为生产环境操作依据。
- `DASHSCOPE_API_KEY` 不应提交到 GitHub，也不会写入 Dockerfile 或镜像。
