import json
from pathlib import Path
from openai import OpenAI
from app.core.config import get_settings
from app.schemas.review import MatchedRule, LayerResult

settings = get_settings()
KNOWLEDGE_DIR = Path(settings.KNOWLEDGE_DIR)
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


def _load_law_provisions(industry: str) -> str:
    parts = []
    law_index_path = DATA_DIR / "law_provisions_index.json"
    if law_index_path.exists():
        laws = json.loads(law_index_path.read_text(encoding="utf-8"))
        for law in laws[:3]:
            law_path = KNOWLEDGE_DIR / law["path"]
            if law_path.exists():
                text = law_path.read_text(encoding="utf-8")[:3000]
                parts.append(f"【{law['title']}】\n{text}")

    industry_dir = KNOWLEDGE_DIR / "L2_industry" / industry
    if industry_dir.exists():
        for rule_file in sorted(industry_dir.glob("*.txt"))[:3]:
            text = rule_file.read_text(encoding="utf-8")[:2000]
            parts.append(f"【行业规则·{rule_file.stem}】\n{text}")

    return "\n\n".join(parts)


def _search_similar_cases(text: str) -> list[dict]:
    try:
        import chromadb
        client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        collection = client.get_collection("ad_cases")
        results = collection.query(query_texts=[text], n_results=5)
        cases = []
        for i, doc_id in enumerate(results["ids"][0]):
            cases.append({
                "id": doc_id,
                "title": results["metadatas"][0][i].get("title", ""),
                "text": results["documents"][0][i][:500],
            })
        return cases
    except Exception:
        return []


def run_semantic_review(text: str, industry: str) -> LayerResult:
    legal_basis = _load_law_provisions(industry)
    similar_cases = _search_similar_cases(text)

    cases_text = "\n".join(
        f"案例{i+1}: {c['title']}\n{c['text']}" for i, c in enumerate(similar_cases)
    )

    system_prompt = f"""你是广告合规审查专家，依据以下法律法规审查广告文案。
LEGAL_BASIS:
{legal_basis}

SIMILAR_CASES:
{cases_text}

审查要求：
1. 识别广告文案中违反上述法律法规的表述
2. 即使没有明确违禁词，也需判断是否存在语义上的违规（如暗示、误导、夸大）
3. 对每项违规给出法律依据和案例参考

输出严格JSON格式：
{{"violations": [{{"text": "违规原文", "reason": "违规原因", "law_ref": "法律依据", "risk_level": "high/medium/low", "suggestion": "修改建议"}}], "overall_assessment": "整体评估"}}"""

    client = OpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)

    try:
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请审查以下{industry}行业广告文案:\n\n{text}"},
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        content = response.choices[0].message.content
        result = json.loads(content) if content else {"violations": [], "overall_assessment": ""}
    except Exception as e:
        return LayerResult(
            layer="第二层·语义推理",
            matched_rules=[MatchedRule(
                rule_id="L2-ERROR",
                rule_text=f"DeepSeek API error: {str(e)[:200]}",
                source_law="",
                match_type="error",
            )],
            explanations=[f"语义推理失败: {str(e)[:200]}"],
        )

    matched = []
    for v in result.get("violations", []):
        matched.append(MatchedRule(
            rule_id=f"L2-{hash(v['text']) & 0xFFFFFFFF:08x}",
            rule_text=v["text"],
            source_law=v.get("law_ref", ""),
            match_type=v.get("risk_level", "medium"),
        ))

    return LayerResult(
        layer="第二层·语义推理",
        matched_rules=matched,
        explanations=[result.get("overall_assessment", "")] if result.get("overall_assessment") else [],
    )
