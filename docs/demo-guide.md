# AI-OpsLog Demo Guide

## 1. 启动服务

```bash
docker compose up -d --build
```

## 2. 检查服务状态

```bash
docker compose ps
```

```bash
curl -s http://127.0.0.1:8000/health | python -m json.tool
```

## 3. 检查通义千问连接

```bash
curl -s http://127.0.0.1:8000/qwen/test | python -m json.tool
```

## 4. 发送 Docker 故障日志

```bash
python scripts/send_log.py \
  --server http://127.0.0.1:8000 \
  --source docker-host-01 \
  --service-name redis-container \
  --env dev \
  --log-type docker_log \
  --file examples/docker_port_conflict.log
```

## 5. 发送 Nginx Error 日志

```bash
python scripts/send_log.py \
  --server http://127.0.0.1:8000 \
  --source nginx-web-01 \
  --service-name nginx \
  --env dev \
  --log-type nginx_error \
  --file examples/nginx_error_502.log
```

## 6. 查看报告

```bash
ls -lh reports/
```

```bash
cat reports/生成的报告文件名.md
```

### 使用 collect_recent_logs.py 采集最近 N 行日志

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source nginx-web-01 \
  --service-name nginx \
  --env dev \
  --log-type nginx_error \
  --file examples/nginx_error_502.log \
  --lines 50
```

然后查看报告：

```bash
ls -lh reports/
```

## 7. 检查报告目录挂载

```bash
curl -s http://127.0.0.1:8000/reports/check | python -m json.tool
```

```bash
docker exec -it ai-opslog-backend ls -lh /app/reports
```

# 第二阶段 Demo：采集最近 N 行日志并生成分析报告

## 1. 启动服务

```bash
docker compose up -d
```

## 2. 检查服务状态

```bash
curl http://127.0.0.1:8000/health
```

## 3. 执行最近日志采集脚本

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source nginx-web-01 \
  --service-name nginx \
  --env dev \
  --log-type nginx_error \
  --file examples/nginx_error_502.log \
  --lines 50
```

## dry-run 预览模式

dry-run 模式适合在发送日志分析前使用，用于确认当前脚本读取到的日志内容是否符合预期。

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source nginx-web-01 \
  --service-name nginx \
  --env dev \
  --log-type nginx_error \
  --file examples/nginx_error_502.log \
  --lines 10 \
  --dry-run
```

预期结果：

- 终端会打印读取到的日志内容
- 输出中会出现 `[DRY-RUN]` 标识
- 不会请求 `/logs/ingest`
- 不会生成 Markdown 报告

如果 dry-run 输出的日志内容确认无误，可以去掉 `--dry-run` 参数，正式发送到 `/logs/ingest` 进行规则分析、AI 分析和报告生成。

## 4. 查看接口返回结果

示例返回结构：

```json
{
  "source": "nginx-web-01",
  "service_name": "nginx",
  "env": "dev",
  "log_type": "nginx_error",
  "rule_severity": "high",
  "ai_risk_level": "high",
  "report_path": "app/reports/ai_opslog_nginx_error_nginx-web-01_nginx_report_xxx.md",
  "message": "log ingested and report generated"
}
```

## 5. 查看生成的报告

```bash
ls -lh reports/
```

如果 `reports/` 目录下出现新的 `.md` 文件，说明“日志文件读取 → 接口发送 → 规则分析 → AI 分析 → 报告生成”链路已经打通。

## 6. 敏感文件拦截测试

测试 `.env`：

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source test-host \
  --service-name test \
  --env dev \
  --log-type docker_log \
  --file .env \
  --lines 10
```

预期结果：

```text
Refuse to read sensitive file: .env
```

测试 `/etc/passwd`：

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source test-host \
  --service-name test \
  --env dev \
  --log-type docker_log \
  --file /etc/passwd \
  --lines 10
```

预期结果：

```text
Refuse to read sensitive file: /etc/passwd
```

## 7. 异常文件测试

测试不存在的文件：

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source test-host \
  --service-name test \
  --env dev \
  --log-type docker_log \
  --file examples/not_exists.log \
  --lines 10
```

预期结果：

```json
{
  "error": "log file does not exist",
  "file": "examples/not_exists.log"
}
```
