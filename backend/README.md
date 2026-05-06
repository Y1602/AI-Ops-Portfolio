# AI-OpsLog Backend

这是 AI-OpsLog 的 FastAPI 后端 Demo。当前提供 `/health`、`/config/check`、`/analyze`、`/analyze/report`、`/analyze/ai` 和 `/analyze/ai/report` 接口，用于验证服务状态、检查 DashScope 配置、规则解析日志、生成规则 Markdown 报告、调用通义千问辅助分析，并生成 AI Markdown 故障分析报告。

当前后端不包含前端、数据库、Docker 化，也不会自动执行任何系统命令。

## 安装

```bash
pip install -r requirements.txt
```

## 配置通义千问 API Key

本项目使用阿里云百炼 / 通义千问 DashScope OpenAI 兼容接口。虽然依赖 `openai` Python SDK，但实际调用的是 DashScope 兼容接口，不是 OpenAI 官方服务。

方式一：使用环境变量

```bash
export DASHSCOPE_API_KEY="your_dashscope_api_key_here"
export DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export QWEN_MODEL="qwen-plus"
```

方式二：使用 `.env` 文件

在项目根目录执行：

```bash
cp .env.example .env
```

然后编辑 `.env`：

```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
```

系统环境变量优先级高于 `.env`。`.env` 已被 `.gitignore` 忽略，不要提交真实 API Key。

## 启动

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

默认服务地址：

```text
http://127.0.0.1:8000
```

## 接口

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

## curl 测试

curl 默认会将 JSON 响应压缩成一行显示，这不是接口错误。可以通过 `python -m json.tool` 或 `jq` 美化输出。

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

