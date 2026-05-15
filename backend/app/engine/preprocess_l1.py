import json, os, re
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "knowledge"
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"

HARD_RULE_PATTERNS = [
    (r"不得[^。；\n]{0,80}", "禁止性规定"),
    (r"禁止[^。；\n]{0,80}", "禁止性规定"),
    (r"严禁[^。；\n]{0,80}", "禁止性规定"),
    (r"应当[^。；\n]{0,80}", "义务性规定"),
    (r"不得使用.{0,30}(国家级|最高级|最佳|第一)", "绝对化用语"),
]

def extract_hard_rules(law_text: str, law_title: str) -> list[dict]:
    rules = []
    for pattern, rule_type in HARD_RULE_PATTERNS:
        for match in re.finditer(pattern, law_text):
            rules.append({
                "rule_id": f"L1-{law_title[:8]}-{len(rules):04d}",
                "rule_text": match.group(0).strip(),
                "source_law": law_title,
                "rule_type": rule_type,
            })
    return rules

def build_l1_index():
    l1_dir = KNOWLEDGE_DIR / "L1_laws"
    all_rules = []
    law_index = []

    for law_file in sorted(l1_dir.glob("*.txt")):
        text = law_file.read_text(encoding="utf-8")
        title = law_file.stem
        law_index.append({"id": law_file.stem[:20], "title": title, "path": str(law_file.relative_to(KNOWLEDGE_DIR))})
        rules = extract_hard_rules(text, title)
        all_rules.extend(rules)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "hard_rules_index.json", "w", encoding="utf-8") as f:
        json.dump(all_rules, f, ensure_ascii=False, indent=2)
    with open(DATA_DIR / "law_provisions_index.json", "w", encoding="utf-8") as f:
        json.dump(law_index, f, ensure_ascii=False, indent=2)

    print(f"L1: extracted {len(all_rules)} hard rules from {len(law_index)} laws.")

if __name__ == "__main__":
    build_l1_index()
