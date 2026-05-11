# MySQL 连接异常 Runbook

## 常见现象

- 应用日志出现数据库连接失败
- MySQL 日志出现 `Access denied`、`Too many connections`、`InnoDB` 错误
- 接口响应变慢或出现 5xx

## 常见原因

- MySQL 服务未启动或端口不可达
- 连接数达到上限
- 账号密码、权限或访问来源限制错误
- 慢查询或锁等待导致连接堆积
- 磁盘空间不足影响 MySQL 写入

## 关键日志关键词

- `Too many connections`
- `Access denied`
- `Connection refused`
- `InnoDB`
- `Lock wait timeout`
- `No space left on device`

## 排查步骤

1. 检查 MySQL 服务状态和端口监听。
2. 查看 MySQL error log 是否有连接数、权限、InnoDB 或磁盘错误。
3. 检查应用数据库连接配置和账号权限。
4. 检查连接数、慢查询和锁等待。
5. 如果出现磁盘相关错误，优先确认磁盘空间和 inode。

## 验证方法

- 确认应用侧数据库连接错误是否停止增长。
- 查看 MySQL 连接数是否回落到正常范围。
- 查看接口响应时间和错误率是否恢复。

## 风险提示

- 不要直接修改生产数据库参数或重启数据库。
- 杀连接、改权限、清理数据前需要确认影响范围和回滚方案。
