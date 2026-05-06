# AI-OpsLog 智能日志分析报告

## 1. 基本信息

- 日志类型：docker_log
- 日志来源：docker-host-01
- 服务名称：redis-container
- 运行环境：dev
- 规则风险等级：high
- AI 风险等级：high
- 是否需要人工介入：true

## 2. 规则解析结果

| 关键词 | 命中次数 |
|---|---|
| port is already allocated | 1 |
| exited with code | 1 |

## 3. AI 故障摘要

Docker 容器启动失败，日志显示端口已被占用，容器随后退出。该问题通常会导致服务无法监听预期端口，需要人工确认端口占用来源和容器端口映射配置。

## 4. 可能原因

- 宿主机目标端口已经被其他进程占用。
- 已有同类容器占用了相同端口。
- docker-compose 或启动参数中配置了冲突的端口映射。

## 5. 排查步骤

- 检查当前运行和退出的容器。
- 检查宿主机端口监听情况。
- 核对容器端口映射配置。
- 查看目标容器完整启动日志。

## 6. 修复建议

- 调整容器端口映射，避免多个服务使用同一宿主机端口。
- 停止或迁移占用端口的旧服务。
- 重新启动容器前确认配置文件中的端口定义。

## 7. 建议排查命令

- `docker ps -a`
- `docker logs <container_name>`
- `ss -lntp`

以上命令仅作为人工排查参考，本系统不会自动执行任何命令。

## 8. 样例日志

- `Error response from daemon: port is already allocated`
- `container exited with code 1`

## 9. 安全说明

本报告由规则解析与大模型辅助分析生成，仅用于运维排障参考。  
AI 分析结果需要结合实际环境人工确认。  
本系统不会自动执行任何系统命令。
