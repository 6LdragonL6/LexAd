import pytest
from pydantic import ValidationError

from app.schemas.material import MaterialUpdate
from app.schemas.review import LegalDecisionRequest
from app.db.base import Base
from app.engine.pipeline import run_review_pipeline
from app.engine.layer2_semantic import SemanticReviewError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_conditional_decision_requires_conditions():
    with pytest.raises(ValidationError, match="必须填写附加条件"):
        LegalDecisionRequest(decision="conditional")

    decision = LegalDecisionRequest(decision="conditional", notes="发布时需补充资质说明")
    assert decision.notes == "发布时需补充资质说明"


def test_material_update_uses_creation_constraints():
    with pytest.raises(ValidationError):
        MaterialUpdate(priority="invalid")
    with pytest.raises(ValidationError):
        MaterialUpdate(name="")
    with pytest.raises(ValidationError):
        MaterialUpdate(platforms=["a"] * 11)


def test_semantic_model_failure_preserves_deterministic_pipeline(monkeypatch):
    import app.engine.layer2_semantic as layer2_semantic

    monkeypatch.setattr(
        layer2_semantic,
        "run_semantic_review",
        lambda *_args: (_ for _ in ()).throw(SemanticReviewError("模型暂不可用")),
    )
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        result = run_review_pipeline("这是普通广告文案", "食品", [], db)
    assert result.layer2.status == "unavailable"
    assert result.layer1.status in {"matched", "no_match"}
    assert result.layer3.status in {"matched", "no_match"}
