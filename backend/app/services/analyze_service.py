from app.parsers import docker_log_parser
from app.parsers import nginx_access_parser
from app.parsers import nginx_error_parser


def analyze_log(log_type: str, log_text: str) -> dict:
    parsers = {
        "nginx_access": nginx_access_parser.parse,
        "nginx_error": nginx_error_parser.parse,
        "docker_log": docker_log_parser.parse,
    }

    parser = parsers.get(log_type)
    if not parser:
        return {
            "error": "unsupported log_type",
            "supported_log_types": sorted(parsers.keys()),
        }

    return parser(log_text)

