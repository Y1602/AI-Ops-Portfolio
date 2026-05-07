# AI-OpsLog 第四阶段总结：历史记录存储

## 1. 阶段目标

第四阶段目标是为 AI-OpsLog 增加结构化历史记录存储能力。

前三个阶段已经可以完成：

```text
日志 / 告警输入 -> 规则分析 -> AI 分析 -> Markdown 报告生成
```

但问题是：

```text
报告只保存在 reports/ 目录中，缺少结构化索引，不方便后续查询、展示和统计。
```

第四阶段解决的问题是：

```text
将每次日志分析和告警分析的关键元数据保存到 SQLite 数据库中，为后续查询接口和第五阶段展示页面做准备。
```

## 2. 技术选型

本阶段选择 SQLite，原因如下：

1. 不需要额外数据库服务
2. 适合本地 Demo 和简历项目展示
3. Docker Compose 环境下更容易验证
4. 使用 Python 标准库 `sqlite3`
5. 不引入 ORM，降低复杂度
6. 后续如果需要，可以迁移到 MySQL

当前阶段不是生产级数据库设计，重点是打通历史记录存储和查询闭环。

## 3. 新增配置

新增环境变量：

```env
AI_OPSLOG_DB_PATH=data/ai_opslog.db
```

说明：

1. 默认数据库路径是 `data/ai_opslog.db`
2. 数据库文件是运行时产物
3. `.gitignore` 已忽略 `data/*.db`、`data/*.sqlite`、`data/*.sqlite3`
4. `data/README.md` 用于保留目录说明
5. `.env.example` 已增加示例配置

## 4. 数据表设计

新增表：

```text
analysis_records
```

| 字段 | 含义 |
|---|---|
| id | 历史记录 ID |
| created_at | 创建时间 |
| source | 日志来源或告警来源 |
| service_name | 服务名或告警名 |
| env | 环境 |
| log_type | 日志或告警类型 |
| rule_severity | 规则侧风险等级 |
| ai_risk_level | AI 分析风险等级 |
| report_path | Markdown 报告路径 |
| message | 接口返回信息 |
| alert_count | Alertmanager 告警数量 |
| webhook_status | Alertmanager 告警状态 |

说明：

1. 当前只保存分析元数据
2. 不保存完整原始日志正文
3. 不保存 API Key
4. 不保存 Webhook Token

## 5. 写入链路

`/logs/ingest` 写入历史记录：

```text
日志输入 -> 规则分析 -> AI 分析 -> 生成 Markdown 报告 -> 写入 analysis_records
```

保存字段包括：

1. source
2. service_name
3. env
4. log_type
5. rule_severity
6. ai_risk_level
7. report_path
8. message

`/alerts/alertmanager` 写入历史记录：

```text
Alertmanager Webhook -> 告警字段解析 -> AI 分析 -> 生成 Markdown 报告 -> 写入 analysis_records
```

保存字段包括：

1. source
2. service_name
3. env
4. log_type = alertmanager_alert
5. rule_severity
6. ai_risk_level
7. report_path
8. message
9. alert_count
10. webhook_status

说明：

1. 空 alerts 返回 400，不写入
2. Token 校验失败返回 401，不写入
3. 只有成功生成报告后才写入

## 6. 查询接口

新增接口：

```text
GET /history/recent
GET /history/{id}
```

### GET /history/recent

功能：

查询最近历史记录。

支持参数：

```text
limit
log_type
source
service_name
env
rule_severity
ai_risk_level
webhook_status
```

说明：

1. 默认 limit 为 10
2. 最大 limit 为 100
3. 多个过滤条件之间是 AND 关系
4. 当前是精确匹配
5. 不支持模糊搜索
6. 不支持时间范围查询
7. 无匹配结果返回空列表

### GET /history/{id}

功能：

根据 ID 查询单条历史记录。

说明：

1. 查询到则返回 record
2. 查询不到返回 404
3. 不读取 Markdown 报告正文

## 7. 验证结果

已完成的验证项：

1. Docker Compose 启动正常
2. FastAPI 健康检查正常
3. SQLite 数据库文件正常生成
4. `analysis_records` 表正常创建
5. `/logs/ingest` 可正常生成报告并写入历史记录
6. `/alerts/alertmanager` 可正常生成报告并写入历史记录
7. `/history/recent` 可查询最近记录
8. `/history/{id}` 可查询单条记录
9. `/history/recent?limit=1` 正常
10. `log_type=docker_log` 过滤正常
11. `log_type=alertmanager_alert` 过滤正常
12. `webhook_status=firing` 过滤正常
13. 多条件过滤正常
14. 无匹配结果返回空列表
15. `limit=0` 返回 400
16. `limit=101` 返回 400
17. 原有 `/logs/ingest` 未受影响
18. 原有 `/alerts/alertmanager` 未受影响

## 8. 当前边界

1. 当前使用 SQLite，不是 MySQL
2. 当前不引入 ORM
3. 当前不做数据库迁移系统
4. 当前不保存完整原始日志
5. 当前不读取 Markdown 报告正文
6. 当前不做前端页面
7. 当前不做图表统计
8. 当前不做复杂分页
9. 当前不做时间范围查询
10. 当前不做模糊搜索
11. 当前不是生产级 AIOps 平台

## 9. 项目价值

本阶段的价值：

1. 从“只生成报告”升级为“可追踪历史记录”
2. 后续可以基于历史记录做查询、筛选和展示
3. 为第五阶段 Web 页面或 API 展示打基础
4. 项目链路更完整，更适合 GitHub 展示和简历表达

以上能力仍然面向 Demo / 学习项目定位，不夸大为生产级平台。

## 10. 下一阶段计划

第五阶段：展示与最终收尾

计划内容：

1. 简单 Web 页面或 API 展示
2. 展示最近分析记录
3. 支持查看单条记录详情
4. 整理 README 最终版
5. 补充示例截图
6. 准备 GitHub 展示说明
7. 准备简历项目描述

本阶段不实现第五阶段内容。
