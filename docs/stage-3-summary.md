# Stage 3 Summary

## 1. 阶段目标

第三阶段目标是让 AI-OpsLog 支持接收 Prometheus Alertmanager Webhook 告警事件，并将告警内容转换为 AI 可分析的事件文本，复用现有规则分析、通义千问 AI 分析和 Markdown 报告生成链路。

本阶段不是部署完整 Prometheus / Alertmanager / Grafana 监控平台，而是先完成 Webhook 接收、告警解析、AI 分析和报告生成闭环。

## 2. 已完成功能

- 新增 `POST /alerts/alertmanager`
- 支持接收 Alertmanager Webhook JSON
- 支持单条 alert
- 支持多条 alerts 合并生成一份报告
- 支持字段缺省处理
- 支持空 alerts 返回 400
- 支持 firing 告警
- 支持 resolved 告警基础识别
- 支持 `webhook_status` 返回字段
- 支持 severity 到 `rule_severity` 的基础映射
- 支持 Alertmanager 告警文本转换
- 支持 `alertmanager_alert` 类型的 AI 分析上下文
- 支持 Alertmanager 专用 Markdown 报告结构
- 支持可选 Token 校验
- 支持 `ALERTMANAGER_WEBHOOK_TOKEN` 环境变量
- 支持 `X-Alertmanager-Token` 请求头
- 支持 Alertmanager 配置示例文档
- 支持 `examples/alertmanager.yml` 示例配置
- 原有 `/logs/ingest` 不受影响

## 3. 核心链路

```text
Alertmanager Webhook
    ↓
POST /alerts/alertmanager
    ↓
Token Check Optional
    ↓
Parse Alertmanager JSON
    ↓
Build Alert Event Text
    ↓
Rule Severity Mapping
    ↓
Qwen AI Analysis
    ↓
Markdown Alert Report
    ↓
reports/
```

## 4. 接口说明

```text
POST /alerts/alertmanager
```

请求来源可以是 Alertmanager Webhook，也可以是本地 `curl` 模拟请求。

示例请求文件：

- `examples/alertmanager_webhook_high_cpu.json`
- `examples/alertmanager_webhook_multi_alerts.json`
- `examples/alertmanager_webhook_missing_fields.json`
- `examples/alertmanager_webhook_empty_alerts.json`
- `examples/alertmanager_webhook_resolved_cpu.json`

返回示例：

```json
{
  "source": "nginx-web-01",
  "service_name": "HighCPUUsage",
  "env": "monitoring",
  "log_type": "alertmanager_alert",
  "rule_severity": "medium",
  "ai_risk_level": "medium",
  "report_path": "app/reports/ai_opslog_alertmanager_alert_nginx-web-01_HighCPUUsage_report_xxx.md",
  "message": "alertmanager webhook ingested and report generated",
  "alert_count": 1,
  "webhook_status": "firing"
}
```

## 5. Token 校验说明

Alertmanager Webhook Token 校验是可选的。

环境变量：

```env
ALERTMANAGER_WEBHOOK_TOKEN=
```

规则：

- 如果 `ALERTMANAGER_WEBHOOK_TOKEN` 为空，则不启用 Token 校验
- 如果 `ALERTMANAGER_WEBHOOK_TOKEN` 有值，则请求必须携带 Header：

```text
X-Alertmanager-Token: <token>
```

错误 Token 或缺失 Token 返回：

```json
{
  "error": "invalid alertmanager webhook token"
}
```

该 Token 校验只是基础保护示例，不是完整认证授权系统。

## 6. 测试记录

### 1. 健康检查

```bash
curl http://127.0.0.1:8000/health
```

结果：

```json
{"status":"ok","service":"ai-opslog"}
```

### 2. 单条 firing 告警

```bash
curl -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -H "X-Alertmanager-Token: change-me-demo-token" \
  -d @examples/alertmanager_webhook_high_cpu.json
```

结果：

- `alert_count=1`
- `webhook_status=firing`
- 返回 `report_path`
- `reports/` 生成 Markdown 报告

### 3. 多条 alerts

```bash
curl -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -H "X-Alertmanager-Token: change-me-demo-token" \
  -d @examples/alertmanager_webhook_multi_alerts.json
```

结果：

- `alert_count=2`
- `rule_severity=high`
- 多条告警合并生成一份报告

### 4. 字段缺失

```bash
curl -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -H "X-Alertmanager-Token: change-me-demo-token" \
  -d @examples/alertmanager_webhook_missing_fields.json
```

结果：

- 接口不崩溃
- 缺省字段使用默认值
- 仍然生成报告

### 5. 空 alerts

```bash
curl -i -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -H "X-Alertmanager-Token: change-me-demo-token" \
  -d @examples/alertmanager_webhook_empty_alerts.json
```

结果：

- HTTP 400
- 返回 `no alerts found in alertmanager webhook`
- 不生成报告

### 6. resolved 告警

```bash
curl -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -H "X-Alertmanager-Token: change-me-demo-token" \
  -d @examples/alertmanager_webhook_resolved_cpu.json
```

结果：

- `webhook_status=resolved`
- 返回 `report_path`
- 生成恢复告警分析报告

### 7. Token 缺失

```bash
curl -i -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -d @examples/alertmanager_webhook_high_cpu.json
```

结果：

- HTTP 401
- 返回 `invalid alertmanager webhook token`

### 8. Token 错误

```bash
curl -i -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -H "X-Alertmanager-Token: wrong-token" \
  -d @examples/alertmanager_webhook_high_cpu.json
```

结果：

- HTTP 401
- 返回 `invalid alertmanager webhook token`

### 9. 原有日志分析接口

```bash
python scripts/send_log.py \
  --server http://127.0.0.1:8000 \
  --source docker-host-01 \
  --service-name redis-container \
  --env dev \
  --log-type docker_log \
  --file examples/docker_port_conflict.log
```

结果：

- `/logs/ingest` 仍然正常
- Docker 日志分析报告正常生成

## 7. 当前边界

- 不部署 Prometheus
- 不部署 Alertmanager
- 不部署 Grafana
- 不配置真实告警规则
- 不做告警去重
- 不做告警静默
- 不做通知分发
- 不维护告警生命周期
- 不关联 firing 和 resolved 两次事件
- 不计算告警持续时间
- 不接数据库
- 不做 Web 页面
- 不自动执行修复命令
- Token 校验不是完整认证授权系统
- AI 输出只作为人工排查参考

## 8. 相关文档

- `docs/alertmanager-webhook.md`
- `docs/alertmanager-config-example.md`
- `docs/stage-3-plan.md`
- `examples/alertmanager.yml`

## 9. 后续方向

第三阶段到这里可以收尾。

后续方向建议进入第四阶段：历史记录存储。

第四阶段目标：接入 SQLite 或 MySQL，保存分析记录、风险等级、报告路径、来源服务、日志类型、告警状态等信息，支持后续查询和简单展示。

这里只写后续方向，不实现第四阶段功能。
