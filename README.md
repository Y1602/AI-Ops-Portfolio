# AI-OpsLog

AI-OpsLog 是一个运维日志分析助手 Demo 项目。当前版本只实现 FastAPI 后端服务：用户提交日志类型和日志文本，后端根据日志类型调用对应解析器，返回结构化 JSON 结果，也可以生成 Markdown 分析报告。

当前 Demo 不包含前端、数据库、Docker，也不会调用任何 AI 或大模型 API。

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

### 日志结构化分析

```http
POST /analyze
```

请求体：

```json
{
  "log_type": "docker_log",
  "log_text": "Error response from daemon: port is already allocated\ncontainer exited with code 1"
}
```

### Markdown 报告分析

```http
POST /analyze/report
```

请求体与 `/analyze` 相同，返回字段包括：

```json
{
  "log_type": "docker_log",
  "severity": "high",
  "markdown_report": "# AI-OpsLog 日志分析报告\n..."
}
```

## curl 测试示例

curl 默认会将 JSON 响应压缩成一行显示，这不是接口错误。可以使用下面两种方式美化输出。

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

