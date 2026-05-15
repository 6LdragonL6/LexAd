import json
from pathlib import Path
from fastapi import APIRouter, Query

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "knowledge"
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / "data"

router = APIRouter()

@router.get("/laws")
def list_laws(search: str = Query(default="")):
    index_path = DATA_DIR / "law_provisions_index.json"
    if not index_path.exists():
        return {"items": [], "total": 0}
    laws = json.loads(index_path.read_text(encoding="utf-8"))
    if search:
        laws = [l for l in laws if search.lower() in l["title"].lower()]
    return {"items": laws, "total": len(laws)}

@router.get("/industry-rules")
def list_industry_rules(industry: str = Query(default="")):
    industry_dir = KNOWLEDGE_DIR / "L2_industry"
    items = []
    search_dir = industry_dir / industry if industry else industry_dir
    if search_dir.exists():
        for txt_file in sorted(search_dir.rglob("*.txt")):
            items.append({"id": txt_file.stem[:30], "title": txt_file.stem, "industry": industry or txt_file.parent.name})
    return {"items": items, "total": len(items)}

@router.get("/cases")
def list_cases(search: str = Query(default=""), province: str = Query(default="")):
    cases_dir = KNOWLEDGE_DIR / "L3_cases"
    items = []
    for txt_file in sorted(cases_dir.rglob("*.txt")):
        if province and txt_file.parent.name != province:
            continue
        try:
            title = txt_file.read_text(encoding="utf-8").split("\n")[0].strip()[:200]
        except:
            title = txt_file.stem
        if search and search.lower() not in title.lower():
            continue
        items.append({"id": txt_file.stem[:40], "title": title, "province": txt_file.parent.name})
    return {"items": items[:50], "total": len(items)}

@router.get("/platforms")
def list_platform_rules(platform: str = Query(default="")):
    platform_dir = KNOWLEDGE_DIR / "L4_platforms"
    items = []
    search_dir = platform_dir / platform if platform else platform_dir
    if search_dir.exists():
        for txt_file in sorted(search_dir.rglob("*.txt")):
            items.append({"platform": txt_file.parent.name, "category": "", "title": txt_file.stem})
    return {"items": items, "total": len(items)}

@router.get("/templates")
def list_templates(category: str = Query(default="")):
    template_path = DATA_DIR / "rewrite_templates.json"
    if not template_path.exists():
        return {"items": {}, "total": 0}
    templates = json.loads(template_path.read_text(encoding="utf-8"))
    return {"items": templates, "total": len(templates)}
