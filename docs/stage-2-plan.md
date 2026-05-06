# AI-OpsLog 第二阶段开发计划

## 1. 阶段目标

第二阶段目标是将项目从“手动发送示例日志”升级为“读取真实日志文件最近 N 行并发送分析”。

当前阶段重点不是构建完整日志采集系统，而是补齐运维场景中常见的能力：

读取某个服务日志文件的最近错误内容，将日志发送到分析接口，由后端完成规则分析、AI 分析和 Markdown 报告生成。

## 2. 当前已完成能力

- 新增 `scripts/collect_recent_logs.py`
- 支持读取指定日志文件最后 N 行
- 支持通过 HTTP POST 发送到 `/logs/ingest`
- 支持 `source`、`service_name`、`env`、`log_type` 等元数据
- 支持 `--server` 参数指定后端服务地址
- 支持 `--file` 参数指定日志文件
- 支持 `--lines` 参数指定读取行数
- 支持 `--dry-run` 预览模式
- 支持在不发送后端请求的情况下预览最近 N 行日志内容
- 支持敏感文件拦截
- 支持文件不存在时返回错误信息
- 支持空内容处理
- 支持与现有规则分析、AI 分析、Markdown 报告生成链路衔接
- 已补充 cron 定时采集说明文档：`docs/cron-guide.md`

## 3. 当前能力边界

- 不执行系统命令
- 不自动执行修复操作
- 不做 tail -f 实时采集
- 不做 cron 定时任务
- 不做断点续读
- 不做日志去重
- 不做多文件批量采集
- 不直接采集 Docker daemon 日志
- 不接入数据库
- 不把 AI 分析结果作为自动操作依据
- AI 返回的命令只作为人工排查建议
- dry-run 只用于本地预览日志内容，不触发后端分析流程
- dry-run 不会生成报告
- 当前只是提供 cron 使用说明
- 项目没有自动写入 crontab
- 项目没有新增后台常驻采集进程

## 4. 测试记录

正常日志采集测试命令：

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

测试结果：

- 后端返回 JSON
- `source` 为 `nginx-web-01`
- `service_name` 为 `nginx`
- `env` 为 `dev`
- `log_type` 为 `nginx_error`
- `rule_severity` 为 `high`
- `ai_risk_level` 为 `high`
- 返回 `report_path`
- `reports/` 目录生成 Markdown 报告

dry-run 预览测试命令：

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

测试结果：

- 终端出现 `[DRY-RUN]` 标识
- 成功打印 `examples/nginx_error_502.log` 中的日志内容
- 没有请求 `/logs/ingest`
- 没有生成新的报告文件

敏感文件拦截测试：

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source test-host \
  --service-name test \
  --env dev \
  --log-type docker_log \
  --file .env \
  --lines 10
```

预期结果：

```text
Refuse to read sensitive file: .env
```

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source test-host \
  --service-name test \
  --env dev \
  --log-type docker_log \
  --file /etc/passwd \
  --lines 10
```

预期结果：

```text
Refuse to read sensitive file: /etc/passwd
```

异常文件测试：

```bash
python scripts/collect_recent_logs.py \
  --server http://127.0.0.1:8000 \
  --source test-host \
  --service-name test \
  --env dev \
  --log-type docker_log \
  --file examples/not_exists.log \
  --lines 10
```

预期结果：

```json
{
  "error": "log file does not exist",
  "file": "examples/not_exists.log"
}
```

## 5. 后续计划

以下内容只是后续方向，本阶段暂不实现：

- 已补充 cron 定时执行说明，后续可根据需要进一步封装部署方式
- 支持 tail -f 增量采集
- 支持 Docker 容器日志采集
- 接入 Prometheus Alertmanager Webhook
- 增加简单 Web 页面展示分析结果
- 增加数据库保存历史分析记录
- 增加更多日志类型解析规则

## 6. 风险与限制

当前 `collect_recent_logs.py` 使用手动执行方式读取日志文件，适合演示和本地测试，不适合作为完整日志采集系统。

当前脚本不会执行系统命令，也不会执行修复操作。后端生成的排查命令和修复建议只作为人工参考。

敏感文件拦截只做基础保护，用于避免误读取 `.env`、私钥、系统账户文件等高风险文件，不代表完整的权限控制系统。
