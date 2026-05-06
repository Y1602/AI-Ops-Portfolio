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

方式一：使用环境变量

```bash
export DASHSCOPE_API_KEY="your_dashscope_api_key_here"
export DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export QWEN_MODEL="qwen-plus"
```

方式二：使用 `.env` 文件

```bash
cp .env.example .env
```

然后编辑项目根目录下的 `.env`：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
```

`.env` 已被 `.gitignore` 忽略，不要将真实 `DASHSCOPE_API_KEY` 提交到 GitHub。

## 使用 Docker Compose 启动

1. 复制环境变量文件：

```bash
cp .env.example .env
```

2. 编辑 `.env`，填入自己的通义千问 API Key：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
```

3. 构建并启动服务：

```bash
docker compose up -d --build
```

4. 查看容器状态：

```bash
docker compose ps
```

5. 查看日志：

```bash
docker compose logs -f ai-opslog-backend
```

6. 测试健康检查：

```bash
curl -s http://127.0.0.1:8000/health | python -m json.tool
```

7. 测试通义千问连接：

```bash
curl -s http://127.0.0.1:8000/qwen/test | python -m json.tool
```

8. 测试日志接收接口：

```bash
curl -s -X POST "http://127.0.0.1:8000/logs/ingest" \
  -H "Content-Type: application/json" \
  -d '{"source":"docker-host-01","service_name":"redis-container","env":"dev","log_type":"docker_log","log_text":"Error response from daemon: port is already allocated\ncontainer exited with code 1"}' \
  | python -m json.tool
```

9. 查看报告：

```bash
ls -lh reports/
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

## 安全说明

- 本项目不会自动执行任何系统命令。
- AI 返回的 `related_commands` 只作为人工排查建议。
- AI 分析结果不能直接作为生产环境操作依据。
- `DASHSCOPE_API_KEY` 不应提交到 GitHub，也不会写入镜像。

