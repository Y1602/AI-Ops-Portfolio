import argparse
from datetime import datetime
import json
from pathlib import Path

import requests


SUPPORTED_LOG_TYPES = {"nginx_access", "nginx_error", "docker_log"}
SENSITIVE_NAME_KEYWORDS = {
    ".env",
    "id_rsa",
    "id_dsa",
    "authorized_keys",
    "known_hosts",
}
SENSITIVE_EXACT_PATHS = {"/etc/passwd", "/etc/shadow"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect recent log lines and send them to AI-OpsLog /logs/ingest."
    )
    parser.add_argument(
        "--server",
        default="http://127.0.0.1:8000",
        help="AI-OpsLog server URL, default: http://127.0.0.1:8000",
    )
    parser.add_argument("--source", required=True, help="Log source host or node.")
    parser.add_argument("--service-name", required=True, help="Service name.")
    parser.add_argument("--env", default="dev", help="Environment name, default: dev.")
    parser.add_argument(
        "--log-type",
        required=True,
        choices=sorted(SUPPORTED_LOG_TYPES),
        help="Log type used by AI-OpsLog parser.",
    )
    parser.add_argument("--file", required=True, help="Local log file path.")
    parser.add_argument(
        "--lines",
        type=int,
        default=50,
        help="Number of recent lines to read, default: 50.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=20000,
        help="Maximum log content characters to keep, default: 20000.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read and print recent log lines without sending them to the server.",
    )
    parser.add_argument(
        "--output-log",
        help="Append this run result to a local log file.",
    )
    return parser.parse_args()


def is_safe_log_file(file_path: str) -> bool:
    path = Path(file_path).expanduser()
    path_text = str(path).replace("\\", "/").lower()
    file_name = path.name.lower()

    if path_text in SENSITIVE_EXACT_PATHS:
        return False

    if any(keyword in file_name for keyword in SENSITIVE_NAME_KEYWORDS):
        return False

    if file_name.endswith(".pem") or file_name.endswith(".key"):
        return False

    return True


def read_last_lines(file_path: str, lines: int) -> str:
    line_count = max(lines, 0)
    content = Path(file_path).read_text(encoding="utf-8", errors="replace")
    if line_count == 0:
        return ""
    return "\n".join(content.splitlines()[-line_count:])


def truncate_log_content(log_content: str, max_chars: int) -> tuple[str, bool]:
    if len(log_content) <= max_chars:
        return log_content, False

    message = (
        f"[TRUNCATED] Log content exceeded max_chars={max_chars}, "
        f"only the last {max_chars} characters are kept."
    )
    return message + "\n" + log_content[-max_chars:], True


def main() -> int:
    args = parse_args()
    log_file = Path(args.file).expanduser()
    truncated = False

    if args.max_chars <= 0:
        append_run_log(
            args.output_log,
            args,
            "failed",
            truncated=truncated,
            error="max_chars must be greater than 0",
        )
        print("Error: --max-chars must be greater than 0")
        return 1

    if not is_safe_log_file(str(log_file)):
        append_run_log(
            args.output_log,
            args,
            "failed",
            truncated=truncated,
            error="sensitive file refused",
        )
        print(f"Refuse to read sensitive file: {args.file}")
        return 1

    if not log_file.exists():
        append_run_log(
            args.output_log,
            args,
            "failed",
            truncated=truncated,
            error="log file does not exist",
        )
        print_json({"error": "log file does not exist", "file": str(log_file)})
        return 1

    if not log_file.is_file():
        append_run_log(
            args.output_log,
            args,
            "failed",
            truncated=truncated,
            error="path is not a regular file",
        )
        print_json({"error": "path is not a regular file", "file": str(log_file)})
        return 1

    if args.lines <= 0:
        append_run_log(
            args.output_log,
            args,
            "failed",
            truncated=truncated,
            error="lines must be greater than 0",
        )
        print_json({"error": "lines must be greater than 0", "lines": args.lines})
        return 1

    try:
        log_text = read_last_lines(str(log_file), args.lines)
    except OSError as exc:
        append_run_log(
            args.output_log,
            args,
            "failed",
            truncated=truncated,
            error=f"failed to read log file: {exc}",
        )
        print_json(
            {
                "error": "failed to read log file",
                "file": str(log_file),
                "detail": str(exc),
            }
        )
        return 1

    if not log_text.strip():
        append_run_log(
            args.output_log,
            args,
            "failed",
            truncated=truncated,
            error="no log content was read from file",
        )
        print_json(
            {
                "message": "no log content was read from file",
                "file": str(log_file),
                "lines": args.lines,
            }
        )
        return 0

    log_text, truncated = truncate_log_content(log_text, args.max_chars)

    if args.dry_run:
        print(f"[DRY-RUN] Read last {args.lines} lines from {args.file}")
        print("[DRY-RUN] The following log content will not be sent to server:")
        print(log_text)
        append_run_log(
            args.output_log,
            args,
            "success",
            truncated=truncated,
            message="dry-run completed",
        )
        return 0

    payload = {
        "source": args.source,
        "service_name": args.service_name,
        "env": args.env,
        "log_type": args.log_type,
        "log_text": log_text,
    }
    url = args.server.rstrip("/") + "/logs/ingest"

    try:
        response = requests.post(url, json=payload, timeout=60)
    except requests.exceptions.RequestException as exc:
        append_run_log(
            args.output_log,
            args,
            "failed",
            truncated=truncated,
            error=f"failed to connect to AI-OpsLog server: {exc}",
        )
        print_json(
            {
                "error": "failed to connect to AI-OpsLog server",
                "url": url,
                "detail": str(exc),
            }
        )
        return 1

    if response.status_code != 200:
        append_run_log(
            args.output_log,
            args,
            "failed",
            truncated=truncated,
            error=f"server returned non-200 status: {response.status_code}",
        )
        print_json(
            {
                "error": "server returned non-200 status",
                "status_code": response.status_code,
                "response": response.text,
            }
        )
        return 1

    try:
        response_data = response.json()
    except ValueError:
        append_run_log(
            args.output_log,
            args,
            "failed",
            truncated=truncated,
            error="server response is not valid JSON",
        )
        print_json(
            {
                "error": "server response is not valid JSON",
                "response": response.text,
            }
        )
        return 1

    append_run_log(
        args.output_log,
        args,
        "success",
        truncated=truncated,
        report_path=response_data.get("report_path"),
    )
    print_json(response_data)
    return 0


def append_run_log(
    output_log,
    args,
    status,
    message=None,
    report_path=None,
    error=None,
    truncated=False,
):
    if not output_log:
        return

    try:
        output_path = Path(output_log).expanduser()
        if output_path.parent != Path("."):
            output_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fields = [
            f"[{timestamp}]",
            f"status={status}",
            f"source={_format_log_value(args.source)}",
            f"service={_format_log_value(args.service_name)}",
            f"env={_format_log_value(args.env)}",
            f"log_type={_format_log_value(args.log_type)}",
            f"file={_format_log_value(args.file)}",
            f"lines={args.lines}",
            f"max_chars={args.max_chars}",
            f"dry_run={str(args.dry_run).lower()}",
            f"truncated={str(truncated).lower()}",
        ]
        if report_path:
            fields.append(f"report_path={_format_log_value(report_path)}")
        if message:
            fields.append(f"message={_format_log_value(message)}")
        if error:
            fields.append(f"error={_format_log_value(error)}")

        with output_path.open("a", encoding="utf-8") as log_file:
            log_file.write(" ".join(fields) + "\n")
    except OSError as exc:
        print(f"Warning: failed to write output log: {exc}")


def _format_log_value(value):
    text = str(value).replace("\n", " ").replace('"', '\\"')
    if any(char.isspace() for char in text):
        return f'"{text}"'
    return text


def print_json(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
