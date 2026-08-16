from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from services.auth.app.db_models.user import User

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: str) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, email: str, hashed_password: str, role: str = "user") -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            role=role,
            is_active=True
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user
