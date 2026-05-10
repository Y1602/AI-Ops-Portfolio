# AI-OpsLog 自动日志采集说明

AI-OpsLog 的 Web 服务只负责展示、筛选、统计和按需 AI 分析。日志写入 SQLite 需要运行采集脚本：

```bash
python scripts/collect_unified_logs.py
```

生产或演示环境中建议使用 cron 定时采集，或者使用 systemd 常驻运行 tail 模式。

## 1. 手动采集一次

```bash
cd /opt/AI-Ops-Portfolio

python scripts/collect_unified_logs.py \
  --mode once \
  --lines 100 \
  --target source=system,path=/var/log/messages,host=RockyLinux
```

如果系统日志路径是 `/var/log/syslog`：

```bash
python scripts/collect_unified_logs.py \
  --mode once \
  --lines 100 \
  --target source=system,path=/var/log/syslog,host=RockyLinux
```

## 2. cron 定时采集

编辑 root 的 crontab：

```bash
sudo crontab -e
```

每分钟采集一次系统日志：

```cron
* * * * * cd /opt/AI-Ops-Portfolio && /usr/bin/python3 scripts/collect_unified_logs.py --mode once --lines 100 --target source=system,path=/var/log/messages,host=RockyLinux >> logs/collect_unified_logs.log 2>&1
```

多来源采集示例：

```cron
* * * * * cd /opt/AI-Ops-Portfolio && /usr/bin/python3 scripts/collect_unified_logs.py --mode once --lines 100 --target source=system,path=/var/log/messages,host=RockyLinux --target source=nginx_error,path=/var/log/nginx/error.log,host=RockyLinux --target source=redis,path=/var/log/redis/redis-server.log,host=RockyLinux >> logs/collect_unified_logs.log 2>&1
```

查看采集日志：

```bash
tail -f /opt/AI-Ops-Portfolio/logs/collect_unified_logs.log
```

## 3. systemd tail 常驻采集

创建服务文件：

```bash
sudo vi /etc/systemd/system/ai-opslog-collector.service
```

写入：

```ini
[Unit]
Description=AI-OpsLog unified log collector
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/AI-Ops-Portfolio
ExecStart=/usr/bin/python3 scripts/collect_unified_logs.py --mode tail --interval 1 --target source=system,path=/var/log/messages,host=RockyLinux
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动并设置开机自启：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ai-opslog-collector
```

查看状态：

```bash
sudo systemctl status ai-opslog-collector
```

查看日志：

```bash
journalctl -u ai-opslog-collector -f
```

## 4. 数据保留

采集脚本启动时会执行归档检查。默认只保留最近 7 天日志，超过 7 天的记录会写入：

```text
data/archives/logs_archive_YYYYMMDD.jsonl
```

归档后旧记录会从 SQLite `logs` 表删除。
