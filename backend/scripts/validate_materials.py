"""批量测试物料验证脚本 —— 通过 API 端到端验证 LexAd 审查引擎准确性。

用法:
    cd backend
    python scripts/validate_materials.py

前置条件:
    - 后端服务已启动（uvicorn app.main:app --port 8000）
    - 数据库已迁移，预置账户可用
"""

from __future__ import annotations

import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import openpyxl
import requests

# ── Config ────────────────────────────────────────────────────────────────

# 测试物料 xlsx 路径
XLSX_PATH = Path(r"D:\LDragonl\桌面\物料1-65.xlsx")

# API 地址
API_BASE = "http://localhost:8000/api/v1"

# 测试账户
AUTH_USERNAME = "market01"
AUTH_PASSWORD = "test1234"

# 列索引（0-based，对应 xlsx 列 A-M）
COL_ID = 0          # A: 物料编号
COL_INDUSTRY = 1    # B: 行业
COL_SUB_INDUSTRY = 2  # C: 子行业
COL_MATERIAL_TYPE = 3  # D: 物料形式
COL_COMPLIANCE = 4   # E: 合规状态（违规/合规）
COL_VIOLATION_1 = 5  # F: 违规类型一级
COL_VIOLATION_2 = 6  # G: 违规类型二级
COL_SEVERITY = 7     # H: 严重程度
COL_RISK_LEVEL = 8   # I: 风险等级（高/中/低）
COL_AD_CONTENT = 9   # J: 广告内容
COL_EXPECTED_RESULT = 10  # K: 模型审核结果
COL_LAW_REF = 11     # L: 涉及法律法规
COL_SOURCE = 12      # M: 来源说明

# 输出报告路径
REPORT_PATH = Path(__file__).resolve().parent / "validation_report.csv"


def read_test_cases() -> list[dict[str, Any]]:
    """读取 xlsx 测试物料，返回字典列表。"""
    wb = openpyxl.load_workbook(XLSX_PATH)
    try:
        ws = wb.active
        cases = []
        for row in ws.iter_rows(min_row=2, values_only=True):  # skip header
            if not row[COL_ID]:
                continue
            cases.append({
                "id": str(row[COL_ID]).strip(),
                "industry": str(row[COL_INDUSTRY] or "").strip(),
                "sub_industry": str(row[COL_SUB_INDUSTRY] or "").strip(),
                "material_type": str(row[COL_MATERIAL_TYPE] or "文字").strip(),
                "expected_compliance": str(row[COL_COMPLIANCE] or "").strip(),  # 违规 / 合规
                "expected_risk": str(row[COL_RISK_LEVEL] or "").strip(),        # 高 / 中 / 低
                "ad_content": str(row[COL_AD_CONTENT] or "").strip(),
                "expected_review": str(row[COL_EXPECTED_RESULT] or "").strip(),
            })
        return cases
    finally:
        wb.close()


# ── API Client ────────────────────────────────────────────────────────────

def login() -> str:
    """登录并返回 JWT access_token。"""
    resp = requests.post(
        f"{API_BASE}/auth/login",
        json={"username": AUTH_USERNAME, "password": AUTH_PASSWORD},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def submit_material(token: str, case: dict[str, Any]) -> str:
    """提交物料，返回 material_id。"""
    resp = requests.post(
        f"{API_BASE}/materials/submit",
        json={
            "name": case["id"],
            "industry": case["industry"],
            "material_type": case["material_type"],
            "raw_text": case["ad_content"],
            "platforms": [],
        },
        headers=_auth_header(token),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def trigger_review(token: str, material_id: str) -> dict[str, Any]:
    """触发 AI 审查，返回审查结果 dict（含 ai_risk_score, ai_result）。"""
    resp = requests.post(
        f"{API_BASE}/reviews/ai-review",
        json={"material_id": material_id},
        headers=_auth_header(token),
        timeout=120,  # AI 审查可能较慢
    )
    resp.raise_for_status()
    return resp.json()


def get_review_result(token: str, material_id: str) -> dict[str, Any]:
    """通过 material_id 获取审查结果。"""
    resp = requests.get(
        f"{API_BASE}/reviews/by-material/{material_id}",
        headers=_auth_header(token),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ── Comparison Logic ──────────────────────────────────────────────────────

def classify_compliance(ai_result: dict) -> str:
    """从 AI 审查结果判定合规状态：违规 / 合规。"""
    ai_risk_score = ai_result.get("ai_risk_score", 100)
    engine_result = ai_result.get("ai_result", {})

    # 任一层有命中违规项即判违规
    for layer_key in ("layer1", "layer2", "layer3"):
        layer = engine_result.get(layer_key, {})
        if layer.get("matched_rules"):
            return "违规"

    if ai_risk_score < 80:
        return "违规"
    return "合规"


def classify_risk(ai_risk_score: int) -> str:
    """risk_score 映射到风险等级：高 / 中 / 低。"""
    if ai_risk_score < 50:
        return "高"
    elif ai_risk_score < 80:
        return "中"
    else:
        return "低"


def compare_result(case: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    """对比期望 vs 实际，返回带偏差标记的结果记录。"""
    expected_compliance = case["expected_compliance"]
    expected_risk = case["expected_risk"]
    actual_score = review.get("ai_risk_score", -1)
    actual_compliance = classify_compliance(review)
    actual_risk = classify_risk(actual_score)

    # 偏差判定
    compliance_ok = (expected_compliance == actual_compliance)
    risk_ok = (expected_risk == actual_risk)

    if not compliance_ok:
        deviation = "严重偏差"  # 二分类错误
    elif not risk_ok:
        deviation = "一般偏差"  # 分类对但风险等级错
    else:
        deviation = "通过"

    return {
        "id": case["id"],
        "industry": case["industry"],
        "ad_content": case["ad_content"][:100],
        "expected_compliance": expected_compliance,
        "actual_compliance": actual_compliance,
        "expected_risk": expected_risk,
        "actual_risk": actual_risk,
        "actual_score": actual_score,
        "deviation": deviation,
        "actual_summary": review.get("ai_result", {}).get("summary", "")[:200],
    }


# ── Test Runner ───────────────────────────────────────────────────────────

def run_all_cases(cases: list[dict[str, Any]], token: str) -> list[dict[str, Any]]:
    """逐条运行测试，返回结果列表。同时收集 material_id 用于清理。"""
    results: list[dict[str, Any]] = []
    material_ids: list[str] = []
    errors: list[str] = []

    for i, case in enumerate(cases):
        case_id = case["id"]
        print(f"[{i+1:02d}/{len(cases)}] {case_id} ...", end=" ", flush=True)
        try:
            mid = submit_material(token, case)
            material_ids.append(mid)

            review = trigger_review(token, mid)
            time.sleep(0.3)  # 避免请求过快

            result = compare_result(case, review)
            results.append(result)

            tag = "✓" if result["deviation"] == "通过" else "✗"
            print(f"{tag} score={result['actual_score']:3d}  {result['deviation']}")

        except requests.RequestException as e:
            print(f"ERROR: {e}")
            errors.append(f"{case_id}: {e}")
            results.append({
                "id": case_id,
                "industry": case.get("industry", ""),
                "ad_content": case.get("ad_content", "")[:100],
                "expected_compliance": case.get("expected_compliance", ""),
                "actual_compliance": "",
                "expected_risk": case.get("expected_risk", ""),
                "actual_risk": "",
                "actual_score": -1,
                "deviation": "API错误",
                "actual_summary": str(e)[:200],
            })

    # 将 material_ids 附加到第一条结果中（供 main() 中的 cleanup 使用）
    if results:
        results[0]["_material_ids"] = material_ids
        results[0]["_token"] = token
    if errors:
        print(f"\n{len(errors)} API 错误:")
        for e in errors:
            print(f"  · {e}")

    return results


def main() -> None:
    print("=" * 60)
    print("LexAd 测试物料批量验证")
    print(f"API: {API_BASE}")
    print(f"物料: {XLSX_PATH}")
    print("=" * 60)
    print()

    # 1. Read xlsx
    cases = read_test_cases()
    print(f"读取到 {len(cases)} 条测试用例\n")

    # 2. Login
    token = login()
    print(f"登录成功，token: {token[:20]}...\n")

    # 3. Run tests
    results = run_all_cases(cases, token)

    # 4. Generate report
    generate_report(results)

    # 5. Summary
    print_summary(results)


if __name__ == "__main__":
    main()
