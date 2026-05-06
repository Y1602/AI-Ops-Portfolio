# Stage 2 Plan

## 1. 阶段目标

在第一阶段手动发送日志的基础上，增加日志采集脚本，支持读取指定日志文件最近 N 行并发送到 AI-OpsLog 服务端。

## 2. 当前范围

- 支持手动执行采集脚本
- 支持最近 N 行日志读取
- 支持发送到 `/logs/ingest`
- 支持基础敏感文件拦截

## 3. 暂不支持

- 实时 tail -f
- 日志断点续读
- 日志去重
- 多文件批量采集
- 生产级采集 Agent

## 4. 后续扩展

- cron 定时采集
- tail -f 增量采集
- Docker 容器日志采集
- Prometheus Alertmanager Webhook 接入
