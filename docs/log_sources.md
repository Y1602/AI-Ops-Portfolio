# AI-OpsLog 统一日志来源说明

本文档说明统一日志采集模块支持的日志来源、常见路径、等级映射、标准化字段和运行方式。

## 1. 支持的日志来源

| source | 说明 | 常见路径示例 |
| --- | --- | --- |
| `system` | Linux 系统日志 | `/var/log/messages`, `/var/log/syslog` |
| `zabbix` | Zabbix 服务日志 | `/var/log/zabbix/zabbix_server.log` |
| `prometheus` | Prometheus 服务日志 | `/var/log/prometheus/prometheus.log` |
| `grafana` | Grafana 服务日志 | `/var/log/grafana/grafana.log` |
| `ansible` | Ansible 执行日志 | `/var/log/ansible.log` |
| `docker` | Docker daemon 或容器日志 | `/var/log/docker.log`, Docker JSON log file |
| `kubernetes` | Kubernetes 组件或 Pod 日志 | `/var/log/pods/...`, `/var/log/containers/...` |
| `nginx_access` | Nginx Access 日志 | `/var/log/nginx/access.log` |
| `nginx_error` | Nginx Error 日志 | `/var/log/nginx/error.log` |
| `redis` | Redis 服务日志 | `/var/log/redis/redis-server.log` |
| `mysql` | MySQL 服务日志 | `/var/log/mysql/error.log` |

采集脚本会校验 `source` 是否在支持列表中，避免未知来源直接写入。

## 2. 日志等级

统一日志等级：

```text
FATAL
ERROR
WARN
INFO
DEBUG
```

采集适配器会识别常见等级别名：

- `fatal`, `panic`, `critical`, `crit`, `emerg`, `alert` -> `FATAL`
- `error`, `err`, `eror` -> `ERROR`
- `warning`, `warn` -> `WARN`
- `notice`, `info`, `information` -> `INFO`
- `debug`, `trace` -> `DEBUG`

`nginx_access` 会根据 HTTP 状态码做基础映射：

- `5xx` -> `ERROR`
- `4xx` -> `WARN`
- 其他 -> `INFO`

如果无法识别等级，默认写入 `INFO`。

## 3. 标准化字段

统一写入 SQLite `logs` 表：

| 字段 | 含义 |
| --- | --- |
| `timestamp` | 日志事件时间，解析失败时为空 |
| `source` | 日志来源服务，例如 `docker`, `nginx_error`, `redis` |
| `host` | 主机、容器或节点名 |
| `log_level` | 标准化日志等级 |
| `message` | 日志内容。JSON 日志会优先提取 `message`, `msg`, `log` 等字段 |
| `AI_analysis_result` | 预留 AI 分析结果字段，当前可为空 |
| `created_at` | 写入数据库时间 |

当前采集模块只保存日志行和元数据，不生成 Markdown 报告，不自动触发 AI 分析。Web 看板可以按 `source`、`host`、`log_level`、时间范围和 `keyword` 查询这些记录。

## 4. 解析适配器

多服务解析适配器位于：

```text
backend/app/collectors/log_adapters.py
```

当前支持：

- ISO 时间格式
- Syslog 时间格式
- Nginx Access/Error 时间格式
- Redis 常见时间格式
- Zabbix 常见时间格式
- JSON 日志字段提取
- logfmt 风格 `level=error` / `ts=...` 字段提取

## 5. 采集脚本示例

读取指定文件最近 200 行：

```bash
python scripts/collect_unified_logs.py \
  --mode once \
  --lines 200 \
  --target source=nginx_error,path=/var/log/nginx/error.log,host=nginx-web-01
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
  --target source=system,path=/var/log/syslog,host=ops-host-01 \
  --target source=redis,path=/var/log/redis/redis-server.log,host=redis-01 \
  --target source=mysql,path=/var/log/mysql/error.log,host=mysql-01
```

配合 cron 每分钟运行一次：

```bash
* * * * * cd /path/to/AI-Ops-Portfolio && python scripts/collect_unified_logs.py --mode once --lines 200 --target source=system,path=/var/log/syslog,host=ops-host-01
```

## 6. 数据保留和归档

默认保留最近 7 天日志。采集脚本启动时会调用归档逻辑，将超过保留期的记录写入：

```text
data/archives/logs_archive_YYYYMMDD.jsonl
```

归档完成后，旧记录会从 `logs` 表删除。

`tail` 模式长时间运行时，会按 `--archive-interval` 定期执行归档检查，默认每天一次。

归档文件属于运行时数据，不应提交到 Git。
