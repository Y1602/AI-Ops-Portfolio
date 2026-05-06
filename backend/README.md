# AI-OpsLog Backend

这是 AI-OpsLog 的 FastAPI 后端 Demo。当前提供规则解析、规则 Markdown 报告、通义千问辅助分析、AI Markdown 报告、AI 报告保存和 Qwen 连通性测试能力。

当前后端不包含前端、数据库、Docker 化，也不会自动执行任何系统命令。

## 安装

```bash
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

不要提交真实 API Key。

## 启动

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
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

## 保存 AI Markdown 报告

用途：生成 AI 日志分析报告，并保存到 `reports/` 目录。

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze/ai/report/save" \
  -H "Content-Type: application/json" \
  -d '{"log_type":"docker_log","log_text":"Error response from daemon: port is already allocated\ncontainer exited with code 1"}' \
  | python -m json.tool
```

查看保存的报告：

```bash
ls -lh reports/
cat reports/生成的报告文件名.md
```

如果中文显示异常，请确保终端编码为 UTF-8。

## 使用示例日志生成报告

建议使用 `examples/` 目录中的日志样例生成报告。

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze/ai/report/save" \
  -H "Content-Type: application/json" \
  -d "{\"log_type\":\"docker_log\",\"log_text\":\"$(cat examples/docker_port_conflict.log)\"}" \
  | python -m json.tool
```

如果多行日志通过 curl 传参不方便，可以先手动复制 `examples/` 中的日志内容进行测试。

## 测试通义千问连接

```bash
curl -s http://127.0.0.1:8000/qwen/test | python -m json.tool
```

## 为什么 JSON 里中文显示为 \uXXXX？

这是 JSON 默认转义，不是乱码。可以使用下面命令直接查看 Markdown 报告正文：

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze/ai/report" \
  -H "Content-Type: application/json" \
  -d '{"log_type":"docker_log","log_text":"Error response from daemon: port is already allocated\ncontainer exited with code 1"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['markdown_report'])"
```

也可以保存为 Markdown 文件：

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze/ai/report" \
  -H "Content-Type: application/json" \
  -d '{"log_type":"docker_log","log_text":"Error response from daemon: port is already allocated\ncontainer exited with code 1"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['markdown_report'])" \
  > reports/docker_port_conflict_ai_report.md
```

## 安全说明

- 本项目不会自动执行任何系统命令。
- AI 返回的 `related_commands` 只作为人工排查建议。
- AI 分析结果不能直接作为生产环境操作依据。
- `DASHSCOPE_API_KEY` 不应提交到 GitHub。

