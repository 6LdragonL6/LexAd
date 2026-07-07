import json
import re
import ahocorasick
from pathlib import Path
from app.schemas.review import MatchedRule, LayerResult

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"

_BOUNDARY_SAFE_WORDS = {
    "最近", "最终", "最后", "最初", "最新", "最低", "最高", "最大", "最小",
    "最多可申请", "最迟", "最早", "最晚", "最为", "最终解释权",
}

_DESCRIPTOR_CHARS = set(
    "耐用安全舒适省电省油先进专业强快稳优纯全美火棒赞"
    "良佳妙精新贵潮酷炫好棒赞省便易巧灵鲜香嫩醇润"
    "洁净透亮白薄轻软弹韧劲足猛"
)

_EXPLANATION_TEMPLATES = {
    "绝对化用语": (
        "属于《广告法》第九条第三项禁止的绝对化用语，"
        "容易误导消费者认为该商品在同类中具有无可比拟的优势。"
        "建议替换为可证明、可限定的客观描述。"
    ),
    "涉医用语": (
        "暗示医疗效果或疾病治疗功能，违反《广告法》第十七条"
        "关于非医疗商品不得涉及疾病治疗功能的规定。请使用非医疗性表述。"
    ),
    "功效宣称": (
        "对商品功效作出超出实际效果的断言或保证，需要提供"
        "法定资质或检测报告支撑。建议标注具体数据和检测依据。"
    ),
    "效果保证": (
        "对使用效果作出绝对化承诺，违反《广告法》关于禁止对"
        "商品效果作保证性承诺的规定。建议使用客观描述替代。"
    ),
    "价格欺诈": (
        "使用误导性价格表述，容易构成价格欺诈。"
        "建议标注真实原价、活动期限和具体规则。"
    ),
    "权威背书": (
        "容易被理解为国家机关、国家级资质或最高等级背书。"
        "如确有认证，应注明认证名称、主体、编号和适用范围；否则建议删除。"
    ),
    "虚假表述": (
        "含有夸大、虚构或无法验证的描述，可能构成虚假广告。"
        "建议使用可核实的客观事实替代。"
    ),
    "迷信内容": (
        "含有迷信色彩的表达，违反《广告法》第九条第八项。"
        "建议使用科学、客观的描述。"
    ),
}


class HardRulesEngine:
    def __init__(self):
        self.automaton = ahocorasick.Automaton()
        self.forbidden_words: dict[str, dict] = {}
        self._load_forbidden_words()
        self._load_hard_rules()

    def _load_forbidden_words(self):
        path = DATA_DIR / "forbidden_words.json"
        if not path.exists():
            return
        words_data = json.loads(path.read_text(encoding="utf-8"))
        for item in words_data:
            word = item["word"]
            if word and word not in self.automaton:
                self.automaton.add_word(
                    word,
                    (word, item["category"], "L5-forbidden", item.get("replacement", "")),
                )
            self.forbidden_words[word] = item

    def _load_hard_rules(self):
        path = DATA_DIR / "hard_rules_index.json"
        if not path.exists():
            return
        rules = json.loads(path.read_text(encoding="utf-8"))
        for rule in rules:
            text = rule["rule_text"]
            if len(text) > 4 and len(text) < 120:
                key_phrase = text[:60]
                if key_phrase not in self.automaton:
                    self.automaton.add_word(
                        key_phrase,
                        (key_phrase, rule["rule_type"], f"L1-{rule['source_law'][:20]}", ""),
                    )
        self.automaton.make_automaton()

    def scan(self, text: str) -> LayerResult:
        matched: list[MatchedRule] = []
        seen_words: set[str] = set()
        automaton_spans: set[tuple[int, int]] = set()

        for end_idx, (word, category, source, _replacement) in self.automaton.iter(text):
            if word in seen_words:
                continue
            seen_words.add(word)
            start_idx = end_idx - len(word) + 1
            automaton_spans.add((start_idx, end_idx))
            explanation = _EXPLANATION_TEMPLATES.get(
                category,
                f"命中{category}类违禁词，建议按相关法规修改。",
            )
            matched.append(
                MatchedRule(
                    rule_id=f"L1-{hash(word) & 0xFFFFFFFF:08x}",
                    rule_text=word,
                    source_law=source,
                    match_type=category,
                    explanation=explanation,
                )
            )

        zui_matches = _find_zui_patterns(text, automaton_spans)
        matched.extend(zui_matches)

        category_weights = {
            "绝对化用语": 30, "涉医用语": 35, "功效宣称": 25, "效果保证": 20,
            "价格欺诈": 20, "权威背书": 15, "虚假表述": 15, "迷信内容": 25,
        }
        deduction = sum(category_weights.get(m.match_type, 15) for m in matched)

        total_count = len(matched)
        if total_count > 0:
            explanations_list = [
                f"本层发现 {total_count} 条明确违禁词或硬性风险点，累计扣分 {deduction}"
            ]
        else:
            explanations_list = ["本层未发现明确违禁词或硬性风险点"]

        return LayerResult(
            layer="第一层·硬规则匹配",
            matched_rules=matched,
            explanations=explanations_list,
        )


def _find_zui_patterns(
    text: str, automaton_spans: set[tuple[int, int]]
) -> list[MatchedRule]:
    matches: list[MatchedRule] = []
    seen_phrases: set[str] = set()

    desc_class = ""
    for ch in sorted(_DESCRIPTOR_CHARS):
        desc_class += ch
    pattern = re.compile(rf'最([{desc_class}]{{1,4}}|[一-鿿]{{1,2}})')

    for match in pattern.finditer(text):
        span_start = match.start()
        span_end = match.end() - 1

        if any(
            aspan[0] <= span_start and span_end <= aspan[1]
            for aspan in automaton_spans
        ):
            continue

        full_match = match.group(0)

        if full_match in _BOUNDARY_SAFE_WORDS:
            continue

        starts_safe = any(
            full_match.startswith(safe)
            for safe in _BOUNDARY_SAFE_WORDS
            if len(safe) >= 2
        )
        if starts_safe:
            continue

        if full_match in seen_phrases:
            continue
        seen_phrases.add(full_match)

        descriptor = match.group(1)
        has_descriptor = any(ch in _DESCRIPTOR_CHARS for ch in descriptor)

        if has_descriptor:
            short_desc = ""
            for ch in descriptor:
                if ch in _DESCRIPTOR_CHARS:
                    short_desc += ch
            short_desc = short_desc[:4]
            desc_note = (
                "属于含“最”字的绝对化表达，可能构成与同业比较的最高级主张。"
                + "建议使用可证明、可限定的表达，例如“经测试具备较好"
                + short_desc
                + "性（注明测试依据）”。"
            )
            explanation = f"'{full_match}'{desc_note}"
        else:
            explanation = (
                f"'{full_match}'属于含“最”字的表述，"
                + "请核实是否构成绝对化比较。"
                + "如非广告主张可忽略，否则建议按《广告法》要求修改。"
            )

        matches.append(
            MatchedRule(
                rule_id=f"L1-zui-{hash(full_match) & 0xFFFFFFFF:08x}",
                rule_text=full_match,
                source_law="广告绝对化用语规则 / 命中模式：最 + 性能/品质描述",
                match_type="绝对化用语",
                explanation=explanation,
            )
        )

    return matches


engine_l1 = HardRulesEngine()
