# AI-OpsLog

AI-OpsLog 是一个运维日志分析助手 Demo 项目。当前版本实现 FastAPI 后端服务：接收外部服务日志、规则解析日志、调用阿里云百炼 / 通义千问 DashScope OpenAI 兼容接口辅助分析，并生成 Markdown 故障分析报告。

当前 Demo 不包含前端和数据库，不会自动执行任何系统命令。

## 支持的日志类型

- `nginx_access`: Nginx access.log
- `nginx_error`: Nginx error.log
- `docker_log`: Docker 或容器运行日志

## 本地启动

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 配置通义千问 API Key

```bash
cp .env.example .env
```

编辑项目根目录下的 `.env`：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
```

`.env` 已被 `.gitignore` 忽略，不要将真实 `DASHSCOPE_API_KEY` 提交到 GitHub。

## 使用 Docker Compose 启动

```bash
cp .env.example .env
docker compose up -d --build
```

查看容器状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f ai-opslog-backend
```

测试健康检查：

```bash
curl -s http://127.0.0.1:8000/health | python -m json.tool
```

测试通义千问连接：

```bash
curl -s http://127.0.0.1:8000/qwen/test | python -m json.tool
```

`reports/` 会挂载到容器内 `/app/reports`，容器生成的 Markdown 报告会持久化到宿主机。

## 接口说明

- `GET /health`: 健康检查
- `GET /config/check`: 检查 DashScope 配置是否已加载，不返回 API Key 原文
- `GET /qwen/test`: 测试通义千问连接
- `POST /analyze`: 规则解析接口
- `POST /analyze/report`: 规则解析 Markdown 报告接口
- `POST /analyze/ai`: 通义千问辅助分析接口
- `POST /analyze/ai/report`: AI Markdown 报告接口
- `POST /analyze/ai/report/save`: 生成 AI 日志分析报告，并保存到 `reports/` 目录
- `POST /logs/ingest`: 接收外部服务日志，自动完成规则解析、通义千问分析、Markdown 报告生成和保存

## 日志接收接口

```bash
curl -s -X POST "http://127.0.0.1:8000/logs/ingest" \
  -H "Content-Type: application/json" \
  -d @examples/ingest_payload_docker.json \
  | python -m json.tool
```

字段说明：

- `source`: 日志来源主机或节点
- `service_name`: 服务名称
- `log_type`: 选择对应解析器
- `env`: 运行环境
- `log_text`: 多行日志内容

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

## 查看报告

```bash
ls -lh reports/
cat reports/生成的报告文件名.md
```

如果中文显示异常，请确保终端编码为 UTF-8。

## 安全说明

- 本项目不会自动执行任何系统命令。
- AI 返回的 `related_commands` 只作为人工排查建议。
- AI 分析结果不能直接作为生产环境操作依据。
- `DASHSCOPE_API_KEY` 不应提交到 GitHub，也不会写入镜像。
