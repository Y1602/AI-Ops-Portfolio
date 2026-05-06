# AI-OpsLog

AI-OpsLog 是一个运维日志分析助手 Demo 项目。当前版本实现 FastAPI 后端服务：接收外部服务日志、规则解析日志、调用阿里云百炼 / 通义千问 DashScope OpenAI 兼容接口辅助分析，并生成 Markdown 故障分析报告。

当前 Demo 不包含前端、数据库、Docker 化，也不会自动执行任何系统命令。

## 支持的日志类型

- `nginx_access`: Nginx access.log
- `nginx_error`: Nginx error.log
- `docker_log`: Docker 或容器运行日志

## 安装依赖

```bash
cd backend
pip install -r requirements.txt
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

## 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

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

`POST /logs/ingest`

用途：接收外部服务发送的日志，自动完成规则解析、通义千问分析、Markdown 报告生成和保存。

请求示例：

```json
{
  "source": "docker-host-01",
  "service_name": "redis-container",
  "env": "dev",
  "log_type": "docker_log",
  "log_text": "Error response from daemon: port is already allocated\ncontainer exited with code 1"
}
```

测试命令：

```bash
curl -s -X POST "http://127.0.0.1:8000/logs/ingest" \
  -H "Content-Type: application/json" \
  -d '{"source":"docker-host-01","service_name":"redis-container","env":"dev","log_type":"docker_log","log_text":"Error response from daemon: port is already allocated\ncontainer exited with code 1"}' \
  | python -m json.tool
```

也可以使用 `examples/ingest_payload_docker.json` 测试：

```bash
curl -s -X POST "http://127.0.0.1:8000/logs/ingest" \
  -H "Content-Type: application/json" \
  -d @examples/ingest_payload_docker.json \
  | python -m json.tool
```

查看报告：

```bash
ls -lh reports/
```

说明：

- `/logs/ingest` 用于模拟接收外部服务日志。
- `source` 用于标记日志来源主机或节点。
- `service_name` 用于标记服务名称。
- `log_type` 用于选择对应解析器。
- `env` 用于标记运行环境。
- AI-OpsLog 只接收和分析日志，不会自动执行任何系统命令。

## 保存 AI Markdown 报告

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze/ai/report/save" \
  -H "Content-Type: application/json" \
  -d '{"log_type":"docker_log","log_text":"Error response from daemon: port is already allocated\ncontainer exited with code 1"}' \
  | python -m json.tool
```

保存后查看：

```bash
ls -lh reports/
cat reports/生成的报告文件名.md
```

如果中文显示异常，请确保终端编码为 UTF-8。

## 测试通义千问连接

```bash
curl -s http://127.0.0.1:8000/qwen/test | python -m json.tool
```

如果返回 `success=true`，说明通义千问连接正常。

## 安全说明

- 本项目不会自动执行任何系统命令。
- AI 返回的 `related_commands` 只作为人工排查建议。
- AI 分析结果不能直接作为生产环境操作依据。
- `DASHSCOPE_API_KEY` 不应提交到 GitHub。

