import json
import ahocorasick
from pathlib import Path
from app.schemas.review import MatchedRule, LayerResult

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


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
                self.automaton.add_word(word, (word, item["category"], "L5-forbidden", item.get("replacement", "")))
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
                    self.automaton.add_word(key_phrase, (key_phrase, rule["rule_type"], f"L1-{rule['source_law'][:20]}", ""))
        self.automaton.make_automaton()

    def scan(self, text: str) -> LayerResult:
        matched: list[MatchedRule] = []
        seen_words: set[str] = set()

        for end_idx, (word, category, source, replacement) in self.automaton.iter(text):
            if word in seen_words:
                continue
            seen_words.add(word)
            matched.append(MatchedRule(
                rule_id=f"L1-{hash(word) & 0xFFFFFFFF:08x}",
                rule_text=word,
                source_law=source,
                match_type=category,
            ))

        category_weights = {
            "绝对化用语": 30, "涉医用语": 35, "功效宣称": 25, "效果保证": 20,
            "价格欺诈": 20, "权威背书": 15, "虚假表述": 15, "迷信内容": 25,
        }
        deduction = sum(category_weights.get(m.match_type, 15) for m in matched)

        return LayerResult(
            layer="第一层·硬规则匹配",
            matched_rules=matched,
            explanations=[f"命中 {len(matched)} 条违禁词/硬规则，扣分 {deduction}"] if matched else ["未命中硬规则"],
        )


engine_l1 = HardRulesEngine()
