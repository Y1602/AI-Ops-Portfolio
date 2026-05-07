# AI-OpsLog 第四阶段开发计划

## 1. 阶段目标

第四阶段目标是增加历史记录存储能力，将每次日志分析或告警分析的关键元数据保存到 SQLite 数据库，为后续查询接口和简单展示做准备。

## 2. 第一步：SQLite 写入闭环

第一步实现最小 SQLite 写入闭环：

- 初始化数据库
- 创建 `analysis_records` 表
- `/logs/ingest` 成功后写入记录
- `/alerts/alertmanager` 成功后写入记录

## 3. 第二步：历史记录查询接口

第二步新增基础历史记录查询接口：

- `GET /history/recent`
- `GET /history/recent?limit=5`
- `GET /history/{id}`

当前只支持基础查询，不读取 Markdown 报告正文，也不返回完整原始日志。

## 4. 第三步：历史记录过滤查询

已支持在 `GET /history/recent` 中按以下字段过滤：

- `log_type`
- `source`
- `service_name`
- `env`
- `rule_severity`
- `ai_risk_level`
- `webhook_status`

当前只支持精确匹配，不支持模糊搜索和时间范围查询。

## 5. 数据库字段

`analysis_records` 表字段如下：

| 字段 | 含义 |
| --- | --- |
| `id` | 自增主键 |
| `created_at` | 记录创建时间 |
| `source` | 日志来源或告警实例 |
| `service_name` | 服务名或告警名 |
| `env` | 环境 |
| `log_type` | 日志类型，例如 `docker_log`、`nginx_error`、`alertmanager_alert` |
| `rule_severity` | 规则风险等级 |
| `ai_risk_level` | AI 风险等级 |
| `report_path` | Markdown 报告路径 |
| `message` | 接口返回信息 |
| `alert_count` | Alertmanager 告警数量，普通日志为空 |
| `webhook_status` | Alertmanager Webhook 状态，例如 `firing`、`resolved`，普通日志为空 |

## 6. 当前边界

- 当前使用 SQLite
- 当前不接 MySQL
- 当前不引入 ORM
- 当前不做数据库迁移系统
- 当前只做基础查询和基础过滤查询接口
- 当前不做模糊搜索
- 当前不做时间范围查询
- 当前不做分页系统
- 当前不做 Web 页面
- 当前只保存分析元数据，不保存完整原始日志
- 当前不保存 API Key
- 当前不保存 Webhook Token

## 7. 后续计划

- 支持时间范围查询
- 支持简单统计接口
- 支持按时间倒序查询
- 后续可选 MySQL 替换 SQLite
