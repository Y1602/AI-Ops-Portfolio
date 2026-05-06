import json
import os
from pathlib import Path


def call_qwen_model(prompt: str) -> dict:
    try:
        try:
            from dotenv import load_dotenv

            project_root_env = Path(__file__).resolve().parents[3] / ".env"
            load_dotenv(project_root_env)
            load_dotenv()
        except ImportError:
            pass

        dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
        if not dashscope_api_key:
            return {"error": "DASHSCOPE_API_KEY is not configured"}

        from openai import OpenAI

        client = OpenAI(
            api_key=dashscope_api_key,
            base_url=os.getenv(
                "DASHSCOPE_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
        )

        completion = client.chat.completions.create(
            model=os.getenv("QWEN_MODEL", "qwen-plus"),
            messages=[
                {"role": "system", "content": "你是一个严谨的运维/SRE日志分析助手。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        content = completion.choices[0].message.content or ""
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
            "error": "Failed to call Qwen model",
            "detail": str(exc),
        }


def _clean_json_code_block(content: str) -> str:
    text = content.strip()

    if text.startswith("```json"):
        text = text.removeprefix("```json").strip()
    elif text.startswith("```"):
        text = text.removeprefix("```").strip()

    if text.endswith("```"):
        text = text.removesuffix("```").strip()

    return text
