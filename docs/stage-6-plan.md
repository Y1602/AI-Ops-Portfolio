# AI-OpsLog 第六阶段计划：集中日志收集与按需分析

## 1. 阶段目标

第六阶段目标是把 AI-OpsLog 整理为“集中日志收集、统一存储、Web 展示筛选、按需 AI 分析”的演示项目。

本阶段不做自动化处置，不做生产级权限系统，不生成新的 Markdown 报告。

## 2. 已完成模块

- 统一日志采集脚本：`scripts/collect_unified_logs.py`
- 多服务日志适配器：`backend/app/collectors/log_adapters.py`
- 支持 `once` 定时采集和 `tail` 实时跟随
- 支持多来源日志：系统日志、Zabbix、Prometheus、Grafana、Ansible、Docker、Kubernetes、Nginx、Redis、MySQL
- 支持日志等级：`FATAL`, `ERROR`, `WARN`, `INFO`, `DEBUG`
- SQLite `logs` 表统一存储
- 标准字段：`timestamp`, `source`, `host`, `log_level`, `message`, `AI_analysis_result`, `created_at`
- 默认保留最近 7 天日志，超出记录归档到 `data/archives/*.jsonl`
- `GET /dashboard/logs` 集中日志看板
- Web 筛选：工具类型、主机、日志等级、最近 N 小时、时间范围、返回数量
- 单条日志按需 AI 分析：`POST /logs/{id}/analyze`
- AI 分析结果在页面详情区展示，不写入 Markdown
- 历史接口 `/history/recent`, `/history/{id}` 保持兼容

## 3. 数据表

统一日志表：

```sql
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    source TEXT,
    host TEXT,
    log_level TEXT,
    message TEXT,
    AI_analysis_result TEXT,
    created_at TEXT
);
```

`AI_analysis_result` 字段当前保留给后续迭代。当前按需 AI 分析结果只返回给页面展示，不强制写入数据库。

## 4. 多服务日志支持

当前适配器支持：

- Syslog 风格时间解析
- ISO 时间解析
- Nginx Access/Error 时间解析
- Redis 常见时间格式解析
- Zabbix 常见时间格式解析
- Docker / Kubernetes JSON 日志字段提取
- Prometheus / Grafana / Ansible 常见 `level=...`、`ts=...` 风格字段提取
- HTTP 状态码到日志等级的基础映射

新增服务时优先在 `backend/app/collectors/log_adapters.py` 中增加解析规则，采集脚本保持只负责读取、排队和写入。

## 5. Web 页面

`GET /dashboard/logs` 默认展示最近 100 条日志。

页面展示字段：

- 时间
- 工具类型
- 主机
- 日志等级
- 日志消息摘要
- AI 分析状态
- AI 分析按钮

页面可读性优化：

- 时间格式化为 `YYYY-MM-DD HH:MM:SS`
- 工具类型中文展示
- 日志等级中文展示和 badge 展示
- 长日志内容截断，避免撑开表格

## 6. 当前边界

- 当前使用 SQLite，后续可替换为 PostgreSQL
- 当前 Web 筛选只覆盖基础字段
- 当前不做复杂分页
- 当前不做全文检索
- 当前不做 AI 自动分析
- 当前不执行系统命令
- 当前不做用户系统和权限系统
- 当前不生成新的 Markdown 报告
- 当前不是生产级 AIOps 平台

## 7. 后续可选增强

- 增加统一日志 JSON 查询 API
- 支持 PostgreSQL 存储
- 增加更细粒度的归档策略
- 增加 AI 分析结果持久化开关
- 增加批量日志分析队列
- 增加截图和演示视频
- 整理简历项目描述和面试讲解材料
