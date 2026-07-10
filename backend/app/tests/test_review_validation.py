import pytest
from pydantic import ValidationError

from app.schemas.material import MaterialUpdate
from app.schemas.review import LegalDecisionRequest


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
