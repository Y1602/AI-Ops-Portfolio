# Docker / Kubernetes 只读现场采集

本功能用于在 Web 看板中展示 Docker 和 Kubernetes 的当前运行现场快照，帮助排查日志时快速确认容器、Pod 和最近事件状态。

## 1. 能力边界

- 只读取现场状态，不修改 Docker 或 Kubernetes 资源。
- 不执行 `delete`、`restart`、`scale`、`apply` 等写操作。
- 不替代日志采集脚本，日志入库仍由 `scripts/collect_unified_logs.py` 完成。
- Docker 或 kubectl 不可用时，只在页面显示错误提示，不影响日志查询和 AI 分析。

## 2. JSON 接口

```text
GET /runtime/snapshot
```

返回内容包括：

- Docker 运行容器：容器 ID、名称、镜像、状态
- Kubernetes Pods：namespace、名称、Ready、状态、重启次数、Age
- Kubernetes Events：namespace、类型、原因、对象、消息

## 3. 环境变量

```env
AI_OPSLOG_ENABLE_DOCKER_SNAPSHOT=true
AI_OPSLOG_ENABLE_KUBERNETES_SNAPSHOT=true
RUNTIME_SNAPSHOT_TIMEOUT_SECONDS=3
RUNTIME_SNAPSHOT_MAX_ITEMS=8
DOCKER_BIN=docker
KUBECTL_BIN=kubectl
```

如果不希望 Web 看板查询 Kubernetes，可以设置：

```env
AI_OPSLOG_ENABLE_KUBERNETES_SNAPSHOT=false
```

如果不希望 Web 看板查询 Docker，可以设置：

```env
AI_OPSLOG_ENABLE_DOCKER_SNAPSHOT=false
```

## 4. 当前固定只读命令

```bash
docker ps --format "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}"
kubectl get pods -A --no-headers
kubectl get events -A --sort-by=.lastTimestamp --no-headers
```

这些命令仅用于读取状态，不会修改现场资源。
