# AI-OpsLog 项目最终总结

## 1. 项目定位

AI-OpsLog 是一个面向运维日志场景的 AI 辅助分析 Demo 项目。

项目目标不是替代生产级 AIOps 平台，而是完整展示一个可运行的运维日志分析链路：

```text
日志采集 -> 统一存储 -> Web 展示与筛选 -> 历史统计 -> 按需 AI 分析
```

## 2. 最终主链路

当前最终版本主链路如下：

```text
系统 / 中间件 / 运维工具日志
        |
        v
scripts/collect_unified_logs.py
        |
        v
backend/app/collectors/log_adapters.py
        |
        v
SQLite logs 表
        |
        v
GET /dashboard/logs
        |
        v
POST /logs/{id}/analyze
```

Web 服务启动后不会自动采集日志。日志采集需要手动运行脚本，或通过 cron / systemd 自动运行。

## 3. 已完成核心功能

- 多服务日志采集：系统日志、Zabbix、Prometheus、Grafana、Ansible、Docker、Kubernetes、Nginx、Redis、MySQL
- 日志等级标准化：`FATAL`、`ERROR`、`WARN`、`INFO`、`DEBUG`
- 字段标准化：`timestamp`、`source`、`host`、`log_level`、`message`、`AI_analysis_result`、`created_at`
- SQLite 本地存储，默认路径 `data/ai_opslog.db`
- 最近 7 天日志保留，过期日志归档到 `data/archives/*.jsonl`
- 采集 offset state，避免 cron 重复采集同一批日志
- Web 看板展示最近日志
- 多条件筛选：工具类型、主机、日志等级、最近 N 小时、时间范围、关键字、数量、页码
- 历史统计：日志等级分布、工具类型分布
- 页面可读性优化：时间格式化、中文字段、风险行高亮、消息折叠、关键字高亮
- 单条日志按需 AI 分析
- Runbook 故障手册：`docs/runbooks/`
- AI 分析会根据日志来源和关键词匹配 Runbook 作为参考
- AI 分析结果展示：问题摘要、关键报错、参考 Runbook、关键证据、命中关键词、根因假设、风险等级、可能原因、排查建议、验证方法、操作风险提示、后续预防建议、补充说明
- AI 分析结果支持浏览器侧复制和导出为 `.txt`，不在服务端生成报告文件
- 保留兼容接口：`/history/recent`、`/history/{id}`

## 4. 性能与稳定性处理

- SQLite 启用 WAL、`busy_timeout`、`synchronous=NORMAL`
- 常用查询字段增加索引
- 日志写入使用队列缓冲和批量插入
- 归档操作后台执行并分批处理
- Web 保持服务端分页，避免一次渲染过多日志
- AI 分析按钮请求期间禁用，避免重复点击

## 5. 当前边界

- 当前使用 SQLite，不是生产数据库方案
- 当前不做用户系统和权限系统
- 当前不做 AI 自动分析
- 当前不执行系统命令
- 当前不做全文检索
- 当前 Web 页面不查询归档文件
- 当前不生成 Markdown 报告
- 当前不是生产级 AIOps 平台

## 6. GitHub 展示建议

README 建议重点展示：

- 项目简介
- 功能概览
- 页面截图
- 快速启动
- 日志采集方式
- Web 筛选与统计
- 按需 AI 分析
- 安全边界

上传前确认不要提交运行时文件：

```text
.env
data/*.db
data/*.sqlite
data/*state*.json
data/archives/*.jsonl
logs/*.log
```

建议执行：

```bash
python -m compileall backend\app scripts\collect_unified_logs.py
git status --short
```

## 7. 后续可选增强

- 增加统一日志 JSON 查询 API
- 支持 PostgreSQL
- 支持归档文件查询
- 增加 AI 分析结果持久化开关
- 增加批量日志分析队列
- 增加更完整的 systemd 部署模板
- 增加真实环境部署截图和演示视频
