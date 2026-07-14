"""Read-only, classified access to the local L1-L5 knowledge base."""

from datetime import datetime, timezone
from pathlib import Path
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.knowledge import PlatformRuleSet, PlatformRuleStatus, PlatformRuleVersion


settings = get_settings()
KNOWLEDGE_DIR = Path(settings.KNOWLEDGE_DIR).resolve()

LAYERS = {
    "L1": ("L1_laws", "法律法规"),
    "L2": ("L2_industry", "行业专项规则"),
    "L3": ("L3_cases", "行政处罚案例"),
    "L4": ("L4_platforms", "平台规则"),
    "L5": ("L5_templates", "合规模板"),
}

GROUP_LABELS = {
    "L5": {
        "disclaimer": "免责声明模板",
        "forbidden": "违禁词清单",
        "lawfirm": "律所实务模板",
        "rewrite": "合规改写模板",
        "standards": "行业合规标准",
    }
}

IGNORED_FILE_PATTERNS = [
    re.compile(r"^run_log_\d{8}_\d{6}\.txt$", re.IGNORECASE),
]

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/platforms")
def list_platform_options(db: Session = Depends(get_db)):
    """Return platform choices backed by a rule version effective right now."""
    now = datetime.now(timezone.utc)
    items = []
    for rule_set in db.query(PlatformRuleSet).filter(
        PlatformRuleSet.deleted_at.is_(None)
    ).order_by(PlatformRuleSet.display_name.asc()).all():
        versions = (
            db.query(PlatformRuleVersion)
            .filter(
                PlatformRuleVersion.rule_set_id == rule_set.id,
                PlatformRuleVersion.status == PlatformRuleStatus.active,
            )
            .order_by(PlatformRuleVersion.activated_at.desc(), PlatformRuleVersion.created_at.desc())
            .all()
        )
        if not any(version.is_effective_at(now) for version in versions):
            continue
        items.append({"value": rule_set.platform_name, "label": rule_set.display_name})
    return {"items": items, "total": len(items)}


@router.get("/catalog/{layer}")
def get_catalog(layer: str):
    layer_key = layer.upper()
    if layer_key not in LAYERS:
        raise HTTPException(status_code=404, detail="知识库分类不存在")

    directory_name, label = LAYERS[layer_key]
    layer_dir = KNOWLEDGE_DIR / directory_name
    if not layer_dir.exists():
        return {"layer": layer_key, "label": label, "items": [], "total": 0}

    items = []
    for text_file in sorted(layer_dir.rglob("*.txt")):
        if not _should_include_knowledge_file(text_file):
            continue
        relative = text_file.relative_to(KNOWLEDGE_DIR)
        within_layer = text_file.relative_to(layer_dir)
        raw_group = within_layer.parts[0] if len(within_layer.parts) > 1 else label
        group = _display_group(layer_key, raw_group)
        items.append(
            {
                "id": relative.as_posix(),
                "title": text_file.stem,
                "group": group,
            }
        )
    return {
        "layer": layer_key,
        "label": label,
        "items": items,
        "total": len(items),
    }


@router.get("/content")
def get_content(item_id: str):
    target = _resolve_knowledge_file(item_id)
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="知识库文件不是有效的 UTF-8 文本")
    except OSError:
        raise HTTPException(status_code=500, detail="知识库文件暂时无法读取")

    relative = target.relative_to(KNOWLEDGE_DIR)
    layer_directory = relative.parts[0]
    layer = next(
        (key for key, value in LAYERS.items() if value[0] == layer_directory),
        "",
    )
    return {
        "id": relative.as_posix(),
        "title": target.stem,
        "layer": layer,
        "content": content,
    }


def _resolve_knowledge_file(item_id: str) -> Path:
    if not item_id or "\x00" in item_id:
        raise HTTPException(status_code=400, detail="无效的知识库条目标识")

    target = (KNOWLEDGE_DIR / item_id).resolve()
    try:
        target.relative_to(KNOWLEDGE_DIR)
    except ValueError:
        raise HTTPException(status_code=400, detail="知识库路径超出允许范围")

    if target.suffix.lower() != ".txt" or not target.is_file():
        raise HTTPException(status_code=404, detail="知识库条目不存在")
    return target


def _should_include_knowledge_file(path: Path) -> bool:
    name = path.name
    if path.stem.strip() == "":
        return False
    if name.startswith("."):
        return False
    return not any(pattern.match(name) for pattern in IGNORED_FILE_PATTERNS)


def _display_group(layer: str, group: str) -> str:
    return GROUP_LABELS.get(layer, {}).get(group, group)
