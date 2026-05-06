# AI-OpsLog API

## GET /health

用途：健康检查。

返回示例：

```json
{
  "status": "ok",
  "service": "ai-opslog"
}
```

## GET /config/check

用途：检查 DashScope 配置是否加载，不返回 API Key 原文。

返回示例：

```json
{
  "dashscope_api_key_configured": true,
  "dashscope_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "qwen_model": "qwen-plus"
}
```

## GET /qwen/test

用途：测试通义千问连接。

返回示例：

```json
{
  "success": true,
  "model": "qwen-plus",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "response": {
    "status": "ok",
    "message": "qwen connected"
  }
}
```

## GET /reports/check

用途：检查报告目录状态，不读取报告正文。

返回示例：

```json
{
  "reports_dir": "/app/reports",
  "exists": true,
  "writable": true,
  "report_count": 3
}
```

## POST /analyze

用途：规则解析日志。

请求示例：

```json
{
  "log_type": "docker_log",
  "log_text": "Error response from daemon: port is already allocated\ncontainer exited with code 1"
}
```

返回示例：

```json
{
  "log_type": "docker_log",
  "total_lines": 2,
  "matched_keywords": {
    "port is already allocated": 1,
    "exited with code": 1
  },
  "severity": "high"
}
```

## POST /analyze/report

用途：基于规则解析结果生成 Markdown 报告。

请求体同 `/analyze`。

返回示例：

```json
{
  "log_type": "docker_log",
  "severity": "high",
  "markdown_report": "# AI-OpsLog 日志分析报告\n..."
}
```

## POST /analyze/ai

用途：规则解析后调用通义千问生成结构化故障分析 JSON。

请求体同 `/analyze`。

返回示例：

```json
{
  "log_type": "docker_log",
  "rule_result": {},
  "ai_result": {
    "summary": "Docker 容器启动失败，端口已被占用。",
    "risk_level": "high"
  }
}
```

## POST /analyze/ai/report

用途：生成 AI Markdown 报告。

请求体同 `/analyze`。

返回示例：

```json
{
  "log_type": "docker_log",
  "rule_severity": "high",
  "ai_risk_level": "high",
  "markdown_report": "# AI-OpsLog 智能日志分析报告\n..."
}
```

## POST /analyze/ai/report/save

用途：生成并保存 AI Markdown 报告。

请求体同 `/analyze`。

返回示例：

```json
{
  "log_type": "docker_log",
  "rule_severity": "high",
  "ai_risk_level": "high",
  "report_path": "/app/reports/ai_opslog_docker_log_report_20260506_153000.md",
  "markdown_report": "# AI-OpsLog 智能日志分析报告\n..."
}
```

## POST /logs/ingest

用途：当前主要日志接收接口。接收外部服务日志，自动完成规则解析、通义千问分析、Markdown 报告生成和保存。

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

返回示例：

```json
{
  "source": "docker-host-01",
  "service_name": "redis-container",
  "env": "dev",
  "log_type": "docker_log",
  "rule_severity": "high",
  "ai_risk_level": "high",
  "report_path": "reports/xxx.md",
  "message": "log ingested and report generated"
}
```
