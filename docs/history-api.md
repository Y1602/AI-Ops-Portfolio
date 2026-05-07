# AI-OpsLog 历史记录查询接口

第四阶段新增历史记录查询接口，用于查询 SQLite 中已经保存的分析元数据。

## 接口列表

- `GET /history/recent`：查询最近 10 条分析记录
- `GET /history/recent?limit=5`：限制返回数量，`limit` 范围为 1 到 100
- `GET /history/recent?log_type=alertmanager_alert&webhook_status=firing&limit=5`：按条件过滤最近分析记录
- `GET /history/{id}`：按记录 ID 查询单条分析记录

## 过滤参数

`GET /history/recent` 支持以下过滤参数：

- `log_type`
- `source`
- `service_name`
- `env`
- `rule_severity`
- `ai_risk_level`
- `webhook_status`
- `limit`

多个过滤条件同时存在时使用 `AND` 关系。当前过滤查询为精确匹配，不支持模糊搜索。

## 请求示例

```bash
curl -s http://127.0.0.1:8000/history/recent | python -m json.tool
curl -s "http://127.0.0.1:8000/history/recent?limit=1" | python -m json.tool
curl -s "http://127.0.0.1:8000/history/recent?log_type=alertmanager_alert&webhook_status=firing&limit=5" | python -m json.tool
curl -s http://127.0.0.1:8000/history/1 | python -m json.tool
```

## 响应示例

`GET /history/recent` 响应示例：

```json
{
  "records": [
    {
      "id": 2,
      "created_at": "2026-05-07T05:03:07.547467+00:00",
      "source": "nginx-web-01",
      "service_name": "HighCPUUsage",
      "env": "monitoring",
      "log_type": "alertmanager_alert",
      "rule_severity": "medium",
      "ai_risk_level": "medium",
      "report_path": "app/reports/xxx.md",
      "message": "alertmanager webhook ingested and report generated",
      "alert_count": 1,
      "webhook_status": "firing"
    }
  ],
  "count": 1
}
```

无匹配结果响应示例：

```json
{
  "records": [],
  "count": 0
}
```

`GET /history/{id}` 响应示例：

```json
{
  "record": {
    "id": 1,
    "created_at": "2026-05-07T05:02:44.222958+00:00",
    "source": "docker-host-01",
    "service_name": "redis-container",
    "env": "dev",
    "log_type": "docker_log",
    "rule_severity": "high",
    "ai_risk_level": "high",
    "report_path": "app/reports/xxx.md",
    "message": "log ingested and report generated",
    "alert_count": null,
    "webhook_status": null
  }
}
```

## 当前边界

- 只返回 SQLite 中保存的分析元数据
- 不返回完整原始日志
- 不读取 Markdown 报告正文
- 不支持模糊搜索
- 不支持时间范围查询
- 不提供分页系统
