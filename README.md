# AI-OpsLog

AI-OpsLog 是一个运维日志分析助手 Demo 项目。当前版本实现 FastAPI 后端服务：用户提交日志类型和日志文本，后端先进行规则解析，再可选生成 Markdown 报告，或调用阿里云百炼 / 通义千问 DashScope OpenAI 兼容接口输出结构化故障分析 JSON，并生成 AI Markdown 故障分析报告。

当前 Demo 不包含前端、数据库、Docker 化，也不会自动执行任何系统命令。

## 当前支持的日志类型

- `nginx_access`: Nginx access.log
- `nginx_error`: Nginx error.log
- `docker_log`: Docker 或容器运行日志

## 安装依赖

进入后端目录：

```bash
cd backend
pip install -r requirements.txt
```

如果安装较慢，可以按需使用镜像源：

```bash
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

## 配置通义千问 API Key

本项目使用阿里云百炼 / 通义千问 DashScope OpenAI 兼容接口。虽然依赖 `openai` Python SDK，但实际请求地址由 `DASHSCOPE_BASE_URL` 指向 DashScope，不是 OpenAI 官方服务。

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

系统环境变量优先级高于 `.env`。`.env` 已被 `.gitignore` 忽略，不要将真实 `DASHSCOPE_API_KEY` 提交到 GitHub。

## 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

默认服务地址：

```text
http://127.0.0.1:8000
```

## 接口说明

- `GET /health`: 健康检查
- `GET /config/check`: 检查 DashScope 配置是否已加载，不会返回 API Key 原文
- `POST /analyze`: 规则解析接口
- `POST /analyze/report`: 规则解析 Markdown 报告接口
- `POST /analyze/ai`: 通义千问辅助分析接口，返回结构化故障分析 JSON
- `POST /analyze/ai/report`: AI Markdown 报告接口，基于规则解析和通义千问分析结果生成 Markdown 故障分析报告

## 检查配置是否生效

```bash
curl -s http://127.0.0.1:8000/config/check | python -m json.tool
```

## curl 测试示例

curl 默认会将 JSON 响应压缩成一行显示，这不是接口错误。可以使用 `python -m json.tool` 或 `jq` 美化输出。

规则解析接口：

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{"log_type":"docker_log","log_text":"Error response from daemon: port is already allocated\ncontainer exited with code 1"}' \
  | python -m json.tool
```

规则 Markdown 报告接口：

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze/report" \
  -H "Content-Type: application/json" \
  -d '{"log_type":"docker_log","log_text":"Error response from daemon: port is already allocated\ncontainer exited with code 1"}' \
  | python -m json.tool
```

通义千问 AI 分析接口：

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze/ai" \
  -H "Content-Type: application/json" \
  -d '{"log_type":"docker_log","log_text":"Error response from daemon: port is already allocated\ncontainer exited with code 1"}' \
  | python -m json.tool
```

AI Markdown 报告接口：

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze/ai/report" \
  -H "Content-Type: application/json" \
  -d '{"log_type":"docker_log","log_text":"Error response from daemon: port is already allocated\ncontainer exited with code 1"}' \
  | python -m json.tool
```

说明：

- `markdown_report` 字段中是完整 Markdown 报告。
- 可以复制 `markdown_report` 内容保存为 `.md` 文件。
- AI 建议命令只用于人工排查参考。
- 本系统不会自动执行命令。

## 安全说明

- 本项目不会自动执行任何系统命令。
- AI 返回的 `related_commands` 只作为人工排查建议。
- AI 分析结果不能直接作为生产环境操作依据。
- `DASHSCOPE_API_KEY` 不应提交到 GitHub。

