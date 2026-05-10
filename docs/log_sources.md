# AI-OpsLog 统一日志来源说明

本文档说明统一日志采集模块当前支持的日志来源、常见路径、日志等级和标准化字段。

## 1. 支持的日志来源

| source | 说明 | 常见路径示例 |
| --- | --- | --- |
| `system` | Linux 系统日志 | `/var/log/messages`、`/var/log/syslog` |
| `zabbix` | Zabbix 服务日志 | `/var/log/zabbix/zabbix_server.log` |
| `prometheus` | Prometheus 服务日志 | `/var/log/prometheus/prometheus.log` |
| `grafana` | Grafana 服务日志 | `/var/log/grafana/grafana.log` |
| `ansible` | Ansible 执行日志 | `/var/log/ansible.log` |
| `docker` | Docker 容器或 daemon 日志 | `/var/log/docker.log`、容器日志文件 |
| `kubernetes` | Kubernetes 组件或 Pod 日志 | `/var/log/pods/...`、`/var/log/containers/...` |
| `nginx_access` | Nginx Access 日志 | `/var/log/nginx/access.log` |
| `nginx_error` | Nginx Error 日志 | `/var/log/nginx/error.log` |
| `redis` | Redis 服务日志 | `/var/log/redis/redis-server.log` |
| `mysql` | MySQL 服务日志 | `/var/log/mysql/error.log` |

## 2. 支持的日志等级

统一日志等级：

```text
FATAL
ERROR
WARN
INFO
DEBUG
```

采集脚本会从日志文本中识别常见等级别名，例如 `critical`、`error`、`warning`、`notice`、`info`、`debug`。`nginx_access` 会根据 HTTP 状态码做基础映射：`5xx -> ERROR`、`4xx -> WARN`、其他为 `INFO`。

## 3. 标准化字段

统一写入 `logs` 表的字段：

| 字段 | 含义 |
| --- | --- |
| `timestamp` | 日志事件时间，解析失败时为空 |
| `source` | 日志来源服务，例如 `docker`、`nginx_error` |
| `host` | 主机、容器或节点名 |
| `log_level` | 标准化日志等级 |
| `message` | 原始日志行内容 |
| `AI_analysis_result` | 预留 AI 分析结果字段，当前为空 |
| `created_at` | 写入数据库时间 |

当前统一日志存储只保存日志行和元数据，不生成 Markdown 报告，不触发 AI 分析。

Web 页面 `GET /dashboard/logs` 默认展示最近 100 条日志，支持按 `source`、`host`、`log_level`、最近 N 小时、时间范围和返回数量筛选最近日志。单条日志可以手动点击 AI 分析按钮，分析结果会显示在页面详情区；当前不写入数据库，`AI_analysis_result` 字段继续保留给后续迭代。

## 4. 采集脚本示例

读取指定文件最近 200 行：

```bash
python scripts/collect_unified_logs.py \
  --mode once \
  --target source=nginx_error,path=/var/log/nginx/error.log,host=nginx-web-01
```

每分钟由 cron 调度一次：

```bash
* * * * * cd /path/to/AI-Ops-Portfolio && python scripts/collect_unified_logs.py --mode once --lines 200 --target source=system,path=/var/log/syslog,host=ops-host-01
```

实时跟随日志文件：

```bash
python scripts/collect_unified_logs.py \
  --mode tail \
  --interval 1 \
  --target source=docker,path=/var/log/docker.log,host=docker-host-01
```

多来源采集：

```bash
python scripts/collect_unified_logs.py \
  --mode once \
  --target source=nginx_error,path=/var/log/nginx/error.log,host=nginx-web-01 \
  --target source=redis,path=/var/log/redis/redis-server.log,host=redis-01
```

## 5. 数据保留和归档

默认保留最近 7 天日志记录。采集脚本启动时会调用归档逻辑，将超过保留期的记录写入：

```text
data/archives/logs_archive_YYYYMMDD.jsonl
```

归档后会从 `logs` 表删除这些旧记录。归档文件属于运行时数据，不应提交到 Git。

`tail` 模式长时间运行时会按 `--archive-interval` 定期执行归档检查，默认每天一次。
