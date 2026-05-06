import json
import os
from pathlib import Path
from typing import Optional

DEFAULT_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_QWEN_MODEL = "qwen-plus"


def call_qwen_model(prompt: str) -> dict:
    try:
        _load_env_file()
        dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
        base_url = os.getenv("DASHSCOPE_BASE_URL", DEFAULT_DASHSCOPE_BASE_URL)
        model = os.getenv("QWEN_MODEL", DEFAULT_QWEN_MODEL)

        if not dashscope_api_key:
            return {
                "error": "DASHSCOPE_API_KEY is not configured",
                "hint": "Please set DASHSCOPE_API_KEY in environment variables or .env file.",
            }

        try:
            from openai import OpenAI

            client = OpenAI(api_key=dashscope_api_key, base_url=base_url)
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个严谨的运维/SRE日志分析助手。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
        except Exception as exc:
            return _api_error_response(exc, dashscope_api_key, base_url, model)

        content = completion.choices[0].message.content or ""
        if not content.strip():
            return {"error": "Qwen response is empty"}

        cleaned_content = _clean_json_code_block(content)
        try:
            return json.loads(cleaned_content)
        except json.JSONDecodeError:
            return {
                "error": "Qwen response is not valid JSON",
                "raw_response": content,
            }
    except Exception as exc:
        return {
            "error": "Qwen API request failed",
            "detail": _safe_detail(exc),
            "error_type": type(exc).__name__,
            "base_url": os.getenv("DASHSCOPE_BASE_URL", DEFAULT_DASHSCOPE_BASE_URL),
            "model": os.getenv("QWEN_MODEL", DEFAULT_QWEN_MODEL),
        }


def test_qwen_connection() -> dict:
    try:
        _load_env_file()
        dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
        base_url = os.getenv("DASHSCOPE_BASE_URL", DEFAULT_DASHSCOPE_BASE_URL)
        model = os.getenv("QWEN_MODEL", DEFAULT_QWEN_MODEL)

        if not dashscope_api_key:
            return {
                "success": False,
                "error": "DASHSCOPE_API_KEY is not configured",
                "hint": "Please set DASHSCOPE_API_KEY in environment variables or .env file.",
            }

        try:
            from openai import OpenAI

            client = OpenAI(api_key=dashscope_api_key, base_url=base_url)
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个严谨的 JSON 输出助手。"},
                    {
                        "role": "user",
                        "content": '请只返回如下 JSON，不要输出其他内容：\n{"status":"ok","message":"qwen connected"}',
                    },
                ],
                temperature=0.2,
            )
        except Exception as exc:
            error_result = _api_error_response(exc, dashscope_api_key, base_url, model)
            return {"success": False, **error_result}

        content = completion.choices[0].message.content or ""
        cleaned_content = _clean_json_code_block(content)

        try:
            response = json.loads(cleaned_content)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Qwen response is not valid JSON",
                "raw_response": content,
                "model": model,
                "base_url": base_url,
            }

        return {
            "success": True,
            "model": model,
            "base_url": base_url,
            "response": response,
        }
    except Exception as exc:
        return {
            "success": False,
            "error": "Qwen API request failed",
            "detail": _safe_detail(exc),
            "error_type": type(exc).__name__,
            "model": os.getenv("QWEN_MODEL", DEFAULT_QWEN_MODEL),
            "base_url": os.getenv("DASHSCOPE_BASE_URL", DEFAULT_DASHSCOPE_BASE_URL),
        }


def _load_env_file() -> None:
    try:
        from dotenv import load_dotenv

        project_root_env = Path(__file__).resolve().parents[3] / ".env"
        load_dotenv(project_root_env, override=False)
    except ImportError:
        pass


def _api_error_response(exc: Exception, api_key: str, base_url: str, model: str) -> dict:
    return {
        "error": "Qwen API request failed",
        "detail": _safe_detail(exc, api_key),
        "error_type": type(exc).__name__,
        "base_url": base_url,
        "model": model,
    }


def _safe_detail(exc: Exception, api_key: Optional[str] = None) -> str:
    detail = str(exc)
    if api_key:
        detail = detail.replace(api_key, "***")
    return detail


def _clean_json_code_block(content: str) -> str:
    text = content.strip()

    if text.startswith("```json"):
        text = text.removeprefix("```json").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()

    if text.endswith("```"):
        text = text.removesuffix("```").strip()

    return text
