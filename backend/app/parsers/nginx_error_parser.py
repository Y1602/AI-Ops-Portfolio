from collections import Counter


ERROR_KEYWORDS = [
    "connect() failed",
    "upstream timed out",
    "no live upstreams",
    "permission denied",
    "too many open files",
    "host not found in upstream",
]


def parse(log_text: str) -> dict:
    try:
        lines = [line.strip() for line in log_text.splitlines() if line.strip()]
        keyword_counter = Counter()
        sample_lines = []

        for line in lines:
            lower_line = line.lower()
            matched = False

            for keyword in ERROR_KEYWORDS:
                if keyword.lower() in lower_line:
                    keyword_counter[keyword] += 1
                    matched = True

            if matched and len(sample_lines) < 5:
                sample_lines.append(line)

        matched_keywords = dict(keyword_counter)
        matched_count = len(matched_keywords)

        if matched_count >= 2:
            severity = "high"
        elif matched_count == 1:
            severity = "medium"
        else:
            severity = "low"

        return {
            "log_type": "nginx_error",
            "total_lines": len(lines),
            "matched_keywords": matched_keywords,
            "error_summary": _build_summary(matched_keywords),
            "severity": severity,
            "sample_lines": sample_lines,
        }
    except Exception as exc:
        return {
            "log_type": "nginx_error",
            "error": "failed to parse nginx error log",
            "detail": str(exc),
        }


def _build_summary(matched_keywords: dict) -> str:
    if not matched_keywords:
        return "No known nginx error keyword matched."

    parts = [
        f"{keyword}: {count}" for keyword, count in sorted(matched_keywords.items())
    ]
    return "; ".join(parts)

