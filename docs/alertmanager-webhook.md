# Alertmanager Webhook 接入说明

## 1. 功能说明

AI-OpsLog 第三阶段新增 `POST /alerts/alertmanager`，用于接收 Alertmanager Webhook 告警事件，并生成 AI 辅助分析报告。

当前接口会将 Alertmanager Webhook JSON 转换为告警事件文本，然后复用现有规则分析、通义千问 AI 分析和 Markdown 报告生成链路。

## 2. 当前边界

- 当前不部署 Prometheus
- 当前不部署 Alertmanager
- 当前不配置真实告警规则
- 当前只提供 Webhook 接收与分析接口
- 当前一个 Webhook 请求生成一份报告
- 当前不做告警去重
- 当前不做告警静默
- 当前不做通知分发
- 当前不自动执行修复命令

## 3. 示例请求

```bash
curl -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -d @examples/alertmanager_webhook_high_cpu.json
```

## 4. 示例返回

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

## 5. 查看报告

```bash
ls -lh reports/
```

## 6. 后续方向

- 接入真实 Alertmanager
- 增加更多告警类型规则
- 增加告警历史记录存储
- 增加告警报告查询接口
- 与 Prometheus/Grafana 演示环境联动
