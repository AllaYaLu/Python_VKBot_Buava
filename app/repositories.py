from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from app.models import User
from app.core.users.constants import RolesEnum

class UserRepository:
    def __init__(self, database):
        self.database = database

    async def create_user_if_not_exists(self, user_id: int, is_waiter: bool = False) -> None:
        """Безопасная вставка пользователя"""
        role = RolesEnum.waiter if is_waiter else RolesEnum.customer
        async with self.database.session() as session:
            stmt = (
                insert(User)
                .values(vk_id=user_id, username=f"id{user_id}", role=role)
                .on_conflict_do_nothing(index_elements=['vk_id'])
            )
            await session.execute(stmt)

    async def get_waiter_user_ids(self) -> list[int]:
        """Получение списка ID всех официантов"""
        async with self.database.session() as session:
            query = select(User.vk_id).where(User.role == RolesEnum.waiter)
            result = await session.scalars(query)
            return list(result.all())

    async def get_user_role(self, user_id: int) -> RolesEnum:
        """Получение роли пользователя из БД"""
        async with self.database.session() as session:
            stmt = select(User).where(User.vk_id == user_id)
            result = await session.execute(stmt)
            db_user = result.scalar_one_or_none()
            return db_user.role if db_user else RolesEnum.customer
