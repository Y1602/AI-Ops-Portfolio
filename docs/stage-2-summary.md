# Stage 2 Summary

## 1. 阶段目标

第二阶段目标是从第一阶段的“手动发送示例日志”升级为“读取日志文件最近 N 行并发送分析”。

本阶段重点是增强日志采集入口，而不是构建完整日志采集平台。

## 2. 已完成功能

- 新增 `scripts/collect_recent_logs.py`
- 支持读取指定日志文件最后 N 行
- 支持发送到 `POST /logs/ingest`
- 支持 `source`、`service_name`、`env`、`log_type` 等元数据
- 支持敏感文件拦截
- 支持 `--dry-run` 预览模式
- 支持 `--output-log` 记录脚本运行结果
- 支持 `--max-chars` 限制日志内容长度
- 支持常见异常处理
- 补充 cron 定时采集说明文档
- 整理 `logs/` 目录说明和 Git 忽略规则

## 3. 核心链路

```text
Log File
    ↓
scripts/collect_recent_logs.py
    ↓
Read Last N Lines
    ↓
Sensitive File Check
    ↓
Max Chars Limit
    ↓
POST /logs/ingest
    ↓
Rule Parser
    ↓
Qwen AI Analysis
    ↓
Markdown Report
    ↓
reports/
```

dry-run 链路：

```text
Log File
    ↓
scripts/collect_recent_logs.py --dry-run
    ↓
Read Last N Lines
    ↓
Sensitive File Check
    ↓
Max Chars Limit
    ↓
Print Preview
    ↓
No Backend Request
```

## 4. 关键参数说明

- `--server`：AI-OpsLog 后端服务地址
- `--source`：日志来源主机或节点
- `--service-name`：服务名称
- `--env`：环境名称
- `--log-type`：日志类型
- `--file`：待读取的日志文件路径
- `--lines`：读取最后 N 行
- `--dry-run`：只预览日志内容，不发送后端
- `--output-log`：记录脚本运行结果
- `--max-chars`：限制最终日志内容最大字符数

## 5. 测试记录

### 1. 正常发送测试

命令：

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source nginx-web-01 \
  --service-name nginx \
  --env dev \
  --log-type nginx_error \
  --file examples/nginx_error_502.log \
  --lines 50 \
  --max-chars 5000 \
  --output-log logs/collect_recent_logs.log
```

结果：

- 后端返回 JSON
- `rule_severity` 为 `high`
- `ai_risk_level` 为 `high`
- 返回 `report_path`
- `reports/` 生成 Markdown 报告
- output-log 记录 `status=success`

### 2. dry-run 测试

命令：

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

结果：

- 终端输出 `[DRY-RUN]`
- 打印读取到的日志内容
- 不请求后端
- 不生成报告

### 3. max-chars 截断测试

命令：

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source nginx-web-01 \
  --service-name nginx \
  --env dev \
  --log-type nginx_error \
  --file examples/nginx_error_502.log \
  --lines 50 \
  --max-chars 200 \
  --dry-run
```

结果：

- 输出 `[TRUNCATED]`
- 只保留最后 200 个字符
- 不请求后端

### 4. 敏感文件拦截测试

命令：

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source test-host \
  --service-name test \
  --env dev \
  --log-type docker_log \
  --file .env \
  --lines 10 \
  --dry-run
```

结果：

```text
Refuse to read sensitive file: .env
```

### 5. 后端未启动测试

当后端未启动时，脚本返回 `failed to connect to AI-OpsLog server`，不出现 Python Traceback。

## 6. 当前边界

- 不执行任何系统命令
- 不自动执行修复操作
- 不做 tail -f 实时采集
- 不做后台常驻进程
- 不做断点续读
- 不做日志去重
- 不做多文件批量采集
- 不直接采集 Docker daemon 日志
- 不接入数据库
- 不保存完整日志归档
- AI 输出只作为人工排查参考

## 7. 后续方向

第二阶段到这里可以收尾。

后续方向建议进入第三阶段：Prometheus Alertmanager Webhook 接入。

第三阶段目标：接收 Alertmanager Webhook 告警事件，将告警内容转换为 AI-OpsLog 可分析的日志/事件文本，复用现有规则分析、Qwen AI 分析和 Markdown 报告生成链路。

这里只记录后续方向，不实现第三阶段功能。
