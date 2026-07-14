from typing import Any

from sqlalchemy.orm import Session

from app.services import deepseek_gateway


class ModelServiceError(RuntimeError):
    """Raised when the shared model service cannot return a structured result."""


def structure_public_opinion_case(
    db: Session,
    *,
    title: str,
    source_text: str,
    consequence_text: str,
) -> dict[str, Any]:
    try:
        return deepseek_gateway.structure_public_opinion_case(
            db,
            title=title,
            source_text=source_text,
            consequence_text=consequence_text,
        )
    except deepseek_gateway.DeepSeekGatewayError as exc:
        raise ModelServiceError(str(exc)) from exc


def explain_public_opinion_risk(
    db: Session,
    *,
    material_text: str,
    deterministic_hits: list[dict[str, Any]],
    similar_events: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        return deepseek_gateway.explain_public_opinion_risk(
            db,
            material_text=material_text,
            deterministic_hits=deterministic_hits,
            similar_events=similar_events,
        )
    except deepseek_gateway.DeepSeekGatewayError as exc:
        raise ModelServiceError(str(exc)) from exc
