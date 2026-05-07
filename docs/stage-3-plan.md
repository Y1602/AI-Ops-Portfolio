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
- 支持 resolved 告警事件示例
- 支持在告警文本和报告中区分 firing 与 resolved
- resolved 告警仍生成一份分析报告，但不做生命周期追踪
- 支持可选 Alertmanager Webhook Token 校验
- 通过 `ALERTMANAGER_WEBHOOK_TOKEN` 环境变量启用
- 请求 Header 使用 `X-Alertmanager-Token`
- 新增 Alertmanager 配置示例文档
- 新增 `examples/alertmanager.yml`
- 提供 `send_resolved: true` 示例
- 提供 Token 场景下通过反向代理添加 Header 的说明
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
- 不关联 firing 与 resolved 两次事件
- 不记录告警状态历史
- 不计算告警持续时间
- 不做告警恢复通知
- 不接数据库
- 不做 Web 页面
- 不自动执行修复命令
- AI 输出只作为人工排查参考
- Token 校验只是基础保护示例
- 不包含用户系统
- 不包含 JWT/OAuth
- 不包含权限管理
- 不包含 IP 白名单
- 不包含签名验签
- Token 校验只保护 `POST /alerts/alertmanager`
- 不影响 `/logs/ingest`
- 当前不部署真实 Alertmanager
- 当前 `examples/alertmanager.yml` 仅作为配置参考
- 当前不保证适配所有 Alertmanager 版本的高级认证配置

## 5. 下一步计划

- 增加更多 Alertmanager 示例
- 后续接入历史记录存储

## 6. 阶段总结

第三阶段总结文档见：`docs/stage-3-summary.md`。

第三阶段完成 Alertmanager Webhook 接入闭环后，后续建议进入历史记录存储阶段。
