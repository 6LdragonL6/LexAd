from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.brand import Brand, BrandIndustry, BrandIndustrySuggestion, BrandIndustrySuggestionStatus
from app.models.material import Material
from app.models.user import User, UserRole
from app.services import brand_service
from app.schemas.brand import BrandOut


def test_brand_industry_suggestion_accumulates_and_can_be_accepted():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        admin = User(id="admin", username="admin", password="x", display_name="管理员", role=UserRole.admin, dept_name="管理部")
        brand = Brand(id="brand", name="多行业品牌", created_by_id=admin.id)
        material = Material(
            id="material",
            name="物料",
            display_name="物料",
            industry="食品、直播电商",
            submitter_id=admin.id,
            brand_id=brand.id,
        )
        db.add_all([admin, brand, material])
        db.commit()

        brand_service.record_material_industries(db, material)
        brand_service.record_material_industries(db, material)
        db.commit()

        suggestions = db.query(BrandIndustrySuggestion).order_by(BrandIndustrySuggestion.industry).all()
        assert [item.industry for item in suggestions] == ["直播电商", "食品"]
        assert {item.occurrence_count for item in suggestions} == {2}

        target = suggestions[0]
        brand_service.review_industry_suggestion(db, brand.id, target.id, "accept", admin.id)
        assert db.query(BrandIndustry).filter_by(brand_id=brand.id, industry=target.industry).one()
        assert target.status == BrandIndustrySuggestionStatus.accepted
        db.expire(brand, ["industry_links"])
        assert BrandOut.model_validate(brand).industries == [target.industry]
    finally:
        db.close()
