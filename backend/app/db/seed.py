from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.models.brand import Brand, BrandStatus
from app.services.knowledge_bootstrap import bootstrap_builtin_knowledge
from app.core.config import get_settings
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()

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
    users = _seed_user_specs()
    if not users:
        db.close()
        print("Production demo seed is disabled; skipping user and knowledge seed.")
        return

    if settings.APP_ENV != "production":
        existing = db.query(User).count()
        if existing > 0:
            print(f"Database already has {existing} users, skipping seed.")
            seed_brands(db)
            summary = bootstrap_builtin_knowledge(db)
            db.close()
            print(f"Builtin knowledge baseline: {summary}")
            return

    created = 0
    updated = 0
    for username, password, display_name, role, dept_name in users:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            db.add(
                User(
                    username=username,
                    password=pwd_context.hash(password),
                    display_name=display_name,
                    role=role,
                    dept_name=dept_name,
                )
            )
            created += 1
        elif settings.APP_ENV == "production":
            # Render 环境变量是竞赛账号凭据的唯一来源，每次部署都恢复预期角色和密码。
            user.password = pwd_context.hash(password)
            user.display_name = display_name
            user.role = role
            user.dept_name = dept_name
            user.is_active = True
            updated += 1
    db.commit()

    seed_brands(db)
    summary = bootstrap_builtin_knowledge(db)
    db.close()
    print(
        f"Seeded users created={created} updated={updated}; "
        f"brands={len(DEMO_BRANDS)}. Builtin knowledge baseline: {summary}"
    )


def _seed_user_specs():
    if settings.APP_ENV != "production":
        return SEED_USERS
    if not settings.DEMO_SEED_ENABLED:
        return []
    return [
        (
            "admin",
            settings.DEMO_ADMIN_PASSWORD.get_secret_value(),
            "管理员",
            UserRole.admin,
            "管理员",
        ),
        (
            "market01",
            settings.DEMO_MARKETING_PASSWORD.get_secret_value(),
            "市场演示账号",
            UserRole.marketing,
            "市场部",
        ),
        (
            "legal01",
            settings.DEMO_LEGAL_PASSWORD.get_secret_value(),
            "法务演示账号",
            UserRole.legal,
            "法务部",
        ),
    ]

if __name__ == "__main__":
    seed()
