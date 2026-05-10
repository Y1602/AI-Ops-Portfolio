# AI-OpsLog 历史记录 API

历史记录接口用于兼容早期分析历史查询能力。当前最终主流程以统一日志表 `logs` 和 Web 看板 `/dashboard/logs` 为主。

## 1. 查询最近历史记录

```text
GET /history/recent
```

支持参数：

- `limit`
- `log_type`
- `source`
- `service_name`
- `env`
- `rule_severity`
- `ai_risk_level`
- `webhook_status`

示例：

```bash
curl "http://127.0.0.1:8000/history/recent?limit=5"
```

响应示例：

```json
{
  "records": [
    {
      "id": 1,
      "created_at": "2026-05-10T12:00:00+00:00",
      "source": "docker-host-01",
      "service_name": "redis-container",
      "env": "dev",
      "log_type": "docker_log",
      "rule_severity": "high",
      "ai_risk_level": "high",
      "report_path": null,
      "message": "log ingested and analyzed without markdown report",
      "alert_count": null,
      "webhook_status": null
    }
  ],
  "count": 1
}
```

## 2. 查询单条历史记录

```text
GET /history/{id}
```

示例：

```bash
curl "http://127.0.0.1:8000/history/1"
```

查询不到时返回 404。

## 3. 当前边界

- 当前接口只返回历史元数据。
- 当前不读取 Markdown 报告正文。
- 当前不生成 Markdown 报告。
- `report_path` 字段为历史兼容字段，当前新数据通常为 `null`。
- 新的统一日志展示、搜索、统计和 AI 按需分析请使用 `/dashboard/logs`。
