import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.engine.industry import format_industries, split_industries
from app.schemas.review import BasisReference, LayerResult, MatchedRule, VerificationItem
from app.services.deepseek_gateway import DeepSeekGatewayError, semantic_review


settings = get_settings()
KNOWLEDGE_DIR = Path(settings.KNOWLEDGE_DIR)
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_RISK_LABELS = {"high": "高风险", "medium": "中风险", "low": "低风险"}


class SemanticReviewError(RuntimeError):
    """Raised when semantic review cannot produce a trustworthy result."""


def _load_law_resources(industry: str) -> list[dict[str, str]]:
    resources: list[dict[str, str]] = []
    law_index_path = DATA_DIR / "law_provisions_index.json"
    if law_index_path.exists():
        laws = json.loads(law_index_path.read_text(encoding="utf-8"))
        for index, law in enumerate(laws[:8], start=1):
            law_path = KNOWLEDGE_DIR / law["path"]
            if law_path.exists():
                resources.append({
                    "id": f"law:{index}",
                    "title": str(law["title"]),
                    "version": "现行资料库",
                    "content": law_path.read_text(encoding="utf-8")[:5000],
                })

    for industry_name in split_industries(industry):
        industry_dir = KNOWLEDGE_DIR / "L2_industry" / industry_name
        if not industry_dir.exists():
            continue
        for rule_file in sorted(industry_dir.glob("*.txt"))[:5]:
            resources.append({
                "id": f"industry:{industry_name}:{rule_file.stem}",
                "title": f"{industry_name}·{rule_file.stem}",
                "version": "行业资料库",
                "content": rule_file.read_text(encoding="utf-8")[:4000],
            })
    return resources


def _search_similar_cases(text: str) -> list[dict[str, Any]]:
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


def run_semantic_review(
    text: str,
    industry: str,
    db: Session,
    hard_rule_candidates: list[MatchedRule] | None = None,
) -> LayerResult:
    industry_label = format_industries(industry) or "通用"
    resources = _load_law_resources(industry)
    candidate_rules = [_candidate_payload(item) for item in (hard_rule_candidates or [])]
    try:
        result = semantic_review(
            db,
            material_text=text,
            industry=industry_label,
            legal_resources=resources,
            candidate_rules=candidate_rules,
            similar_cases=_search_similar_cases(text),
        )
    except DeepSeekGatewayError as exc:
        raise SemanticReviewError(str(exc)) from exc

    resource_map = {item["id"]: item for item in resources}
    matched: list[MatchedRule] = []
    rejected_count = 0
    seen_findings: set[tuple[str, str]] = set()
    for index, finding in enumerate(result.findings):
        quote = finding.evidence_quote.strip()
        valid_basis_ids = [basis_id for basis_id in finding.basis_ids if basis_id in resource_map]
        if not _is_meaningful_quote(text, quote) or not valid_basis_ids:
            rejected_count += 1
            continue
        key = (_normalize(quote), _normalize(finding.risk_type))
        if key in seen_findings:
            continue
        seen_findings.add(key)
        basis_refs = [_basis_reference(resource_map[basis_id]) for basis_id in valid_basis_ids]
        matched.append(
            MatchedRule(
                rule_id=f"legal-{index + 1}-{abs(hash(key)) & 0xFFFFFFFF:08x}",
                rule_text=quote,
                source_law="；".join(ref.title for ref in basis_refs),
                match_type=finding.risk_type,
                explanation=finding.reason,
                matched_text="",
                match_method="ai_adjudicated",
                source_id=valid_basis_ids[0],
                suggestion=finding.suggestion,
                evidence_quote=quote,
                reasoning=finding.reason,
                risk_level=finding.risk_level,
                risk_level_label=_RISK_LABELS[finding.risk_level],
                confidence=finding.confidence,
                adjudication_status="confirmed",
                basis_refs=basis_refs,
            )
        )

    verification_items: list[VerificationItem] = []
    seen_verifications: set[tuple[str, str]] = set()
    for index, item in enumerate(result.verification_items):
        quote = item.evidence_quote.strip()
        if not _is_meaningful_quote(text, quote):
            rejected_count += 1
            continue
        key = (_normalize(quote), _normalize(item.verification_type))
        if key in seen_verifications:
            continue
        seen_verifications.add(key)
        basis_refs = [
            _basis_reference(resource_map[basis_id])
            for basis_id in item.basis_ids
            if basis_id in resource_map
        ]
        verification_items.append(
            VerificationItem(
                item_id=f"verify-legal-{index + 1}-{abs(hash(key)) & 0xFFFFFFFF:08x}",
                evidence_quote=quote,
                verification_type=item.verification_type,
                reason=item.reason,
                required_materials=item.required_materials,
                basis_refs=basis_refs,
            )
        )

    explanations = [result.overall_assessment] if result.overall_assessment else []
    if rejected_count:
        explanations.append(f"有 {rejected_count} 项模型输出未通过引用校验，已转入内部审计")
    if not resources:
        explanations.append("法律与行业资料库当前没有可用资源，结论需人工复核")
    return LayerResult(
        layer="法律语义裁决",
        matched_rules=matched,
        explanations=explanations,
        status="matched" if matched else "no_match",
        source_versions=[item["title"] for item in resources],
        candidate_count=len(candidate_rules),
        verification_items=verification_items,
        requires_manual_review=bool(rejected_count or not resources),
    )


def _candidate_payload(item: MatchedRule) -> dict[str, Any]:
    return {
        "id": item.rule_id,
        "evidence": item.rule_text,
        "category": item.match_type,
        "source": item.source_law,
        "explanation": item.explanation,
    }


def _basis_reference(resource: dict[str, str]) -> BasisReference:
    return BasisReference(
        id=resource["id"],
        title=resource["title"],
        version=resource.get("version", ""),
    )


def _is_meaningful_quote(material_text: str, quote: str) -> bool:
    normalized_quote = _normalize(quote)
    if not normalized_quote or normalized_quote not in _normalize(material_text):
        return False
    semantic_chars = re.findall(r"[A-Za-z\u4e00-\u9fff]", quote)
    return len(semantic_chars) >= 2 and len(normalized_quote) >= 3


def _normalize(value: str) -> str:
    return "".join(str(value or "").lower().split())
