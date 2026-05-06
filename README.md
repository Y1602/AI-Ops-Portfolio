# AI-OpsLog

AI-OpsLog 是一个运维日志分析助手 Demo 项目。当前版本只实现后端服务：用户通过 FastAPI 接口提交日志类型和日志文本，服务端根据日志类型调用对应解析器，并返回结构化 JSON 解析结果。

当前 Demo 不包含前端、数据库、Docker，也不会调用任何大模型 API。

## 支持的日志类型

- `nginx_access`: Nginx access.log
- `nginx_error`: Nginx error.log
- `docker_log`: Docker 或容器运行日志

## 安装依赖

进入后端目录：

```bash
cd ai-opslog/backend
pip install -r requirements.txt
```

## 启动服务

```bash
uvicorn app.main:app --reload
```

默认服务地址：

```text
http://127.0.0.1:8000
```

## 接口说明

### 健康检查

```http
GET /health
```

返回：

```json
{
  "status": "ok",
  "service": "ai-opslog"
}
```

### 日志分析

```http
POST /analyze
```

请求体：

```json
{
  "log_type": "nginx_access",
  "log_text": "多行日志内容"
}
```

## curl 测试示例

### Nginx access.log

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"log_type\":\"nginx_access\",\"log_text\":\"127.0.0.1 - - [06/May/2026:10:00:00 +0800] \\\"GET /admin HTTP/1.1\\\" 404 123 \\\"-\\\" \\\"curl/8.0\\\"\"}"
```

### Nginx error.log

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"log_type\":\"nginx_error\",\"log_text\":\"2026/05/06 10:01:00 [error] 12#12: *1 connect() failed (111: Connection refused) while connecting to upstream\"}"
```

### Docker 日志

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"log_type\":\"docker_log\",\"log_text\":\"Error response from daemon: port is already allocated\\ncontainer exited with code 1\"}"
```

