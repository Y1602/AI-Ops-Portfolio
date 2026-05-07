# Alertmanager 配置示例

## 1. 使用场景

AI-OpsLog 第三阶段提供 `POST /alerts/alertmanager` 接口，可以作为 Alertmanager webhook receiver 的目标地址。

该文档只提供配置示例，用于说明 Alertmanager 如何将告警事件发送到 AI-OpsLog。

当前边界：

- 本项目当前不负责部署 Prometheus
- 本项目当前不负责部署 Alertmanager
- 本项目当前不负责部署 Grafana
- 本项目当前不负责配置真实告警规则
- 本文档只展示 webhook receiver 配置方式

## 2. 不启用 Token 的配置示例

```yaml
global:
  resolve_timeout: 5m

route:
  receiver: ai-opslog-webhook

receivers:
  - name: ai-opslog-webhook
    webhook_configs:
      - url: "http://127.0.0.1:8000/alerts/alertmanager"
        send_resolved: true
```

说明：

- `url` 指向 AI-OpsLog 的 `POST /alerts/alertmanager`
- `send_resolved: true` 表示 firing 和 resolved 告警都会发送
- 如果 AI-OpsLog 部署在其他机器，需要替换 IP 或域名

## 3. 启用 Token 的配置示例

如果 AI-OpsLog 设置了：

```env
ALERTMANAGER_WEBHOOK_TOKEN=change-me-demo-token
```

AI-OpsLog 当前接口期望请求携带 Header：

```text
X-Alertmanager-Token: <token>
```

Alertmanager 原生 `webhook_configs` 是否直接支持自定义 Header 取决于版本和配置能力。为了避免写错配置，可以使用反向代理在转发到 AI-OpsLog 前添加 Header。

Nginx 反向代理示例：

```nginx
server {
    listen 8080;

    location /alerts/alertmanager {
        proxy_pass http://127.0.0.1:8000/alerts/alertmanager;
        proxy_set_header X-Alertmanager-Token change-me-demo-token;
        proxy_set_header Content-Type application/json;
    }
}
```

然后 Alertmanager 指向反向代理地址：

```yaml
receivers:
  - name: ai-opslog-webhook
    webhook_configs:
      - url: "http://127.0.0.1:8080/alerts/alertmanager"
        send_resolved: true
```

注意：

- 示例 Token 只是占位符
- 不要把真实 Token 写入 GitHub
- 如果使用 Nginx，真实环境应结合访问控制和 HTTPS
- 如果实际 Alertmanager 版本无法直接配置自定义 Header，可以通过反向代理添加 Header
- 也可以在内网 Demo 环境中暂时不启用 Token

## 4. 测试 Webhook

可以先不用真实 Alertmanager，使用 `curl` 测试。

启用 Token 时：

```bash
curl -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -H "X-Alertmanager-Token: change-me-demo-token" \
  -d @examples/alertmanager_webhook_high_cpu.json
```

未启用 Token 时：

```bash
curl -X POST http://127.0.0.1:8000/alerts/alertmanager \
  -H "Content-Type: application/json" \
  -d @examples/alertmanager_webhook_high_cpu.json
```

## 5. 查看报告

```bash
ls -lh reports/
```

如果 `reports/` 下生成新的 Markdown 文件，说明 AI-OpsLog 已经收到告警并生成分析报告。

## 6. 当前边界

- 当前只提供 Alertmanager webhook 接收接口
- 当前不维护告警生命周期
- 当前不关联 firing 和 resolved 事件
- 当前不做告警去重
- 当前不做告警静默
- 当前不做通知分发
- 当前不部署完整监控系统
- 当前 AI 输出只作为人工排查参考
