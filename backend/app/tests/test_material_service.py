from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.material import Material, MaterialStatus
from app.models.user import User, UserRole
from app.services import material_service


def _session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def test_marketing_material_list_hides_archived_materials():
    factory = _session_factory()
    db = factory()
    try:
        user = User(
            id="market-1",
            username="market-1",
            password="not-used",
            display_name="市场用户",
            role=UserRole.marketing,
            dept_name="市场部",
        )
        active = Material(
            id="active-material",
            name="待修改物料",
            submitter_id=user.id,
            status=MaterialStatus.returned,
        )
        archived = Material(
            id="archived-material",
            name="已归档物料",
            submitter_id=user.id,
            status=MaterialStatus.archived,
        )
        db.add_all([user, active, archived])
        db.commit()

        materials = material_service.list_materials(db, user)

        assert [material.id for material in materials] == ["active-material"]
    finally:
        db.close()
