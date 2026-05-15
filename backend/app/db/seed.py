from app.db.session import SessionLocal
from app.models.user import User, UserRole
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SEED_USERS = [
    ("admin", "admin123", "管理员", UserRole.admin, "管理员"),
    *[(f"market{i:02d}", "test1234", f"市场专员{i:02d}", UserRole.marketing, "市场部") for i in range(1, 11)],
    *[(f"legal{i:02d}", "test1234", f"法务专员{i:02d}", UserRole.legal, "法务部") for i in range(1, 11)],
]

def seed():
    db = SessionLocal()
    existing = db.query(User).count()
    if existing > 0:
        print(f"Database already has {existing} users, skipping seed.")
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
    db.close()
    print(f"Seeded {len(SEED_USERS)} users.")

if __name__ == "__main__":
    seed()
