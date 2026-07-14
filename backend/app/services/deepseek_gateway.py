from __future__ import annotations

import json
import random
import time
from typing import Any, TypeVar

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.services.admin_settings_service import FIXED_BASE_URL, FIXED_MODEL, get_api_key


logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)


class DeepSeekGatewayError(RuntimeError):
    def __init__(self, message: str, *, category: str, retryable: bool = False):
        super().__init__(message)
        self.category = category
        self.retryable = retryable


class HealthOutput(BaseModel):
    ok: bool


class PublicOpinionCaseOutput(BaseModel):
    industry: list[str] = Field(default_factory=list, max_length=20)
    platforms: list[str] = Field(default_factory=list, max_length=20)
    event_process: dict[str, Any]
    consequences: dict[str, Any]
    risk_topics: list[str] = Field(default_factory=list, max_length=30)
    trigger_patterns: list[str] = Field(default_factory=list, max_length=30)
    affected_groups: list[str] = Field(default_factory=list, max_length=30)
    propagation_drivers: list[str] = Field(default_factory=list, max_length=30)
    normalized_tags: dict[str, Any]
    severity_level: str | None = None
    summary: str = Field(default="", max_length=4000)
    confidence: int | None = Field(default=None, ge=0, le=100)


class PublicOpinionRiskOutput(BaseModel):
    risk_level: str = Field(pattern="^(low|medium|high|severe|uncertain)$")
    risk_topics: list[str] = Field(default_factory=list, max_length=30)
    affected_groups: list[str] = Field(default_factory=list, max_length=30)
    propagation_drivers: list[str] = Field(default_factory=list, max_length=30)
    suggestions: list[str] = Field(default_factory=list, max_length=30)
    explanation: str = Field(max_length=4000)
    confidence: int = Field(default=0, ge=0, le=100)


class SemanticViolation(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    reason: str = Field(default="", max_length=2000)
    law_ref: str = Field(default="", max_length=1000)
    risk_level: str = Field(default="medium", pattern="^(high|medium|low)$")
    suggestion: str = Field(default="", max_length=2000)


class SemanticReviewOutput(BaseModel):
    violations: list[SemanticViolation] = Field(default_factory=list, max_length=50)
    overall_assessment: str = Field(default="", max_length=4000)


def validate_api_key(api_key: str) -> None:
    _request_json(
        db=None,
        api_key_override=api_key,
        system_prompt="你是 API 连通性检查器，只返回 JSON。",
        payload={"task": "health_check", "required_output": {"ok": True}},
        output_model=HealthOutput,
        max_tokens=16,
    )


def structure_public_opinion_case(
    db: Session,
    *,
    title: str,
    source_text: str,
    consequence_text: str,
) -> dict[str, Any]:
    result = _request_json(
        db=db,
        system_prompt=(
            "你是企业品牌舆情案例整理助手。只根据输入事实整理结构化结果，不得编造。"
            "不确定字段使用空字符串、空数组或 null。"
        ),
        payload={
            "task": "structure_public_opinion_case",
            "title": _normalize_text(title, 200),
            "source_text": _normalize_text(source_text, 20000),
            "consequence_text": _normalize_text(consequence_text, 10000),
            "required_fields": [
                "industry", "platforms", "event_process", "consequences", "risk_topics",
                "trigger_patterns", "affected_groups", "propagation_drivers", "normalized_tags",
                "severity_level", "summary", "confidence",
            ],
        },
        output_model=PublicOpinionCaseOutput,
        max_tokens=2048,
    )
    return result.model_dump()


def explain_public_opinion_risk(
    db: Session,
    *,
    material_text: str,
    deterministic_hits: list[dict[str, Any]],
    similar_events: list[dict[str, Any]],
) -> dict[str, Any]:
    result = _request_json(
        db=db,
        system_prompt=(
            "你是企业品牌舆情风险审查助手。只根据输入物料、确定性命中和相似历史事件解释风险。"
            "不得虚构历史事件；依据不足时 risk_level 必须为 uncertain。"
        ),
        payload={
            "task": "explain_public_opinion_risk",
            "material_text": _normalize_text(material_text, 20000),
            "deterministic_hits": deterministic_hits[:20],
            "similar_events": similar_events[:10],
            "required_risk_levels": ["low", "medium", "high", "severe", "uncertain"],
        },
        output_model=PublicOpinionRiskOutput,
        max_tokens=1536,
    )
    return result.model_dump()


def semantic_review(
    db: Session,
    *,
    material_text: str,
    industry: str,
    legal_basis: str,
    similar_cases: list[dict[str, Any]],
) -> SemanticReviewOutput:
    return _request_json(
        db=db,
        system_prompt=(
            "你是广告合规审查助手。仅依据输入法规和案例识别语义违规。"
            "每项必须引用输入中存在的依据；无法确认时不要编造。"
        ),
        payload={
            "task": "semantic_ad_review",
            "industry": _normalize_text(industry, 100),
            "material_text": _normalize_text(material_text, 30000),
            "legal_basis": _normalize_text(legal_basis, 24000),
            "similar_cases": similar_cases[:5],
            "risk_levels": ["high", "medium", "low"],
        },
        output_model=SemanticReviewOutput,
        max_tokens=2048,
    )


def _request_json(
    *,
    db: Session | None,
    system_prompt: str,
    payload: dict[str, Any],
    output_model: type[T],
    max_tokens: int,
    api_key_override: str | None = None,
) -> T:
    api_key = api_key_override or (get_api_key(db) if db is not None else "")
    if not api_key:
        raise DeepSeekGatewayError("DeepSeek API Key 尚未配置", category="unconfigured")

    client = OpenAI(
        api_key=api_key,
        base_url=FIXED_BASE_URL,
        timeout=httpx.Timeout(90.0, connect=10.0),
        max_retries=0,
    )
    last_error: DeepSeekGatewayError | None = None
    for attempt in range(3):
        started = time.monotonic()
        try:
            response = client.chat.completions.create(
                model=FIXED_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            if not content:
                raise DeepSeekGatewayError("模型返回空响应", category="empty_response")
            parsed = json.loads(_strip_code_fence(content))
            result = output_model.model_validate(parsed)
            logger.info(
                "DeepSeek call succeeded task=%s attempt=%s elapsed_ms=%s",
                payload.get("task", "unknown"),
                attempt + 1,
                int((time.monotonic() - started) * 1000),
            )
            return result
        except DeepSeekGatewayError:
            raise
        except (AuthenticationError, PermissionDeniedError) as exc:
            raise DeepSeekGatewayError("API Key 无效或无权使用固定模型", category="authentication") from exc
        except BadRequestError as exc:
            raise DeepSeekGatewayError("模型请求格式或固定模型不可用", category="bad_request") from exc
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            last_error = DeepSeekGatewayError("模型服务暂时不可用", category="transient", retryable=True)
        except APIStatusError as exc:
            if exc.status_code >= 500:
                last_error = DeepSeekGatewayError("模型服务暂时不可用", category="upstream", retryable=True)
            else:
                raise DeepSeekGatewayError("模型服务拒绝请求", category="upstream_request") from exc
        except (json.JSONDecodeError, ValidationError, KeyError, IndexError, TypeError) as exc:
            raise DeepSeekGatewayError("模型响应未通过结构校验", category="invalid_response") from exc

        if last_error and attempt < 2:
            time.sleep((0.25 * (2**attempt)) + random.uniform(0, 0.1))
            continue
        break
    raise last_error or DeepSeekGatewayError("模型调用失败", category="unknown")


def _normalize_text(value: str, max_length: int) -> str:
    lines = [line.strip() for line in str(value or "").replace("\r\n", "\n").split("\n")]
    normalized = "\n".join(line for line in lines if line).strip()
    return normalized[:max_length]


def _strip_code_fence(content: str) -> str:
    normalized = content.strip()
    if normalized.startswith("```"):
        first_newline = normalized.find("\n")
        if first_newline >= 0:
            normalized = normalized[first_newline + 1 :]
        if normalized.endswith("```"):
            normalized = normalized[:-3]
    return normalized.strip()
