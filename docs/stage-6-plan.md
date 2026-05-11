# AI-OpsLog 第六阶段计划：集中日志收集与按需分析

## 1. 阶段目标

第六阶段目标是把 AI-OpsLog 整理为“集中日志收集、统一存储、Web 展示筛选、历史统计、按需 AI 分析”的演示项目。

本阶段不做自动化处置，不做生产级权限系统，不生成 Markdown 报告。

当前第六阶段已完成，项目进入 GitHub 展示和简历整理阶段。最终总结见：

```text
docs/project-final-summary.md
```

## 2. 已完成模块

- 统一日志采集脚本：`scripts/collect_unified_logs.py`
- 多服务日志适配器：`backend/app/collectors/log_adapters.py`
- 支持 `once` 定时采集和 `tail` 实时跟随
- 支持多来源日志：系统日志、Zabbix、Prometheus、Grafana、Ansible、Docker、Kubernetes、Nginx、Redis、MySQL
- 支持日志等级：`FATAL`、`ERROR`、`WARN`、`INFO`、`DEBUG`
- SQLite `logs` 表统一存储
- 标准字段：`timestamp`、`source`、`host`、`log_level`、`message`、`AI_analysis_result`、`created_at`
- 默认保留最近 7 天日志，超出记录归档到 `data/archives/*.jsonl`
- `GET /dashboard/logs` 集中日志看板
- Web 筛选：工具类型、主机、日志等级、最近 N 小时、时间范围、消息关键字、返回数量、页码
- Web 统计：按日志等级和工具类型展示过去 24 小时或 7 天分布
- Web 可读性优化：默认最近 24 小时、默认 10 条、消息列省略、关键字高亮、高风险行高亮
- 单条日志按需 AI 分析：`POST /logs/{id}/analyze`
- AI 分析前提取关键报错摘要、命中关键词和上下文
- AI 分析会按日志来源和关键词匹配 `docs/runbooks/` 中的故障手册作为参考
- 历史接口 `/history/recent`、`/history/{id}` 保持兼容
- 自动采集说明文档：`docs/auto-collection.md`

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

## 4. Web 页面

`GET /dashboard/logs` 默认展示最近 24 小时的 10 条日志。

支持查询参数：

- `source`
- `host`
- `log_level`
- `recent_hours`
- `time_from`
- `time_to`
- `keyword`
- `limit`
- `page`

多个筛选条件之间使用 AND 关系。`keyword` 会在 `message` 字段中做基础包含匹配。

统计模块：

- 日志等级分布：`FATAL`、`ERROR`、`WARN`、`INFO`、`DEBUG`
- 工具类型分布：系统日志、Zabbix、Prometheus、Grafana、Ansible、Docker、Kubernetes、Nginx、Redis、MySQL
- 时间范围：过去 24 小时、过去 7 天
- 展示方式：纯 HTML/CSS 条形图
- 交互优化：鼠标悬停显示数量和占比，点击统计项可快速筛选日志列表

展示层优化：
- 时间统一显示为 `YYYY-MM-DD HH:MM:SS`
- 日志等级、工具类型、AI 状态中文显示
- 日志消息列超过 3 行折叠，悬停显示完整内容，点击可展开/收起
- 关键字搜索结果在消息列高亮显示
- `FATAL` / `ERROR` 日志行红色高亮，`WARN` 日志行橙色高亮
- 筛选栏包含工具类型、主机、等级、最近 N 小时、时间范围、关键字、数量和操作按钮
- AI 分析结果面板使用卡片布局，风险等级色块展示，建议内容可折叠/展开
- AI 分析结果支持复制为文本和浏览器侧导出 `.txt` 文件，不在服务端生成报告
- 分页工具栏包含总数、页码、上一页/下一页和跳页输入
- 页面每 60 秒自动刷新一次，并保留当前筛选条件

性能优化：
- SQLite 启用 WAL、`busy_timeout`、`synchronous=NORMAL` 和常用索引
- 日志写入使用队列缓冲和批量插入
- `once` 采集模式使用 offset state，只读取新增日志
- 归档操作后台执行，降低对采集主流程的阻塞
- Web 保持服务端分页，控制单页 DOM 数量
- AI 分析按钮请求期间禁用，避免重复触发

按需 AI 分析结果展示：

- 问题摘要
- 关键报错
- 参考 Runbook
- 关键证据
- 命中关键词
- 根因假设
- 风险等级
- 可能原因
- 排查建议
- 验证方法
- 操作风险提示
- 后续预防建议
- 补充说明

## 5. 自动采集

Web 服务启动后不会自动采集日志。日志采集由 `scripts/collect_unified_logs.py` 完成。

推荐方式：

- cron 定时运行 `--mode once`
- systemd 常驻运行 `--mode tail`

详细说明见：

```text
docs/auto-collection.md
```

## 6. 当前边界

- 当前使用 SQLite，后续可替换为 PostgreSQL
- 当前 Web 筛选覆盖基础字段
- 当前不做全文检索
- 当前不做 AI 自动分析
- 当前不执行系统命令
- 当前不做用户系统和权限系统
- 当前不生成 Markdown 报告
- 当前 Web 页面不查询归档文件
- 当前不是生产级 AIOps 平台

## 7. 后续可选增强

- 增加统一日志 JSON 查询 API
- 支持 PostgreSQL 存储
- 增加归档文件查询能力
- 增加 AI 分析结果持久化开关
- 增加批量日志分析队列
- 增加更完整的 systemd 部署模板
