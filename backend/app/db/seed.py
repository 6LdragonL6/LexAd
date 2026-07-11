from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.models.brand import Brand, BrandStatus
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SEED_USERS = [
    ("admin", "admin123", "管理员", UserRole.admin, "管理员"),
    *[(f"market{i:02d}", "test1234", f"市场专员{i:02d}", UserRole.marketing, "市场部") for i in range(1, 11)],
    *[(f"legal{i:02d}", "test1234", f"法务专员{i:02d}", UserRole.legal, "法务部") for i in range(1, 11)],
]

DEMO_BRANDS = [
    {"name": "雀巢", "aliases": ["Nestlé", "Nestle"], "industry": "食品", "description": "全球知名食品饮料品牌"},
    {"name": "欧莱雅", "aliases": ["L'Oréal", "Loreal"], "industry": "美妆", "description": "全球化妆品品牌"},
    {"name": "华为", "aliases": ["Huawei", "HUAWEI"], "industry": "科技", "description": "全球ICT解决方案提供商"},
]


def seed_brands(db):
    admin = db.query(User).filter(User.role == UserRole.admin).first()
    if not admin:
        return

    for b in DEMO_BRANDS:
        existing = db.query(Brand).filter(Brand.name == b["name"]).first()
        if existing:
            continue
        brand = Brand(
            name=b["name"],
            aliases=b["aliases"],
            industry=b["industry"],
            description=b["description"],
            status=BrandStatus.active,
            created_by_id=admin.id,
        )
        db.add(brand)
    db.commit()


def seed():
    db = SessionLocal()
    existing = db.query(User).count()
    if existing > 0:
        print(f"Database already has {existing} users, skipping seed.")
        seed_brands(db)
        db.close()
        return

    for username, password, display_name, role, dept_name in SEED_USERS:
        user = User(
            username=username,
            password=pwd_context.hash(password),
            display_name=display_name,
            role=role,
            dept_name=dept_name,
        )
        db.add(user)
    db.commit()

    seed_brands(db)
    db.close()
    print(f"Seeded {len(SEED_USERS)} users and {len(DEMO_BRANDS)} brands.")

if __name__ == "__main__":
    seed()
