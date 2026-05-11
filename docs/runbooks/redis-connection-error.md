# Redis 连接异常 Runbook

## 常见现象

- 应用日志出现 `Redis connection refused`
- Redis 日志出现连接异常、内存不足或持久化失败
- 缓存访问超时，接口延迟升高

## 常见原因

- Redis 服务未启动或端口未监听
- Redis 达到最大连接数
- Redis 内存不足或触发淘汰策略
- 网络、防火墙或容器网络异常
- 应用侧 Redis 地址、端口、密码配置错误

## 关键日志关键词

- `connection refused`
- `timeout`
- `max number of clients reached`
- `OOM`
- `MISCONF`
- `loading the dataset`

## 排查步骤

1. 检查 Redis 服务状态和端口监听。
2. 检查 Redis 日志中是否有连接数、内存或持久化相关错误。
3. 确认应用配置中的 Redis 地址、端口、密码是否正确。
4. 查看故障时间点是否存在 Redis 重启、主从切换或网络波动。
5. 检查客户端连接数和慢查询情况。

## 验证方法

- 使用只读方式验证 Redis 是否响应 `PING`。
- 观察应用错误日志是否停止增长。
- 查看 Redis 连接数和内存使用是否恢复正常。

## 风险提示

- 不要直接执行 `FLUSHALL`、`CONFIG SET` 等高风险命令。
- 重启 Redis 可能导致短时间缓存不可用，需要评估业务影响。
