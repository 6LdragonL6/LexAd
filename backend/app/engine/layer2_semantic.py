import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.engine.industry import format_industries, split_industries
from app.schemas.review import LayerResult, MatchedRule
from app.services.deepseek_gateway import DeepSeekGatewayError, semantic_review


settings = get_settings()
KNOWLEDGE_DIR = Path(settings.KNOWLEDGE_DIR)
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


class SemanticReviewError(RuntimeError):
    """Raised when semantic review cannot produce a trustworthy result."""


def _load_law_provisions(industry: str) -> str:
    parts = []
    law_index_path = DATA_DIR / "law_provisions_index.json"
    if law_index_path.exists():
        laws = json.loads(law_index_path.read_text(encoding="utf-8"))
        for law in laws[:3]:
            law_path = KNOWLEDGE_DIR / law["path"]
            if law_path.exists():
                parts.append(f"【{law['title']}】\n{law_path.read_text(encoding='utf-8')[:3000]}")

    for industry_name in split_industries(industry):
        industry_dir = KNOWLEDGE_DIR / "L2_industry" / industry_name
        if industry_dir.exists():
            for rule_file in sorted(industry_dir.glob("*.txt"))[:3]:
                text = rule_file.read_text(encoding="utf-8")[:2000]
                parts.append(f"【行业规则·{industry_name}·{rule_file.stem}】\n{text}")
    return "\n\n".join(parts)


def _search_similar_cases(text: str) -> list[dict]:
    try:
        import chromadb

        client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        collection = client.get_collection("ad_cases")
        results = collection.query(query_texts=[text], n_results=5)
        return [
            {
                "id": doc_id,
                "title": results["metadatas"][0][index].get("title", ""),
                "text": results["documents"][0][index][:500],
            }
            for index, doc_id in enumerate(results["ids"][0])
        ]
    except Exception:
        return []


def run_semantic_review(text: str, industry: str, db: Session) -> LayerResult:
    industry_label = format_industries(industry) or "通用"
    try:
        result = semantic_review(
            db,
            material_text=text,
            industry=industry_label,
            legal_basis=_load_law_provisions(industry),
            similar_cases=_search_similar_cases(text),
        )
    except DeepSeekGatewayError as exc:
        raise SemanticReviewError(str(exc)) from exc

    matched = [
        MatchedRule(
            rule_id=f"L2-{hash(violation.text) & 0xFFFFFFFF:08x}",
            rule_text=violation.text,
            source_law=violation.law_ref,
            match_type=violation.risk_level,
            suggestion=violation.suggestion,
        )
        for violation in result.violations
    ]
    return LayerResult(
        layer="第二层·语义推理",
        matched_rules=matched,
        explanations=[result.overall_assessment] if result.overall_assessment else [],
    )
