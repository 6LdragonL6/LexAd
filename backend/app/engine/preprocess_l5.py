import json, re
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "knowledge"
DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"

CATEGORY_MAP = {
    "001": "绝对化用语", "002": "绝对化用语", "003": "绝对化用语", "004": "绝对化用语",
    "005": "价格欺诈", "006": "涉医用语", "007": "功效宣称",
    "008": "虚假表述", "009": "效果保证", "010": "效果保证",
    "011": "权威背书", "012": "迷信内容", "013": "效果保证",
    "014": "功效宣称", "015": "虚假表述", "016": "虚假表述", "017": "虚假表述",
}

def build_forbidden_words():
    forbidden_dir = KNOWLEDGE_DIR / "L5_templates" / "forbidden"
    forbidden_words = []
    rewrite_map = {}

    for txt_file in sorted(forbidden_dir.glob("*.txt")):
        prefix = txt_file.stem[:3]
        category = CATEGORY_MAP.get(prefix, "其他")
        content = txt_file.read_text(encoding="utf-8")
        # Split on blank lines to get blocks; each block pairs a ❌ line with a ✅ line
        blocks = content.split("\n\n")
        for block in blocks:
            lines = block.strip().split("\n")
            forbidden_word = None
            replacement = None
            for line in lines:
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith("#") or line_stripped == "---":
                    continue
                if "❌" in line_stripped:
                    # Extract word after ❌
                    match = re.search(r"❌\s*(.*)", line_stripped)
                    if match:
                        forbidden_word = match.group(1).strip()
                elif "✅" in line_stripped:
                    match = re.search(r"✅\s*(.*)", line_stripped)
                    if match:
                        replacement = match.group(1).strip()
            if forbidden_word:
                forbidden_words.append({
                    "word": forbidden_word,
                    "category": category,
                    "replacement": replacement or "",
                })
                if replacement:
                    rewrite_map[forbidden_word] = replacement

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "forbidden_words.json", "w", encoding="utf-8") as f:
        json.dump(forbidden_words, f, ensure_ascii=False, indent=2)
    with open(DATA_DIR / "rewrite_templates.json", "w", encoding="utf-8") as f:
        json.dump(rewrite_map, f, ensure_ascii=False, indent=2)

    print(f"L5: extracted {len(forbidden_words)} forbidden words, {len(rewrite_map)} rewrite templates.")

if __name__ == "__main__":
    build_forbidden_words()
