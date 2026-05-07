# AI-OpsLog 历史记录查询接口

第四阶段第二步新增基础历史记录查询接口，用于查询 SQLite 中已经保存的分析元数据。

## 接口列表

- `GET /history/recent`：查询最近 10 条分析记录
- `GET /history/recent?limit=5`：限制返回数量，`limit` 范围为 1 到 100
- `GET /history/{id}`：按记录 ID 查询单条分析记录

## 请求示例

```bash
curl -s http://127.0.0.1:8000/history/recent | python -m json.tool
curl -s "http://127.0.0.1:8000/history/recent?limit=1" | python -m json.tool
curl -s http://127.0.0.1:8000/history/1 | python -m json.tool
```

## 响应示例

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

## 当前边界

- 只返回 SQLite 中保存的分析元数据
- 不返回完整原始日志
- 不读取 Markdown 报告正文
- 不支持按 `source`、`log_type` 或风险等级过滤
- 不提供分页系统
