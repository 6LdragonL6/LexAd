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
    safety_score: int | None = Field(default=None, ge=0, le=100)
    risk_topics: list[str] = Field(default_factory=list, max_length=30)
    affected_groups: list[str] = Field(default_factory=list, max_length=30)
    propagation_drivers: list[str] = Field(default_factory=list, max_length=30)
    evidence_quotes: list[str] = Field(default_factory=list, max_length=30)
    counter_signals: list[str] = Field(default_factory=list, max_length=30)
    suggestions: list[str] = Field(default_factory=list, max_length=30)
    explanation: str = Field(default="", max_length=4000)
    confidence: int = Field(default=0, ge=0, le=100)
    matched_case_ids: list[str] = Field(default_factory=list, max_length=10)


class AdjudicatedFindingOutput(BaseModel):
    evidence_quote: str = Field(min_length=1, max_length=1000)
    risk_type: str = Field(min_length=1, max_length=100)
    risk_level: str = Field(default="medium", pattern="^(high|medium|low)$")
    reason: str = Field(min_length=1, max_length=2000)
    basis_ids: list[str] = Field(default_factory=list, max_length=10)
    suggestion: str = Field(default="", max_length=2000)
    confidence: int = Field(default=0, ge=0, le=100)


class VerificationItemOutput(BaseModel):
    evidence_quote: str = Field(min_length=1, max_length=1000)
    verification_type: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=2000)
    required_materials: list[str] = Field(default_factory=list, max_length=20)
    basis_ids: list[str] = Field(default_factory=list, max_length=10)


class AdjudicationReviewOutput(BaseModel):
    findings: list[AdjudicatedFindingOutput] = Field(default_factory=list, max_length=50)
    verification_items: list[VerificationItemOutput] = Field(default_factory=list, max_length=30)
    excluded_candidate_ids: list[str] = Field(default_factory=list, max_length=100)
    overall_assessment: str = Field(default="", max_length=4000)


def validate_api_key(api_key: str) -> None:
    _request_json(
        db=None,
        api_key_override=api_key,
        system_prompt='你是 API 连通性检查器。只返回这个 JSON 示例：{"ok": true}',
        payload={"task": "health_check", "required_output": {"ok": True}},
        output_model=HealthOutput,
        max_tokens=64,
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
            "不确定字段使用空字符串、空数组或 null。必须只返回 JSON 对象，格式示例："
            '{"industry":[],"platforms":[],"event_process":{},"consequences":{},'
            '"risk_topics":[],"trigger_patterns":[],"affected_groups":[],'
            '"propagation_drivers":[],"normalized_tags":{},"severity_level":null,'
            '"summary":"","confidence":0}'
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
    trigger_word_hits: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result = _request_json(
        db=db,
        system_prompt=(
            "你是企业品牌舆情风险审查助手。请独立阅读完整物料，识别价值观偏差、苦难营销、"
            "焦虑营销、群体冒犯、歧视、低俗擦边、灾难营销、社会伦理和情绪操纵等开放风险。"
            "舆情风险与是否违法无关，不能因为没有法律违规就判为低风险。"
            "如果商业文案把消费者经历的痛苦、失败、年龄压力、职场困境或社会焦虑与商品价值、"
            "口味理解、身份资格或购买行为绑定，形成说教、消费苦难或情绪操纵，通常至少为 medium；"
            "只有原文存在明确的批判、反讽、公益倡导或非商业语境时，才能用 counter_signals 说明降级。"
            "本地触发词只是不确定线索，不得仅凭单个词直接判定中高风险。"
            "优先使用输入中已核验的相似历史事件，但只有风险机制和完整语境确实相似时才能引用；"
            "共同数字、单字、公共短语、matched_text、分词或相似度分数都不能作为用户可见依据。"
            "相似历史事件只能引用输入中的 event_id，不得虚构事件。evidence_quotes 必须逐字来自物料原文，"
            "应为语义完整片段，不得输出数字切片、关键词列表、内部匹配分或思维过程。"
            "必须只返回 JSON 对象，格式示例："
            'safety_score 表示舆情安全程度，0 到 100，越高越安全。必须与 risk_level 方向一致。'
            '{"risk_level":"medium","safety_score":70,"risk_topics":["价值观争议"],'
            '"affected_groups":[],"propagation_drivers":[],"evidence_quotes":["原文片段"],'
            '"counter_signals":[],"suggestions":["修改建议"],"explanation":"判断理由",'
            '"confidence":70,"matched_case_ids":["输入中的事件ID"]}'
        ),
        payload={
            "task": "explain_public_opinion_risk",
            "material_text": _normalize_text(material_text, 20000),
            "deterministic_hits": deterministic_hits[:20],
            "similar_events": similar_events[:10],
            "trigger_word_hits": (trigger_word_hits or [])[:30],
            "required_risk_levels": ["low", "medium", "high", "severe", "uncertain"],
            "safety_score_range": [0, 100],
            "score_direction": "higher_is_safer",
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
    legal_resources: list[dict[str, Any]],
    candidate_rules: list[dict[str, Any]],
    similar_cases: list[dict[str, Any]],
) -> AdjudicationReviewOutput:
    return _request_json(
        db=db,
        system_prompt=(
            "你是广告法律合规裁决助手。完整阅读物料，并优先依据输入的法规、行业资料和已核验案例裁决。"
            "candidate_rules 只是召回线索，关键词、数字、字符片段或规则命中绝不等于违规。"
            "对每个候选结合上下文选择确认、排除或需核验；也可发现候选未覆盖但输入资料能够支持的问题。"
            "确认问题必须逐字引用物料中的完整证据片段，并且 basis_ids 只能引用 legal_resources 中存在的 id。"
            "销量、数据、检测、认证、资质和来源声明在真实性尚未核实时应进入 verification_items，"
            "不能仅因包含数字或‘累计’等词判为违规。无法找到可靠资料依据时不得编造法规或条款。"
            "不得在面向用户的字段中输出分词、命中关键词、数字切片、内部相似度或思维过程。"
            "必须只返回 JSON 对象，格式示例："
            '{"findings":[{"evidence_quote":"完整违规原文","risk_type":"虚假或误导性宣传",'
            '"risk_level":"medium","reason":"结合上下文的判断理由","basis_ids":["law:1"],'
            '"suggestion":"修改建议","confidence":85}],'
            '"verification_items":[{"evidence_quote":"完整待核验声明","verification_type":"销量数据核验",'
            '"reason":"需核验统计来源和口径","required_materials":["第三方统计报告"],'
            '"basis_ids":["law:1"]}],"excluded_candidate_ids":[],"overall_assessment":"整体评估"}'
        ),
        payload={
            "task": "legal_adjudication_review",
            "industry": _normalize_text(industry, 100),
            "material_text": _normalize_text(material_text, 30000),
            "legal_resources": legal_resources[:20],
            "candidate_rules": candidate_rules[:50],
            "similar_cases": similar_cases[:5],
            "risk_levels": ["high", "medium", "low"],
        },
        output_model=AdjudicationReviewOutput,
        max_tokens=3072,
    )


def platform_review(
    db: Session,
    *,
    material_text: str,
    platform: str,
    rule_version: str,
    candidate_rules: list[dict[str, Any]],
) -> AdjudicationReviewOutput:
    return _request_json(
        db=db,
        system_prompt=(
            "你是平台广告规则裁决助手。完整阅读物料，只依据输入中当前平台的生效规则判断。"
            "candidate_rules 是待审资料，不是已确认违规；关键词、数字、短片段和相似度不得直接决定结论。"
            "只有规则确实适用于当前业务场景且原文存在语义完整的冲突表达时才能确认。"
            "findings 的 evidence_quote 必须逐字来自物料，basis_ids 只能引用输入规则 id。"
            "事实、资质或证明材料不足应进入 verification_items。没有明确问题时返回空 findings。"
            "不得输出原始关键词、分词、数字切片、匹配分或内部推理。必须只返回 JSON 对象，格式与示例一致："
            '{"findings":[],"verification_items":[],"excluded_candidate_ids":[],"overall_assessment":"未发现明确冲突"}'
        ),
        payload={
            "task": "platform_adjudication_review",
            "platform": _normalize_text(platform, 100),
            "rule_version": _normalize_text(rule_version, 200),
            "material_text": _normalize_text(material_text, 30000),
            "candidate_rules": candidate_rules[:60],
            "risk_levels": ["high", "medium", "low"],
        },
        output_model=AdjudicationReviewOutput,
        max_tokens=2560,
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
                extra_body={"thinking": {"type": "disabled"}},
            )
            choice = response.choices[0]
            finish_reason = getattr(choice, "finish_reason", None) or "stop"
            if finish_reason == "length":
                last_error = DeepSeekGatewayError(
                    "模型响应被长度限制截断，请重试",
                    category="truncated_response",
                    retryable=True,
                )
                if attempt < 2:
                    time.sleep((0.25 * (2**attempt)) + random.uniform(0, 0.1))
                    continue
                raise last_error
            if finish_reason not in {"stop", "tool_calls"}:
                raise DeepSeekGatewayError(
                    f"模型未正常完成响应（{finish_reason}）",
                    category="incomplete_response",
                )
            content = choice.message.content
            if not content:
                last_error = DeepSeekGatewayError(
                    "模型返回空响应，请重试",
                    category="empty_response",
                    retryable=True,
                )
                if attempt < 2:
                    time.sleep((0.25 * (2**attempt)) + random.uniform(0, 0.1))
                    continue
                raise last_error
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
        except AuthenticationError as exc:
            raise DeepSeekGatewayError("DeepSeek 拒绝了当前 API Key（HTTP 401）", category="authentication") from exc
        except PermissionDeniedError as exc:
            raise DeepSeekGatewayError("当前 API Key 无权使用固定模型（HTTP 403）", category="permission") from exc
        except BadRequestError as exc:
            logger.warning(
                "DeepSeek request rejected task=%s status=400 request_id=%s",
                payload.get("task", "unknown"),
                getattr(exc, "request_id", None) or "unknown",
            )
            raise DeepSeekGatewayError("审查请求不符合模型接口要求（HTTP 400）", category="bad_request") from exc
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            last_error = DeepSeekGatewayError("模型服务暂时不可用", category="transient", retryable=True)
        except APIStatusError as exc:
            if exc.status_code == 402:
                raise DeepSeekGatewayError("DeepSeek 账户余额不足（HTTP 402）", category="balance") from exc
            if exc.status_code == 422:
                raise DeepSeekGatewayError("DeepSeek 请求参数无效（HTTP 422）", category="bad_request") from exc
            if exc.status_code >= 500:
                last_error = DeepSeekGatewayError("模型服务暂时不可用", category="upstream", retryable=True)
            else:
                raise DeepSeekGatewayError("模型服务拒绝请求", category="upstream_request") from exc
        except (json.JSONDecodeError, ValidationError, KeyError, IndexError, TypeError) as exc:
            last_error = DeepSeekGatewayError(
                "模型响应未通过结构校验",
                category="invalid_response",
                retryable=True,
            )
            logger.warning(
                "DeepSeek response validation failed task=%s attempt=%s error_type=%s",
                payload.get("task", "unknown"),
                attempt + 1,
                type(exc).__name__,
            )

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
