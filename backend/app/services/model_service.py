import json
from typing import Any

from openai import OpenAI

from app.core.config import get_settings


class ModelServiceError(RuntimeError):
    """Raised when the shared model service cannot return a structured result."""


def structure_public_opinion_case(
    *,
    title: str,
    source_text: str,
    consequence_text: str,
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY.strip():
        raise ModelServiceError("DeepSeek API key is not configured")

    system_prompt = """你是企业品牌舆情案例整理助手。只根据用户提供的事实材料整理结构化 JSON。
要求：
1. 不得编造材料中没有的事实。
2. 不确定的字段使用空字符串、空数组或 null。
3. 只输出 JSON，不输出 Markdown。
JSON 格式：
{
  "industry": [],
  "platforms": [],
  "event_process": {
    "trigger": "",
    "timeline": [],
    "brand_response": "",
    "outcome": ""
  },
  "consequences": {
    "reputation": "",
    "business": "",
    "regulatory": "",
    "duration_days": null,
    "severity_hint": null
  },
  "risk_topics": [],
  "trigger_patterns": [],
  "affected_groups": [],
  "propagation_drivers": [],
  "normalized_tags": {},
  "severity_level": null,
  "summary": "",
  "confidence": 0
}"""
    user_prompt = f"""标题：{title}

事件材料：
{source_text}

后果材料：
{consequence_text}
"""
    try:
        client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        content = response.choices[0].message.content
        if not content:
            raise ModelServiceError("DeepSeek returned an empty response")
        result = _parse_json_content(content)
        _validate_public_opinion_model_result(result)
        return result
    except ModelServiceError:
        raise
    except Exception as exc:
        raise ModelServiceError(f"DeepSeek public opinion structuring failed: {str(exc)[:200]}") from exc


def explain_public_opinion_risk(
    *,
    material_text: str,
    deterministic_hits: list[dict[str, Any]],
    similar_events: list[dict[str, Any]],
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY.strip():
        raise ModelServiceError("DeepSeek API key is not configured")

    system_prompt = """你是企业品牌舆情风险审查助手。只根据广告物料、确定性命中和相似历史事件解释风险。
要求：
1. 不得虚构未提供的历史事件或后果。
2. 依据不足时 risk_level 使用 uncertain。
3. 只输出 JSON，不输出 Markdown。
JSON 格式：
{
  "risk_level": "low|medium|high|severe|uncertain",
  "risk_topics": [],
  "affected_groups": [],
  "propagation_drivers": [],
  "suggestions": [],
  "explanation": "",
  "confidence": 0
}"""
    user_prompt = json.dumps(
        {
            "material_text": material_text,
            "deterministic_hits": deterministic_hits,
            "similar_events": similar_events,
        },
        ensure_ascii=False,
    )
    try:
        client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=1536,
        )
        content = response.choices[0].message.content
        if not content:
            raise ModelServiceError("DeepSeek returned an empty response")
        result = _parse_json_content(content)
        _validate_public_opinion_risk_result(result)
        return result
    except ModelServiceError:
        raise
    except Exception as exc:
        raise ModelServiceError(f"DeepSeek public opinion risk explanation failed: {str(exc)[:200]}") from exc


def _parse_json_content(content: str) -> dict[str, Any]:
    normalized = content.strip()
    if normalized.startswith("```"):
        normalized = normalized.removeprefix("```json").removeprefix("```")
        normalized = normalized.removesuffix("```").strip()
    result = json.loads(normalized)
    if not isinstance(result, dict):
        raise ModelServiceError("DeepSeek returned a non-object JSON result")
    return result


def _validate_public_opinion_model_result(result: dict[str, Any]) -> None:
    required_object_fields = ["event_process", "consequences", "normalized_tags"]
    for field in required_object_fields:
        if field not in result or not isinstance(result[field], dict):
            raise ModelServiceError(f"DeepSeek result missing object field: {field}")
    required_list_fields = [
        "industry",
        "platforms",
        "risk_topics",
        "trigger_patterns",
        "affected_groups",
        "propagation_drivers",
    ]
    for field in required_list_fields:
        if field not in result or not isinstance(result[field], list):
            raise ModelServiceError(f"DeepSeek result missing list field: {field}")


def _validate_public_opinion_risk_result(result: dict[str, Any]) -> None:
    if result.get("risk_level") not in {"low", "medium", "high", "severe", "uncertain"}:
        raise ModelServiceError("DeepSeek result has invalid risk_level")
    for field in ["risk_topics", "affected_groups", "propagation_drivers", "suggestions"]:
        if field not in result or not isinstance(result[field], list):
            raise ModelServiceError(f"DeepSeek result missing list field: {field}")
    if "explanation" not in result or not isinstance(result["explanation"], str):
        raise ModelServiceError("DeepSeek result missing explanation")
