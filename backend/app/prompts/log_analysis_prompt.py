import json


def build_log_analysis_prompt(log_type: str, raw_log: str, parsed_result: dict) -> str:
    parsed_json = json.dumps(parsed_result, ensure_ascii=False, indent=2)

    if log_type == "alertmanager_alert":
        return _build_alertmanager_analysis_prompt(log_type, raw_log, parsed_json)

    return f"""你是一个运维/SRE 日志分析助手，负责根据日志内容和规则解析结果，生成故障分析建议。

请根据以下输入进行分析：

日志类型：
{log_type}

原始日志：
{raw_log}

规则解析结果：
{parsed_json}

输出要求：
1. 输出必须是严格 JSON，不要输出 Markdown，不要输出额外解释。
2. 输出内容必须使用中文。
3. 输出必须能被 json.loads() 解析。
4. 不要编造日志中不存在的信息。
5. 如果信息不足，要明确说明需要人工确认。
6. 不允许自动执行命令。
7. 不要输出危险命令。
8. 不要建议 rm -rf、mkfs、格式化磁盘、清空数据库、关闭防火墙、删除数据等高风险操作。
9. related_commands 只能提供只读排查命令，例如：
   - docker ps -a
   - docker logs <container_name>
   - ss -lntp
   - systemctl status nginx
   - nginx -t
   - journalctl -u nginx --no-pager -n 100

JSON 字段固定如下：
{{
  "summary": "故障摘要",
  "log_type": "日志类型",
  "risk_level": "low | medium | high | critical",
  "possible_causes": [
    "可能原因1",
    "可能原因2"
  ],
  "troubleshooting_steps": [
    "排查步骤1",
    "排查步骤2"
  ],
  "fix_suggestions": [
    "修复建议1",
    "修复建议2"
  ],
  "related_commands": [
    "建议执行的安全排查命令"
  ],
  "need_manual_intervention": true
}}"""


def _build_alertmanager_analysis_prompt(log_type: str, raw_log: str, parsed_json: str) -> str:
    return f"""你是一个运维/SRE 监控告警分析助手，负责根据 Alertmanager Webhook 告警事件和规则解析结果，生成告警辅助排查建议。

请重点关注：
1. 告警含义
2. 可能影响范围
3. 可能原因
4. 建议优先级
5. 人工排查步骤
6. 需要查看的指标或只读排查命令
7. 风险等级判断依据

请根据以下输入进行分析：

日志类型：
{log_type}

Alertmanager 告警事件文本：
{raw_log}

规则解析结果：
{parsed_json}

输出要求：
1. 输出必须是严格 JSON，不要输出 Markdown，不要输出额外解释。
2. 输出内容必须使用中文。
3. 输出必须能被 json.loads() 解析。
4. 不要编造告警事件中不存在的信息。
5. 如果信息不足，要明确说明需要人工确认。
6. 不允许自动执行命令。
7. 不要输出危险命令。
8. 不要建议 rm -rf、mkfs、格式化磁盘、清空数据库、关闭防火墙、删除数据等高风险操作。
9. related_commands 只能提供只读排查命令或指标查看命令，例如：
   - curl -s http://127.0.0.1:8000/health
   - systemctl status nginx
   - journalctl -u nginx --no-pager -n 100
   - df -h
   - top -b -n 1
   - uptime
   - ss -lntp
10. 建议命令只作为人工排查参考，不要把 AI 结果作为生产自动操作依据。

JSON 字段固定如下：
{{
  "summary": "告警摘要",
  "log_type": "日志类型",
  "risk_level": "low | medium | high | critical",
  "possible_causes": [
    "可能原因1",
    "可能原因2"
  ],
  "troubleshooting_steps": [
    "人工排查步骤1",
    "人工排查步骤2"
  ],
  "fix_suggestions": [
    "人工处理建议1",
    "人工处理建议2"
  ],
  "related_commands": [
    "建议执行的安全只读排查命令"
  ],
  "need_manual_intervention": true
}}"""
