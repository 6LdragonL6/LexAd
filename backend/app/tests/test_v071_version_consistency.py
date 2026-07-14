from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.brand import Brand
from app.models.material import Material, MaterialStatus
from app.models.user import User, UserRole
from app.schemas.material import MaterialResubmit
from app.schemas.review import ReviewOut
from app.services import material_service


def _db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_resubmit_preserves_display_name_brand_and_creates_snapshot():
    db = _db()
    try:
        user = User(id="u1", username="u1", password="x", display_name="市场", role=UserRole.marketing, dept_name="市场部")
        brand = Brand(id="b1", name="品牌一", created_by_id=user.id)
        material = Material(
            id="m1",
            name="首次名称",
            display_name="首次名称",
            raw_text="首次文案",
            industry="食品",
            platforms=["抖音"],
            submitter_id=user.id,
            brand_id=brand.id,
            status=MaterialStatus.returned,
        )
        db.add_all([user, brand, material])
        db.commit()

        review = material_service.create_resubmission(db, material, MaterialResubmit(
            name="第二次名称",
            raw_text="第二次修改后的文案",
            industry="食品、直播电商",
            platforms=["抖音"],
            material_type="文字",
            priority="normal",
        ))

        db.refresh(material)
        assert material.current_version == 2
        assert material.display_name == "首次名称"
        assert material.name == "第二次名称"
        assert material.brand_id == brand.id
        assert review.version == 2
        assert review.submission is not None
        assert review.submission.name == "第二次名称"
        assert review.submission.raw_text == "第二次修改后的文案"
        payload = ReviewOut.model_validate(review)
        assert payload.submission is not None
        assert payload.submission.raw_text == "第二次修改后的文案"
    finally:
        db.close()
