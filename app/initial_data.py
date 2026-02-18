import asyncio
import logging

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.role import Role
from app.models.user import User
from app.core.security import get_password_hash
from sqlalchemy.future import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db() -> None:
    async with AsyncSessionLocal() as db:
        # Create roles
        roles = ["admin", "user"]
        for role_name in roles:
            result = await db.execute(select(Role).filter(Role.name == role_name))
            role = result.scalars().first()
            if not role:
                role = Role(name=role_name, description=f"{role_name} role")
                db.add(role)
                await db.commit()
                logger.info(f"Role {role_name} created")
        
        # Create superuser
        superuser_email = "admin@example.com"
        result = await db.execute(select(User).filter(User.email == superuser_email))
        user = result.scalars().first()
        if not user:
            # Get admin role
            result = await db.execute(select(Role).filter(Role.name == "admin"))
            admin_role = result.scalars().first()
            
            user = User(
                email=superuser_email,
                hashed_password=get_password_hash("password"),
                full_name="Super Admin",
                is_superuser=True,
                is_active=True,
                role_id=admin_role.id if admin_role else None
            )
            db.add(user)
            await db.commit()
            logger.info(f"Superuser {superuser_email} created")
        else:
            logger.info(f"Superuser {superuser_email} already exists")

if __name__ == "__main__":
    asyncio.run(init_db())
