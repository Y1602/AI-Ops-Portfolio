# AI-OpsLog 第三阶段开发计划

## 1. 阶段目标

第三阶段目标是接入 Prometheus Alertmanager Webhook，让 AI-OpsLog 可以接收监控告警事件，并生成 AI 辅助分析报告。

当前阶段不是部署完整 Prometheus/Grafana 监控平台，而是先完成 Webhook 接收、告警解析和报告生成闭环。

## 2. 当前已完成能力

- 新增 `POST /alerts/alertmanager`
- 支持接收 Alertmanager Webhook JSON
- 支持单条 alert
- 支持多条 alerts 合并生成一份报告
- 支持字段缺省处理
- 支持空 alerts 返回 400
- 支持 severity 到 rule_severity 的基础映射
- 支持生成 Markdown 告警分析报告
- 不影响原有 `/logs/ingest` 日志分析接口

## 3. 当前链路

```text
Alertmanager Webhook
    ↓
POST /alerts/alertmanager
    ↓
Parse Alertmanager JSON
    ↓
Build Alert Event Text
    ↓
Rule Severity Mapping
    ↓
Qwen AI Analysis
    ↓
Markdown Alert Report
    ↓
reports/
```

## 4. 当前边界

- 不部署 Prometheus
- 不部署 Alertmanager
- 不部署 Grafana
- 不配置真实告警规则
- 不做告警去重
- 不做告警静默
- 不做通知分发
- 不接数据库
- 不做 Web 页面
- 不自动执行修复命令
- AI 输出只作为人工排查参考

## 5. 下一步计划

- 增加更多 Alertmanager 示例
- 增加告警状态 resolved 处理说明
- 增加 Webhook 安全说明
- 增加真实 Alertmanager 配置示例
- 后续接入历史记录存储
