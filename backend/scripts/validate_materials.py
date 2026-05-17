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
