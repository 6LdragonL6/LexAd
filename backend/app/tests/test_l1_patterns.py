from app.engine.layer1_hard_rules import engine_l1


def test_zui_naiyong_detected():
    result = engine_l1.scan("这款产品最耐用，值得购买。")
    rule_texts = [r.rule_text for r in result.matched_rules]
    assert "最耐用" in rule_texts
    for r in result.matched_rules:
        if r.rule_text == "最耐用":
            assert "最" in r.source_law
            assert r.explanation != ""


def test_zui_pattern_not_greedy():
    """最+描述词 should stop at descriptor boundary, not swallow product names."""
    result = engine_l1.scan("最耐用汽车坐垫，国家级品质")
    rule_texts = [r.rule_text for r in result.matched_rules]
    # Must match "最耐用" not "最耐用汽车坐垫"
    assert "最耐用" in rule_texts
    for r in result.matched_rules:
        assert "汽车坐垫" not in r.rule_text, f"Pattern too greedy: {r.rule_text}"
        assert "耐用汽车坐垫性" not in r.explanation, f"Explanation contains product name: {r.explanation}"


def test_zui_anquan_detected():
    result = engine_l1.scan("我们的产品最安全，请放心使用。")
    rule_texts = [r.rule_text for r in result.matched_rules]
    assert "最安全" in rule_texts


def test_zui_shengdian_detected():
    result = engine_l1.scan("本空调最省电，是家庭首选。")
    rule_texts = [r.rule_text for r in result.matched_rules]
    assert "最省电" in rule_texts


def test_zui_jin_not_flagged():
    result = engine_l1.scan("最近公司推出了新产品。")
    rule_texts = [r.rule_text for r in result.matched_rules]
    assert "最近" not in rule_texts


def test_zui_zhong_not_flagged():
    result = engine_l1.scan("本公司拥有最终解释权。")
    rule_texts = [r.rule_text for r in result.matched_rules]
    assert "最终" not in rule_texts


def test_guojiaji_quality_has_explanation():
    result = engine_l1.scan("本产品具有国家级品质。")
    matched = [r for r in result.matched_rules if r.rule_text == "国家级"]
    assert len(matched) >= 1
    assert matched[0].explanation != ""


def test_pattern_explanation_field_present():
    result = engine_l1.scan("最先进的技术，最专业的设计。")
    for r in result.matched_rules:
        if r.rule_text.startswith("最"):
            assert r.explanation != "", f"Pattern match {r.rule_text} missing explanation"


def test_duplicate_not_double_counted():
    """If automaton catches '最低价' the pattern should not re-match it."""
    result = engine_l1.scan("本产品全网最低价。")
    text_matches = [r.rule_text for r in result.matched_rules]
    assert "最低价" in text_matches
    assert "最低" not in text_matches  # should not appear separately


def test_ordinary_text_not_flagged():
    result = engine_l1.scan("公司最近发展顺利，产品质量稳步提升。")
    zui_matches = [r for r in result.matched_rules if r.rule_text.startswith("最")]
    assert len(zui_matches) == 0


def test_existing_exact_word_still_matched():
    result = engine_l1.scan("这是最好产品。")
    rule_texts = [r.rule_text for r in result.matched_rules]
    assert "最好" in rule_texts
