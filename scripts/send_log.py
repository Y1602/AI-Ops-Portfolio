import argparse
import json
from pathlib import Path

import requests


SUPPORTED_LOG_TYPES = {"nginx_access", "nginx_error", "docker_log"}
BLOCKED_FILE_NAMES = {".env", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}
BLOCKED_PATH_PARTS = {"etc", "proc", "sys", "dev", "root", ".ssh"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a local log file to AI-OpsLog /logs/ingest."
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    log_file = Path(args.file).expanduser()

    if not _is_allowed_file(log_file):
        print_json(
            {
                "error": "refusing to read sensitive or unsafe file path",
                "file": str(log_file),
            }
        )
        return 1

    if not log_file.exists() or not log_file.is_file():
        print_json({"error": "log file does not exist", "file": str(log_file)})
        return 1

    try:
        log_text = log_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print_json({"error": "failed to read log file as UTF-8", "file": str(log_file)})
        return 1
    except OSError as exc:
        print_json(
            {
                "error": "failed to read log file",
                "file": str(log_file),
                "detail": str(exc),
            }
        )
        return 1

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


def _is_allowed_file(log_file: Path) -> bool:
    file_name = log_file.name.lower()
    if file_name in BLOCKED_FILE_NAMES or file_name.endswith(".key"):
        return False

    path_parts = {part.lower() for part in log_file.parts}
    if path_parts & BLOCKED_PATH_PARTS:
        return False

    return True


def print_json(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
