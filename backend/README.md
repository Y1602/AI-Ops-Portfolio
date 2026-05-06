# AI-OpsLog Backend

这是 AI-OpsLog 的 FastAPI 后端 Demo。当前提供 `/health`、`/analyze` 和 `/analyze/report` 接口，用于验证服务状态、解析日志文本并生成 Markdown 分析报告。

当前后端不包含前端、数据库、Docker，也不会调用任何 AI 或大模型 API。

## 安装

```bash
pip install -r requirements.txt
```

## 启动

```bash
uvicorn app.main:app --reload
```

默认服务地址：

```text
http://127.0.0.1:8000
```

## 接口

- `GET /health`: 健康检查
- `POST /analyze`: 返回结构化 JSON 分析结果
- `POST /analyze/report`: 返回 Markdown 格式分析报告

## curl 测试

curl 默认会将 JSON 响应压缩成一行显示，这不是接口错误。可以通过 `python -m json.tool` 或 `jq` 美化输出。

方式一：使用 `python -m json.tool`

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{"log_type":"docker_log","log_text":"Error response from daemon: port is already allocated\ncontainer exited with code 1"}' \
  | python -m json.tool
```

方式二：如果系统安装了 `jq`，可以使用 `jq`

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{"log_type":"docker_log","log_text":"Error response from daemon: port is already allocated\ncontainer exited with code 1"}' \
  | jq
```

测试 `/analyze/report`：

```bash
curl -s -X POST "http://127.0.0.1:8000/analyze/report" \
  -H "Content-Type: application/json" \
  -d '{"log_type":"docker_log","log_text":"Error response from daemon: port is already allocated\ncontainer exited with code 1"}' \
  | python -m json.tool
```

