# 日志

该目录用于保存 AI-OpsLog 本地脚本运行日志。

示例：

- `collect_recent_logs.log`：`collect_recent_logs.py` 通过 `--output-log` 写入的结构化运行结果
- `collect_recent_stdout.log`：可选的 cron 标准输出和错误输出日志

注意：

- 本目录下的 `*.log` 文件为运行时生成文件，不建议提交到 GitHub
- AI 分析生成的 Markdown 报告保存在 `reports/` 目录
- `logs/` 与 `reports/` 作用不同
