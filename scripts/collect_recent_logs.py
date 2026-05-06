import argparse
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


def main() -> int:
    args = parse_args()
    log_file = Path(args.file).expanduser()

    if not is_safe_log_file(str(log_file)):
        print(f"Refuse to read sensitive file: {args.file}")
        return 1

    if not log_file.exists():
        print_json({"error": "log file does not exist", "file": str(log_file)})
        return 1

    if not log_file.is_file():
        print_json({"error": "path is not a regular file", "file": str(log_file)})
        return 1

    try:
        log_text = read_last_lines(str(log_file), args.lines)
    except OSError as exc:
        print_json(
            {
                "error": "failed to read log file",
                "file": str(log_file),
                "detail": str(exc),
            }
        )
        return 1

    if not log_text.strip():
        print_json(
            {
                "message": "no log content was read from file",
                "file": str(log_file),
                "lines": args.lines,
            }
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
        print_json(
            {
                "error": "failed to connect to AI-OpsLog server",
                "url": url,
                "detail": str(exc),
            }
        )
        return 1

    if response.status_code != 200:
        print_json(
            {
                "error": "server returned non-200 status",
                "status_code": response.status_code,
                "response": response.text,
            }
        )
        return 1

    try:
        print_json(response.json())
    except ValueError:
        print_json(
            {
                "error": "server response is not valid JSON",
                "response": response.text,
            }
        )
        return 1

    return 0


def print_json(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
