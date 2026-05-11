# Nginx 502 / upstream 异常 Runbook

## 常见现象

- Nginx access 日志出现 `502`、`503`、`504`
- Nginx error 日志出现 `connect() failed`、`upstream timed out`、`connection refused`
- 用户访问接口失败，但 Nginx 本身仍然运行

## 常见原因

- 后端服务未启动或端口未监听
- upstream 地址或端口配置错误
- 后端服务健康检查失败
- 后端连接数耗尽或响应超时
- 发布后服务实例未全部 Ready

## 关键日志关键词

- `502`
- `upstream`
- `connect() failed`
- `connection refused`
- `upstream timed out`
- `no live upstreams`

## 排查步骤

1. 确认 Nginx error 日志中失败的 upstream 地址和端口。
2. 检查后端服务进程、端口监听和健康检查状态。
3. 检查 Nginx upstream 配置是否指向正确实例。
4. 对比故障时间点附近是否有发布、重启或配置变更。
5. 如果是 Kubernetes 环境，检查 Pod Ready 状态、Service 和 Endpoints。

## 验证方法

- 再次访问相同 URL，确认 5xx 是否消失。
- 查看 Nginx access 日志中相同接口的状态码是否恢复为 2xx/3xx。
- 查看后端服务日志是否仍有连接拒绝或超时。

## 风险提示

- 不要在证据不足时直接重启 Nginx 或后端服务。
- 修改 upstream 配置前需要确认回滚方式。
- 如果涉及生产流量切换，应先评估影响范围。
