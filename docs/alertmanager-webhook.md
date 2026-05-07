# Alertmanager Webhook 接入说明

## 1. 功能说明

AI-OpsLog 第三阶段新增 `POST /alerts/alertmanager`，用于接收 Alertmanager Webhook 告警事件，并生成 AI 辅助分析报告。

当前接口会将 Alertmanager Webhook JSON 转换为告警事件文本，然后复用现有规则分析、通义千问 AI 分析和 Markdown 报告生成链路。

`alertmanager_alert` 会生成偏向监控告警排查的 Markdown 报告，与普通 Docker/Nginx 日志报告不同。报告会突出告警基本信息、告警事件内容、AI 告警分析和人工排查建议。

## 2. 当前边界

- 当前不部署 Prometheus
- 当前不部署 Alertmanager
- 当前不配置真实告警规则
- 当前只提供 Webhook 接收与分析接口
- 当前一个 Webhook 请求生成一份报告
- 当前多条 alerts 会合并进一份报告
- 当前不做告警去重
- 当前不做告警恢复状态处理
- 当前不做告警静默
- 当前不做通知分发
- 当前不会执行任何系统命令

## 3. 单条告警测试

```bash
curl -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -d @examples/alertmanager_webhook_high_cpu.json
```

示例返回：

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
  "alert_count": 1
}
```

## 4. 多条告警测试

```bash
curl -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -d @examples/alertmanager_webhook_multi_alerts.json
```

预期：

- `alert_count=2`
- `rule_severity=high`
- 生成一份 Markdown 报告

## 5. 字段缺失测试

```bash
curl -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -d @examples/alertmanager_webhook_missing_fields.json
```

预期：

- 接口不崩溃
- 缺省字段使用默认值
- 仍可生成报告

## 6. 空 alerts 测试

```bash
curl -i -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -d @examples/alertmanager_webhook_empty_alerts.json
```

预期：

- 返回 400
- 返回 `no alerts found` 相关错误
- 不生成报告

## 7. resolved 告警测试

```bash
curl -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -d @examples/alertmanager_webhook_resolved_cpu.json
```

预期：

- `webhook_status` 或报告内容显示 `resolved`
- 报告中体现这是恢复告警
- 报告仍会生成
- 不做生命周期追踪
- 不关联历史 firing 事件

## 8. 查看报告

```bash
ls -lh reports/
```

## 9. Webhook Token 校验

AI-OpsLog 支持通过 `ALERTMANAGER_WEBHOOK_TOKEN` 启用简单 Token 校验。

如果未设置该环境变量，则不启用 Token 校验，方便本地 Demo 测试。

如果设置了该环境变量，请求需要携带：

```text
X-Alertmanager-Token: <token>
```

启用示例：

```env
ALERTMANAGER_WEBHOOK_TOKEN=change-me-demo-token
```

携带正确 Token 的请求示例：

```bash
curl -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -H "X-Alertmanager-Token: change-me-demo-token" \
  -d @examples/alertmanager_webhook_high_cpu.json
```

错误 Token 示例：

```bash
curl -i -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -H "X-Alertmanager-Token: wrong-token" \
  -d @examples/alertmanager_webhook_high_cpu.json
```

预期：

```text
HTTP/1.1 401 Unauthorized
```

该 Token 校验只是 Demo 项目的基础保护示例，不等于完整认证授权系统。

## 10. 告警报告结构

Alertmanager 告警报告主要包含：

- 告警基本信息：source、service_name、env、log_type、alert_count、rule_severity、AI risk level、report time
- 告警事件内容：展示转换后的 Alertmanager Webhook 事件文本
- AI 告警分析：偏向告警含义、影响范围、可能原因、风险判断和优先级
- 人工排查建议：展示排查步骤和只读排查命令

多条 alerts 会合并到同一份报告中，报告内容会包含 `Alert #1`、`Alert #2` 等告警详情。

AI 输出的命令或步骤仅作为人工排查参考，AI-OpsLog 不会自动执行任何系统命令。

## 11. 后续方向

- 接入真实 Alertmanager
- 增加更多告警类型规则
- 增加告警历史记录存储
- 增加告警报告查询接口
- 与 Prometheus/Grafana 演示环境联动
