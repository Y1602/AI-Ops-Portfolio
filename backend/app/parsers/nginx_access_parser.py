import re
from collections import Counter


ACCESS_PATTERN = re.compile(
    r'(?P<ip>\d{1,3}(?:\.\d{1,3}){3}).*?"(?P<method>[A-Z]+)\s+(?P<path>\S+)\s+HTTP/[^"]+"\s+(?P<status>\d{3})'
)

SUSPICIOUS_PATH_KEYWORDS = [
    "/admin",
    "/login",
    "/wp-admin",
    "/.env",
    "/phpmyadmin",
]


def parse(log_text: str) -> dict:
    try:
        lines = [line.strip() for line in log_text.splitlines() if line.strip()]
        status_counter = Counter()
        ip_counter = Counter()
        suspicious_paths = set()
        parsed_samples = []
        error_count = 0

        for line in lines:
            match = ACCESS_PATTERN.search(line)
            if not match:
                continue

            ip = match.group("ip")
            method = match.group("method")
            path = match.group("path")
            status_code = match.group("status")

            status_counter[status_code] += 1
            ip_counter[ip] += 1

            if status_code.startswith(("4", "5")):
                error_count += 1

            if any(keyword in path.lower() for keyword in SUSPICIOUS_PATH_KEYWORDS):
                suspicious_paths.add(path)

            if len(parsed_samples) < 5:
                parsed_samples.append(
                    {
                        "ip": ip,
                        "method": method,
                        "path": path,
                        "status_code": status_code,
                    }
                )

        total_lines = len(lines)
        error_rate = error_count / total_lines if total_lines else 0

        if error_rate >= 0.5:
            severity = "high"
        elif error_rate >= 0.2:
            severity = "medium"
        else:
            severity = "low"

        return {
            "log_type": "nginx_access",
            "total_lines": total_lines,
            "status_code_count": dict(status_counter),
            "top_client_ips": [
                {"ip": ip, "count": count} for ip, count in ip_counter.most_common(5)
            ],
            "suspicious_paths": sorted(suspicious_paths),
            "error_count": error_count,
            "error_rate": round(error_rate, 4),
            "severity": severity,
            "parsed_samples": parsed_samples,
        }
    except Exception as exc:
        return {
            "log_type": "nginx_access",
            "error": "failed to parse nginx access log",
            "detail": str(exc),
        }

