# AI-OpsLog

AI-OpsLog 是一个运维日志分析助手 Demo 项目。当前版本实现 FastAPI 后端服务：接收外部服务日志、规则解析日志、调用阿里云百炼 / 通义千问 DashScope OpenAI 兼容接口辅助分析，并生成 Markdown 故障分析报告。

当前 Demo 不包含前端和数据库，不会自动执行任何系统命令。

## 本地启动

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

本地直接运行可以不设置 `REPORTS_DIR`，默认保存到项目根目录 `reports/`。

## Docker Compose 启动

```bash
cp .env.example .env
docker compose up -d --build
```

Docker Compose 中使用：

```text
./reports:/app/reports
```

容器内报告保存路径：

```text
/app/reports
```

宿主机报告保存路径：

```text
./reports
```

Docker Compose 会设置：

```env
REPORTS_DIR=/app/reports
```

## 常用检查

健康检查：

```bash
curl -s http://127.0.0.1:8000/health | python -m json.tool
```

通义千问连接：

```bash
curl -s http://127.0.0.1:8000/qwen/test | python -m json.tool
```

检查报告目录：

```bash
curl -s http://127.0.0.1:8000/reports/check | python -m json.tool
```

查看宿主机报告：

```bash
ls -lh reports/
```

查看容器内报告：

```bash
docker exec -it ai-opslog-backend ls -lh /app/reports
```

## 接口说明

- `GET /health`: 健康检查
- `GET /config/check`: 检查 DashScope 配置是否已加载，不返回 API Key 原文
- `GET /qwen/test`: 测试通义千问连接
- `GET /reports/check`: 检查当前报告目录状态，不读取报告正文
- `POST /analyze`: 规则解析接口
- `POST /analyze/report`: 规则解析 Markdown 报告接口
- `POST /analyze/ai`: 通义千问辅助分析接口
- `POST /analyze/ai/report`: AI Markdown 报告接口
- `POST /analyze/ai/report/save`: 生成 AI 日志分析报告，并保存到 `reports/` 目录
- `POST /logs/ingest`: 接收外部服务日志，自动完成规则解析、通义千问分析、Markdown 报告生成和保存

## 日志接收测试

```bash
curl -s -X POST "http://127.0.0.1:8000/logs/ingest" \
  -H "Content-Type: application/json" \
  -d @examples/ingest_payload_docker.json \
  | python -m json.tool
```

## 日志发送脚本

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

## 安全说明

- 本项目不会自动执行任何系统命令。
- AI 返回的 `related_commands` 只作为人工排查建议。
- AI 分析结果不能直接作为生产环境操作依据。
- `DASHSCOPE_API_KEY` 不应提交到 GitHub，也不会写入镜像。
