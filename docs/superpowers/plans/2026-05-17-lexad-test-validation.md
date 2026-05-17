# LexAd 测试物料批量验证 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a batch validation script that reads 65 test ad cases from xlsx, runs each through the LexAd API, compares AI review output against expected results, and cleans up all created records.

**Architecture:** Single Python script at `backend/scripts/validate_materials.py`. It acts as an HTTP client to the running FastAPI server for testing, and uses a direct DB session for cleanup. Reads xlsx via openpyxl, calls API via requests, generates console + CSV report.

**Tech Stack:** Python 3.11, openpyxl, requests, SQLAlchemy (for cleanup only)

---

### Task 1: Create script directory and skeleton

**Files:**
- Create: `backend/scripts/__init__.py`
- Create: `backend/scripts/validate_materials.py`

- [ ] **Step 1: Create scripts package init**

```bash
mkdir -p backend/scripts
```

- [ ] **Step 2: Write the skeleton with all imports, constants, and config**

Write `backend/scripts/__init__.py` (empty):

```python
```

Write `backend/scripts/validate_materials.py`:

```python
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
```

- [ ] **Step 3: Verify skeleton runs without import errors**

```bash
cd backend && python -c "import scripts.validate_materials; print('imports OK')"
```

Expected: `imports OK`

---

### Task 2: Implement xlsx reader

**Files:**
- Modify: `backend/scripts/validate_materials.py` — add `read_test_cases()`

- [ ] **Step 1: Add the read_test_cases function**

Insert after the `REPORT_PATH` line and before `def main()`:

```python
def read_test_cases() -> list[dict[str, Any]]:
    """读取 xlsx 测试物料，返回字典列表。"""
    wb = openpyxl.load_workbook(XLSX_PATH)
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
    wb.close()
    return cases
```

- [ ] **Step 2: Verify reads correct number of cases**

```bash
cd backend && python -c "
from scripts.validate_materials import read_test_cases
cases = read_test_cases()
print(f'Total cases: {len(cases)}')
print(f'First: {cases[0][\"id\"]} - {cases[0][\"expected_compliance\"]} / {cases[0][\"expected_risk\"]}')
print(f'Last: {cases[-1][\"id\"]} - {cases[-1][\"expected_compliance\"]} / {cases[-1][\"expected_risk\"]}')
"
```

Expected: `Total cases: 65`, T001 = 违规/高, T065 = 合规/低

---

### Task 3: Implement API client functions

**Files:**
- Modify: `backend/scripts/validate_materials.py` — add `login()`, `submit_material()`, `trigger_review()`, `get_review_result()`

- [ ] **Step 1: Add API client functions**

Insert after `read_test_cases()` and before `def main()`:

```python
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
```

- [ ] **Step 2: Verify login works (requires running server)**

Start the backend server in a separate terminal first:
```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then test:
```bash
cd backend && python -c "
from scripts.validate_materials import login, submit_material, trigger_review, read_test_cases
token = login()
print(f'Token obtained: {len(token)} chars')
cases = read_test_cases()
mid = submit_material(token, cases[0])
print(f'Material created: {mid}')
review = trigger_review(token, mid)
print(f'Review score: {review[\"ai_risk_score\"]}')
print(f'Summary: {review[\"ai_result\"][\"summary\"][:100]}')
"
```

Expected: Token obtained, material created, review score printed

---

### Task 4: Implement comparison logic

**Files:**
- Modify: `backend/scripts/validate_materials.py` — add `classify_compliance()`, `classify_risk()`, `compare_result()`

- [ ] **Step 1: Add comparison functions**

Insert after API client functions and before `def main()`:

```python
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
```

- [ ] **Step 2: Unit test comparison logic (no server needed)**

```bash
cd backend && python -c "
from scripts.validate_materials import classify_compliance, classify_risk, compare_result

# Test risk classification
assert classify_risk(30) == '高'
assert classify_risk(65) == '中'
assert classify_risk(90) == '低'
print('Risk classification: OK')

# Test compliance classification
violation_review = {'ai_risk_score': 30, 'ai_result': {'layer1': {'matched_rules': [{'rule_id': 'x'}]}}}
assert classify_compliance(violation_review) == '违规'
clean_review = {'ai_risk_score': 95, 'ai_result': {'layer1': {'matched_rules': []}, 'layer2': {'matched_rules': []}, 'layer3': {'matched_rules': []}}}
assert classify_compliance(clean_review) == '合规'
print('Compliance classification: OK')

# Test compare
case = {'id': 'T001', 'industry': '医疗健康', 'ad_content': 'test', 'expected_compliance': '违规', 'expected_risk': '高'}
result = compare_result(case, violation_review)
assert result['deviation'] == '通过'
print('Compare result: OK')
print('All comparison tests passed')
"
```

Expected: All assertions pass

---

### Task 5: Implement the test runner loop with cleanup tracking

**Files:**
- Modify: `backend/scripts/validate_materials.py` — add `run_all_cases()`

- [ ] **Step 1: Add the runner function**

Insert after comparison functions and before `def main()`:

```python
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

    # 将 material_ids 附加到第一条结果中（hack，供 cleanup 使用）
    if results:
        results[0]["_material_ids"] = material_ids
        results[0]["_token"] = token
    if errors:
        print(f"\n{len(errors)} API 错误:")
        for e in errors:
            print(f"  · {e}")

    return results
```

- [ ] **Step 2: Verify the runner compiles**

```bash
cd backend && python -c "from scripts.validate_materials import run_all_cases; print('OK')"
```

Expected: `OK`

---

### Task 6: Implement cleanup

**Files:**
- Modify: `backend/scripts/validate_materials.py` — add `cleanup()`

- [ ] **Step 1: Add cleanup function**

Insert after `run_all_cases()` and before `def main()`:

```python
# ── Cleanup ───────────────────────────────────────────────────────────────

def cleanup(material_ids: list[str]) -> None:
    """通过数据库直接删除测试创建的物料和关联审查记录。"""
    if not material_ids:
        print("无需清理（无物料创建）")
        return

    # 需要确保从 backend/ 目录运行，.env 才能被正确加载
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from app.db.session import SessionLocal
    from app.models.material import Material
    from app.models.review import Review

    db = SessionLocal()
    try:
        # 先删 Review（外键依赖），再删 Material
        review_deleted = (
            db.query(Review)
            .filter(Review.material_id.in_(material_ids))
            .delete(synchronize_session="fetch")
        )
        material_deleted = (
            db.query(Material)
            .filter(Material.id.in_(material_ids))
            .delete(synchronize_session="fetch")
        )
        db.commit()
        print(f"清理完成：删除 {review_deleted} 条 Review，{material_deleted} 条 Material")
    except Exception as e:
        db.rollback()
        print(f"清理失败: {e}")
        print(f"请手动删除以下 material_id:")
        for mid in material_ids:
            print(f"  {mid}")
    finally:
        db.close()
```

- [ ] **Step 2: Verify cleanup imports work**

```bash
cd backend && python -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('scripts/validate_materials.py').resolve().parent.parent))
from app.db.session import SessionLocal
from app.models.material import Material
from app.models.review import Review
print('Cleanup imports OK')
"
```

Expected: `Cleanup imports OK`

---

### Task 7: Implement report generation and wire up main()

**Files:**
- Modify: `backend/scripts/validate_materials.py` — add `generate_report()`, `print_summary()`, update `main()`

- [ ] **Step 1: Add report functions**

Insert after `cleanup()` and before `def main()`:

```python
# ── Report ────────────────────────────────────────────────────────────────

def generate_report(results: list[dict[str, Any]]) -> None:
    """输出 CSV 详细报告。"""
    fieldnames = [
        "id", "industry", "ad_content",
        "expected_compliance", "actual_compliance",
        "expected_risk", "actual_risk", "actual_score",
        "deviation", "actual_summary",
    ]
    with open(REPORT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    print(f"\n详细报告已保存至: {REPORT_PATH}")


def print_summary(results: list[dict[str, Any]]) -> None:
    """打印终端汇总。"""
    total = len(results)
    passed = sum(1 for r in results if r["deviation"] == "通过")
    critical = sum(1 for r in results if r["deviation"] == "严重偏差")
    minor = sum(1 for r in results if r["deviation"] == "一般偏差")
    errors = sum(1 for r in results if r["deviation"] == "API错误")

    compliance_correct = sum(
        1 for r in results
        if r["expected_compliance"] == r["actual_compliance"]
    )
    risk_correct = sum(
        1 for r in results
        if r["expected_risk"] == r["actual_risk"]
    )

    print()
    print("=" * 60)
    print("验证汇总")
    print("=" * 60)
    print(f"总用例数:     {total}")
    print(f"通过:         {passed}  ({passed/max(total,1)*100:.1f}%)")
    print(f"严重偏差:     {critical}  ({critical/max(total,1)*100:.1f}%)")
    print(f"一般偏差:     {minor}  ({minor/max(total,1)*100:.1f}%)")
    print(f"API错误:      {errors}")
    print(f"---")
    print(f"二分类准确率: {compliance_correct}/{total} = {compliance_correct/max(total,1)*100:.1f}%")
    print(f"风险等级准确率: {risk_correct}/{total} = {risk_correct/max(total,1)*100:.1f}%")
    print("=" * 60)

    if critical > 0:
        print("\n严重偏差案例（二分类错误）:")
        for r in results:
            if r["deviation"] == "严重偏差":
                print(f"  · {r['id']} 期望={r['expected_compliance']} 实际={r['actual_compliance']} score={r['actual_score']}")
```

- [ ] **Step 2: Update main() to wire everything together**

Replace the existing `main()` function:

```python
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
    try:
        token = login()
        print(f"登录成功 (账户: {AUTH_USERNAME})\n")
    except requests.RequestException as e:
        print(f"登录失败: {e}")
        print("请确认后端服务已启动: uvicorn app.main:app --port 8000")
        sys.exit(1)

    # 3. Run tests (cleanup is guaranteed in finally)
    material_ids: list[str] = []
    try:
        results = run_all_cases(cases, token)
        # Extract material_ids from results hack
        if results and "_material_ids" in results[0]:
            material_ids = results[0].pop("_material_ids")
            results[0].pop("_token", None)
    finally:
        # 4. Cleanup — always runs
        print()
        cleanup(material_ids)

    # 5. Report
    generate_report(results)
    print_summary(results)
```

- [ ] **Step 3: Verify full script compiles and --help-like dry run works**

```bash
cd backend && python -c "
from scripts.validate_materials import read_test_cases, login, classify_compliance, classify_risk, compare_result, cleanup, generate_report, print_summary
print('All imports OK')
cases = read_test_cases()
print(f'{len(cases)} cases loaded')
"
```

Expected: `All imports OK` and `65 cases loaded`

---

### Task 8: Full test run

**Files:**
- No changes — verification only

- [ ] **Step 1: Ensure backend server is running**

In a separate terminal:
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: Run the full validation script**

```bash
cd backend && python scripts/validate_materials.py
```

- [ ] **Step 3: Verify output**

Expected:
- All 65 cases processed
- Summary shows accuracy percentages
- CSV report generated at `backend/scripts/validation_report.csv`
- Cleanup confirmation printed (`删除 N 条 Review，N 条 Material`)
- No records remain in DB for the test materials

- [ ] **Step 4: Verify DB is clean**

```bash
cd backend && python -c "
from app.db.session import SessionLocal
from app.models.material import Material
db = SessionLocal()
count = db.query(Material).filter(Material.name.like('T%')).count()
print(f'Remaining test materials: {count}')
db.close()
"
```

Expected: `Remaining test materials: 0`

- [ ] **Step 5: Commit**

```bash
cd D:/LDragonl/Documents/GitHub/LexAd
git add backend/scripts/__init__.py backend/scripts/validate_materials.py docs/superpowers/plans/2026-05-17-lexad-test-validation.md docs/superpowers/specs/2026-05-17-lexad-test-validation-design.md
git commit -m "feat: add batch validation script for test materials accuracy check"
```
