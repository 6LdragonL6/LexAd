from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session
from pydantic import Field

from app.models.knowledge import PlatformRuleSet, PlatformRuleStatus, PlatformRuleVersion
from app.schemas.review import LayerResult, MatchedRule

_PLATFORM_ALIASES: dict[str, set[str]] = {
    "抖音": {"douyin", "douyin_ec", "巨量引擎"},
    "小红书": {"xiaohongshu", "red", "xhs"},
    "微信": {"wechat", "weixin", "shipinhao", "视频号"},
    "视频号": {"wechat", "weixin", "shipinhao", "微信"},
    "微博": {"weibo"},
    "京东": {"jd", "jingdong"},
    "淘宝": {"taobao", "tmall"},
    "拼多多": {"pdd", "pinduoduo"},
}


def _resolve_aliases(platform: str) -> set[str]:
    normalized = _normalize(platform)
    for canonical, aliases in _PLATFORM_ALIASES.items():
        alias_set = {_normalize(a) for a in aliases} | {_normalize(canonical)}
        if normalized in alias_set:
            return alias_set
    return {normalized}


class PlatformReviewResult(LayerResult):
    platform_rule_version_ids: list[str] = Field(default_factory=list)
    unavailable_platforms: list[str] = Field(default_factory=list)
    platform_version_labels: dict[str, str] = Field(default_factory=dict)


def run_platform_review(text: str, platforms: list[str], db: Session | None) -> PlatformReviewResult:
    if db is None:
        return PlatformReviewResult(
            layer="第四层：平台差异适配",
            matched_rules=[],
            explanations=["平台规则审核暂不可用：缺少数据库会话"],
            platform_rule_version_ids=[],
            unavailable_platforms=platforms,
        )

    matched: list[MatchedRule] = []
    explanations: list[str] = []
    version_ids: list[str] = []
    unavailable: list[str] = []
    version_labels: dict[str, str] = {}

    for platform in platforms or []:
        rule_set = _find_rule_set(db, platform)
        if not rule_set:
            unavailable.append(platform)
            explanations.append(f"{platform}：暂无规则集，请管理员补充")
            continue

        version = _find_active_version(db, rule_set.id)
        if not version:
            unavailable.append(platform)
            explanations.append(f"{rule_set.display_name}：已有规则集，但暂无生效版本")
            continue

        version_ids.append(version.id)
        version_labels[version.id] = f"{rule_set.display_name} / {version.version_label}"
        platform_matches = _match_version_rules(text, rule_set, version)
        matched.extend(platform_matches)
        if platform_matches:
            explanations.append(
                f"{rule_set.display_name} / {version.version_label} 已用于本次审核，命中 {len(platform_matches)} 条规则"
            )
        else:
            explanations.append(
                f"{rule_set.display_name} / {version.version_label} 本次未发现与该平台生效规则直接冲突的表达"
            )

    if not platforms:
        explanations.append("未选择投放平台，跳过平台差异适配")

    return PlatformReviewResult(
        layer="第四层：平台差异适配",
        matched_rules=matched,
        explanations=explanations,
        platform_rule_version_ids=_dedupe(version_ids),
        unavailable_platforms=unavailable,
        platform_version_labels=version_labels,
    )


def _find_rule_set(db: Session, platform: str) -> PlatformRuleSet | None:
    user_aliases = _resolve_aliases(platform)
    candidates = db.query(PlatformRuleSet).all()
    for candidate in candidates:
        candidate_aliases = _resolve_aliases(candidate.platform_name) | _resolve_aliases(candidate.display_name)
        if user_aliases & candidate_aliases:
            return candidate
    return None


def _find_active_version(db: Session, rule_set_id: str) -> PlatformRuleVersion | None:
    now = datetime.now(timezone.utc)
    versions = (
        db.query(PlatformRuleVersion)
        .filter(
            PlatformRuleVersion.rule_set_id == rule_set_id,
            PlatformRuleVersion.status == PlatformRuleStatus.active,
        )
        .order_by(PlatformRuleVersion.activated_at.desc(), PlatformRuleVersion.created_at.desc())
        .all()
    )
    for version in versions:
        if version.is_effective_at(now):
            return version
    return versions[0] if versions else None


def _match_version_rules(
    text: str,
    rule_set: PlatformRuleSet,
    version: PlatformRuleVersion,
) -> list[MatchedRule]:
    matches: list[MatchedRule] = []
    for index, rule in enumerate(version.structured_rules or []):
        keywords = _extract_keywords(rule)
        if not keywords:
            continue
        hit_keywords = [keyword for keyword in keywords if keyword and keyword in text]
        if not hit_keywords:
            continue
        rule_key = str(rule.get("rule_id") or rule.get("id") or f"rule-{index + 1}")
        matches.append(
            MatchedRule(
                rule_id=f"L4-{version.id}-{rule_key}",
                rule_text=_rule_text(rule, hit_keywords),
                source_law=f"{rule_set.display_name} {version.version_label}",
                match_type=str(rule.get("risk_level") or rule.get("category") or "平台规则"),
            )
        )
    return matches


def _extract_keywords(rule: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for field in ("keywords", "keyword", "patterns", "pattern"):
        value = rule.get(field)
        if isinstance(value, list):
            values.extend(str(item).strip() for item in value)
        elif isinstance(value, str):
            values.append(value.strip())

    if not values:
        for field in ("text", "rule_text", "title"):
            value = rule.get(field)
            if isinstance(value, str) and 0 < len(value.strip()) <= 30:
                values.append(value.strip())
    return [value for value in values if value]


def _rule_text(rule: dict[str, Any], hit_keywords: list[str]) -> str:
    base = rule.get("text") or rule.get("rule_text") or rule.get("title")
    if base:
        return str(base)
    return f"命中平台规则关键词：{', '.join(hit_keywords)}"


def _normalize(value: str) -> str:
    return "".join(str(value or "").lower().split())


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
