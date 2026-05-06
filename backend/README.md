# AI-OpsLog Backend

这是 AI-OpsLog 的 FastAPI 后端 Demo。当前提供 `/health` 和 `/analyze` 两个接口，用于验证服务状态和解析日志文本。

## 安装

```bash
pip install -r requirements.txt
```

## 启动

```bash
uvicorn app.main:app --reload
```

## 调用示例

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"log_type\":\"docker_log\",\"log_text\":\"Error response from daemon: port is already allocated\"}"
```

