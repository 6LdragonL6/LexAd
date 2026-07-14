from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.engine.layer4_platform import (
    PlatformReviewResult,
    _validated_platform_findings,
)
from app.engine.pipeline import run_review_pipeline
from app.engine.public_opinion import run_public_opinion_review
from app.schemas.review import LayerResult, VerificationItem
from app.services.deepseek_gateway import (
    AdjudicatedFindingOutput,
    AdjudicationReviewOutput,
    VerificationItemOutput,
)


TARGET_COPY = "优益畅益生菌，累计售出100万盒（数据来源：第三方销售统计报告），呵护肠道健康。"


def test_legal_adjudication_rejects_numeric_fragment_and_keeps_full_verification(monkeypatch):
    import app.engine.layer2_semantic as layer2

    monkeypatch.setattr(
        layer2,
        "_load_law_resources",
        lambda _industry: [{
            "id": "law:1",
            "title": "广告真实性规则",
            "version": "现行资料库",
            "content": "广告中的数据、统计资料和引用内容应当真实、准确并表明出处。",
        }],
    )
    monkeypatch.setattr(layer2, "_search_similar_cases", lambda _text: [])
    monkeypatch.setattr(
        layer2,
        "semantic_review",
        lambda *_args, **_kwargs: AdjudicationReviewOutput(
            findings=[
                AdjudicatedFindingOutput(
                    evidence_quote="100万",
                    risk_type="虚假宣传",
                    risk_level="high",
                    reason="错误地仅依据数字判断",
                    basis_ids=["law:1"],
                    confidence=90,
                )
            ],
            verification_items=[
                VerificationItemOutput(
                    evidence_quote="累计售出100万盒（数据来源：第三方销售统计报告）",
                    verification_type="销量数据核验",
                    reason="需核验第三方报告真实性、统计周期和销量口径",
                    required_materials=["第三方销售统计报告"],
                    basis_ids=["law:1"],
                )
            ],
            overall_assessment="该表述属于待核验的事实声明",
        ),
    )

    result = layer2.run_semantic_review(TARGET_COPY, "食品", None, [])

    assert result.matched_rules == []
    assert len(result.verification_items) == 1
    assert result.verification_items[0].verification_type == "销量数据核验"
    assert result.requires_manual_review is True  # invalid numeric-only finding was rejected


def test_pipeline_never_exposes_hard_rule_candidates_or_deducts_for_verification(monkeypatch):
    import app.engine.layer2_semantic as layer2
    import app.engine.pipeline as pipeline

    verification = VerificationItem(
        item_id="verify-sales",
        evidence_quote="累计售出100万盒（数据来源：第三方销售统计报告）",
        verification_type="销量数据核验",
        reason="需核验来源和统计口径",
        required_materials=["第三方销售统计报告"],
    )
    monkeypatch.setattr(
        layer2,
        "run_semantic_review",
        lambda *_args, **_kwargs: LayerResult(
            layer="法律语义裁决",
            verification_items=[verification],
            status="no_match",
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "run_platform_adjudication",
        lambda *_args, **_kwargs: PlatformReviewResult(layer="平台规则裁决", status="no_match"),
    )

    result = run_review_pipeline(TARGET_COPY, "食品", [], None)

    assert result.layer1.matched_rules == []
    assert result.hit_count == 0
    assert result.risk_score == 100
    assert result.review_status == "needs_verification"
    assert result.verification_items[0].evidence_quote.startswith("累计售出100万盒")


def test_empty_legal_resource_library_requires_manual_review(monkeypatch):
    import app.engine.layer2_semantic as layer2

    monkeypatch.setattr(layer2, "_load_law_resources", lambda _industry: [])
    monkeypatch.setattr(layer2, "_search_similar_cases", lambda _text: [])
    monkeypatch.setattr(
        layer2,
        "semantic_review",
        lambda *_args, **_kwargs: AdjudicationReviewOutput(overall_assessment="没有可引用资料"),
    )

    result = layer2.run_semantic_review("普通广告文案", "食品", None, [])

    assert result.matched_rules == []
    assert result.requires_manual_review is True
    assert any("资料库" in message for message in result.explanations)


def test_platform_validator_rejects_numeric_slice_and_accepts_complete_evidence():
    rule_set = SimpleNamespace(display_name="测试平台")
    version = SimpleNamespace(id="version-1", version_label="2026-07")
    candidates = {
        "L4-version-1-rule-1": {
            "id": "L4-version-1-rule-1",
            "title": "数据宣传规则",
        }
    }
    findings, rejected = _validated_platform_findings(
        TARGET_COPY,
        rule_set,
        version,
        [
            {
                "evidence_quote": "0万",
                "risk_type": "数据宣传风险",
                "risk_level": "high",
                "reason": "无意义数字切片",
                "basis_ids": ["L4-version-1-rule-1"],
                "confidence": 90,
            },
            {
                "evidence_quote": "累计售出100万盒（数据来源：第三方销售统计报告）",
                "risk_type": "数据宣传风险",
                "risk_level": "medium",
                "reason": "完整声明需要结合平台规则核验",
                "basis_ids": ["L4-version-1-rule-1"],
                "confidence": 85,
            },
        ],
        candidates,
    )

    assert rejected == 1
    assert len(findings) == 1
    assert findings[0].matched_text == ""
    assert findings[0].evidence_quote.startswith("累计售出100万盒")


def test_public_opinion_exposes_only_ai_validated_evidence(monkeypatch):
    import app.engine.public_opinion as public_opinion

    monkeypatch.setattr(
        public_opinion.model_service,
        "explain_public_opinion_risk",
        lambda **_kwargs: {
            "risk_level": "low",
            "risk_score": 10,
            "risk_topics": [],
            "affected_groups": [],
            "propagation_drivers": [],
            "evidence_quotes": ["累计售出100万盒（数据来源：第三方销售统计报告）"],
            "counter_signals": ["提供了明确的数据来源"],
            "suggestions": ["发布前核验报告"],
            "explanation": "未发现明确舆情风险，数据声明应另行核验。",
            "confidence": 90,
            "matched_case_ids": [],
        },
    )
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        result = run_public_opinion_review(
            material_text=TARGET_COPY,
            industry="食品",
            platforms=["抖音"],
            db=db,
        )

    assert result.result["risk_level"] == "low"
    assert result.result["similar_events"] == []
    assert "deterministic_hits" not in result.result
    assert "trigger_word_hits" not in result.result
    assert result.result["evidence_quotes"] == ["累计售出100万盒（数据来源：第三方销售统计报告）"]


def test_public_opinion_model_failure_never_promotes_local_keywords(monkeypatch):
    import app.engine.public_opinion as public_opinion

    monkeypatch.setattr(
        public_opinion.model_service,
        "explain_public_opinion_risk",
        lambda **_kwargs: (_ for _ in ()).throw(public_opinion.model_service.ModelServiceError("模型不可用")),
    )
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        result = run_public_opinion_review(
            material_text=TARGET_COPY,
            industry="食品",
            platforms=["抖音"],
            db=db,
        )

    assert result.result["risk_level"] == "uncertain"
    assert result.result["requires_manual_review"] is True
    assert result.result["similar_events"] == []
    assert result.result["evidence_quotes"] == []
