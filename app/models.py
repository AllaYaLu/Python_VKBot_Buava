from sqlalchemy import BigInteger, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from app.core.users.constants import RolesEnum

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    vk_id: Mapped[int] = mapped_column("vk_id", BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[RolesEnum] = mapped_column(String(20), default=RolesEnum.customer, nullable=False)
