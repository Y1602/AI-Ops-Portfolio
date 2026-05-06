# AI-OpsLog Cron 定时采集说明

## 1. 使用场景

AI-OpsLog 当前支持通过 `scripts/collect_recent_logs.py` 手动读取日志文件最近 N 行并发送到 `/logs/ingest`。

如果希望周期性检查某个日志文件，可以借助 Linux cron 定时执行该脚本。

cron 只负责定时触发脚本。`collect_recent_logs.py` 只负责读取最近 N 行并发送到后端。AI-OpsLog 不会执行系统修复命令。

## 2. 前置条件

- AI-OpsLog 后端服务已经启动
- 当前机器可以访问 `http://127.0.0.1:8000` 或对应服务地址
- Python 环境可用
- `requests` 依赖已安装
- 待读取的日志文件路径存在
- 执行 cron 的用户对日志文件有读取权限

检查命令示例：

```bash
docker compose ps
```

```bash
curl http://127.0.0.1:8000/health
```

## 3. 先手动验证采集命令

在写入 cron 前，必须先手动执行 `collect_recent_logs.py`，确认命令本身可用。

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source nginx-web-01 \
  --service-name nginx \
  --env dev \
  --log-type nginx_error \
  --file examples/nginx_error_502.log \
  --lines 50
```

成功标准：

- 终端返回 JSON
- 返回 `rule_severity`
- 返回 `ai_risk_level`
- 返回 `report_path`
- `reports/` 目录生成 Markdown 报告

## 4. 使用 dry-run 预览采集内容

可以先使用 `--dry-run` 预览脚本读取到的最近 N 行日志，确认读取范围正确，再去掉 `--dry-run` 正式发送。

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source nginx-web-01 \
  --service-name nginx \
  --env dev \
  --log-type nginx_error \
  --file examples/nginx_error_502.log \
  --lines 10 \
  --dry-run
```

dry-run 模式不会请求 `/logs/ingest`，也不会生成报告。

## 5. cron 示例

每 5 分钟采集一次 Nginx Error 日志最近 50 行：

```cron
*/5 * * * * cd /opt/AI-Ops-Portfolio && /usr/bin/python3 scripts/collect_recent_logs.py --server http://127.0.0.1:8000 --source nginx-web-01 --service-name nginx --env dev --log-type nginx_error --file examples/nginx_error_502.log --lines 50 --max-chars 20000 --output-log logs/collect_recent_logs.log
```

说明：

- `cd /opt/AI-Ops-Portfolio` 用于切换到项目目录
- `/usr/bin/python3` 建议使用绝对路径
- `--max-chars 20000` 可以避免 cron 周期执行时一次性发送过大的日志内容
- `--output-log logs/collect_recent_logs.log` 用于记录 `collect_recent_logs.py` 每次执行的结果，适合配合 cron 查看采集任务是否成功
- 如果需要同时记录终端标准输出和错误输出，也可以继续使用 shell 重定向
- 实际项目路径需要根据部署位置调整
- 实际日志文件路径需要根据目标服务调整

如果还希望保留终端输出和错误输出，可以使用：

```cron
*/5 * * * * cd /opt/AI-Ops-Portfolio && /usr/bin/python3 scripts/collect_recent_logs.py --server http://127.0.0.1:8000 --source nginx-web-01 --service-name nginx --env dev --log-type nginx_error --file examples/nginx_error_502.log --lines 50 --max-chars 20000 --output-log logs/collect_recent_logs.log >> logs/collect_recent_stdout.log 2>&1
```

日志文件用途：

- `collect_recent_logs.log` 记录脚本结构化运行结果
- `collect_recent_stdout.log` 记录终端标准输出和错误输出
- 两者用途不同

## 6. 建议创建 logs/ 目录

如果使用 cron，建议创建 `logs/` 目录保存脚本执行日志。

```bash
mkdir -p logs
```

`logs/` 目录用于保存采集脚本自身的运行日志，不是被分析的业务日志。

## 7. 常见问题

### 1. cron 中 python 命令找不到

原因：

cron 环境变量较少，可能找不到 python。

建议：

使用 `which python3` 查看绝对路径，然后在 cron 中使用绝对路径。

```bash
which python3
```

### 2. cron 中相对路径找不到文件

原因：

cron 默认工作目录不一定是项目目录。

建议：

在 cron 命令中先 `cd` 到项目目录，或者全部使用绝对路径。

### 3. 后端服务未启动

表现：

脚本返回 `failed to connect to AI-OpsLog server`。

建议：

先检查：

```bash
docker compose ps
```

```bash
curl http://127.0.0.1:8000/health
```

### 4. 没有生成 reports 报告

排查方向：

- 后端服务是否启动
- cron 是否真的执行
- `logs/collect_recent_logs.log` 是否有错误
- 日志文件路径是否正确
- cron 执行用户是否有读取日志文件权限

### 5. 不要用 cron 读取敏感文件

脚本会拦截 `.env`、`id_rsa`、`/etc/passwd`、`/etc/shadow`、`*.pem`、`*.key` 等敏感文件。

## 8. 当前边界

- cron 只是定时触发脚本
- 当前不做 tail -f 实时流式采集
- 当前不做断点续读
- 当前不做日志去重
- 当前不做多文件批量采集
- 当前不做 systemd 服务管理
- 当前不执行任何系统修复命令
- AI 分析结果只作为人工排查参考
