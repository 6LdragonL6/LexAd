"""Security regression tests for v0.4.1."""

from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.deps import can_view_material
from app.api.v1.endpoints.knowledge import KNOWLEDGE_DIR, _resolve_knowledge_file
from app.models.material import Material, MaterialStatus
from app.models.user import User, UserRole
from app.storage import TEMP_ROOT, cleanup_temp, save_upload_temp


class FakeUpload:
    filename = "../../outside.txt"
    file = BytesIO("安全测试".encode("utf-8"))


def _user(user_id: str, role: UserRole) -> User:
    return User(
        id=user_id,
        username=f"user-{user_id}",
        password="not-used",
        display_name="测试用户",
        role=role,
        dept_name="测试部门",
    )


def _material(owner_id: str, status: MaterialStatus) -> Material:
    return Material(
        id="material-1",
        name="测试物料",
        submitter_id=owner_id,
        status=status,
    )


def test_upload_filename_cannot_escape_temp_directory():
    path = save_upload_temp(FakeUpload())
    try:
        assert path.is_file()
        assert path.parent.parent.resolve() == TEMP_ROOT.resolve()
        assert path.name != "outside.txt"
        assert ".." not in path.name
    finally:
        cleanup_temp(path)


def test_marketing_can_only_view_own_material():
    owner = _user("owner", UserRole.marketing)
    other = _user("other", UserRole.marketing)
    material = _material(owner.id, MaterialStatus.pending_legal)

    assert can_view_material(owner, material) is True
    assert can_view_material(other, material) is False


def test_legal_cannot_view_draft_but_can_view_pending_material():
    legal = _user("legal", UserRole.legal)

    assert can_view_material(legal, _material("owner", MaterialStatus.draft)) is False
    assert can_view_material(legal, _material("owner", MaterialStatus.pending_legal)) is True


def test_knowledge_path_rejects_traversal():
    with pytest.raises(HTTPException) as exc_info:
        _resolve_knowledge_file("../README.md")
    assert exc_info.value.status_code == 400


def test_knowledge_path_accepts_catalog_file():
    sample = next(KNOWLEDGE_DIR.joinpath("L1_laws").glob("*.txt"))
    relative = sample.relative_to(KNOWLEDGE_DIR).as_posix()
    assert _resolve_knowledge_file(relative) == sample.resolve()
