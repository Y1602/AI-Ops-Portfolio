# AI-OpsLog

AI-OpsLog 是一个运维日志分析助手 Demo 项目。当前版本实现 FastAPI 后端服务：用户提交日志类型和日志文本，后端先进行规则解析，再可选生成 Markdown 报告，或调用阿里云百炼 / 通义千问 DashScope OpenAI 兼容接口输出结构化故障分析 JSON。

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

## 环境变量

项目根目录提供 [.env.example](E:/Git/AI-Ops-Portfolio/.env.example) 示例文件。不要提交真实 API Key。

Linux / macOS：

```bash
export DASHSCOPE_API_KEY="your_dashscope_api_key_here"
export DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
export QWEN_MODEL="qwen-plus"
```

PowerShell：

```powershell
$env:DASHSCOPE_API_KEY="your_dashscope_api_key_here"
$env:DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
$env:QWEN_MODEL="qwen-plus"
```

也可以在项目根目录创建本地 `.env` 文件，内容参考 `.env.example`。真实 `.env` 已被 `.gitignore` 忽略。

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
- `POST /analyze`: 规则解析接口
- `POST /analyze/report`: 规则报告接口，返回 Markdown 报告
- `POST /analyze/ai`: 通义千问辅助分析接口，返回结构化故障分析 JSON

AI 相关说明：

- 本项目使用阿里云百炼 / 通义千问 DashScope OpenAI 兼容接口。
- 虽然依赖 `openai` Python SDK，但实际请求地址由 `DASHSCOPE_BASE_URL` 指向 DashScope，不是 OpenAI 官方服务。
- 本项目不会自动执行任何系统命令。
- AI 输出中的命令只作为人工排查建议。
- AI 分析结果需要人工确认，不能直接作为生产环境操作依据。

## curl 测试示例

curl 默认会将 JSON 响应压缩成一行显示，这不是接口错误。可以使用 `python -m json.tool` 或 `jq` 美化输出。

规则解析接口：

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{"log_type":"docker_log","log_text":"Error response from daemon: port is already allocated\ncontainer exited with code 1"}' \
  | python -m json.tool
```

Markdown 报告接口：

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

如果系统安装了 `jq`，也可以将 `python -m json.tool` 替换为 `jq`。

