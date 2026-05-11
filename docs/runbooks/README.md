# AI-OpsLog Runbook 说明

本目录用于沉淀常见运维故障的排查经验。

Runbook 当前主要服务于按需 AI 分析：

- AI 分析单条日志时，会根据 `source`、日志内容和命中关键词选择一个相关 Runbook。
- Runbook 只作为经验参考，不能替代当前日志证据。
- AI 不会执行 Runbook 中的命令，所有排查步骤都需要人工确认后执行。

当前内置 Runbook：

- `nginx-502.md`
- `redis-connection-error.md`
- `mysql-connection-error.md`
- `disk-space-low.md`
- `system-service-error.md`
